import pytest

from wrench.components.grouper import Grouper
from wrench.grouper.base import BaseGrouper
from wrench.models import Group, Item
from wrench.pipeline.types import Operation, OperationType


class MockBaseGrouper(BaseGrouper):
    """Mock grouper for testing."""

    def __init__(self, group_mapping=None):
        """
        Initialize with a mapping function to determine grouping.

        Args:
            group_mapping: A function that takes items and returns groups
        """
        self.group_mapping = group_mapping or (lambda items: [])

    def group_items(self, items):
        return self.group_mapping(items)


# Test cases for IncrementalGrouper
@pytest.mark.asyncio
async def test_incremental_grouper_first_run():
    """Test the first run with no existing groups."""
    # Create test items
    item1 = Item(id="1", content={"value": "data1"})
    item2 = Item(id="2", content={"value": "data2"})

    # Define groups to be returned by the mock grouper
    group1 = Group(name="Group1", items=[item1])
    group2 = Group(name="Group2", items=[item2])

    # Create mock grouper that returns predefined groups
    def mock_group_items(items):
        return [group1, group2]

    mock_grouper = MockBaseGrouper(group_mapping=mock_group_items)
    incremental_grouper = Grouper(grouper=mock_grouper)

    # Run grouper for the first time
    result = await incremental_grouper.run([item1, item2], [])

    # Verify results
    assert len(result.groups) == 2
    assert {group.name for group in result.groups} == {"Group1", "Group2"}
    assert incremental_grouper._groups == [group1, group2]


@pytest.mark.asyncio
async def test_incremental_grouper_add_operation():
    """Test applying an ADD operation to existing groups."""
    # Create test items
    item1 = Item(id="1", content={"value": "data1"})
    item2 = Item(id="2", content={"value": "data2"})
    item3 = Item(id="3", content={"value": "data3"})

    # Define groups for initial state
    group1 = Group(name="Group1", items=[item1])
    group2 = Group(name="Group2", items=[item2])

    # Define groups for the result of grouping item3
    group3 = Group(name="Group3", items=[item3])

    # Create a mock grouper with dynamic behavior
    def mock_group_items(items):
        if any(item.id == "3" for item in items):
            return [group3]
        return [group1, group2]

    mock_grouper = MockBaseGrouper(group_mapping=mock_group_items)
    incremental_grouper = Grouper(grouper=mock_grouper)

    # First run to establish baseline
    await incremental_grouper.run([item1, item2], [])

    # Create ADD operation
    add_op = Operation(type=OperationType.ADD, item_id="3", item=item3)

    # Run with ADD operation
    result = await incremental_grouper.run([], [add_op])

    # Verify results
    assert len(result.groups) == 1
    assert result.groups[0].name == "Group3"
    assert len(result.groups[0].items) == 1
    assert result.groups[0].items[0].id == "3"

    # Verify internal state
    assert len(incremental_grouper._groups) == 3  # Original 2 + new 1
    assert {group.name for group in incremental_grouper._groups} == {
        "Group1",
        "Group2",
        "Group3",
    }


@pytest.mark.asyncio
async def test_incremental_grouper_update_operation():
    """Test applying an UPDATE operation to existing groups."""
    # Create test items
    item1 = Item(id="1", content={"value": "data1"})
    item2 = Item(id="2", content={"value": "data2"})

    # Create updated item
    item2_updated = Item(id="2", content={"value": "data2_updated"})

    # Define groups
    group1 = Group(name="Group1", items=[item1])
    group2 = Group(name="Group2", items=[item2])

    # Define updated group
    group2_updated = Group(name="Group2", items=[item2_updated])

    # Create a mock grouper with dynamic behavior
    def mock_group_items(items):
        if any(
            item.id == "2" and item.content == {"value": "data2_updated"}
            for item in items
        ):
            return [group2_updated]
        return [group1, group2]

    mock_grouper = MockBaseGrouper(group_mapping=mock_group_items)
    incremental_grouper = Grouper(grouper=mock_grouper)

    # First run to establish baseline
    await incremental_grouper.run([item1, item2], [])

    # Create UPDATE operation
    update_op = Operation(type=OperationType.UPDATE, item_id="2", item=item2_updated)

    # Run with UPDATE operation
    result = await incremental_grouper.run([], [update_op])

    # Verify results
    assert len(result.groups) == 1
    assert result.groups[0].name == "Group2"

    # Verify item was updated in the group
    updated_group = result.groups[0]
    assert len(updated_group.items) == 1
    assert updated_group.items[0].id == "2"
    assert updated_group.items[0].content == {"value": "data2_updated"}


