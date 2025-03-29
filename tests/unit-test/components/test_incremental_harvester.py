import pytest

from wrench.components.harvester import Harvester
from wrench.harvester.base import BaseHarvester
from wrench.models import Item
from wrench.pipeline.types import OperationType


# Mock classes for testing
class MockBaseHarvester(BaseHarvester):
    """Mock harvester for testing."""

    def __init__(self, items=None):
        self.items = items if items is not None else []

    def return_items(self):
        return self.items


# Test cases for IncrementalHarvester
@pytest.mark.asyncio
async def test_incremental_harvester_first_run():
    """Test the behavior of the first run (no previous items)."""
    # Create test items
    item1 = Item(id="1", content={"value": "data1"})
    item2 = Item(id="2", content={"value": "data2"})

    # Create mock harvester
    mock_harvester = MockBaseHarvester(items=[item1, item2])
    incremental_harvester = Harvester(harvester=mock_harvester)

    # Run the harvester
    result = await incremental_harvester.run()

    # Verify results
    assert len(result.devices) == 2
    assert len(result.operations) == 2
    assert all(op.type == OperationType.ADD for op in result.operations)
    assert {op.item_id for op in result.operations} == {"1", "2"}


@pytest.mark.asyncio
async def test_incremental_harvester_detect_add():
    """Test detecting add operations when new items appear."""
    # Create test items
    item1 = Item(id="1", content={"value": "data1"})
    item2 = Item(id="2", content={"value": "data2"})

    # Create mock harvester that will change its return value
    mock_harvester = MockBaseHarvester(items=[item1])
    incremental_harvester = Harvester(harvester=mock_harvester)

    # First run to establish baseline
    await incremental_harvester.run()

    # Change harvester to return additional item
    mock_harvester.items = [item1, item2]

    # Second run should detect the added item
    result = await incremental_harvester.run()

    # Verify results
    assert len(result.operations) == 1
    assert result.operations[0].type == OperationType.ADD
    assert result.operations[0].item_id == "2"


@pytest.mark.asyncio
async def test_incremental_harvester_detect_update():
    """Test detecting update operations when items change."""
    # Create test items
    item1 = Item(id="1", content={"value": "data1"})
    item2 = Item(id="2", content={"value": "data2"})

    # Create mock harvester
    mock_harvester = MockBaseHarvester(items=[item1, item2])
    incremental_harvester = Harvester(harvester=mock_harvester)

    # First run to establish baseline
    await incremental_harvester.run()

    # Update an item
    item2_updated = Item(id="2", content={"value": "data2_updated"})
    mock_harvester.items = [item1, item2_updated]

    # Second run should detect the updated item
    result = await incremental_harvester.run()

    # Verify results
    assert len(result.operations) == 1
    assert result.operations[0].type == OperationType.UPDATE
    assert result.operations[0].item_id == "2"
    assert result.operations[0].item.content == {"value": "data2_updated"}


@pytest.mark.asyncio
async def test_incremental_harvester_detect_delete():
    """Test detecting delete operations when items disappear."""
    # Create test items
    item1 = Item(id="1", content={"value": "data1"})
    item2 = Item(id="2", content={"value": "data2"})

    # Create mock harvester
    mock_harvester = MockBaseHarvester(items=[item1, item2])
    incremental_harvester = Harvester(harvester=mock_harvester)

    # First run to establish baseline
    await incremental_harvester.run()

    # Remove an item
    mock_harvester.items = [item1]

    # Second run should detect the deleted item
    result = await incremental_harvester.run()

    # Verify results
    assert len(result.operations) == 1
    assert result.operations[0].type == OperationType.DELETE
    assert result.operations[0].item_id == "2"


@pytest.mark.asyncio
async def test_incremental_harvester_multiple_operations():
    """Test detecting multiple types of operations in one run."""
    # Create test items
    item1 = Item(id="1", content={"value": "data1"})
    item2 = Item(id="2", content={"value": "data2"})

    # Create mock harvester
    mock_harvester = MockBaseHarvester(items=[item1, item2])
    incremental_harvester = Harvester(harvester=mock_harvester)

    # First run to establish baseline
    await incremental_harvester.run()

    # Make multiple changes:
    # - Update item1
    # - Remove item2
    # - Add item3
    item1_updated = Item(id="1", content={"value": "data1_updated"})
    item3 = Item(id="3", content={"value": "data3"})
    mock_harvester.items = [item1_updated, item3]

    # Next run should detect all changes
    result = await incremental_harvester.run()

    # Verify results
    assert len(result.operations) == 3

    # Check for update operation
    update_ops = [op for op in result.operations if op.type == OperationType.UPDATE]
    assert len(update_ops) == 1
    assert update_ops[0].item_id == "1"

    # Check for delete operation
    delete_ops = [op for op in result.operations if op.type == OperationType.DELETE]
    assert len(delete_ops) == 1
    assert delete_ops[0].item_id == "2"

    # Check for add operation
    add_ops = [op for op in result.operations if op.type == OperationType.ADD]
    assert len(add_ops) == 1
    assert add_ops[0].item_id == "3"
