from unittest.mock import MagicMock, call, patch

import pytest
import requests

from wrench.harvester.sensorthings.client import SensorThingsClient
from wrench.harvester.sensorthings.config import PaginationConfig
from wrench.harvester.sensorthings.models import Thing


@pytest.fixture
def base_url():
    return "https://example.com/api/v1.1"


@pytest.fixture
def pagination_config():
    return PaginationConfig(page_delay=0.1, timeout=30, batch_size=100)


@pytest.fixture
def client(base_url, pagination_config):
    return SensorThingsClient(base_url=base_url, config=pagination_config)


def test_init_with_config(base_url, pagination_config):
    """Test initialization with provided config."""
    client = SensorThingsClient(base_url=base_url, config=pagination_config)
    assert client.base_url == base_url
    assert client.config == pagination_config


def test_init_without_config(base_url):
    """Test initialization without config (should use default)."""
    client = SensorThingsClient(base_url=base_url, config=None)
    assert client.base_url == base_url
    assert isinstance(client.config, PaginationConfig)
    assert client.config.page_delay == 0.1  # Default value
    assert client.config.timeout == 60  # Default value
    assert client.config.batch_size == 100  # Default value


@patch("wrench.harvester.sensorthings.client.requests.get")
@patch("wrench.harvester.sensorthings.client.time.sleep")
def test_fetch_items_single_page(
    mock_sleep, mock_get, client, base_url, pagination_config
):
    """Test fetching items when API returns a single page of results."""
    # Setup mock response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "value": [
            {"@iot.id": "1", "name": "Thing 1", "description": "Test Thing 1"},
            {"@iot.id": "2", "name": "Thing 2", "description": "Test Thing 2"},
        ]
    }
    mock_get.return_value = mock_response

    # Execute
    result = client.fetch_items()

    # Verify
    assert len(result) == 2
    assert isinstance(result[0], Thing)
    assert result[0].id == "1"
    assert result[0].name == "Thing 1"

    mock_get.assert_called_once_with(
        f"{base_url}/Things?$expand=Locations,Datastreams($expand=Sensor)",
        timeout=pagination_config.timeout,
    )
    mock_sleep.assert_not_called()  # No pagination, so no sleep


@patch("wrench.harvester.sensorthings.client.requests.get")
@patch("wrench.harvester.sensorthings.client.time.sleep")
def test_fetch_items_with_pagination(
    mock_sleep, mock_get, client, base_url, pagination_config
):
    """Test fetching items when API returns multiple pages of results."""
    # Setup mock responses for two pages
    first_response = MagicMock()
    first_response.json.return_value = {
        "value": [{"@iot.id": "1", "name": "Thing 1", "description": "Test Thing 1"}],
        "@iot.nextLink": "https://example.com/api/v1.1/Things?$skip=1",
    }

    second_response = MagicMock()
    second_response.json.return_value = {
        "value": [{"@iot.id": "2", "name": "Thing 2", "description": "Test Thing 2"}]
    }

    mock_get.side_effect = [first_response, second_response]

    # Execute
    result = client.fetch_items()

    # Verify
    assert len(result) == 2
    assert result[0].id == "1"
    assert result[1].id == "2"

    assert mock_get.call_count == 2
    mock_get.assert_has_calls(
        [
            call(
                f"{base_url}/Things?$expand=Locations,Datastreams($expand=Sensor)",
                timeout=pagination_config.timeout,
            ),
            call(
                "https://example.com/api/v1.1/Things?$skip=1",
                timeout=pagination_config.timeout,
            ),
        ]
    )
    mock_sleep.assert_called_once_with(pagination_config.page_delay)


@patch("wrench.harvester.sensorthings.client.requests.get")
def test_fetch_items_with_limit(mock_get, client):
    """Test fetching items with a specific limit."""
    # Setup mock response with more items than the limit
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "value": [
            {"@iot.id": "1", "name": "Thing 1", "description": "Test Thing 1"},
            {"@iot.id": "2", "name": "Thing 2", "description": "Test Thing 2"},
            {"@iot.id": "3", "name": "Thing 3", "description": "Test Thing 3"},
        ]
    }
    mock_get.return_value = mock_response

    # Execute with limit=2
    result = client.fetch_items(limit=2)

    # Verify only 2 items are returned
    assert len(result) == 2
    assert result[0].id == "1"
    assert result[1].id == "2"


