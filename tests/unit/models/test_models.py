from datetime import datetime, timezone

import pytest
from geojson import Feature, Point
from pydantic import ValidationError

from wrench.models import CommonMetadata, Device, Group, Location, TimeFrame


class TestLocation:
    def test_create_from_point_dict(self):
        loc = Location(
            encoding_type="application/geo+json",
            location={"type": "Point", "coordinates": [11.5, 48.1]},
        )
        assert loc.location is not None

    def test_create_from_feature_dict(self):
        loc = Location(
            encoding_type="application/geo+json",
            location={
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [11.5, 48.1]},
                "properties": {},
            },
        )
        assert loc.location is not None

    def test_create_from_polygon_dict(self):
        loc = Location(
            encoding_type="application/geo+json",
            location={
                "type": "Polygon",
                "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
            },
        )
        assert loc.location is not None

    def test_create_from_geojson_object(self):
        point = Point([11.5, 48.1])
        loc = Location(
            encoding_type="application/geo+json",
            location=Feature(geometry=point, properties={}),
        )
        assert loc.location is not None

    def test_missing_type_field_raises(self):
        with pytest.raises(ValidationError):
            Location(
                encoding_type="application/geo+json",
                location={"coordinates": [11.5, 48.1]},
            )

    def test_invalid_type_raises(self):
        with pytest.raises(ValidationError):
            Location(
                encoding_type="application/geo+json",
                location="not-geojson",
            )

    def test_get_coordinates_point(self):
        loc = Location(
            encoding_type="application/geo+json",
            location={"type": "Point", "coordinates": [11.576, 48.137]},
        )
        coords = loc.get_coordinates()
        assert len(coords) >= 1
        assert coords[0] == (11.576, 48.137)

    def test_get_coordinates_polygon(self):
        loc = Location(
            encoding_type="application/geo+json",
            location={
                "type": "Polygon",
                "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
            },
        )
        coords = loc.get_coordinates()
        assert len(coords) == 5


class TestTimeFrame:
    def test_creation(self):
        tf = TimeFrame(
            start_time=datetime(2023, 1, 1, tzinfo=timezone.utc),
            latest_time=datetime(2024, 6, 15, tzinfo=timezone.utc),
        )
        assert tf.start_time.year == 2023
        assert tf.latest_time.year == 2024


class TestDevice:
    @pytest.fixture()
    def device_a(self, make_device):
        return make_device(id="dev-a", name="Device A")

    @pytest.fixture()
    def device_a_copy(self, make_device):
        return make_device(id="dev-a", name="Device A Different Name")

    @pytest.fixture()
    def device_b(self, make_device):
        return make_device(id="dev-b", name="Device B")

    def test_eq_same_id(self, device_a, device_a_copy):
        assert device_a == device_a_copy

    def test_neq_different_id(self, device_a, device_b):
        assert device_a != device_b

    def test_eq_not_device_returns_not_implemented(self, device_a):
        result = device_a.__eq__("not a device")
        assert result is NotImplemented

    def test_hash_same_id(self, device_a, device_a_copy):
        assert hash(device_a) == hash(device_a_copy)

    def test_hash_different_id(self, device_a, device_b):
        assert hash(device_a) != hash(device_b)

    def test_hash_usable_in_set(self, device_a, device_a_copy, device_b):
        device_set = {device_a, device_a_copy, device_b}
        assert len(device_set) == 2

    def test_to_string_includes_fields(self, device_a):
        result = device_a.to_string()
        assert "dev-a" in result
        assert "Device A" in result

    def test_to_string_with_exclude(self, device_a):
        result = device_a.to_string(exclude=["id", "name"])
        assert "dev-a" not in result
        assert "Device A" not in result

    def test_creation_with_all_fields(self, make_location, make_timeframe):
        device = Device(
            id="full-device",
            name="Full Device",
            description="A fully specified device",
            datastreams={"Stream1", "Stream2"},
            sensors={"Sensor1"},
            observed_properties={"Prop1", "Prop2"},
            locations=[make_location()],
            time_frame=make_timeframe(),
            properties={"key": "value"},
        )
        assert device.id == "full-device"
        assert len(device.datastreams) == 2

    def test_creation_with_none_timeframe(self, make_location):
        device = Device(
            id="no-tf",
            name="No TimeFrame",
            description="Device without timeframe",
            datastreams=set(),
            sensors=set(),
            observed_properties=set(),
            locations=[make_location()],
            time_frame=None,
        )
        assert device.time_frame is None


class TestCommonMetadata:
    def test_required_fields_only(self):
        meta = CommonMetadata(
            identifier="test-id",
            title="Test Title",
            description="Test Description",
            endpoint_urls=["https://example.com"],
            source_type="sensorthings",
        )
        assert meta.identifier == "test-id"
        assert meta.spatial_extent == ""
        assert meta.temporal_extent is None
        assert meta.tags == []
        assert meta.keywords == []
        assert meta.owner is None

    def test_all_fields(self, make_timeframe):
        tf = make_timeframe()
        meta = CommonMetadata(
            identifier="full-id",
            title="Full Title",
            description="Full Description",
            endpoint_urls=["https://example.com", "https://example2.com"],
            source_type="sensorthings",
            spatial_extent="POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))",
            temporal_extent=tf,
            tags=["tag1", "tag2"],
            keywords=["kw1"],
            thematic_groups=["environment"],
            last_updated=datetime(2024, 1, 1, tzinfo=timezone.utc),
            update_frequency="daily",
            owner="test-org",
            license="CC-BY-4.0",
        )
        assert len(meta.endpoint_urls) == 2
        assert meta.owner == "test-org"
        assert meta.license == "CC-BY-4.0"


class TestGroup:
    def test_creation(self, make_device):
        devices = [make_device(id=f"d-{i}") for i in range(3)]
        group = Group(name="Test Group", devices=devices)
        assert group.name == "Test Group"
        assert len(group.devices) == 3
        assert group.keywords == []
        assert group.parent_classes == set()

    def test_with_parent_classes(self, make_device):
        group = Group(
            name="Env Group",
            devices=[make_device()],
            parent_classes={"Environment", "Health"},
        )
        assert "Environment" in group.parent_classes

    def test_representative_devices_max_three(self, make_device):
        devices = [
            make_device(
                id=f"d-{i}",
                datastreams={f"stream-{i}"},
            )
            for i in range(5)
        ]
        group = Group(name="Large", devices=devices)
        reps = group.representative_devices
        assert len(reps) <= 3

    def test_representative_devices_unique_datastreams(self, make_device):
        d1 = make_device(id="d-1", datastreams={"A", "B"})
        d2 = make_device(id="d-2", datastreams={"A", "C"})
        group = Group(name="Overlap", devices=[d1, d2])
        reps = group.representative_devices
        assert len(reps) >= 1
        assert len(reps) <= 3