@pytest.mark.asyncio
async def test_incremental_grouper_delete_operation():
    """Test applying a DELETE operation to existing groups."""
    # Create test items
    item1 = Item(id="1", content={"value": "data1"})
    item2 = Item(id="2", content={"value": "data2"})

    # Define groups
    group1 = Group(name="Group1", items=[item1, item2])

    # Create a mock grouper
    def mock_group_items(items):
        return [group1]

    mock_grouper = MockBaseGrouper(group_mapping=mock_group_items)
    incremental_grouper = Grouper(grouper=mock_grouper)

    # First run to establish baseline
    await incremental_grouper.run([item1, item2], [])

    # Create DELETE operation
    delete_op = Operation(type=OperationType.DELETE, item_id="2", item=item2)

    # Run with DELETE operation
    result = await incremental_grouper.run([], [delete_op])

    # Verify results
    assert len(result.groups) == 1
    assert result.groups[0].name == "Group1"

    # Verify item was removed
    assert len(result.groups[0].items) == 1
    assert result.groups[0].items[0].id == "1"


@pytest.mark.asyncio
async def test_incremental_grouper_multiple_operations():
    """Test applying multiple operations in one run."""
    # Create test items
    item1 = Item(id="1", content={"value": "data1"})
    item2 = Item(id="2", content={"value": "data2"})
    item3 = Item(id="3", content={"value": "data3"})

    # Define groups
    group1 = Group(name="Group1", items=[item1, item2])
    group3 = Group(name="Group3", items=[item3])

    # Create a mock grouper with dynamic behavior
    def mock_group_items(items):
        if any(item.id == "3" for item in items):
            return [group3]
        return [group1]

    mock_grouper = MockBaseGrouper(group_mapping=mock_group_items)
    incremental_grouper = Grouper(grouper=mock_grouper)

    # First run to establish baseline
    await incremental_grouper.run([item1, item2], [])

    # Create operations
    add_op = Operation(type=OperationType.ADD, item_id="3", item=item3)
    delete_op = Operation(type=OperationType.DELETE, item_id="2", item=item2)

    # Run with multiple operations
    result = await incremental_grouper.run([], [add_op, delete_op])

    # Verify results - should return both modified groups
    assert len(result.groups) == 2

    # Find the groups by name
    group1_result = next((g for g in result.groups if g.name == "Group1"), None)
    group3_result = next((g for g in result.groups if g.name == "Group3"), None)

    # Verify Group1 modifications (item2 removed)
    assert group1_result is not None
    assert len(group1_result.items) == 1
    assert group1_result.items[0].id == "1"

    # Verify Group3 was added with item3
    assert group3_result is not None
    assert len(group3_result.items) == 1
    assert group3_result.items[0].id == "3"


@pytest.mark.asyncio
async def test_incremental_grouper_no_operations():
    """Test running with no operations after initial state is set."""
    # Create test items
    item1 = Item(id="1", content={"value": "data1"})
    item2 = Item(id="2", content={"value": "data2"})

    # Define groups
    group1 = Group(name="Group1", items=[item1])
    group2 = Group(name="Group2", items=[item2])

    # Create a mock grouper
    def mock_group_items(items):
        return [group1, group2]

    mock_grouper = MockBaseGrouper(group_mapping=mock_group_items)
    incremental_grouper = Grouper(grouper=mock_grouper)

    # First run to establish baseline
    await incremental_grouper.run([item1, item2], [])
    print("Before second run")
    # Run with no operations
    result = await incremental_grouper.run([], [])

    # Verify no groups were modified
    assert len(result.groups) == 0

    # Verify internal state remains unchanged
    assert len(incremental_grouper._groups) == 2
    assert {group.name for group in incremental_grouper._groups} == {"Group1", "Group2"}
