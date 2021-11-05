# Tenda Beli to MQTT Gateway

tendabeli2mqtt enables local control of your Tenda Beli smart plugs/switches via MQTT. It supports Home Assistant MQTT discovery for easy integration. Supports multiple Tenda Beli devices. Not sure if anyone would actually be interested in this (personally, I prefer devices that can be flashed with Tasmota), but I do this stuff for fun anyway.

Special thanks to nohous for reverse engineering these devices' local protocol (https://github.com/nohous/tenda-beli).

**Initial release: there is still some additional work to be done, but this is in a usable state**

# How to run

**Docker via `docker-compose`**

1. Create your docker-compose.yaml (or add to existing). Example docker-compose.yaml with all environmental variables:
```yaml
version: '3'
services:
  tendabeli2mqtt:
    container_name: tendabeli2mqtt
    image: tediore/tendabeli2mqtt:latest
    environment:
    - MQTT_HOST=10.0.0.2
    - MQTT_PORT=1883
    - MQTT_USER=user
    - MQTT_PASSWORD=password
    - MQTT_QOS=1
    - BASE_TOPIC=tendabeli2mqtt
    - DEVICE_IPS=10.0.1.4,10.0.1.20
    - LOG_LEVEL=debug
    restart: unless-stopped
```
2. `docker-compose up -d tendabeli2mqtt`

<br>

**Docker via `docker run`**

Example `docker run` command with all environment variables:
```
docker run --name tendabeli2mqtt \
-e MQTT_HOST=10.0.0.2 \
-e MQTT_PORT=1883 \
-e MQTT_USER=user \
-e MQTT_PASSWORD=password \
-e MQTT_QOS=1 \
-e BASE_TOPIC=tendabeli2mqtt \
-e DEVICE_IPS=10.0.1.4,10.0.1.20 \
-e LOG_LEVEL=debug \
tediore/tendabeli2mqtt:latest
```

<br>

**Bare metal (not recommended)**
1. Set the necessary environment variables
2. `git clone https://github.com/Tediore/tendabeli2mqtt`
3. `cd tendabeli2mqtt`
4. `python3 tendabeli2mqtt.py`

<br>

# Configuration
| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `MQTT_HOST` | None | True |IP address or hostname of the MQTT broker to connect to. |
| `MQTT_PORT` | 1883 | True | The port the MQTT broker is bound to. |
| `MQTT_USER` | None | False | The user to send to the MQTT broker. |
| `MQTT_PASSWORD` | None | False | The password to send to the MQTT broker. |
| `MQTT_QOS` | 1 | False | The MQTT QoS level. |
| `BASE_TOPIC` | tendabeli2mqtt | True | The topic prefix to use for all payloads. |
| `DEVICE_IPS` | None | True | Comma-separated string containing the IP address(es) of your Tenda Beli device(s). |
| `LOG_LEVEL` | info | False | Set minimum log level. Valid options are `debug`, `info`, `warning`, and `error` |

<br>

# Home Assistant
audioflow2mqtt supports Home Assistant MQTT discovery which creates a Device for the Audioflow switch and entities for each zone.

![Home Assistant Device screenshot](ha_screenshot.png)

<br>