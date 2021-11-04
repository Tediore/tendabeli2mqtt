import os
import sys
import json
import logging
import requests
from time import sleep
from threading import Thread as t
import paho.mqtt.client as mqtt_client

MQTT_HOST = os.getenv('MQTT_HOST')
MQTT_PORT = int(os.getenv('MQTT_PORT', 1883))
MQTT_USER = os.getenv('MQTT_USER')
MQTT_PASSWORD = os.getenv('MQTT_PASSWORD')
MQTT_QOS = int(os.getenv('MQTT_QOS', 1))
BASE_TOPIC = os.getenv('BASE_TOPIC', 'tendabeli2mqtt')
HOME_ASSISTANT = os.getenv('HOME_ASSISTANT', True)
DEVICE_IPS = os.getenv('DEVICE_IPS')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()

client = mqtt_client.Client(BASE_TOPIC)

def mqtt_connect():
    """Connect to MQTT broker and set LWT"""
    try:
        client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
        client.will_set(f'{BASE_TOPIC}/status', 'offline', 1, True)
        client.on_connect = on_connect
        client.on_message = on_message
        client.connect(MQTT_HOST, MQTT_PORT)
        client.publish(f'{BASE_TOPIC}/status', 'online', 1, True)
    except Exception as e:
        logging.error(f'Unable to connect to MQTT broker: {e}')
        sys.exit()

def on_connect(client, userdata, flags, rc):
    # The callback for when the client receives a CONNACK response from the MQTT broker.
    logging.info('Connected to MQTT broker with result code ' + str(rc))
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe(f'{BASE_TOPIC}/#')
    # mqtt_discovery()

def on_message(client, userdata, msg):
    """Listen for MQTT payloads and forward to Tenda device"""
    payload = msg.payload.decode('utf-8')
    topic = str(msg.topic)
    commands = {'off': 0, 'on': 1, 'toggle': 'toggle'}
    device_mac = topic[topic.find(f'set_state')+10:].lower()
    if 'set_state' in topic:
        if payload == 'toggle':
            d.get_state(device_mac)
            command = 1 if int(d.get_state(device_mac)) == 0 else 0
        else:
            command = commands[payload]
        d.set_state(device_mac, command)
    # elif 'get_state' in topic:
    #     d.set_zone_enable(switch_no, payload)

class Devices:
    def __init__(self):
        self.device_ips = DEVICE_IPS.split(',')
        self.devices = {}
        self.timeout = 3

    def get_device_info(self):
        """Get information about Tenda Beli device(s)"""
        for ip in self.device_ips:
            url = requests.get(f'http://{ip}:5000/getDetail', timeout=self.timeout)
            info = json.loads(url.text)
            mac = info['data']['mac'].replace(':','')
            self.devices[mac] = {}
            self.devices[mac]['ip_addr'] = ip
            for item in ['sn', 'model']:
                self.devices[mac][item] = info['data'][item]
        
        print(self.devices)

    def set_state(self, device_mac, state):
        try:
            print(f'http://{self.devices[device_mac]["ip_addr"]}:5000/setSta')
            requests.post(f'http://{self.devices[device_mac]["ip_addr"]}:5000/setSta', data=json.dumps({"status":state}), timeout=self.timeout, headers={'content-type': 'application/json'})
        except Exception as e:
            logging.error(f'{e}')
        d.get_state(device_mac)

    def get_state(self, device_mac):
        url = requests.get(f'http://{self.devices[device_mac]["ip_addr"]}:5000/getSta')
        state_text = json.loads(url.text)
        return state_text['data']['status']

if MQTT_HOST == None:
    logging.error('Please specify the IP address or hostname of your MQTT broker.')
    sys.exit()

if LOG_LEVEL.lower() not in ['debug', 'info', 'warning', 'error']:
    logging.basicConfig(level='INFO', format='%(asctime)s %(levelname)s: %(message)s')
    logging.warning(f'Selected log level "{LOG_LEVEL}" is not valid; using default')
else:
    logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s %(levelname)s: %(message)s')

d = Devices()

mqtt_connect()
d.get_device_info()
client.loop_forever()