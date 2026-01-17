"""Unified caching system for test data."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import numpy as np

if TYPE_CHECKING:
    from wrench.harvester.sensorthings import SensorThingsHarvester
    from wrench.models import Device

DEFAULT_CACHE_DIR = Path("tools/fixtures/data")


class DataCache:
    """Manages cached test data for different sources."""

    def __init__(self, cache_dir: Path | None = None):
        """Initialize the data cache.

        Args:
            cache_dir: Directory to store cached data. Defaults to tools/fixtures/data
        """
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_cache_path(
        self, source: str, data_type: Literal["devices", "embeddings"]
    ) -> Path:
        """Get the cache file path for a given source and data type.

        Args:
            source: Data source name (e.g., 'hamburg', 'osnabrueck')
            data_type: Type of cached data ('devices' or 'embeddings')

        Returns:
            Path to the cache file
        """
        if data_type == "devices":
            return self.cache_dir / f"{source}_devices.json"
        elif data_type == "embeddings":
            return self.cache_dir / f"{source}_embeddings.npz"
        else:
            raise ValueError(f"Unknown data type: {data_type}")

    def has_cached(
        self, source: str, data_type: Literal["devices", "embeddings"]
    ) -> bool:
        """Check if cached data exists.

        Args:
            source: Data source name
            data_type: Type of cached data

        Returns:
            True if cache exists, False otherwise
        """
        return self.get_cache_path(source, data_type).exists()

    def save_devices(self, source: str, devices: list[Device]) -> Path:
        """Save devices to cache.

        Args:
            source: Data source name
            devices: List of Device objects to cache

        Returns:
            Path to the saved cache file
        """
        cache_path = self.get_cache_path(source, "devices")
        with open(cache_path, "w") as f:
            json.dump(
                [
                    device.model_dump(mode="json", exclude={"raw_data"})
                    for device in devices
                ],
                f,
                indent=2,
            )
        return cache_path

    def load_devices(self, source: str) -> list[Device]:
        """Load devices from cache.

        Args:
            source: Data source name

        Returns:
            List of Device objects

        Raises:
            FileNotFoundError: If cache doesn't exist
        """
        from wrench.models import Device

        cache_path = self.get_cache_path(source, "devices")
        if not cache_path.exists():
            raise FileNotFoundError(
                f"No cached devices for source '{source}'. Run 'wrench-tools data fetch {source}' first."
            )

        with open(cache_path, "r") as f:
            content = json.load(f)

        return [Device.model_validate(device) for device in content]

    def save_embeddings(self, source: str, embeddings: np.ndarray) -> Path:
        """Save embeddings to cache.

        Args:
            source: Data source name
            embeddings: Numpy array of embeddings

        Returns:
            Path to the saved cache file
        """
        cache_path = self.get_cache_path(source, "embeddings")
        np.savez_compressed(cache_path, embeddings=embeddings)
        return cache_path

    def load_embeddings(self, source: str) -> np.ndarray:
        """Load embeddings from cache.

        Args:
            source: Data source name

        Returns:
            Numpy array of embeddings

        Raises:
            FileNotFoundError: If cache doesn't exist
        """
        cache_path = self.get_cache_path(source, "embeddings")
        if not cache_path.exists():
            raise FileNotFoundError(
                f"No cached embeddings for source '{source}'. Run 'wrench-tools data fetch {source} --embeddings' first."
            )

        data = np.load(cache_path)
        return data["embeddings"]

    def fetch_and_cache_devices(
        self, source: str, base_url: str, limit: int = -1
    ) -> list[Device]:
        """Fetch devices from a SensorThings server and cache them.

        Args:
            source: Data source name for caching
            base_url: SensorThings API base URL
            limit: Maximum number of devices to fetch (-1 for no limit)

        Returns:
            List of fetched Device objects
        """
        from wrench.harvester.sensorthings import SensorThingsHarvester

        harvester = SensorThingsHarvester(base_url=base_url, default_limit=limit)
        devices = harvester.return_devices()
        self.save_devices(source, devices)
        return devices

    def generate_and_cache_embeddings(
        self,
        source: str,
        model_name: str = "intfloat/multilingual-e5-large-instruct",
        exclude_fields: list[str] | None = None,
    ) -> np.ndarray:
        """Generate embeddings for cached devices and cache them.

        Args:
            source: Data source name
            model_name: Name of the sentence transformer model
            exclude_fields: Fields to exclude when creating text representations

        Returns:
            Numpy array of embeddings

        Raises:
            FileNotFoundError: If devices are not cached
        """
        from sentence_transformers import SentenceTransformer

        devices = self.load_devices(source)

        if exclude_fields is None:
            exclude_fields = [
                "id",
                "observed_properties",
                "locations",
                "time_frame",
                "properties",
                "_raw_data",
                "sensor_names",
            ]

        # Create text representations
        docs = [device.to_string(exclude=exclude_fields) for device in devices]

        # Generate embeddings
        encoder = SentenceTransformer(model_name)
        embeddings = encoder.encode(docs, show_progress_bar=True)

        # Cache embeddings
        self.save_embeddings(source, embeddings)

        return embeddings

    def list_cached_sources(self) -> dict[str, dict[str, bool]]:
        """List all cached data sources and what's available.

        Returns:
            Dictionary mapping source names to available data types
        """
        sources = {}

        # Find all cached device files
        for device_file in self.cache_dir.glob("*_devices.json"):
            source = device_file.stem.replace("_devices", "")
            sources[source] = {
                "devices": True,
                "embeddings": self.has_cached(source, "embeddings"),
            }

        return sources

    def get_cache_stats(self, source: str) -> dict:
        """Get statistics about cached data.

        Args:
            source: Data source name

        Returns:
            Dictionary with cache statistics
        """
        stats = {
            "source": source,
            "has_devices": self.has_cached(source, "devices"),
            "has_embeddings": self.has_cached(source, "embeddings"),
        }

        if stats["has_devices"]:
            devices = self.load_devices(source)
            stats["device_count"] = len(devices)
            stats["devices_size_mb"] = (
                self.get_cache_path(source, "devices").stat().st_size / 1024 / 1024
            )

        if stats["has_embeddings"]:
            embeddings = self.load_embeddings(source)
            stats["embedding_shape"] = embeddings.shape
            stats["embeddings_size_mb"] = (
                self.get_cache_path(source, "embeddings").stat().st_size / 1024 / 1024
            )

        return stats
