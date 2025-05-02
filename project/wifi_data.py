"""
Wi-Fi and MQTT Connection Configuration

This module contains the configuration settings for Wi-Fi network connectivity
and MQTT broker connection. It defines constants used by other modules in the project
for establishing network communications.

Variables:
    mqtt_server (str): IP address or hostname of the MQTT broker
    SSID (str): Wi-Fi network name to connect to
    PASSWORD (str): Wi-Fi network password

Usage:
    from wifi_data import mqtt_server, SSID, PASSWORD

Notes:
    - This file should be excluded from version control systems to protect credentials
    - For production use, consider implementing more secure credential management
    - For development environments, replace with your actual network information
    - The MQTT server should be accessible from the ESP32's network

Author: Unknown
Version: 1.0
"""

# MQTT broker address - replace with your actual MQTT server IP/hostname
mqtt_server = '192.168.1.18'

# Wi-Fi network credentials - replace with your actual network details
SSID = "WIFI-SSID"       # Wi-Fi network name
PASSWORD = "1234567890"  # Wi-Fi password