@patch("wrench.harvester.sensorthings.client.requests.get")
def test_fetch_items_validation_error(mock_get, client):
    """Test handling validation errors for invalid items."""
    # Setup mock response with one valid and one invalid item
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "value": [
            {"@iot.id": "1", "name": "Thing 1", "description": "Test Thing 1"},
            {"missing_required_fields": True},  # This should fail validation
        ]
    }
    mock_get.return_value = mock_response

    # Execute
    result = client.fetch_items()

    # Verify only the valid item is returned
    assert len(result) == 1
    assert result[0].id == "1"


@patch("wrench.harvester.sensorthings.client.requests.get")
def test_fetch_items_empty_response(mock_get, client):
    """Test handling an empty response from the API."""
    # Setup mock response with no items
    mock_response = MagicMock()
    mock_response.json.return_value = {"value": []}
    mock_get.return_value = mock_response

    # Execute
    result = client.fetch_items()

    # Verify empty list is returned
    assert len(result) == 0


@patch("wrench.harvester.sensorthings.client.requests.get")
def test_fetch_items_invalid_response_format(mock_get, client):
    """Test handling invalid response format (missing 'value' field)."""
    # Setup mock response with invalid format
    mock_response = MagicMock()
    mock_response.json.return_value = {"invalid_format": True}
    mock_get.return_value = mock_response

    # Execute
    result = client.fetch_items()

    # Verify empty list is returned
    assert len(result) == 0


@patch("wrench.harvester.sensorthings.client.requests.get")
def test_fetch_items_http_error(mock_get, client):
    """Test handling HTTP error from the API."""
    # Setup mock to raise a RequestException
    mock_get.side_effect = requests.RequestException("HTTP Error")

    # Execute
    result = client.fetch_items()

    # Verify empty list is returned
    assert len(result) == 0


@patch("wrench.harvester.sensorthings.client.requests.get")
@patch("wrench.harvester.sensorthings.client.time.sleep")
def test_pagination_stops_at_limit_across_pages(mock_sleep, mock_get, client):
    """Test that pagination stops when limit is reached across multiple pages."""
    # Setup mock responses for two pages, but we'll set limit=2
    first_response = MagicMock()
    first_response.json.return_value = {
        "value": [
            {"@iot.id": "1", "name": "Thing 1", "description": "Test Thing 1"},
            {"@iot.id": "2", "name": "Thing 2", "description": "Test Thing 2"},
        ],
        "@iot.nextLink": "https://example.com/api/v1.1/Things?$skip=2",
    }

    second_response = MagicMock()
    second_response.json.return_value = {
        "value": [{"@iot.id": "3", "name": "Thing 3", "description": "Test Thing 3"}]
    }

    mock_get.side_effect = [first_response, second_response]

    # Execute with limit=2 which should be reached on the first page
    result = client.fetch_items(limit=2)

    # Verify
    assert len(result) == 2
    assert mock_get.call_count == 1  # Only the first page should be requested


@patch("wrench.harvester.sensorthings.client.requests.get")
def test_response_raise_for_status(mock_get, client):
    """Test that response.raise_for_status() is called."""
    # Setup mock response
    mock_response = MagicMock()
    mock_response.json.return_value = {"value": []}
    mock_get.return_value = mock_response

    # Execute
    client.fetch_items()

    # Verify raise_for_status was called
    mock_response.raise_for_status.assert_called_once()


@patch("wrench.harvester.sensorthings.client.requests.get")
def test_fetch_items_with_limit_spanning_pages(mock_get, client, pagination_config):
    """Test fetching items with a limit that spans multiple pages."""
    # Setup mock responses
    first_response = MagicMock()
    first_response.json.return_value = {
        "value": [
            {"@iot.id": "1", "name": "Thing 1", "description": "Test Thing 1"},
            {"@iot.id": "2", "name": "Thing 2", "description": "Test Thing 2"},
        ],
        "@iot.nextLink": "https://example.com/api/v1.1/Things?$skip=2",
    }

    second_response = MagicMock()
    second_response.json.return_value = {
        "value": [
            {"@iot.id": "3", "name": "Thing 3", "description": "Test Thing 3"},
            {"@iot.id": "4", "name": "Thing 4", "description": "Test Thing 4"},
        ]
    }

    mock_get.side_effect = [first_response, second_response]

    # Execute with limit=3 which should span the first and second pages
    result = client.fetch_items(limit=3)

    # Verify
    assert len(result) == 3
    assert result[0].id == "1"
    assert result[1].id == "2"
    assert result[2].id == "3"
    assert mock_get.call_count == 2  # Both pages should be requested
