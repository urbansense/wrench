import pytest

from wrench.pipeline.state_manager import PipelineStateManager
from wrench.pipeline.stores import InMemoryStore


@pytest.fixture()
def store():
    return InMemoryStore()


@pytest.fixture()
def manager(store):
    return PipelineStateManager(store)


class TestPipelineStateManager:
    async def test_initialize_no_existing_version(self, manager):
        await manager.initialize()
        assert manager.current_version is None

    async def test_initialize_with_existing_version(self, store, manager):
        await store.add("pipeline:state:current_version", "run-old")
        await manager.initialize()
        assert manager.current_version == "run-old"

    async def test_get_component_state_no_version(self, manager):
        await manager.initialize()
        state = await manager.get_component_state("comp-a")
        assert state == {}

    async def test_get_component_state_with_version(self, store, manager):
        await store.add("pipeline:state:current_version", "run-1")
        await store.add("state:vrun-1:comp-a", {"key": "value"})
        await manager.initialize()
        state = await manager.get_component_state("comp-a")
        assert state == {"key": "value"}

    async def test_prepare_stage_commit_lifecycle(self, manager, store):
        await manager.initialize()

        await manager.prepare_new_version("run-42")
        await manager.stage_component_state("comp-a", {"data": [1, 2, 3]})
        await manager.stage_component_state("comp-b", {"data": [4, 5, 6]})
        await manager.commit_version()

        assert manager.current_version == "run-42"

        stored_a = await store.get("state:vrun-42:comp-a")
        assert stored_a == {"data": [1, 2, 3]}

        stored_b = await store.get("state:vrun-42:comp-b")
        assert stored_b == {"data": [4, 5, 6]}

        current = await store.get("pipeline:state:current_version")
        assert current == "run-42"

    async def test_discard_pending(self, manager, store):
        await manager.initialize()
        await manager.prepare_new_version("run-99")
        await manager.stage_component_state("comp-a", {"data": "pending"})
        await manager.discard_pending()

        assert not hasattr(manager, "pending_version")
        stored = await store.get("state:vrun-99:comp-a")
        assert stored is None

    async def test_commit_without_pending_states(self, manager):
        await manager.initialize()
        await manager.prepare_new_version("run-empty")
        # No staged states
        await manager.commit_version()
        # Should not crash, just warn

    async def test_stage_before_prepare_raises(self, manager):
        await manager.initialize()
        with pytest.raises(ValueError, match="prepare_new_version"):
            await manager.stage_component_state("comp-a", {"data": "bad"})

    async def test_version_history_tracked(self, manager, store):
        await manager.initialize()

        await manager.prepare_new_version("run-1")
        await manager.stage_component_state("comp", {"v": 1})
        await manager.commit_version()

        await manager.prepare_new_version("run-2")
        await manager.stage_component_state("comp", {"v": 2})
        await manager.commit_version()

        assert manager.current_version == "run-2"
        prev = await store.get("pipeline:state:previous_version")
        assert prev == "run-1"
