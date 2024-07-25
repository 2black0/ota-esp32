import network
import urequests
import os
import json
import machine
from time import sleep

class OTAUpdater:
    """ This class handles OTA updates. It connects to the Wi-Fi, checks for updates, downloads and installs them."""
    def __init__(self, ssid, password, repo_url, filename):
        self.filename = filename
        self.ssid = ssid
        self.password = password
        self.repo_url = repo_url
        if "www.github.com" in self.repo_url:
            print(f"Updating {repo_url} to raw.githubusercontent")
            self.repo_url = self.repo_url.replace("www.github", "raw.githubusercontent")
        elif "github.com" in self.repo_url:
            print(f"Updating {repo_url} to raw.githubusercontent")
            self.repo_url = self.repo_url.replace("github", "raw.githubusercontent")
        self.version_url = self.repo_url + 'main/version.json'
        print(f"version url is: {self.version_url}")
        self.firmware_url = self.repo_url + 'main/' + filename

        # get the current version (stored in version.json)
        if 'version.json' in os.listdir():
            with open('version.json') as f:
                self.current_version = int(json.load(f)['version'])
            print(f"Current device firmware version is '{self.current_version}'")
        else:
            self.current_version = 0
            # save the current version
            with open('version.json', 'w') as f:
                json.dump({'version': self.current_version}, f)

    def connect_wifi(self):
        """ Connect to Wi-Fi."""
        print('Connecting to WiFi...')
        sta_if = network.WLAN(network.STA_IF)
        sta_if.active(True)
        sta_if.connect(self.ssid, self.password)
        attempt = 0
        while not sta_if.isconnected() and attempt < 20:
            print('.', end="")
            sleep(0.5)
            attempt += 1
        if sta_if.isconnected():
            print(f'\nConnected to WiFi, IP is: {sta_if.ifconfig()[0]}')
        else:
            print('\nFailed to connect to WiFi')
            machine.reset()  # Reset device if unable to connect to WiFi

    def fetch_latest_code(self) -> bool:
        """ Fetch the latest code from the repo, replace the current code, and restart the device."""
        try:
            response = urequests.get(self.firmware_url)
            if response.status_code == 200:
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
        """ Replace the current code with the latest code, update version, and restart the device."""
        print(f"Updating device... (Renaming latest_code.mpy to {self.filename})", end="")
        try:
            os.rename('latest_code.mpy', self.filename)  # Overwrite the old code.
            with open('version.json', 'w') as f:
                json.dump({'version': self.latest_version}, f)  # Update version
            print('Restarting device...')
            machine.reset()  # Reset the device to run the new code.
        except Exception as e:
            print(f'Exception occurred while updating and resetting: {e}')
            machine.reset()  # Reset the device even if rename fails

    def check_for_updates(self):
        """ Check if updates are available."""
        # Connect to Wi-Fi
        self.connect_wifi()
        if not network.WLAN(network.STA_IF).isconnected():
            return False  # Exit if not connected to WiFi

        print(f'Checking for latest version... on {self.version_url}')
        try:
            response = urequests.get(self.version_url)
            if response.status_code != 200:
                print(f"Error: received status code {response.status_code}")
                print(f"Response text was: {response.text}")
                return False  # Assume no updates if the file is not found

            try:
                data = json.loads(response.text)
            except ValueError as e:
                print(f"Error parsing JSON: {e}")
                print(f"Response text was: {response.text}")
                return False  # Assume no updates if JSON is invalid

            print(f"data is: {data}, url is: {self.version_url}")
            print(f"data version is: {data['version']}")

            self.latest_version = int(data['version'])
            print(f'latest version is: {self.latest_version}')

            # compare versions
            newer_version_available = self.current_version < self.latest_version
            print(f'Newer version available: {newer_version_available}')
            return newer_version_available
        except Exception as e:
            print(f'Exception occurred while checking for updates: {e}')
            return False

    def download_and_install_update_if_available(self):
        """ Check for updates, download and install them."""
        if self.check_for_updates():
            if self.fetch_latest_code():
                self.update_and_reset()
        else:
            print('No new updates available.')
