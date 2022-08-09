import rp2
import network
import ubinascii
import machine
import time
from secrets import secrets
import socket
from umqtt.simple import MQTTClient
from machine import Pin

sensor_temp = machine.ADC(machine.ADC.CORE_TEMP)
conversion_factor = 3.3 / (65535)

last_message = 0
message_interval = 5
counter = 0

led = machine.Pin('LED', machine.Pin.OUT)

#
# Set country to avoid possible errors / https://randomnerdtutorials.com/micropython-mqtt-esp32-esp8266/
rp2.country('ES')

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
# If you need to disable powersaving mode

# See the MAC address in the wireless chip OTP
mac = ubinascii.hexlify(network.WLAN().config('mac'), ':').decode()
print('mac = ' + mac)

# Other things to query
# print(wlan.config('channel'))
# print(wlan.config('essid'))
# print(wlan.config('txpower'))

# Load login data from different file for safety reasons
ssid = secrets['ssid']
pw = secrets['pw']
broker = secrets['broker']
sub_topic = secrets['subtopic']
pub_topic = secrets['pubtopic']
mqtt_pw = secrets['mqtt_key']
mqtt_user = secrets['mqtt_username']
# client_id = ubinascii.hexlify(machine.unique_id())
# client_id = mac
client_id = secrets['client_id']
print(client_id)
print(ssid)


def connect():
    wlan = network.WLAN(network.STA_IF)
    # Connect to WLAN
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, pw)
    while wlan.isconnected() == False:
        print('Waiting for connection...')
        time.sleep(1)
    ip = wlan.ifconfig()[0]
    print(f'Connected on {ip}')


# Handle connection error
# Error meanings
# 0  Link Down
# 1  Link Join
# 2  Link NoIp
# 3  Link Up
# -1 Link Fail
# -2 Link NoNet
# -3 Link BadAuth

### Topic Setup ###

def sub_cb(topic, msg):
    print((topic, msg))
    if msg == b'LEDon':
        print('Device received LEDon message on subscribed topic')
        led.value(1)
    if msg == b'LEDoff':
        print('Device received LEDoff message on subscribed topic')
        led.value(0)


def connect_and_subscribe():
    global client_id, mqtt_server, topic_sub, mqtt_pw, mqtt_user
    print("Connectiong to broker")
    print(
        'Trying to connect to %s MQTT broker as client ID: %s, subscribed to %s topic' % (broker, client_id, sub_topic))

    client = MQTTClient(client_id=client_id, server=broker, port=1883, user=mqtt_user, password=mqtt_pw)
    client.set_callback(sub_cb)
    client.connect()
    client.subscribe(sub_topic)
    print('Connected to %s MQTT broker as client ID: %s, subscribed to %s topic' % (broker, client_id, sub_topic))
    return client


def restart_and_reconnect():
    print('Failed to connect to MQTT broker. Reconnecting...')
    time.sleep(10)
    machine.reset()


connect()

if wlan.status() != 3:
    raise RuntimeError('Wi-Fi connection failed')
else:
    led = machine.Pin('LED', machine.Pin.OUT)
    for i in range(wlan.status()):
        led.on()
        time.sleep(.1)
        led.off()
    print('Connected')
    status = wlan.ifconfig()
    print('ip = ' + status[0])

try:
    client = connect_and_subscribe()
except OSError as e:
    restart_and_reconnect()

while True:
    try:
        client.check_msg()
        if (time.time() - last_message) > message_interval:
            reading = sensor_temp.read_u16() * conversion_factor
            temperature = 27 - (reading - 0.706) / 0.001721
            pub_msg = str(temperature)
            client.publish(pub_topic, pub_msg)
            last_message = time.time()
        time.sleep_ms(10)
    except OSError as e:
        restart_and_reconnect()
