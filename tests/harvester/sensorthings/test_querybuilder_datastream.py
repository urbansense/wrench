from urllib.parse import unquote_plus

import pytest

from wrench.harvester.sensorthings.querybuilder import DatastreamQuery


@pytest.fixture
def datastream_query():
    return DatastreamQuery()


def test_build(datastream_query):
    query = datastream_query.build()
    assert query == "Datastreams?"


def test_expand_observed_property(datastream_query):
    query = datastream_query.expand("ObservedProperty").build()
    assert unquote_plus(query) == "Datastreams?$expand=ObservedProperty"


def test_expand_sensor(datastream_query):
    query = datastream_query.expand("Sensor").build()
    assert unquote_plus(query) == "Datastreams?$expand=Sensor"


def test_nested_expansions(datastream_query):
    query = datastream_query.expand("Thing", {"Locations"}).build()
    assert unquote_plus(query) == "Datastreams?$expand=Thing($expand=Locations)"


def test_multiple_expansions(datastream_query):
    query = datastream_query.expand("Thing").expand("Sensor").build()
    assert unquote_plus(query) in (
        "Datastreams?$expand=Thing,SensorDatastreams?$expand=Sensor,Thing"
    )


def test_invalid_expansion(datastream_query):
    with pytest.raises(ValueError) as exc_info:
        datastream_query.expand("InvalidEntity")
    assert "not a valid expansion" in str(exc_info.value)


def test_invalid_nested_expansion(datastream_query):
    with pytest.raises(ValueError) as exc_info:
        datastream_query.expand("Thing", {"InvalidNested"})
    assert "Invalid nested expansion(s)" in str(exc_info.value)


def test_nested_expansion_on_unsupported_entity(datastream_query):
    with pytest.raises(ValueError) as exc_info:
        datastream_query.expand("Sensor", {"Something"})
    assert "does not support nested expansions" in str(exc_info.value)


def test_complex_query(datastream_query):
    query = (
        datastream_query.expand("Sensor")
        .expand("Thing", {"Locations"})
        .limit(10)
        .build()
    )
    assert unquote_plus(query) in (
        "Datastreams?$expand=Sensor,Thing($expand=Locations)&$top=10",
        "Datastreams?$expand=Thing($expand=Locations),Sensor&$top=10",
    )


def test_simple_filter(datastream_query):
    query = datastream_query.filter(DatastreamQuery.property("name").eq("test")).build()
    assert unquote_plus(query) == "Datastreams?$filter=name eq 'test'"


def test_numeric_filter(datastream_query):
    query = datastream_query.filter(
        DatastreamQuery.property("properties/value").gt(20)
    ).build()
    assert unquote_plus(query) == "Datastreams?$filter=properties/value gt 20"


def test_combined_filter_and(datastream_query):
    query = datastream_query.filter(
        (DatastreamQuery.property("name").contains("sensor"))
        & (DatastreamQuery.property("properties/status").eq("active"))
    ).build()
    assert (
        unquote_plus(query)
        == "Datastreams?$filter=(substringof(name, 'sensor') and properties/status eq 'active')"
    )


def test_combined_filter_or(datastream_query):
    query = datastream_query.filter(
        (DatastreamQuery.property("name").contains("temperature"))
        | (DatastreamQuery.property("name").contains("humidity"))
    ).build()
    assert (
        unquote_plus(query)
        == "Datastreams?$filter=(substringof(name, 'temperature') or substringof(name, 'humidity'))"
    )


def test_complex_filter(datastream_query):
    query = datastream_query.filter(
        (DatastreamQuery.property("name").contains("sensor"))
        & (
            (DatastreamQuery.property("properties/value").gt(20))
            | (DatastreamQuery.property("properties/status").eq("active"))
        )
    ).build()
    assert (
        unquote_plus(query)
        == "Datastreams?$filter=(substringof(name, 'sensor') and (properties/value gt 20 or properties/status eq 'active'))"
    )


def test_filter_with_expand(datastream_query):
    query = (
        datastream_query.expand("Sensor")
        .filter(DatastreamQuery.property("name").contains("sensor"))
        .build()
    )
    assert (
        unquote_plus(query)
        == "Datastreams?$expand=Sensor&$filter=substringof(name, 'sensor')"
    )
