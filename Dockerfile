FROM python:3-alpine

ADD tendabeli2mqtt.py /

RUN pip install paho.mqtt requests

CMD [ "python", "./tendabeli2mqtt.py" ]