# home-assistant-findmy
A python script that reads local FindMy cache files to publish device locations and metadata (including those of AirTags, AirPods, Apple Watches, iPhones) to Home Assistant via MQTT.

> [!IMPORTANT]
> It doesn't work on macOS versions Sonoma 14.4 / Ventura 13.6.5 / Monterey 12.7.5 and above due to encryption by Apple per CVE-2024-23229.

[Migration to v1.0.2](https://github.com/muehlt/home-assistant-findmy/tree/main/.github/MIGRATION_GUIDE/1.0.2.md) • 
[Support this project](https://buymeacoffee.com/muehlt)


## Disclaimer

This script is provided as-is, without any warranty. Use at your own risk.
This code is not tested and should only be used for experimental purposes.
Loading the FindMy cache files is not intended by Apple and might cause problems.
The project is not affiliated to Apple Inc., Home Assistant or MQTT.

## Description

This python script reads the FindMy cache files and publishes the location 
data to MQTT to be used in Home Assistant. It uses auto discovery so no 
further entity configuration is needed in Home Assistant. Consult the 
documentation on how to set up an MQTT broker for Home Assistant. The script
needs to be executed on macOS with a running FindMy installation. It must 
be executed as root and in a terminal with full disk access to be able 
to read the cache files.

## Supports
- Devices (iPhones, iPads, MacBooks, AirPods, Apple Watches, ...)
    - including family devices
- Objects (AirTags, ...)

## How to use

### Docker
1. Ensure that Docker instance (Desktop/Engine) has full disk access through the System's Settings.
2. Configure .env
3. Run `docker compose up`.

## Versions

### 1.1.1
- rename mqtt client to more descriptive.  improved `model`.  **[@ofirsnb](https://github.com/ofirsnb)**

### 1.1.0
- added `findmy_` prefix to entity id.   added `manufacturer` and `model`.  Additional Minor Improvements.  **[@ofirsnb](https://github.com/ofirsnb)**

### 1.0.3
- Removed the requirement of `known_locations.json`.   In case not passed,  HomeAssistant will use HA Zones to determine the locations. **[@ofirsnb](https://github.com/ofirsnb)**

### 1.0.X - Breaking changes
- Configuration is now done solely via environment variables and a JSON file for known locations
- Installation using pip is now possible
- Device data is only updated if the location timestamp changed in FindMy (skip with `-f` flag)
- Improved terminal output
- Minor improvements

### 0.0.2
- Adjusted device names to fit [recent MQTT changes](https://community.home-assistant.io/t/psa-mqtt-name-changes-in-2023-8/598099) ([PR](https://github.com/muehlt/home-assistant-findmy/pull/4))

### 0.0.1
- Initial version

## License

See [LICENSE.md](https://github.com/muehlt/home-assistant-findmy/blob/main/LICENSE.md)

## Roadmap

- Support DeviceGroups
- Write comprehensive tests

Could I help you? [You can buy me a coffee here if you want 🙏](https://buymeacoffee.com/muehlt)
