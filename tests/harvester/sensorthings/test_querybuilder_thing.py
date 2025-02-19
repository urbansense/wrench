from urllib.parse import unquote_plus

import pytest

from wrench.harvester.sensorthings.querybuilder import ThingQuery


@pytest.fixture
def thing_query():
    return ThingQuery()


def test_build(thing_query):
    query = thing_query.build()
    assert query == "Things?"


def test_expand_locations(thing_query):
    query = thing_query.expand("Locations").build()
    assert unquote_plus(query) == "Things?$expand=Locations"


def test_expand_datastreams(thing_query):
    query = thing_query.expand("Datastreams").build()
    assert unquote_plus(query) == "Things?$expand=Datastreams"


def test_nested_expansions(thing_query):
    query = thing_query.expand("Datastreams", {"Sensor"}).build()
    assert unquote_plus(query) == "Things?$expand=Datastreams($expand=Sensor)"


def test_multiple_expansions(thing_query):
    query = thing_query.expand("Locations").expand("Datastreams").build()
    assert unquote_plus(query) in (
        "Things?$expand=Locations,Datastreams",
        "Things?$expand=Datastreams,Locations",
    )


def test_invalid_expansion(thing_query):
    with pytest.raises(ValueError) as exc_info:
        thing_query.expand("InvalidEntity")
    assert "not a valid expansion" in str(exc_info.value)


def test_invalid_nested_expansion(thing_query):
    with pytest.raises(ValueError) as exc_info:
        thing_query.expand("Datastreams", {"InvalidNested"})
    assert "Invalid nested expansion(s)" in str(exc_info.value)


def test_nested_expansion_on_unsupported_entity(thing_query):
    with pytest.raises(ValueError) as exc_info:
        thing_query.expand("Locations", {"Something"})
    assert "does not support nested expansions" in str(exc_info.value)


def test_complex_query(thing_query):
    query = (
        thing_query.expand("Locations")
        .expand("Datastreams", {"Sensor"})
        .limit(10)
        .build()
    )
    assert unquote_plus(query) in (
        "Things?$expand=Locations,Datastreams($expand=Sensor)&$top=10",
        "Things?$expand=Datastreams($expand=Sensor),Locations&$top=10",
    )


def test_simple_filter(thing_query):
    query = thing_query.filter(ThingQuery.property("name").eq("test")).build()
    assert unquote_plus(query) == "Things?$filter=name eq 'test'"


def test_numeric_filter(thing_query):
    query = thing_query.filter(ThingQuery.property("properties/value").gt(20)).build()
    assert unquote_plus(query) == "Things?$filter=properties/value gt 20"


def test_combined_filter_and(thing_query):
    query = thing_query.filter(
        (ThingQuery.property("name").contains("sensor"))
        & (ThingQuery.property("properties/status").eq("active"))
    ).build()
    assert (
        unquote_plus(query)
        == "Things?$filter=(substringof(name, 'sensor') and properties/status eq 'active')"
    )


def test_combined_filter_or(thing_query):
    query = thing_query.filter(
        (ThingQuery.property("name").contains("temperature"))
        | (ThingQuery.property("name").contains("humidity"))
    ).build()
    assert (
        unquote_plus(query)
        == "Things?$filter=(substringof(name, 'temperature') or substringof(name, 'humidity'))"
    )


def test_complex_filter(thing_query):
    query = thing_query.filter(
        (ThingQuery.property("name").contains("sensor"))
        & (
            (ThingQuery.property("properties/value").gt(20))
            | (ThingQuery.property("properties/status").eq("active"))
        )
    ).build()
    assert (
        unquote_plus(query)
        == "Things?$filter=(substringof(name, 'sensor') and (properties/value gt 20 or properties/status eq 'active'))"
    )


def test_filter_with_expand(thing_query):
    query = (
        thing_query.expand("Locations")
        .filter(ThingQuery.property("name").contains("sensor"))
        .build()
    )
    assert (
        unquote_plus(query)
        == "Things?$expand=Locations&$filter=substringof(name, 'sensor')"
    )
