import json
from pathlib import Path

import pytest
import requests as _requests_module
import responses

from wrench.harvester.sensorthings.client import (
    ENDPOINT_WITH_MULTIDATASTREAM,
    SensorThingsClient,
)
from wrench.harvester.sensorthings.config import PaginationConfig
from wrench.harvester.sensorthings.models import Thing

FIXTURES_DIR = (
    Path(__file__).parent.parent.parent / "fixtures" / "sensorthings_responses"
)
BASE_URL = "https://example.com/FROST/v1.1"


def _prepared_url():
    """Return the actual URL that requests.get() will send.

    The ENDPOINT constants contain newlines which get percent-encoded
    by requests. We need the exact encoded URL for mock matching.
    """
    raw_url = f"{BASE_URL}/{ENDPOINT_WITH_MULTIDATASTREAM}"
    req = _requests_module.Request("GET", raw_url)
    return req.prepare().url


@pytest.fixture(scope="module")
def page1_json():
    with open(FIXTURES_DIR / "things_page1.json") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def page2_json():
    with open(FIXTURES_DIR / "things_page2.json") as f:
        return json.load(f)


def _make_client(base_url=BASE_URL, config=None):
    return SensorThingsClient(
        base_url=base_url,
        config=config or PaginationConfig(page_delay=0),
    )


class TestFetchThingsSinglePage:
    @responses.activate
    def test_single_page_returns_all_things(self, page1_json):
        single_page = {**page1_json, "@iot.nextLink": None}
        responses.add(
            responses.GET,
            _prepared_url(),
            json=single_page,
            status=200,
        )
        client = _make_client()
        things = client.fetch_things()
        assert len(things) == 2
        assert all(isinstance(t, Thing) for t in things)

    @responses.activate
    def test_single_page_thing_ids(self, page1_json):
        single_page = {**page1_json}
        single_page.pop("@iot.nextLink", None)
        responses.add(
            responses.GET,
            _prepared_url(),
            json=single_page,
            status=200,
        )
        client = _make_client()
        things = client.fetch_things()
        ids = {t.id for t in things}
        assert ids == {"1", "2"}


class TestFetchThingsMultiPage:
    @responses.activate
    def test_multi_page_pagination(self, page1_json, page2_json):
        responses.add(
            responses.GET,
            _prepared_url(),
            json=page1_json,
            status=200,
        )
        responses.add(
            responses.GET,
            page1_json["@iot.nextLink"],
            json=page2_json,
            status=200,
        )
        client = _make_client()
        things = client.fetch_things()
        assert len(things) == 3
        ids = {t.id for t in things}
        assert ids == {"1", "2", "3"}

    @responses.activate
    def test_pagination_respects_limit(self, page1_json):
        responses.add(
            responses.GET,
            _prepared_url(),
            json=page1_json,
            status=200,
        )
        client = _make_client()
        things = client.fetch_things(limit=1)
        assert len(things) == 1
        assert things[0].id == "1"


class TestFetchThingsEmptyResponse:
    @responses.activate
    def test_empty_value_list(self):
        responses.add(
            responses.GET,
            _prepared_url(),
            json={"value": []},
            status=200,
        )
        client = _make_client()
        things = client.fetch_things()
        assert things == []


class TestPaginateErrorHandling:
    @responses.activate
    def test_request_exception_stops_pagination(self):
        responses.add(
            responses.GET,
            _prepared_url(),
            body=responses.ConnectionError("Connection refused"),
        )
        client = _make_client()
        things = client.fetch_things()
        assert things == []

    @responses.activate
    def test_http_error_stops_pagination(self):
        responses.add(
            responses.GET,
            _prepared_url(),
            json={"error": "internal server error"},
            status=500,
        )
        client = _make_client()
        things = client.fetch_things()
        assert things == []

    @responses.activate
    def test_missing_value_field_stops_pagination(self):
        responses.add(
            responses.GET,
            _prepared_url(),
            json={"results": [{"@iot.id": "1", "name": "X"}]},
            status=200,
        )
        client = _make_client()
        things = client.fetch_things()
        assert things == []

    @responses.activate
    def test_validation_failure_skips_item(self, page1_json):
        """Items that fail Pydantic validation are skipped, not fatal."""
        bad_page = {
            "value": [
                {"@iot.id": "1"},  # Missing required fields
                page1_json["value"][0],  # Valid item
            ]
        }
        responses.add(
            responses.GET,
            _prepared_url(),
            json=bad_page,
            status=200,
        )
        client = _make_client()
        things = client.fetch_things()
        assert len(things) >= 1

    @responses.activate
    def test_error_on_second_page_returns_first_page_results(self, page1_json):
        responses.add(
            responses.GET,
            _prepared_url(),
            json=page1_json,
            status=200,
        )
        responses.add(
            responses.GET,
            page1_json["@iot.nextLink"],
            body=responses.ConnectionError("timeout"),
        )
        client = _make_client()
        things = client.fetch_things()
        assert len(things) == 2


class TestClientInit:
    def test_default_pagination_config(self):
        client = SensorThingsClient(base_url=BASE_URL, config=None)
        assert client.config.page_delay == 0.1
        assert client.config.timeout == 60

    def test_custom_pagination_config(self):
        config = PaginationConfig(page_delay=0.5, timeout=30, batch_size=50)
        client = SensorThingsClient(base_url=BASE_URL, config=config)
        assert client.config.page_delay == 0.5
        assert client.config.timeout == 30
        assert client.config.batch_size == 50
