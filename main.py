from machine import Pin, reset, time_pulse_us
import time
import random
from umqtt.simple import MQTTClient
import json
import dht  # Pastikan pustaka DHT sudah diinstal

# Tentukan pin GPIO yang digunakan untuk LED
led = Pin(2, Pin.OUT)  # Pin 2 sering digunakan sebagai LED bawaan pada ESP32
dht_sensor = dht.DHT11(Pin(23))  # Sensor DHT11 pada pin 23

# Tentukan pin untuk sensor SRF04
trigger = Pin(18, Pin.OUT)
echo = Pin(19, Pin.IN)

# Informasi MQTT
mqtt_server = '172.16.0.35'
mqtt_topic_reset = 'esp32/reset'
mqtt_topic_temp = 'esp32/sensor/temp'
mqtt_topic_hum = 'esp32/sensor/hum'
mqtt_topic_led = 'esp32/led'
mqtt_topic_version = 'esp32/version'
mqtt_topic_distance = 'esp32/sensor/distance'
client_id = 'esp32_client'

from ota import OTAUpdater

firmware_url = "https://raw.githubusercontent.com/2black0/ota-esp32/"
SSID = "Fave"
PASSWORD = "freewifi"

ota_updater = OTAUpdater(SSID, PASSWORD, firmware_url, "main.mpy")
ota_updater.download_and_install_update_if_available()

# Fungsi callback ketika menerima pesan dari broker MQTT
def mqtt_callback(topic, msg):
    print((topic, msg))
    if topic.decode() == mqtt_topic_reset and msg.decode() == 'reset':
        reset()
    elif topic.decode() == mqtt_topic_led:
        if msg.decode() == 'true':
            led.value(1)  # Nyalakan LED
        elif msg.decode() == 'false':
            led.value(0)  # Matikan LED

# Fungsi untuk menghubungkan ke broker MQTT
def connect_mqtt():
    client = MQTTClient(client_id, mqtt_server)
    client.set_callback(mqtt_callback)
    client.connect()
    client.subscribe(mqtt_topic_reset)
    client.subscribe(mqtt_topic_led)
    print('Connected to MQTT broker and subscribed to topics:', mqtt_topic_reset, mqtt_topic_led)
    return client

# Fungsi untuk membaca versi dari file JSON
def read_version():
    try:
        with open('version.json', 'r') as f:
            data = json.load(f)
            return data.get('version', None)
    except Exception as e:
        print('Failed to read version:', e)
        return None

# Fungsi untuk mengukur jarak dengan sensor SRF04
def measure_distance():
    # Kirim sinyal trigger
    trigger.off()
    time.sleep_us(2)
    trigger.on()
    time.sleep_us(10)
    trigger.off()
    
    # Tunggu echo dan hitung durasi pulsa
    duration = time_pulse_us(echo, 1, 30000)  # Timeout 30ms
    distance = (duration / 2) / 29.1  # Konversi durasi ke jarak dalam cm
    
    return distance

# Membaca versi dari file version.json
version = read_version()

# Menghubungkan ke broker MQTT
client = connect_mqtt()

# Mengirim versi ke topik esp32/version
if version is not None:
    client.publish(mqtt_topic_version, str(version))
    print(f'Published version: {version} to {mqtt_topic_version}')

# Loop utama
last_publish_time = time.time()

while True:
    client.check_msg()  # Memeriksa pesan yang masuk
    time.sleep(0.1)  # Tunggu selama 0.1 detik

    # Memeriksa apakah 5 detik telah berlalu untuk publish nilai sensor
    current_time = time.time()
    if current_time - last_publish_time >= 5:
        # Membaca nilai dari sensor DHT11
        dht_sensor.measure()
        temp = dht_sensor.temperature()
        hum = dht_sensor.humidity()
        
        # Mengukur jarak dengan sensor SRF04
        distance = measure_distance()

        # Publish nilai sensor ke MQTT
        client.publish(mqtt_topic_temp, str(temp))
        client.publish(mqtt_topic_hum, str(hum))
        client.publish(mqtt_topic_distance, str(distance))
        print(f'Published temp: {temp} to {mqtt_topic_temp}')
        print(f'Published hum: {hum} to {mqtt_topic_hum}')
        print(f'Published distance: {distance} to {mqtt_topic_distance}')
        last_publish_time = current_time