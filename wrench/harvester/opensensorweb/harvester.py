import requests

from wrench.harvester.base import BaseHarvester
from wrench.models import Device as WrenchDevice

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

    def return_devices(self) -> list[WrenchDevice]:  # type: ignore[override]
        """Returns devices."""
        return self.devices  # type: ignore[return-value]
