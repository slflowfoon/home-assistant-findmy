FROM python:3.9.7-bullseye

COPY ./requirements.txt ./requirements.txt

RUN pip install -r requirements.txt

COPY ./findmy/ ./

CMD [ "python", "__init__.py" ]
