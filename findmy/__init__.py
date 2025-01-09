#!/usr/bin/python3

# .                                       .           .                   .
# |                                 o     |           |        ,- o       |
# |-. ,-. ;-.-. ,-. --- ,-: ,-. ,-. . ,-. |-  ,-: ;-. |-  ---  |  . ;-. ,-| ;-.-. . .
# | | | | | | | |-'     | | `-. `-. | `-. |   | | | | |        |- | | | | | | | | | |
# ' ' `-' ' ' ' `-'     `-` `-' `-' ' `-' `-' `-` ' ' `-'      |  ' ' ' `-' ' ' ' `-|
#                                                             -'                  `-'
# made with ♡ by muehlt
# github.com/muehlt
# version 1.1.1
#
# DESCRIPTION:  This python script reads the FindMy cache files and publishes the location
#               data to MQTT to be used in Home Assistant. It uses auto discovery so no
#               further entity configuration is needed in Home Assistant. Consult the
#               documentation on how to set up an MQTT broker for Home Assistant. The script
#               needs to be executed on macOS with a running FindMy installation. It needs
#               to be executed as root and in a terminal with full disk access to be able
#               to read the cache files. The script must be configured using the variables
#               below and the mqtt client password as environment variable.
#
# DISCLAIMER:   This script is provided as-is, without any warranty. Use at your own risk.
#               This code is not tested and should only be used for experimental purposes.
#               Loading the FindMy cache files is not inteded by Apple and might cause problems.
#
# LICENSE:      See the LICENSE.md file of the original authors' repository
#               (https://github.com/muehlt/home-assistant-findmy).

from datetime import datetime
import math
import re
import time
import click
import paho.mqtt.client as mqtt
import os
import json
from unidecode import unidecode
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

load_dotenv()

DEFAULT_TOLERANCE = 70  # meters
PAYLOAD_RESET = 'reset'

(mqtt_broker_ip,
 mqtt_broker_port,
 mqtt_client_username,
 mqtt_client_password,
 findmy_file_scan_interval,
 is_manual_known_locations) = (None,) * 6

cache_file_location = os.path.expanduser('~') + '/Library/Caches/com.apple.findmy.fmipcore/'
cache_file_location_items = cache_file_location + 'Items.data'
cache_file_location_devices = cache_file_location + 'Devices.data'

known_locations = {}
device_updates = {}

client = mqtt.Client("ha-findmy")

def connect_broker():
    client.username_pw_set(mqtt_client_username, mqtt_client_password)
    client.connect(host=mqtt_broker_ip, port=mqtt_broker_port)
    client.loop_start()


def get_time(timestamp):
    if (type(timestamp) is not int):
        return "unknown"
    return str(datetime.fromtimestamp(timestamp / 1000))


def get_lat_lng_approx(meters):
    return meters / 111111


def load_data(data_file):
    with open(data_file, 'r') as f:
        data = json.load(f)
        f.close()
        return data


def get_device_id(name):
    sub = re.sub('[^0-9a-zA-Z_]+', '', unidecode(re.sub(r'[\s-]', '_', name).lower()))
    return f"findmy_{sub}"


def get_source_type(apple_position_type):
    switcher = {
        "crowdsourced": "gps",  # ble only used for stationary ble trackers
        "safeLocation": "gps",
        "Wifi": "router"
    }
    return switcher.get(apple_position_type, "gps")


def get_location_name(pos):
    for name, location in known_locations.items():
        tolerance = get_lat_lng_approx(location['tolerance'] or DEFAULT_TOLERANCE)
        if (math.isclose(location['latitude'], pos[0], abs_tol=tolerance) and
                math.isclose(location['longitude'], pos[1], abs_tol=tolerance)):
            return name
    return "not_home"

def getManufacturer(device):
    manufacturer = device.get('productType',{}).get('productInformation',{}).get('manufacturerName')
    if manufacturer is not None:
        return manufacturer
    return "Apple"

def getModel(device, manufacturer):
    model = device.get("deviceDisplayName")
    if model is not None:
        return model
    if manufacturer == 'Apple':
        return 'AirTag'
    model = device.get('productType',{}).get('productInformation',{}).get('modelName')
    if model == "":
        return None
    return model

def send_mqtt_data(force_sync, device):
    device_name = device['name']
    battery_status = device['batteryStatus']
    battery_level = device.get('batteryLevel')
    source_type = get_source_type(device.get('location').get('positionType') if device.get('location') else None)
    manufacturer = getManufacturer(device)
    model = getModel(device, manufacturer)

    location_name = address = latitude = longitude = accuracy = last_update = "unknown"
    if device['location'] is not None:
        latitude = device['location']['latitude']
        longitude = device['location']['longitude']
        address = device['address']
        accuracy = math.sqrt(
            device['location']['horizontalAccuracy'] ** 2 + device['location']['verticalAccuracy'] ** 2)
        location_name = get_location_name((latitude, longitude))
        last_update = device['location']['timeStamp']

    device_update = device_updates.get(device_name)
    if not force_sync and device_update and len(device_update) > 0 and device_update[0] == last_update:
        return

    device_id = get_device_id(device_name)
    device_updates[device_name] = (last_update, location_name, device_id)

    device_topic = f"homeassistant/device_tracker/{device_id}/"

    device_config = {
        "unique_id": f"{device_id} {device_name}",
        "state_topic": device_topic + "state",
        "json_attributes_topic": device_topic + "attributes",
        "device": {
            "identifiers": device_id,
            "manufacturer": manufacturer,
            "name": f"FindMy {device_name}",
        },
        "source_type": source_type,
    }
    if is_manual_known_locations:
        device_config["payload_home"] = "home"
        device_config["payload_not_home"] = "not_home"
    else:
        device_config["payload_reset"] = PAYLOAD_RESET

    device_attributes = {
        "latitude": latitude,
        "longitude": longitude,
        "gps_accuracy": accuracy,
        "address": address,
        "batteryStatus": battery_status,
        "last_update_timestamp": last_update,
        "last_update": get_time(last_update),
        "provider": "FindMy (ofirsnb/home-assistant-findmy) v1.1.1"
    }
    if battery_level:
        device_attributes["battery_level"] = battery_level
    if model:
        device_config["device"]["model"] = model

    client.publish(device_topic + "config", json.dumps(device_config), retain=True)
    client.publish(device_topic + "attributes", json.dumps(device_attributes), retain=True)
    client.publish(device_topic + "state", location_name if is_manual_known_locations else PAYLOAD_RESET, retain=True)


