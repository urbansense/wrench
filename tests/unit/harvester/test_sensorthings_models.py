import json
from pathlib import Path

import pytest

from wrench.harvester.sensorthings.models import (
    Datastream,
    Location,
    Sensor,
    Thing,
)

FIXTURES_DIR = (
    Path(__file__).parent.parent.parent / "fixtures" / "sensorthings_responses"
)


@pytest.fixture(scope="module")
def things_page1_json():
    with open(FIXTURES_DIR / "things_page1.json") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def multidatastreams_json():
    with open(FIXTURES_DIR / "multidatastreams.json") as f:
        return json.load(f)


class TestThingModelValidation:
    def test_parse_thing_from_api_json(self, things_page1_json):
        raw = things_page1_json["value"][0]
        thing = Thing.model_validate(raw)
        assert thing.id == "1"
        assert thing.name == "Weather Station Alpha"
        assert thing.description == "Rooftop weather station in city center"

    def test_iot_id_alias(self, things_page1_json):
        raw = things_page1_json["value"][0]
        thing = Thing.model_validate(raw)
        assert thing.id == "1"

    def test_locations_alias(self, things_page1_json):
        raw = things_page1_json["value"][0]
        thing = Thing.model_validate(raw)
        assert len(thing.location) == 1
        assert thing.location[0].name == "City Center Rooftop"

    def test_datastreams_alias(self, things_page1_json):
        raw = things_page1_json["value"][0]
        thing = Thing.model_validate(raw)
        assert len(thing.datastreams) == 2
        ds_names = {ds.name for ds in thing.datastreams}
        assert "Air Temperature" in ds_names
        assert "Relative Humidity" in ds_names

    def test_thing_with_no_datastreams(self):
        raw = {
            "@iot.id": "99",
            "name": "Empty Thing",
            "description": "No datastreams",
            "Locations": [],
        }
        thing = Thing.model_validate(raw)
        assert thing.datastreams == []

    def test_thing_properties(self, things_page1_json):
        raw = things_page1_json["value"][0]
        thing = Thing.model_validate(raw)
        assert thing.properties is not None
        assert thing.properties["owner"] == "City Council"

    def test_thing_null_properties(self, things_page1_json):
        raw = things_page1_json["value"][1]
        thing = Thing.model_validate(raw)
        assert thing.properties is None

    def test_thing_hash_consistency(self, things_page1_json):
        raw = things_page1_json["value"][0]
        t1 = Thing.model_validate(raw)
        t2 = Thing.model_validate(raw)
        assert t1.__hash__() == t2.__hash__()

    def test_multiple_things_parsed(self, things_page1_json):
        things = [Thing.model_validate(raw) for raw in things_page1_json["value"]]
        assert len(things) == 2
        ids = {t.id for t in things}
        assert ids == {"1", "2"}


class TestDatastreamModel:
    def test_parse_datastream(self, things_page1_json):
        raw_ds = things_page1_json["value"][0]["Datastreams"][0]
        ds = Datastream.model_validate(raw_ds)
        assert ds.id == "ds-1"
        assert ds.name == "Air Temperature"
        assert ds.phenomenon_time == "2022-01-15T00:00:00Z/2024-06-15T23:59:59Z"

    def test_datastream_sensor(self, things_page1_json):
        raw_ds = things_page1_json["value"][0]["Datastreams"][0]
        ds = Datastream.model_validate(raw_ds)
        assert ds.sensor.name == "DHT22"
        assert isinstance(ds.sensor, Sensor)

    def test_datastream_observed_property(self, things_page1_json):
        raw_ds = things_page1_json["value"][0]["Datastreams"][0]
        ds = Datastream.model_validate(raw_ds)
        assert ds.observed_property.name == "Temperature"

    def test_datastream_unit_of_measurement(self, things_page1_json):
        raw_ds = things_page1_json["value"][0]["Datastreams"][0]
        ds = Datastream.model_validate(raw_ds)
        assert ds.unit_of_measurement["name"] == "Celsius"


class TestMultiDatastreamModel:
    def test_parse_multidatastream(self, multidatastreams_json):
        raw_thing = multidatastreams_json["value"][0]
        thing = Thing.model_validate(raw_thing)
        assert len(thing.multidatastreams) == 1
        mds = thing.multidatastreams[0]
        assert mds.name == "Temperature and Humidity Combined"

    def test_multidatastream_observed_properties(self, multidatastreams_json):
        raw_thing = multidatastreams_json["value"][0]
        thing = Thing.model_validate(raw_thing)
        mds = thing.multidatastreams[0]
        assert mds.observed_properties is not None
        assert len(mds.observed_properties) == 2
        op_names = {op.name for op in mds.observed_properties}
        assert op_names == {"Temperature", "Humidity"}

    def test_multidatastream_sensor(self, multidatastreams_json):
        raw_thing = multidatastreams_json["value"][0]
        thing = Thing.model_validate(raw_thing)
        mds = thing.multidatastreams[0]
        assert mds.sensor.name == "BME280"


class TestLocationModel:
    def test_parse_location(self, things_page1_json):
        raw_loc = things_page1_json["value"][0]["Locations"][0]
        loc = Location.model_validate(raw_loc)
        assert loc.id == "loc-1"
        assert loc.name == "City Center Rooftop"

    def test_location_geojson(self, things_page1_json):
        raw_loc = things_page1_json["value"][0]["Locations"][0]
        loc = Location.model_validate(raw_loc)
        coords = loc.get_coordinates()
        assert len(coords) >= 1
        assert coords[0] == (11.576, 48.137)
