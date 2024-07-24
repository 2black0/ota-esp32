import network
import time
import machine
from umqtt.simple import MQTTClient

# Koneksi ke broker MQTT
mqtt_server = 'broker.emqx.io'
client_id = 'esp32_client'
topic_pub_temp = b'esp32/sensor/temp'
topic_pub_hum = b'esp32/sensor/hum'
topic_sub = b'esp32/reset'

def sub_cb(topic, msg):
    print((topic, msg))
    if msg == b'reset':
        print('Reset command received, resetting...')
        machine.reset()

client = MQTTClient(client_id, mqtt_server)
client.set_callback(sub_cb)
client.connect()
client.subscribe(topic_sub)

print('Connected to %s MQTT broker, subscribed to %s topic' % (mqtt_server, topic_sub))

def publish():
    while True:
        temp_msg = b'25.5'  # Example temperature value
        hum_msg = b'60'     # Example humidity value
        client.publish(topic_pub_temp, temp_msg)
        client.publish(topic_pub_hum, hum_msg)
        print('Published temperature: %s' % temp_msg)
        print('Published humidity: %s' % hum_msg)
        time.sleep(10)  # Publish every 10 seconds

def subscribe():
    while True:
        client.check_msg()
        time.sleep(1)

# Main loop
try:
    import _thread
    _thread.start_new_thread(publish, ())
    subscribe()
except KeyboardInterrupt:
    print('Disconnected from broker')
    client.disconnect()
