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
        self.items: list[Device] | None = None
        self.ground_truth: defaultdict[str, list] = defaultdict(list)

    def fetch_items(self) -> list[Device]:
        """Fetch items from the harvester.

        Returns:
            List of items
        """
        if self.items is None:
            self.items = self.harvester.return_items()
        return self.items

    def add_rule(
        self,
        category: str,
        condition: Callable[[Device], bool],
        items: list[Device] | None = None,
    ) -> int:
        """Add a classification rule.

        Args:
            category: Category name for items matching the condition
            condition: Function that takes an Device and returns True if it belongs to category
            items: Devices to check (optional, uses fetched items if None)

        Returns:
            Number of items added to the category
        """
        if items is None:
            items = self.fetch_items()

        count = 0
        for item in items:
            if condition(item):
                self.ground_truth[category].append(str(item.id))
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
            Number of items added to the category
        """

        def condition(item: Device) -> bool:
            if not item.properties or field not in item.properties:
                return False
            item_keywords = item.properties[field]
            if isinstance(item_keywords, str):
                item_keywords = [item_keywords]
            return any(kw in item_keywords for kw in keywords)

        return self.add_rule(category, condition)

    def add_name_prefix_rule(self, category: str, prefixes: list[str]) -> int:
        """Add a rule based on name prefix matching.

        Args:
            category: Category name
            prefixes: List of name prefixes to match

        Returns:
            Number of items added to the category
        """

        def condition(item: Device) -> bool:
            return any(item.name.startswith(prefix) for prefix in prefixes)

        return self.add_rule(category, condition)

    def add_name_contains_rule(self, category: str, patterns: list[str]) -> int:
        """Add a rule based on name substring matching.

        Args:
            category: Category name
            patterns: List of substrings to match in name

        Returns:
            Number of items added to the category
        """

        def condition(item: Device) -> bool:
            return any(pattern in item.name for pattern in patterns)

        return self.add_rule(category, condition)

    def get_unassigned_items(self) -> list[Device]:
        """Get items that haven't been assigned to any category.

        Returns:
            List of unassigned items
        """
        items = self.fetch_items()
        assigned_ids = set()
        for item_ids in self.ground_truth.values():
            assigned_ids.update(item_ids)

        return [item for item in items if str(item.id) not in assigned_ids]

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
