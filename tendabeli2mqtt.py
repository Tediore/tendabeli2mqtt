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
# HOME_ASSISTANT = os.getenv('HOME_ASSISTANT', True)
DEVICE_IPS = os.getenv('DEVICE_IPS')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()

HOME_ASSISTANT = True

client = mqtt_client.Client(BASE_TOPIC)

class Devices:
    def __init__(self):
        self.device_ips = DEVICE_IPS.split(',')
        self.devices = {}
        self.timeout = 3
        self.states = ['off', 'on']

    def get_device_info(self):
        """Get information about Tenda Beli device(s)"""
        for ip in self.device_ips:
            try:
                url = requests.get(f'http://{ip}:5000/getDetail', timeout=self.timeout)
                info = json.loads(url.text)
                mac = info['data']['mac'].replace(':','')
                self.devices[mac] = {}
                self.devices[mac]['ip_addr'] = ip
                self.devices[mac]['retry_count'] = 0
                for item in info['data']:
                    self.devices[mac][item] = info['data'][item]

            except Exception as e:
                logging.warning(f'Tenda device not found at {ip}; ignoring.')
        
    def set_state(self, device_mac, state):
        try:
            requests.post(f'http://{self.devices[device_mac]["ip_addr"]}:5000/setSta', data=json.dumps({"status":state}), timeout=self.timeout, headers={'content-type': 'application/json'})

        except Exception as e:
            logging.error(f'Set state for Tenda device at {self.devices[device_mac]["ip_addr"]} failed: {e}')

        d.get_state(device_mac)

    def get_state(self, device_mac):
        base_url = f'http://{self.devices[device_mac]["ip_addr"]}:5000'
        try:
            state_url = requests.get(f'{base_url}/getSta', timeout=self.timeout)
            rssi_url = requests.get(f'{base_url}/getDetail', timeout=self.timeout)
            state_text = json.loads(state_url.text)
            rssi_text = json.loads(rssi_url.text)
            state = state_text['data']['status']
            rssi = rssi_text['data']['rssi']
            ip_addr = self.devices[device_mac]["ip_addr"]
            if self.devices[device_mac]['retry_count'] > 0:
                logging.info(f'Reconnected to Tenda device at {ip_addr}')
                self.devices[device_mac]['retry_count'] = 0
            client.publish(f'{BASE_TOPIC}/{device_mac}/state', self.states[state], MQTT_QOS)
            client.publish(f'{BASE_TOPIC}/{device_mac}/rssi', rssi, MQTT_QOS)

        except Exception as e:
            if self.devices[device_mac]['retry_count'] < 3:
                logging.error(f'Unable to communicate with Tenda device at {ip_addr}: {e}')
            self.devices[device_mac]['retry_count'] += 1
            if self.devices[device_mac]['retry_count'] > 2:
                client.publish(f'{BASE_TOPIC}/{device_mac}/status', 'offline', MQTT_QOS, True)
                if self.devices[device_mac]['retry_count'] < 4:
                    logging.warning('Tenda device unreachable; marking as offline.')
                    logging.warning('Trying to reconnect every 10 sec in the background...')

        if self.devices[device_mac]['retry_count'] < 1:
            return state

    def poll_device(self):
        """Poll for Tenda device information every 10 seconds in case button is pressed on device"""
        while True:
            sleep(10)
            for device in d.devices:
                d.get_state(device)

    def mqtt_discovery(self):
        """Send Home Assistant MQTT discovery payloads"""
        if HOME_ASSISTANT:
            ha_switch = 'homeassistant/switch/'
            ha_sensor = 'homeassistant/sensor/'
            try:
                for device_mac in self.devices:
                    device_info = self.devices[device_mac]
                    name = device_info['nick']
                    mac = device_info['mac'].replace(':','')
                    serial_no = device_info['sn']
                    model = device_info['model']
                    fw_ver = device_info['sft_ver']

                    # switch payload
                    client.publish(f'{ha_switch}{device_mac}/config',json.dumps({
                        'availability': [
                            {'topic': f'{BASE_TOPIC}/status'},
                            {'topic': f'{BASE_TOPIC}/{device_mac}/status'}
                            ], 
                        'name': f'{name} switch', 
                        'command_topic': f'{BASE_TOPIC}/set_state/{mac}', 
                        'state_topic': f'{BASE_TOPIC}/{mac}/state', 
                        'payload_on': 'on', 
                        'payload_off': 'off', 
                        'unique_id': f'{mac}', 
                        'device': {
                            'name': f'{name}', 
                            'identifiers': f'{serial_no}', 
                            'manufacturer': 'Tenda', 
                            'model': f'{model}', 
                            'sw_version': f'{fw_ver}'}, 
                            'platform': 'mqtt'
                            }), 1, True)

                    # RSSI sensor payload
                    client.publish(f'{ha_sensor}{device_mac}/config',json.dumps({
                        'availability': [
                            {'topic': f'{BASE_TOPIC}/status'},
                            {'topic': f'{BASE_TOPIC}/{device_mac}/status'}
                            ], 
                        'name': f'{name} switch RSSI', 
                        'state_topic': f'{BASE_TOPIC}/{mac}/rssi', 
                        'unique_id': f'{mac}', 
                        'device': {
                            'name': f'{name}', 
                            'identifiers': f'{serial_no}', 
                            'manufacturer': 'Tenda', 
                            'model': f'{model}', 
                            'sw_version': f'{fw_ver}'}, 
                            'platform': 'mqtt', 
                            'icon': 'mdi:signal-variant',
                            'unit_of_measurement': 'dBm'
                            }), 1, True)

            except Exception as e:
                logging.error(f'Unable to publish Home Assistant MQTT discovery payloads: {e}')

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
    d.mqtt_discovery()

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
        elif payload in ['off', 'on']:
            command = commands[payload]
        else:
            logging.warning(f"Command {payload} not valid. Valid commands are 'on', 'off', 'toggle'")
        d.set_state(device_mac, command)

if MQTT_HOST == None:
    logging.error('Please specify the IP address or hostname of your MQTT broker.')
    sys.exit()

if LOG_LEVEL.lower() not in ['debug', 'info', 'warning', 'error']:
    logging.basicConfig(level='INFO', format='%(asctime)s %(levelname)s: %(message)s')
    logging.warning(f'Selected log level "{LOG_LEVEL}" is not valid; using default')
else:
    logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s %(levelname)s: %(message)s')

d = Devices()

if __name__ == '__main__':
    mqtt_connect()
    d.get_device_info()
    for device in d.devices:
        d.get_state(device)
    polling_thread = t(target=d.poll_device, daemon=True)
    polling_thread.start()
    client.loop_forever()