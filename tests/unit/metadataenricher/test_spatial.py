import pytest
from geojson import FeatureCollection, Polygon

from wrench.metadataenricher.sensorthings.spatial import (
    GeometryCollector,
    PolygonalExtentCalculator,
)


class TestPolygonalExtentCalculator:
    def test_single_point_produces_degenerate_polygon(self, make_device):
        calc = PolygonalExtentCalculator()
        device = make_device(id="d-1")
        result = calc.calculate_extent([device])
        assert isinstance(result, Polygon)
        # Single point => bounding box is a degenerate rectangle
        coords = result["coordinates"][0]
        assert len(coords) == 5  # Closed polygon
        assert coords[0] == coords[-1]  # First == last

    def test_two_points_bounding_box(self, make_device, make_location):
        calc = PolygonalExtentCalculator()
        loc1 = make_location(lng=10.0, lat=47.0)
        loc2 = make_location(lng=12.0, lat=49.0)
        d1 = make_device(id="d-1", locations=[loc1])
        d2 = make_device(id="d-2", locations=[loc2])
        result = calc.calculate_extent([d1, d2])
        coords = result["coordinates"][0]
        # Bounding box corners
        lngs = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        assert min(lngs) == 10.0
        assert max(lngs) == 12.0
        assert min(lats) == 47.0
        assert max(lats) == 49.0

    def test_multiple_devices_extent(self, make_device, make_location):
        calc = PolygonalExtentCalculator()
        devices = [
            make_device(id="d-1", locations=[make_location(lng=10.0, lat=47.0)]),
            make_device(id="d-2", locations=[make_location(lng=11.0, lat=48.0)]),
            make_device(id="d-3", locations=[make_location(lng=12.0, lat=49.0)]),
        ]
        result = calc.calculate_extent(devices)
        coords = result["coordinates"][0]
        lngs = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        assert min(lngs) == 10.0
        assert max(lngs) == 12.0
        assert min(lats) == 47.0
        assert max(lats) == 49.0

    def test_empty_devices_raises(self):
        calc = PolygonalExtentCalculator()
        with pytest.raises(ValueError, match="Locations cannot be extracted"):
            calc.calculate_extent([])

    def test_device_with_no_locations_raises(self):
        calc = PolygonalExtentCalculator()
        from wrench.models import Device

        device = Device(
            id="d-1",
            name="No Location",
            description="Device without location",
            datastreams={"T"},
            sensors={"S"},
            observed_properties={"T"},
            locations=[],
            time_frame=None,
        )
        with pytest.raises(ValueError, match="Locations cannot be extracted"):
            calc.calculate_extent([device])

    def test_polygon_is_closed(self, make_device):
        calc = PolygonalExtentCalculator()
        device = make_device(id="d-1")
        result = calc.calculate_extent([device])
        coords = result["coordinates"][0]
        assert coords[0] == coords[-1]

    def test_result_is_geojson_polygon(self, make_device):
        calc = PolygonalExtentCalculator()
        device = make_device(id="d-1")
        result = calc.calculate_extent([device])
        assert result["type"] == "Polygon"

    def test_device_with_multiple_locations(self, make_device, make_location):
        calc = PolygonalExtentCalculator()
        loc1 = make_location(lng=10.0, lat=47.0)
        loc2 = make_location(lng=12.0, lat=49.0)
        device = make_device(id="d-1", locations=[loc1, loc2])
        result = calc.calculate_extent([device])
        coords = result["coordinates"][0]
        lngs = [c[0] for c in coords]
        assert min(lngs) == 10.0
        assert max(lngs) == 12.0


class TestGeometryCollector:
    def test_single_device_returns_feature_collection(self, make_device):
        collector = GeometryCollector()
        device = make_device(id="d-1")
        result = collector.calculate_extent([device])
        assert isinstance(result, FeatureCollection)
        assert result["type"] == "FeatureCollection"

    def test_features_count_matches_locations(self, make_device, make_location):
        collector = GeometryCollector()
        loc1 = make_location(lng=10.0, lat=47.0)
        loc2 = make_location(lng=12.0, lat=49.0)
        d1 = make_device(id="d-1", locations=[loc1])
        d2 = make_device(id="d-2", locations=[loc2])
        result = collector.calculate_extent([d1, d2])
        assert len(result["features"]) == 2

    def test_empty_devices(self):
        collector = GeometryCollector()
        result = collector.calculate_extent([])
        assert isinstance(result, FeatureCollection)
        assert len(result["features"]) == 0

    def test_device_with_multiple_locations(self, make_device, make_location):
        collector = GeometryCollector()
        loc1 = make_location(lng=10.0, lat=47.0)
        loc2 = make_location(lng=12.0, lat=49.0)
        device = make_device(id="d-1", locations=[loc1, loc2])
        result = collector.calculate_extent([device])
        assert len(result["features"]) == 2
