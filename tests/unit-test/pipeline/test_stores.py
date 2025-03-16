import tempfile

import pytest

from wrench.pipeline.stores import FileStore, InMemoryStore


@pytest.fixture
def in_memory_store():
    return InMemoryStore()


@pytest.fixture
def file_store():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = FileStore(directory=tmpdir)
        yield store


@pytest.mark.asyncio
async def test_in_memory_store_add_get(in_memory_store):
    """Test adding and retrieving items from in-memory store."""
    await in_memory_store.add("test_key", {"value": "test_data"})
    result = await in_memory_store.get("test_key")
    assert result == {"value": "test_data"}


@pytest.mark.asyncio
async def test_in_memory_store_add_no_overwrite(in_memory_store):
    """Test adding with overwrite=False."""
    await in_memory_store.add("test_key", "original")

    with pytest.raises(KeyError):
        await in_memory_store.add("test_key", "new_value", overwrite=False)

    # Value should be unchanged
    result = await in_memory_store.get("test_key")
    assert result == "original"


@pytest.mark.asyncio
async def test_in_memory_store_delete(in_memory_store):
    """Test deleting items from in-memory store."""
    await in_memory_store.add("test_key", "test_data")
    await in_memory_store.delete("test_key")
    result = await in_memory_store.get("test_key")
    assert result is None


@pytest.mark.asyncio
async def test_in_memory_store_list_keys(in_memory_store):
    """Test listing keys from in-memory store."""
    await in_memory_store.add("key1", "value1")
    await in_memory_store.add("key2", "value2")
    keys = await in_memory_store.list_keys()
    assert set(keys) == {"key1", "key2"}


@pytest.mark.asyncio
async def test_file_store_add_get(file_store):
    """Test adding and retrieving items from file store."""
    await file_store.add("test_key", {"value": "test_data"})
    result = await file_store.get("test_key")
    assert result == {"value": "test_data"}


@pytest.mark.asyncio
async def test_file_store_add_no_overwrite(file_store):
    """Test adding with overwrite=False for file store."""
    await file_store.add("test_key", "original")

    with pytest.raises(KeyError):
        await file_store.add("test_key", "new_value", overwrite=False)

    # Value should be unchanged
    result = await file_store.get("test_key")
    assert result == "original"


@pytest.mark.asyncio
async def test_file_store_delete(file_store):
    """Test deleting items from file store."""
    await file_store.add("test_key", "test_data")
    await file_store.delete("test_key")
    result = await file_store.get("test_key")
    assert result is None


@pytest.mark.asyncio
async def test_file_store_list_keys(file_store):
    """Test listing keys from file store."""
    await file_store.add("key1", "value1")
    await file_store.add("key2", "value2")
    keys = await file_store.list_keys()
    assert set(keys) == {"key1", "key2"}


@pytest.mark.asyncio
async def test_result_store_component_results(in_memory_store):
    """Test storing and retrieving component results."""
    run_id = "test-run-123"
    component = "test-component"

    await in_memory_store.add_result_for_component(
        run_id, component, {"output": "test-result"}
    )
    result = await in_memory_store.get_result_for_component(run_id, component)

    assert result == {"output": "test-result"}


@pytest.mark.asyncio
async def test_result_store_component_status(in_memory_store):
    """Test storing and retrieving component status."""
    run_id = "test-run-123"
    component = "test-component"

    await in_memory_store.add_status_for_component(run_id, component, "RUNNING")
    status = await in_memory_store.get_status_for_component(run_id, component)

    assert status == "RUNNING"
