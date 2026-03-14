from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from wrench.cataloger.sddi.cataloger import SDDICataloger
from wrench.cataloger.sddi.models import DeviceGroup, OnlineService
from wrench.models import CommonMetadata, TimeFrame


@pytest.fixture()
def mock_ckan():
    """Patch RemoteCKAN so no real HTTP calls are made."""
    with patch("wrench.cataloger.sddi.cataloger.RemoteCKAN") as MockCKAN:
        mock_instance = MagicMock()
        MockCKAN.return_value = mock_instance
        mock_instance.call_action.return_value = {}
        yield mock_instance


@pytest.fixture()
def cataloger(mock_ckan):
    return SDDICataloger(
        base_url="https://ckan.example.com",
        api_key="test-key",
        owner_org="test-org",
    )


@pytest.fixture()
def service_metadata():
    return CommonMetadata(
        identifier="test-service",
        title="Test Service",
        description="A test service",
        endpoint_urls=["https://api.example.com/v1"],
        source_type="sensorthings",
        spatial_extent='{"type":"Point","coordinates":[11.5,48.1]}',
        temporal_extent=TimeFrame(
            start_time=datetime(2023, 1, 1, tzinfo=timezone.utc),
            latest_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
        ),
        last_updated=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


@pytest.fixture()
def group_metadata():
    return CommonMetadata(
        identifier="weather-group",
        title="Weather Group",
        description="Weather sensors",
        endpoint_urls=["https://api.example.com/v1/things/1"],
        source_type="sensorthings",
        tags=["weather", "temperature"],
        spatial_extent='{"type":"Point","coordinates":[11.5,48.1]}',
        temporal_extent=TimeFrame(
            start_time=datetime(2023, 1, 1, tzinfo=timezone.utc),
            latest_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
        ),
        last_updated=datetime(2024, 1, 1, tzinfo=timezone.utc),
        thematic_groups=["environment"],
    )


class TestSDDICatalogerInit:
    def test_init_sets_fields(self, mock_ckan):
        cat = SDDICataloger(
            base_url="https://ckan.example.com",
            api_key="my-key",
            owner_org="my-org",
        )
        assert cat.endpoint == "https://ckan.example.com"
        assert cat.api_key == "my-key"
        assert cat.owner_org == "my-org"

    def test_default_owner_org(self, mock_ckan):
        cat = SDDICataloger(
            base_url="https://ckan.example.com",
            api_key="my-key",
        )
        assert cat.owner_org == "lehrstuhl-fur-geoinformatik"


class TestCreateOnlineService:
    def test_creates_online_service_from_metadata(self, cataloger, service_metadata):
        result = cataloger._create_online_service(service_metadata)
        assert isinstance(result, OnlineService)
        assert result.name == "test-service"
        assert result.title == "Test Service"
        assert result.notes == "A test service"
        assert result.url == "https://api.example.com/v1"


class TestCreateDeviceGroups:
    def test_creates_device_groups(self, cataloger, group_metadata):
        result = cataloger._create_device_groups([group_metadata])
        assert len(result) == 1
        assert isinstance(result[0], DeviceGroup)
        assert result[0].name == "weather-group"

    def test_device_group_has_resources(self, cataloger, group_metadata):
        result = cataloger._create_device_groups([group_metadata])
        assert len(result[0].resources) == 1
        assert result[0].resources[0]["url"] == "https://api.example.com/v1/things/1"

    def test_device_group_domain_groups_filtered(self, cataloger, group_metadata):
        result = cataloger._create_device_groups([group_metadata])
        group_names = [g["name"] for g in result[0].groups]
        # "environment" is in DOMAIN_GROUPS, so it should appear
        assert "environment" in group_names

    def test_device_group_invalid_domain_excluded(self, cataloger):
        meta = CommonMetadata(
            identifier="test-group",
            title="Test",
            description="desc",
            endpoint_urls=["https://example.com"],
            source_type="test",
            spatial_extent="{}",
            temporal_extent=TimeFrame(
                start_time=datetime(2023, 1, 1, tzinfo=timezone.utc),
                latest_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
            ),
            last_updated=datetime(2024, 1, 1, tzinfo=timezone.utc),
            thematic_groups=["not-a-real-domain"],
        )
        result = cataloger._create_device_groups([meta])
        # "not-a-real-domain" not in DOMAIN_GROUPS, so groups only contain "device"
        group_names = [g["name"] for g in result[0].groups]
        assert "not-a-real-domain" not in group_names


class TestRegister:
    def test_register_new_service_and_groups(
        self, cataloger, mock_ckan, service_metadata, group_metadata
    ):
        result = cataloger.register(
            service=service_metadata,
            groups=[group_metadata],
            managed_entries=None,
        )
        assert isinstance(result, list)
        # Should have registered both service and group
        assert "test-service" in result
        assert "weather-group" in result
        # package_create called for service and group
        create_calls = [
            c
            for c in mock_ckan.call_action.call_args_list
            if c.kwargs.get("action") == "package_create"
            or (c.args and c.args[0] == "package_create")
        ]
        assert len(create_calls) >= 2

    def test_register_updates_existing_service(
        self, cataloger, mock_ckan, service_metadata, group_metadata
    ):
        cataloger.register(
            service=service_metadata,
            groups=[group_metadata],
            managed_entries=["test-service"],
        )
        # Service should be updated (package_patch) not created
        patch_calls = [
            c
            for c in mock_ckan.call_action.call_args_list
            if c.kwargs.get("action") == "package_patch"
            or (c.args and c.args[0] == "package_patch")
        ]
        assert len(patch_calls) >= 1

    def test_register_no_groups(self, cataloger, mock_ckan, service_metadata):
        result = cataloger.register(
            service=service_metadata,
            groups=[],
            managed_entries=None,
        )
        assert "test-service" in result

    def test_register_creates_relationship(
        self, cataloger, mock_ckan, service_metadata, group_metadata
    ):
        cataloger.register(
            service=service_metadata,
            groups=[group_metadata],
            managed_entries=None,
        )
        relationship_calls = [
            c
            for c in mock_ckan.call_action.call_args_list
            if c.kwargs.get("action") == "package_relationship_create"
            or (c.args and c.args[0] == "package_relationship_create")
        ]
        assert len(relationship_calls) == 1


class TestDeleteResource:
    def test_delete_calls_dataset_purge(self, cataloger, mock_ckan):
        cataloger.delete_resource("my-dataset")
        mock_ckan.call_action.assert_called_with(
            action="dataset_purge", data_dict={"id": "my-dataset"}
        )


class TestGetOwnerOrgs:
    def test_get_owner_orgs_calls_action(self, cataloger, mock_ckan):
        mock_ckan.call_action.return_value = ["org-1", "org-2"]
        result = cataloger.get_owner_orgs()
        assert result == ["org-1", "org-2"]
        mock_ckan.call_action.assert_called_with(action="organization_list")
