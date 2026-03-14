from datetime import datetime, timezone

import pytest

from wrench.models import CommonMetadata, Device, Group, Location, TimeFrame


@pytest.fixture(scope="session")
def make_location():
    def _make_location(lng=11.5, lat=48.1):
        return Location(
            encoding_type="application/geo+json",
            location={
                "type": "Point",
                "coordinates": [lng, lat],
            },
        )

    return _make_location


@pytest.fixture(scope="session")
def make_timeframe():
    def _make_timeframe(
        start=None,
        end=None,
    ):
        start = start or datetime(2023, 1, 1, tzinfo=timezone.utc)
        end = end or datetime(2024, 6, 15, tzinfo=timezone.utc)
        return TimeFrame(start_time=start, latest_time=end)

    return _make_timeframe


@pytest.fixture(scope="session")
def make_device(make_location, make_timeframe):
    def _make_device(
        id="thing-1",
        name="Temperature Sensor",
        description="A temperature sensor",
        datastreams=None,
        sensors=None,
        observed_properties=None,
        locations=None,
        time_frame="default",
        properties=None,
    ):
        return Device(
            id=id,
            name=name,
            description=description,
            datastreams=datastreams or {"Temperature"},
            sensors=sensors or {"DHT22"},
            observed_properties=observed_properties or {"Temperature"},
            locations=locations or [make_location()],
            time_frame=make_timeframe() if time_frame == "default" else time_frame,
            properties=properties,
        )

    return _make_device


@pytest.fixture(scope="session")
def make_group(make_device):
    def _make_group(
        name="Environment Sensors",
        devices=None,
        keywords=None,
        parent_classes=None,
    ):
        devices = devices or [make_device()]
        return Group(
            name=name,
            devices=devices,
            keywords=keywords or [],
            parent_classes=parent_classes or set(),
        )

    return _make_group


@pytest.fixture(scope="session")
def make_common_metadata():
    def _make_common_metadata(**overrides):
        defaults = {
            "identifier": "test-service",
            "title": "Test Service",
            "description": "A test service",
            "endpoint_urls": ["https://example.com/api"],
            "source_type": "sensorthings",
        }
        defaults.update(overrides)
        return CommonMetadata(**defaults)

    return _make_common_metadata


@pytest.fixture(scope="module")
def sample_devices(make_device, make_location, make_timeframe):
    return [
        make_device(
            id="thing-1",
            name="Temperature Sensor Munich",
            description="Measures air temperature in Munich city center",
            datastreams={"Temperature", "Humidity"},
            sensors={"DHT22", "BME280"},
            observed_properties={"Temperature", "Humidity"},
            locations=[make_location(11.576, 48.137)],
            time_frame=make_timeframe(
                datetime(2022, 3, 1, tzinfo=timezone.utc),
                datetime(2024, 6, 15, tzinfo=timezone.utc),
            ),
        ),
        make_device(
            id="thing-2",
            name="Air Quality Monitor",
            description="PM2.5 and PM10 air quality monitoring station",
            datastreams={"PM2.5", "PM10"},
            sensors={"SDS011"},
            observed_properties={"PM2.5", "PM10"},
            locations=[make_location(11.582, 48.145)],
            time_frame=make_timeframe(
                datetime(2023, 1, 15, tzinfo=timezone.utc),
                datetime(2024, 8, 20, tzinfo=timezone.utc),
            ),
        ),
        make_device(
            id="thing-3",
            name="Noise Level Sensor",
            description="Monitors urban noise levels in dB",
            datastreams={"Noise_Level"},
            sensors={"SPH0645"},
            observed_properties={"Noise Level"},
            locations=[make_location(11.590, 48.150)],
            time_frame=make_timeframe(
                datetime(2023, 6, 1, tzinfo=timezone.utc),
                datetime(2024, 12, 1, tzinfo=timezone.utc),
            ),
        ),
    ]


@pytest.fixture(scope="module")
def sample_groups(sample_devices):
    return [
        Group(
            name="Weather Monitoring",
            devices=[sample_devices[0]],
            keywords=["temperature", "humidity"],
            parent_classes={"Environment"},
        ),
        Group(
            name="Air Quality",
            devices=[sample_devices[1], sample_devices[2]],
            keywords=["air", "pollution", "noise"],
            parent_classes={"Environment", "Health"},
        ),
    ]
