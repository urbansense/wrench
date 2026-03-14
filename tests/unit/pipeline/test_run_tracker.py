import pytest

from wrench.pipeline.run_tracker import PipelineRunStatus, PipelineRunTracker
from wrench.pipeline.stores import InMemoryStore


@pytest.fixture()
def store():
    return InMemoryStore()


@pytest.fixture()
def tracker(store):
    return PipelineRunTracker(store)


class TestPipelineRunTracker:
    async def test_record_run_start(self, tracker):
        record = await tracker.record_run_start("run-1", {"input": "data"})
        assert record.run_id == "run-1"
        assert record.status == PipelineRunStatus.STARTED
        assert record.inputs == {"input": "data"}
        assert record.end_time is None

    async def test_record_run_completion(self, tracker):
        await tracker.record_run_start("run-1")
        record = await tracker.record_run_completion("run-1")
        assert record.status == PipelineRunStatus.COMPLETED
        assert record.end_time is not None

    async def test_record_run_completion_stopped_early(self, tracker):
        await tracker.record_run_start("run-1")
        record = await tracker.record_run_completion("run-1", stopped_early=True)
        assert record.status == PipelineRunStatus.STOPPED

    async def test_record_run_failure(self, tracker):
        await tracker.record_run_start("run-1")
        record = await tracker.record_run_failure("run-1", "Something broke")
        assert record.status == PipelineRunStatus.FAILED
        assert record.error == "Something broke"
        assert record.end_time is not None

    async def test_get_run_records_sorted(self, tracker):
        await tracker.record_run_start("run-1")
        await tracker.record_run_start("run-2")
        await tracker.record_run_start("run-3")
        records = await tracker.get_run_records()
        assert len(records) == 3
        # Most recent first
        assert records[0].run_id == "run-3"

    async def test_get_run_records_with_limit(self, tracker):
        for i in range(5):
            await tracker.record_run_start(f"run-{i}")
        records = await tracker.get_run_records(limit=2)
        assert len(records) == 2

    async def test_get_last_successful_run(self, tracker):
        await tracker.record_run_start("run-1")
        await tracker.record_run_completion("run-1")

        await tracker.record_run_start("run-2")
        await tracker.record_run_failure("run-2", "err")

        result = await tracker.get_last_successful_run()
        assert result is not None
        assert result.run_id == "run-1"

    async def test_get_last_successful_run_none(self, tracker):
        await tracker.record_run_start("run-1")
        await tracker.record_run_failure("run-1", "err")
        result = await tracker.get_last_successful_run()
        assert result is None

    async def test_load_history_from_store(self, store):
        tracker1 = PipelineRunTracker(store)
        await tracker1.record_run_start("run-1")
        await tracker1.record_run_completion("run-1")

        # Create a new tracker from the same store
        tracker2 = PipelineRunTracker(store)
        await tracker2.load_history()
        records = await tracker2.get_run_records()
        assert len(records) == 1
        assert records[0].run_id == "run-1"

    async def test_find_nonexistent_run_returns_none(self, tracker):
        record = await tracker.record_run_completion("nonexistent")
        assert record is None
