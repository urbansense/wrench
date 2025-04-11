import pytest

from wrench.components.cataloger import Cataloger, CatalogerStatus
from wrench.models import CommonMetadata


class MockBaseCataloger:
    """Mock cataloger for testing."""

    def __init__(self, fail=False):
        self.fail = fail
        self.registered_service = None
        self.registered_groups = None

    def register(self, service, groups, managed_entries: list[str]) -> list[str]:
        if self.fail:
            raise Exception("Registration failed")
        self.registered_service = service
        self.registered_groups = groups
        return True


@pytest.mark.asyncio
async def test_cataloger_component_basic():
    """Test the basic functionality of the Cataloger component."""
    # Create test data
    service_metadata = CommonMetadata(
        endpoint_url="http://test-url.com/",
        source_type="mock-source",
        title="Test Service",
        description="This is a test service",
        identifier="test-service-id",
    )

    group_metadata = [
        CommonMetadata(
            endpoint_url="http://test-url.com/",
            source_type="mock-source",
            title="Group 1",
            description="This is group 1",
            identifier="group-1-id",
        ),
        CommonMetadata(
            endpoint_url="http://test-url.com/",
            source_type="mock-source",
            title="Group 2",
            description="This is group 2",
            identifier="group-2-id",
        ),
    ]

    # Create mock base cataloger
    mock_cataloger = MockBaseCataloger()

    # Create component
    cataloger_component = Cataloger(cataloger=mock_cataloger)

    # Run component
    result = await cataloger_component.run(service_metadata, group_metadata)

    # Verify result
    assert isinstance(result, CatalogerStatus)
    assert result.success is True
    assert len(result.groups) == 2
    assert "group-1-id" in result.groups
    assert "group-2-id" in result.groups

    # Verify the mock was called correctly
    assert mock_cataloger.registered_service == service_metadata
    assert mock_cataloger.registered_groups == group_metadata


@pytest.mark.asyncio
async def test_cataloger_component_empty_groups():
    """Test cataloger with empty group list."""
    # Create test data
    service_metadata = CommonMetadata(
        endpoint_url="http://test-url.com/",
        source_type="mock-source",
        title="Test Service",
        description="This is a test service",
        identifier="test-service-id",
    )

    group_metadata = []

    # Create mock base cataloger
    mock_cataloger = MockBaseCataloger()

    # Create component
    cataloger_component = Cataloger(cataloger=mock_cataloger)

    # Run component
    result = await cataloger_component.run(service_metadata, group_metadata)

    # Verify result
    assert isinstance(result, CatalogerStatus)
    assert result.success is True
    assert len(result.groups) == 0


@pytest.mark.asyncio
async def test_cataloger_component_failure():
    """Test cataloger component with failure."""
    # Create test data
    service_metadata = CommonMetadata(
        endpoint_url="http://test-url.com/",
        source_type="mock-source",
        title="Test Service",
        description="This is a test service",
        identifier="test-service-id",
    )

    group_metadata = [
        CommonMetadata(
            endpoint_url="http://test-url.com/",
            source_type="mock-source",
            title="Group 1",
            description="This is group 1",
            identifier="group-1-id",
        )
    ]

    # Create mock base cataloger that will fail
    mock_cataloger = MockBaseCataloger(fail=True)

    # Create component
    cataloger_component = Cataloger(cataloger=mock_cataloger)

    # Run component and expect exception
    with pytest.raises(Exception):
        await cataloger_component.run(service_metadata, group_metadata)
