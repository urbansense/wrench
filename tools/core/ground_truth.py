"""Ground truth creation utilities."""

import json
from collections import defaultdict
from pathlib import Path
from typing import Callable

from wrench.harvester.sensorthings import SensorThingsHarvester
from wrench.models import Device


class GroundTruthBuilder:
    """Builds ground truth datasets from harvested devices based on rules."""

    def __init__(self, harvester: SensorThingsHarvester):
        """Initialize the ground truth builder.

        Args:
            harvester: SensorThings harvester to fetch devices
        """
        self.harvester = harvester
        self.devices: list[Device] | None = None
        self.ground_truth: defaultdict[str, list] = defaultdict(list)

    def fetch_devices(self) -> list[Device]:
        """Fetch devices from the harvester.

        Returns:
            List of devices
        """
        if self.devices is None:
            self.devices = self.harvester.return_devices()
        return self.devices

    def add_rule(
        self,
        category: str,
        condition: Callable[[Device], bool],
        devices: list[Device] | None = None,
    ) -> int:
        """Add a classification rule.

        Args:
            category: Category name for devices matching the condition
            condition: Function that takes an Device and returns True if it belongs to category
            devices: Devices to check (optional, uses fetched devices if None)

        Returns:
            Number of devices added to the category
        """
        if devices is None:
            devices = self.fetch_devices()

        count = 0
        for device in devices:
            if condition(device):
                self.ground_truth[category].append(str(device.id))
                count += 1

        return count

    def add_keyword_rule(
        self, category: str, keywords: list[str], field: str = "keywords"
    ) -> int:
        """Add a rule based on keyword matching in properties.

        Args:
            category: Category name
            keywords: List of keywords to match
            field: Property field to check (default: 'keywords')

        Returns:
            Number of devices added to the category
        """

        def condition(device: Device) -> bool:
            if not device.properties or field not in device.properties:
                return False
            device_keywords = device.properties[field]
            if isinstance(device_keywords, str):
                device_keywords = [device_keywords]
            return any(kw in device_keywords for kw in keywords)

        return self.add_rule(category, condition)

    def add_name_prefix_rule(self, category: str, prefixes: list[str]) -> int:
        """Add a rule based on name prefix matching.

        Args:
            category: Category name
            prefixes: List of name prefixes to match

        Returns:
            Number of devices added to the category
        """

        def condition(device: Device) -> bool:
            return any(device.name.startswith(prefix) for prefix in prefixes)

        return self.add_rule(category, condition)

    def add_name_contains_rule(self, category: str, patterns: list[str]) -> int:
        """Add a rule based on name substring matching.

        Args:
            category: Category name
            patterns: List of substrings to match in name

        Returns:
            Number of devices added to the category
        """

        def condition(device: Device) -> bool:
            return any(pattern in device.name for pattern in patterns)

        return self.add_rule(category, condition)

    def get_unassigned_devices(self) -> list[Device]:
        """Get devices that haven't been assigned to any category.

        Returns:
            List of unassigned devices
        """
        devices = self.fetch_devices()
        assigned_ids = set()
        for device_ids in self.ground_truth.values():
            assigned_ids.update(device_ids)

        return [device for device in devices if str(device.id) not in assigned_ids]

    def save(self, output_path: Path | str) -> None:
        """Save ground truth to JSON file.

        Args:
            output_path: Path to save the ground truth
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(dict(self.ground_truth), f, indent=2)

    def load(self, input_path: Path | str) -> dict[str, list]:
        """Load ground truth from JSON file.

        Args:
            input_path: Path to load the ground truth from

        Returns:
            Ground truth dictionary
        """
        with open(input_path) as f:
            self.ground_truth = defaultdict(list, json.load(f))
        return dict(self.ground_truth)

    def get_statistics(self) -> dict:
        """Get statistics about the ground truth.

        Returns:
            Dictionary with statistics
        """
        total_devices = len(self.fetch_devices())
        assigned_devices = sum(len(devices) for devices in self.ground_truth.values())
        unassigned_devices = total_devices - assigned_devices

        return {
            "total_devices": total_devices,
            "assigned_devices": assigned_devices,
            "unassigned_devices": unassigned_devices,
            "categories": len(self.ground_truth),
            "category_distribution": {
                cat: len(devices) for cat, devices in self.ground_truth.items()
            },
        }
