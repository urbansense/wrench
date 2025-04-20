import requests

from wrench.harvester.base import BaseHarvester

from .models import Device


class OpenSensorWebHarvester(BaseHarvester):
    def __init__(self, device_url: str):
        self.url = device_url
        self.devices = self.fetch_items()

    def fetch_items(self) -> list[Device]:
        response = requests.get(self.url)
        devices: list[Device] = []
        device_list = response.json()["items"]
        for device in device_list:
            device_resp = requests.get(device["href"])
            devices.append(device_resp)

        return devices

    def return_items(self) -> list[Device]:
        """Returns devices."""
        return self.devices
