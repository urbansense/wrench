import pytest

from wrench.pipeline.stores import FileStore, InMemoryStore, ResultStore


class TestInMemoryStore:
    @pytest.fixture()
    def store(self):
        return InMemoryStore()

    async def test_add_and_get(self, store):
        await store.add("key1", "value1")
        result = await store.get("key1")
        assert result == "value1"

    async def test_get_missing_returns_none(self, store):
        result = await store.get("nonexistent")
        assert result is None

    async def test_add_overwrite_true(self, store):
        await store.add("key1", "original")
        await store.add("key1", "updated", overwrite=True)
        result = await store.get("key1")
        assert result == "updated"

    async def test_add_overwrite_false_raises(self, store):
        await store.add("key1", "original")
        with pytest.raises(KeyError, match="already exists"):
            await store.add("key1", "duplicate", overwrite=False)

    async def test_delete(self, store):
        await store.add("key1", "value1")
        await store.delete("key1")
        result = await store.get("key1")
        assert result is None

    async def test_delete_nonexistent_no_error(self, store):
        await store.delete("nonexistent")

    async def test_list_keys(self, store):
        await store.add("a", 1)
        await store.add("b", 2)
        await store.add("c", 3)
        keys = await store.list_keys()
        assert set(keys) == {"a", "b", "c"}

    async def test_list_keys_empty(self, store):
        keys = await store.list_keys()
        assert keys == []

    async def test_stores_complex_values(self, store):
        await store.add("dict", {"nested": {"key": [1, 2, 3]}})
        result = await store.get("dict")
        assert result["nested"]["key"] == [1, 2, 3]


class TestFileStore:
    @pytest.fixture()
    def store(self, tmp_path):
        return FileStore(directory=str(tmp_path / "store"))

    async def test_add_and_get(self, store):
        await store.add("key1", {"data": "value"})
        result = await store.get("key1")
        assert result == {"data": "value"}

    async def test_get_missing_returns_none(self, store):
        result = await store.get("nonexistent")
        assert result is None

    async def test_add_overwrite_true(self, store):
        await store.add("key1", "original")
        await store.add("key1", "updated", overwrite=True)
        result = await store.get("key1")
        assert result == "updated"

    async def test_add_overwrite_false_raises(self, store):
        await store.add("key1", "original")
        with pytest.raises(KeyError, match="already exists"):
            await store.add("key1", "duplicate", overwrite=False)

    async def test_delete(self, store):
        await store.add("key1", "value")
        await store.delete("key1")
        result = await store.get("key1")
        assert result is None

    async def test_delete_nonexistent_no_error(self, store):
        await store.delete("nonexistent")

    async def test_list_keys(self, store):
        await store.add("a", 1)
        await store.add("b", 2)
        keys = await store.list_keys()
        assert len(keys) == 2

    async def test_file_written_to_disk(self, store, tmp_path):
        await store.add("test:key", {"hello": "world"})
        import os

        files = os.listdir(store.directory)
        assert len(files) == 1
        assert files[0].endswith(".json")

    async def test_key_sanitization(self, store):
        store._get_file_path("run:comp:status")
        # Colons and slashes are replaced with underscores
        path = store._get_file_path("a:b/c")
        assert ":" not in path.split("/")[-1]


class TestResultStore:
    def test_get_key_basic(self):
        key = ResultStore.get_key("run-1", "harvester")
        assert key == "run-1:harvester"

    def test_get_key_with_suffix(self):
        key = ResultStore.get_key("run-1", "harvester", "status")
        assert key == "run-1:harvester:status"

    async def test_status_lifecycle(self):
        store = InMemoryStore()
        await store.add_status_for_component("run-1", "comp-a", "RUNNING")
        status = await store.get_status_for_component("run-1", "comp-a")
        assert status == "RUNNING"

    async def test_result_lifecycle(self):
        store = InMemoryStore()
        await store.add_result_for_component("run-1", "comp-a", {"output": 42})
        result = await store.get_result_for_component("run-1", "comp-a")
        assert result == {"output": 42}

    async def test_get_status_missing_returns_none(self):
        store = InMemoryStore()
        status = await store.get_status_for_component("run-1", "comp-a")
        assert status is None

    async def test_get_result_missing_returns_none(self):
        store = InMemoryStore()
        result = await store.get_result_for_component("run-1", "comp-a")
        assert result is None