def send_data_items(force_sync):
    for device in load_data(cache_file_location_items):
        send_mqtt_data(force_sync, device)


def send_data_devices(force_sync):
    for device in load_data(cache_file_location_devices):
        send_mqtt_data(force_sync, device)


def scan_cache(privacy, force_sync):
    console = Console()
    with console.status(
            f"[bold green]Synchronizing {len(device_updates)} devices and {len(known_locations)} known locations") as status:
        while True:
            send_data_items(force_sync)
            send_data_devices(force_sync)

            os.system('clear')

            if not privacy:
                device_table = Table()
                device_table.add_column("Device")
                device_table.add_column("Device ID", overflow='fold')
                device_table.add_column("Last Update")
                device_table.add_column("Location")
                for device, details in sorted(device_updates.items(), key=lambda x: get_time(x[1][0])):
                    location = details[1] if (is_manual_known_locations or details[1] == 'unknown') else 'HA Zone based'
                    device_table.add_row(device, details[2], get_time(details[0]), location)
                console.print(device_table)

            status.update(
                f"[bold green]Synchronizing {len(device_updates)} devices and {len(known_locations)} known locations")

            time.sleep(findmy_file_scan_interval)


def validate_param_locations(_, __, path):
    if path is None:
        return path, {}

    if not os.path.isfile(path):
        raise click.BadParameter('The provided path is not a file.')

    with open(path, 'r') as f:
        try:
            locations = json.load(f)
        except json.JSONDecodeError:
            raise click.BadParameter('The provided file does not contain valid JSON data.')

    if not isinstance(locations, dict):
        raise click.BadParameter('The provided file does not contain a valid JSON object.')

    for name, location in locations.items():
        if not isinstance(name, str):
            raise click.BadParameter(f'The location name "{name}" is not a string.')
        if not isinstance(location, dict):
            raise click.BadParameter(f'The location "{name}" is not a valid JSON object.')
        if not isinstance(location.get('latitude'), float):
            raise click.BadParameter(f'The location "{name}" does not contain a valid latitude.')
        if not isinstance(location.get('longitude'), float):
            raise click.BadParameter(f'The location "{name}" does not contain a valid longitude.')
        if not isinstance(location.get('tolerance'), int):
            raise click.BadParameter(f'The location "{name}" does not contain a valid tolerance in meters.')

    return path, locations


def set_known_locations(locations):
    global known_locations, is_manual_known_locations
    _path, _known_locations = locations
    known_locations = _known_locations
    is_manual_known_locations = bool(len(known_locations))


@click.command("home-assistant-findmy", no_args_is_help=False)
@click.option('--locations', '-l',
              type=click.Path(),
              callback=validate_param_locations,
              help='Path to the known locations JSON configuration file')
@click.option('--privacy', '-p',
              is_flag=True,
              help='Hides specific device data from the console output')
@click.option('--force-sync', '-f',
              is_flag=True,
              help='Disables the timestamp check and provides and update every FINDMY_FILE_SCAN_INTERVAL seconds')
@click.option('--ip',
              envvar='MQTT_BROKER_IP',
              required=True,
              help="IP of the MQTT broker.")
@click.option('--port',
              envvar='MQTT_BROKER_PORT',
              default=1883, type=int,
              help="Port of the MQTT broker.")
@click.option('--username',
              envvar='MQTT_CLIENT_USERNAME',
              required=True,
              help="MQTT client username.")
@click.option('--password',
              envvar='MQTT_CLIENT_PASSWORD',
              required=True,
              help="[WARNING] Set this via environment variable! MQTT client password.")
@click.option('--scan-interval',
              envvar='FINDMY_FILE_SCAN_INTERVAL',
              default=5,
              type=int,
              help="File scan interval in seconds.")
def main(locations, privacy, force_sync, ip, port, username, password, scan_interval):
    global mqtt_broker_ip, mqtt_broker_port, mqtt_client_username, mqtt_client_password, findmy_file_scan_interval

    mqtt_broker_ip = ip
    mqtt_broker_port = port
    mqtt_client_username = username
    mqtt_client_password = password
    findmy_file_scan_interval = scan_interval

    connect_broker()
    set_known_locations(locations)
    scan_cache(privacy, force_sync)


if __name__ == '__main__':
    main()
