"""
ESP32 IoT Sensor Hub with OTA Update Capability

This application runs on an ESP32 microcontroller and provides the following functionality:
1. Over-the-Air (OTA) firmware updates from a GitHub repository
2. Multiple sensor readings (DHT11 temperature/humidity, SRF04 ultrasonic distance)
3. MQTT connectivity for sensor data publication and remote control
4. LED control via MQTT commands
5. Remote reset capability via MQTT

The program publishes sensor data to specified MQTT topics at regular intervals
and subscribes to topics for receiving commands.

Hardware Requirements:
- ESP32 development board
- DHT11 temperature/humidity sensor on pin 23
- SRF04 ultrasonic distance sensor (trigger pin 18, echo pin 19)
- Built-in LED on pin 2

Dependencies:
- machine, time, random, json, urandom
- umqtt.simple
- dht
- wifi_data (custom module with credentials)
- ota (custom module for OTA updates)

Author: Unknown
Version: Stored in version.json
"""

from machine import Pin, reset, time_pulse_us, SoftI2C
import time
import random
from umqtt.simple import MQTTClient
import json
import urandom
import dht
from wifi_data import mqtt_server, SSID, PASSWORD
#import ahtx0  # Alternative temperature/humidity sensor library (currently disabled)

# Initialize onboard LED
led = Pin(2, Pin.OUT)  # Built-in LED on most ESP32 boards

# Initialize DHT11 temperature and humidity sensor
sensor = dht.DHT11(Pin(23))

# Initialize SRF04 ultrasonic distance sensor
trigger = Pin(18, Pin.OUT)
echo = Pin(19, Pin.IN)

# I2C configuration for AHT10 sensor (currently disabled)
#i2c = SoftI2C(scl=Pin(22), sda=Pin(21))
#sensor = ahtx0.AHT10(i2c)

# MQTT configuration
mqtt_topic_reset = 'esp32/reset'       # Topic for receiving reset commands
mqtt_topic_temp = 'esp32/sensor/temp'  # Topic for publishing temperature readings
mqtt_topic_hum = 'esp32/sensor/hum'    # Topic for publishing humidity readings
mqtt_topic_led = 'esp32/led'           # Topic for receiving LED control commands
mqtt_topic_version = 'esp32/version'   # Topic for publishing firmware version
mqtt_topic_distance = 'esp32/sensor/distance'  # Topic for publishing distance readings
mqtt_topic_alarm = 'esp32/sensor/alarmstatus'  # Topic for publishing alarm status
client_id = 'esp32_client'             # MQTT client identifier

# Initialize OTA updater
from ota import OTAUpdater

# GitHub repository URL for OTA updates
firmware_url = "https://raw.githubusercontent.com/2black0/OTA-ESP32/"

# Create OTA updater instance and check for available updates
ota_updater = OTAUpdater(SSID, PASSWORD, firmware_url, "main.mpy")
ota_updater.download_and_install_update_if_available()

def random_float(min_value, max_value):
    """
    Generate a random float between min_value and max_value.
    Used for testing when physical sensors aren't available.
    
    Args:
        min_value (float): Minimum value for the random number
        max_value (float): Maximum value for the random number
        
    Returns:
        float: Random value between min_value and max_value, rounded to 2 decimal places
    """
    random_int = urandom.getrandbits(16) % 10000
    scaled_float = min_value + (max_value - min_value) * (random_int / 10000.0)
    return round(scaled_float, 2)

def mqtt_callback(topic, msg):
    """
    Callback function triggered when messages are received from subscribed MQTT topics.
    Handles reset commands and LED control.
    
    Args:
        topic (bytes): The topic that received the message
        msg (bytes): The message payload
    """
    print((topic, msg))
    if topic.decode() == mqtt_topic_reset and msg.decode() == 'reset':
        reset()  # Perform device reset when 'reset' message is received
    elif topic.decode() == mqtt_topic_led:
        if msg.decode() == 'true':
            led.value(1)  # Turn LED on
        elif msg.decode() == 'false':
            led.value(0)  # Turn LED off

def connect_mqtt():
    """
    Connect to the MQTT broker and subscribe to control topics.
    
    Returns:
        MQTTClient: Connected MQTT client object
    """
    client = MQTTClient(client_id, mqtt_server)
    client.set_callback(mqtt_callback)
    client.connect()
    client.subscribe(mqtt_topic_reset)
    client.subscribe(mqtt_topic_led)
    print('Connected to MQTT broker and subscribed to topics:', mqtt_topic_reset, mqtt_topic_led)
    return client

def read_version():
    """
    Read firmware version from version.json file.
    
    Returns:
        str or None: Version string if successful, None if error occurs
    """
    try:
        with open('version.json', 'r') as f:
            data = json.load(f)
            return data.get('version', None)
    except Exception as e:
        print('Failed to read version:', e)
        return None

def measure_distance():
    """
    Measure distance using the SRF04 ultrasonic sensor.
    
    Returns:
        float: Distance in centimeters
    """
    # Send trigger pulse
    trigger.off()
    time.sleep_us(2)
    trigger.on()
    time.sleep_us(10)
    trigger.off()
    
    # Wait for echo and calculate distance
    duration = time_pulse_us(echo, 1, 30000)  # Timeout after 30ms
    distance = (duration / 2) / 29.1  # Convert pulse duration to distance in cm
    
    return distance

# Read firmware version
version = read_version()

# Connect to MQTT broker
client = connect_mqtt()

# Publish firmware version to MQTT
if version is not None:
    client.publish(mqtt_topic_version, str(version))
    print(f'Published version: {version} to {mqtt_topic_version}')

# Main program loop
last_publish_time = time.time()

while True:
    client.check_msg()  # Check for incoming MQTT messages
    
    # Publish sensor data every 5 seconds
    current_time = time.time()
    if current_time - last_publish_time >= 5:
        # For testing without sensors (currently commented out):
        #temp = random_float(20.0, 21.0)
        #hum = random_float(50.0, 55.0)
        #distance = random_float(10, 150.0)
        
        # Read actual sensor data
        sensor.measure() 
        temp = sensor.temperature()
        hum = sensor.humidity()
        #temp = sensor.temperature      # For AHT10 sensor (commented out)
        #hum = sensor.relative_humidity # For AHT10 sensor (commented out)
        distance = measure_distance()
        
        # Set alarm status based on distance threshold (15cm)
        if distance > 15:
            alarmstatus = False
        else:
            alarmstatus = True
        
        # Publish all sensor readings to respective MQTT topics
        client.publish(mqtt_topic_temp, str(temp))
        client.publish(mqtt_topic_hum, str(hum))
        client.publish(mqtt_topic_distance, str(distance))
        client.publish(mqtt_topic_alarm, str(alarmstatus))
        print(f'Published temp: {temp} to {mqtt_topic_temp}')
        print(f'Published hum: {hum} to {mqtt_topic_hum}')
        print(f'Published distance: {distance} to {mqtt_topic_distance}')
        last_publish_time = current_time  # Reset timer