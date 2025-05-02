"""
OTA (Over-The-Air) Update Module for ESP32

This module provides functionality to check for, download, and install firmware updates
from a GitHub repository. It handles the entire OTA update process including:
- Wi-Fi connection management
- Version comparison between local and remote firmware
- Downloading updated firmware
- Installing updates and restarting the device

Usage:
    from ota import OTAUpdater
    
    # Initialize with Wi-Fi and repository details
    updater = OTAUpdater(ssid, password, github_repo_url, firmware_filename)
    
    # Check and install updates if available
    updater.download_and_install_update_if_available()

Requirements:
    - Wi-Fi credentials
    - GitHub repository with:
        - version.json file containing current version number
        - Firmware file (typically .mpy file)
    
Dependencies:
    - network (for Wi-Fi connectivity)
    - urequests (for HTTP requests)
    - os (for file operations)
    - json (for parsing version information)
    - machine (for device reset)
    - time (for sleep function)

Author: Unknown
License: Not specified
"""

import network
import urequests
import os
import json
import machine
from time import sleep

class OTAUpdater:
    """ 
    This class handles OTA updates. It connects to Wi-Fi, checks for updates, 
    downloads and installs them.
    """
    def __init__(self, ssid, password, repo_url, filename):
        """
        Initialize the OTA updater with required parameters.
        
        Args:
            ssid (str): Wi-Fi network name
            password (str): Wi-Fi password
            repo_url (str): GitHub repository URL containing the firmware
            filename (str): Name of the firmware file to update
        """
        self.filename = filename
        self.ssid = ssid
        self.password = password
        self.repo_url = repo_url
        
        # Convert regular GitHub URLs to raw content URLs if needed
        if "www.github.com" in self.repo_url:
            print(f"Updating {repo_url} to raw.githubusercontent")
            self.repo_url = self.repo_url.replace("www.github", "raw.githubusercontent")
        elif "github.com" in self.repo_url:
            print(f"Updating {repo_url} to raw.githubusercontent")
            self.repo_url = self.repo_url.replace("github", "raw.githubusercontent")
            
        # Construct URLs for version check and firmware download
        self.version_url = self.repo_url + 'main/version.json'
        print(f"version url is: {self.version_url}")
        self.firmware_url = self.repo_url + 'main/' + filename

        # Load current firmware version from local file
        if 'version.json' in os.listdir():
            with open('version.json') as f:
                self.current_version = int(json.load(f)['version'])
            print(f"Current device firmware version is '{self.current_version}'")
        else:
            # If no version file exists, create one with version 0
            self.current_version = 0
            # save the current version
            with open('version.json', 'w') as f:
                json.dump({'version': self.current_version}, f)

    def connect_wifi(self):
        """
        Connect to Wi-Fi network using stored credentials.
        
        Will attempt to connect up to 20 times before giving up.
        If connection fails, the device will reset.
        """
        print('Connecting to WiFi...')
        sta_if = network.WLAN(network.STA_IF)
        sta_if.active(True)
        sta_if.connect(self.ssid, self.password)
        
        # Wait for connection with timeout
        attempt = 0
        while not sta_if.isconnected() and attempt < 20:
            print('.', end="")
            sleep(0.5)
            attempt += 1
            
        # Report connection status
        if sta_if.isconnected():
            print(f'\nConnected to WiFi, IP is: {sta_if.ifconfig()[0]}')
        else:
            print('\nFailed to connect to WiFi')
            machine.reset()  # Reset device if unable to connect to WiFi

    def fetch_latest_code(self) -> bool:
        """
        Download the latest firmware from the repository.
        
        Returns:
            bool: True if download was successful, False otherwise
        """
        try:
            # Request the firmware file
            response = urequests.get(self.firmware_url)
            if response.status_code == 200:
                # Save firmware to temporary file
                with open('latest_code.mpy', 'wb') as f:  # Open in binary mode
                    f.write(response.content)  # Write content directly to handle any binary data
                return True
            else:
                print(f'Failed to download the latest code, status code: {response.status_code}')
                return False
        except Exception as e:
            print(f'Exception occurred while fetching latest code: {e}')
            return False

    def update_and_reset(self):
        """
        Replace the current firmware with the downloaded version.
        
        This method:
        1. Renames the downloaded file to the target firmware name
        2. Updates the version number in version.json
        3. Resets the device to load the new firmware
        """
        print(f"Updating device... (Renaming latest_code.mpy to {self.filename})", end="")
        try:
            # Replace current firmware with downloaded version
            os.rename('latest_code.mpy', self.filename)  # Overwrite the old code
            
            # Update version information
            with open('version.json', 'w') as f:
                json.dump({'version': self.latest_version}, f)  # Update version
                
            print('Restarting device...')
            machine.reset()  # Reset the device to run the new code
        except Exception as e:
            print(f'Exception occurred while updating and resetting: {e}')
            machine.reset()  # Reset the device even if rename fails

    def check_for_updates(self):
        """
        Check if a newer firmware version is available in the repository.
        
        Returns:
            bool: True if an update is available, False otherwise
        """
        # Connect to Wi-Fi
        self.connect_wifi()
        if not network.WLAN(network.STA_IF).isconnected():
            return False  # Exit if not connected to WiFi

        print(f'Checking for latest version... on {self.version_url}')
        try:
            # Get version information from repository
            response = urequests.get(self.version_url)
            if response.status_code != 200:
                print(f"Error: received status code {response.status_code}")
                print(f"Response text was: {response.text}")
                return False  # Assume no updates if the file is not found

            try:
                # Parse version information
                data = json.loads(response.text)
            except ValueError as e:
                print(f"Error parsing JSON: {e}")
                print(f"Response text was: {response.text}")
                return False  # Assume no updates if JSON is invalid

            print(f"data is: {data}, url is: {self.version_url}")
            print(f"data version is: {data['version']}")

            self.latest_version = int(data['version'])
            print(f'latest version is: {self.latest_version}')

            # Compare versions to determine if update is needed
            newer_version_available = self.current_version < self.latest_version
            print(f'Newer version available: {newer_version_available}')
            return newer_version_available
        except Exception as e:
            print(f'Exception occurred while checking for updates: {e}')
            return False

    def download_and_install_update_if_available(self):
        """
        Main method to orchestrate the update process.
        
        This method:
        1. Checks if updates are available
        2. Downloads the updated firmware if available
        3. Installs the update and resets the device
        
        Returns nothing, but will reset device if update is successful.
        """
        if self.check_for_updates():
            if self.fetch_latest_code():
                self.update_and_reset()
        else:
            print('No new updates available.')