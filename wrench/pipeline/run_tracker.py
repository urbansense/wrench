from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel

from wrench.log import logger
from wrench.pipeline.stores import ResultStore


class PipelineRunStatus(str, Enum):
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"


class RunRecord(BaseModel):
    """Record of a pipeline run."""

    run_id: str
    status: PipelineRunStatus
    start_time: datetime
    end_time: datetime | None = None
    error: str | None = None

    # Additional metadata for observability
    component_statuses: dict[str, str] = {}  # Component name -> status
    inputs: dict[str, Any] = {}  # High-level inputs (sanitized)


class PipelineRunTracker:
    """Tracks all pipeline runs for observability."""

    def __init__(self, store: ResultStore):
        self.store = store
        self.logger = logger.getChild(self.__class__.__name__)

    async def load_history(self):
        """Load run history from storage."""
        self.run_records = []
        run_history = await self.store.get("pipeline:run_history")
        if run_history:
            self.run_records: list[RunRecord] = [
                RunRecord.model_validate(record) for record in run_history
            ]
        self.logger.debug(f"Loaded {len(self.run_records)} historical runs")

    async def get_run_records(self, limit: int = 100) -> list[RunRecord]:
        """Get the most recent run records."""
        if not hasattr(self, "run_records"):
            await self.load_history()
        # Return most recent runs first
        return sorted(self.run_records, key=lambda r: r.start_time, reverse=True)[
            :limit
        ]

    async def get_last_successful_run(self) -> RunRecord | None:
        """Get the most recent successful run."""
        records = await self.get_run_records()
        for record in records:
            if record.status == PipelineRunStatus.COMPLETED:
                return record
        return None

    async def record_run_start(
        self, run_id: str, inputs: dict[str, Any] = {}
    ) -> RunRecord:
        """Record the start of a pipeline run."""
        record = RunRecord(
            run_id=run_id,
            status=PipelineRunStatus.STARTED,
            start_time=datetime.now(),
            inputs=inputs,
        )

        if not hasattr(self, "run_records"):
            await self.load_history()

        self.run_records.append(record)
        await self._save_history()
        return record

    async def record_run_completion(self, run_id: str) -> RunRecord:
        """Record successful completion of a run."""
        record = await self._find_run_record(run_id)
        if record:
            record.status = PipelineRunStatus.COMPLETED
            record.end_time = datetime.now()

            # Collect final component statuses
            # (Implementation detail - could fetch from store)

            await self._save_history()
        return record

    async def record_run_failure(self, run_id: str, error: str) -> RunRecord:
        """Record failure of a run."""
        record = await self._find_run_record(run_id)
        if record:
            record.status = PipelineRunStatus.FAILED
            record.end_time = datetime.now()
            record.error = error

            # Collect component statuses at failure point

            await self._save_history()
        return record

    async def _find_run_record(self, run_id: str) -> RunRecord | None:
        """Find a run record by ID."""
        if not hasattr(self, "run_records"):
            await self.load_history()

        for record in self.run_records:
            if record.run_id == run_id:
                return record
        return None

    async def _save_history(self):
        """Save run history to storage."""
        await self.store.add(
            "pipeline:run_history",
            [record.model_dump(mode="json") for record in self.run_records],
            overwrite=True,
        )
