from abc import ABC, abstractmethod
from typing import Any

from geojson import FeatureCollection, Polygon

from wrench.harvester.sensorthings.models import Thing


class SpatialExtentCalculator(ABC):
    """
    Abstract base class for calculating geographic extents from a list of Things.

    This class defines the interface for all geographic extent calculation strategies.
    """

    @abstractmethod
    def calculate_extent(self, things: list[Thing]) -> Any:
        """
        Calculate geographic extent from a list of Things.

        Args:
            things: List of Thing objects with location data

        Returns:
            A GeoJSON object representing the geographic extent
        """
        pass


class PolygonalExtentCalculator(SpatialExtentCalculator):
    """
    Calculates a bounding box as a GeoJSON Polygon from a set of locations.

    This strategy creates a rectangular bounding box that encompasses all points.
    """

    def calculate_extent(self, things: list[Thing]) -> Polygon:
        """
        Calculate the geographic bounding box from a set of locations.

        Args:
            things: List of Thing objects with location data

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
            for thing in things
            if thing.location
            for loc in thing.location  # a thing can have many locations
            for coord in loc.get_coordinates()  # a location can be have many coord
        }

        if not locations:
            raise ValueError("Locations cannot be extracted from Things")

        # Update bounds for each location
        for lng, lat in locations:
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

    def calculate_extent(self, things: list[Thing]) -> FeatureCollection:
        geometries: list = []
        for thing in things:
            for loc in thing.location:
                geometries.append(loc.location)

        return FeatureCollection(geometries)
