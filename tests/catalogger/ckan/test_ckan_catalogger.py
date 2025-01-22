import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from autoreg_metadata.catalogger.ckan.models import APIService, BaseDataset, DeviceGroup, SDDICategory
from autoreg_metadata.common.models import EndpointMetadata, TimeFrame, Coordinate
from autoreg_metadata.catalogger.ckan.register import CKANCatalogger


@pytest.fixture
def mock_ckan():
    with patch('ckanapi.RemoteCKAN') as mock:
        yield mock


@pytest.fixture
def sample_endpoint_metadata():
    return EndpointMetadata(
        endpoint_url="https://api.example.com",
        timeframe=TimeFrame(
            start_time=datetime(2024, 1, 1),
            latest_time=datetime(2024, 1, 31)
        ),
        geographical_extent=(
            Coordinate(longitude=10.0, latitude=50.0),
            Coordinate(longitude=11.0, latitude=51.0)
        ),
        sensor_types=["temperature", "humidity"],
        measurements=["celsius", "percent"],
        language="en",
        author="Test Author"
    )


@pytest.fixture
def sample_data():
    return {
        "temperature_sensors": ["sensor1", "sensor2"],
        "humidity_sensors": ["sensor3", "sensor4"]
    }


@pytest.fixture
def catalogger(mock_ckan):
    return CKANCatalogger(
        url="https://ckan.example.com",
        api_key="test-api-key"
    )


def test_init(mock_ckan):
    """Test CKANCatalogger initialization"""
    catalogger = CKANCatalogger(
        url="https://ckan.example.com",
        api_key="test-api-key"
    )

    mock_ckan.assert_called_once_with(
        address="https://ckan.example.com",
        apikey="test-api-key"
    )
    assert catalogger.endpoint == "https://ckan.example.com"
    assert catalogger.api_key == "test-api-key"


def test_register_api_service(catalogger, sample_endpoint_metadata):
    """Test registration of API service"""
    mock_response = {"id": "test-id", "name": "test-api"}
    catalogger.ckan_server.call_action = Mock(return_value=mock_response)

    # Create an APIService instance with required fields
    api_service = APIService(
        author=sample_endpoint_metadata.author,
        author_email="test@example.com",
        name="test-api",
        language=sample_endpoint_metadata.language or "en",
        license_id="cc-by",
        notes="Test API Service",
        owner_org="test-org",
        spatial="",
        tags=[{"name": "api"}, {"name": "test"}],
        title="Test API Service",
        api_url=sample_endpoint_metadata.endpoint_url
    )

    result = catalogger._register_api_service(api_service)

    catalogger.ckan_server.call_action.assert_called_once_with(
        action='package_create',
        data_dict=api_service.model_dump()
    )
    assert result == mock_response


def test_register_device_groups(catalogger, sample_endpoint_metadata, sample_data):
    """Test registration of device groups"""
    mock_response = {"id": "test-device-id", "name": "test-device"}
    catalogger.ckan_server.call_action = Mock(return_value=mock_response)

    # Create an APIService instance to link devices to
    api_service = APIService(
        author=sample_endpoint_metadata.author,
        author_email="test@example.com",
        name="test-api",
        language=sample_endpoint_metadata.language or "en",
        license_id="cc-by",
        notes="Test API Service",
        owner_org="test-org",
        spatial="",
        tags=[{"name": "api"}, {"name": "test"}],
        title="Test API Service",
        api_url=sample_endpoint_metadata.endpoint_url
    )

    catalogger._register_device_groups(api_service, sample_data)

    # Verify call_action was called for each device group
    assert catalogger.ckan_server.call_action.call_count == len(sample_data)

    # Verify the structure of each device group registration
    calls = catalogger.ckan_server.call_action.call_args_list
    for idx, (key, _) in enumerate(sample_data.items()):
        call = calls[idx]
        args, kwargs = call

        assert kwargs['action'] == 'package_create'
        device_dict = kwargs['data_dict'].model_dump()

        # Verify device group has correct structure
        assert device_dict['name'] == key
        assert device_dict['groups'] == [{"name": SDDICategory.device.value}]
        assert device_dict['relationships_as_subject'] == [{
            "subject": key,
            "object": api_service.name,
            "type": "links_to"
        }]


def test_register_complete_flow(catalogger, sample_endpoint_metadata, sample_data):
    """Test the complete registration flow"""
    mock_api_response = {"id": "test-api-id", "name": "test-api"}
    mock_device_response = {"id": "test-device-id", "name": "test-device"}

    catalogger.ckan_server.call_action = Mock(side_effect=[
        mock_api_response,
        *[mock_device_response for _ in range(len(sample_data))]
    ])

    catalogger.register(sample_endpoint_metadata, sample_data)

    # First call should be for API service
    first_call = catalogger.ckan_server.call_action.call_args_list[0]
    assert first_call[1]['action'] == 'package_create'

    # Subsequent calls should be for device groups
    device_calls = catalogger.ckan_server.call_action.call_args_list[1:]
    assert len(device_calls) == len(sample_data)

    for call in device_calls:
        assert call[1]['action'] == 'package_create'
        device_dict = call[1]['data_dict']
        assert device_dict['groups'] == [{"name": SDDICategory.device}]


def test_error_handling(catalogger, sample_endpoint_metadata):
    """Test error handling during registration"""
    error_message = "API Error"
    catalogger.ckan_server.call_action = Mock(
        side_effect=Exception(error_message))

    api_service = APIService(
        author=sample_endpoint_metadata.author,
        author_email="test@example.com",
        name="test-api",
        language=sample_endpoint_metadata.language or "en",
        license_id="cc-by",
        notes="Test API Service",
        owner_org="test-org",
        spatial="",
        tags=[{"name": "api"}, {"name": "test"}],
        title="Test API Service",
        api_url=sample_endpoint_metadata.endpoint_url
    )

    with pytest.raises(Exception) as exc_info:
        catalogger._register_api_service(api_service)

    assert str(exc_info.value) == error_message
