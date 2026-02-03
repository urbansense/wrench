from abc import ABC, abstractmethod
from typing import Any, cast

from geojson import FeatureCollection, Polygon

from wrench.harvester.sensorthings.models import Location
from wrench.models import Device


class SpatialExtentCalculator(ABC):
    """
    Abstract base class for calculating geographic extents from a list of Things.

    This class defines the interface for all geographic extent calculation strategies.
    """

    @abstractmethod
    def calculate_extent(self, devices: list[Device]) -> Any:
        """
        Calculate geographic extent from a list of Things.

        Args:
            devices: List of devices with location data

        Returns:
            A GeoJSON object representing the geographic extent
        """
        pass


class PolygonalExtentCalculator(SpatialExtentCalculator):
    """
    Calculates a bounding box as a GeoJSON Polygon from a set of locations.

    This strategy creates a rectangular bounding box that encompasses all points.
    """

    def calculate_extent(self, devices: list[Device]) -> Polygon:
        """
        Calculate the geographic bounding box from a set of locations.

        Args:
            devices: List of devices with location data

        Returns:
            Polygon: GeoJSON polygon representing the bounding box
        """
        # Initialize bounds
        bounds = {
            "min_lat": float("inf"),
            "max_lat": float("-inf"),
            "min_lng": float("inf"),
            "max_lng": float("-inf"),
        }

        # get locations of each thing, put them into a set to avoid duplicates
        locations = {
            coord
            for device in devices
            if device.locations
            for loc in device.locations  # a thing can have many locations
            for coord in loc.get_coordinates()  # a location can be have many coord
        }

        if not locations:
            raise ValueError("Locations cannot be extracted from Things")

        # Update bounds for each location (handle both 2D and 3D coordinates)
        for coord in locations:
            lng, lat = coord[0], coord[1]
            bounds["min_lat"] = min(bounds["min_lat"], lat)
            bounds["max_lat"] = max(bounds["max_lat"], lat)
            bounds["min_lng"] = min(bounds["min_lng"], lng)
            bounds["max_lng"] = max(bounds["max_lng"], lng)

        # Create polygon coordinates
        coordinates = [
            (bounds["min_lng"], bounds["min_lat"]),
            (bounds["max_lng"], bounds["min_lat"]),
            (bounds["max_lng"], bounds["max_lat"]),
            (bounds["min_lng"], bounds["max_lat"]),
            (bounds["min_lng"], bounds["min_lat"]),  # Close the polygon
        ]

        return Polygon([coordinates])


class GeometryCollector(SpatialExtentCalculator):
    """
    Collects GeoJSON Geometries from a set of Things.

    This strategy collects the location of each Thing and aggregates it into a
    FeatureCollection
    """

    def calculate_extent(self, devices: list[Device]) -> FeatureCollection:
        geometries: list = []
        for device in devices:
            for loc in device.locations:
                loc = cast(Location, loc)
                geometries.append(loc.location)

        return FeatureCollection(geometries)
