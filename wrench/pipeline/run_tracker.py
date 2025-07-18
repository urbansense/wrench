from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel

from wrench.log import logger
from wrench.pipeline.stores import ResultStore
from wrench.utils.performance import ComponentPerformanceMetrics


class PipelineRunStatus(str, Enum):
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class ComponentPerformanceRecord(BaseModel):
    """Performance record for a single component."""

    component_name: str
    execution_time_seconds: float
    memory_peak_mb: float
    memory_start_mb: float
    memory_end_mb: float
    memory_delta_mb: float
    memory_percent_peak: float
    tracemalloc_peak_mb: float | None = None
    tracemalloc_current_mb: float | None = None

    @classmethod
    def from_metrics(
        cls, metrics: ComponentPerformanceMetrics
    ) -> "ComponentPerformanceRecord":
        """Create record from performance metrics."""
        return cls(
            component_name=metrics.component_name,
            execution_time_seconds=metrics.execution_time_seconds,
            memory_peak_mb=metrics.memory_peak_mb,
            memory_start_mb=metrics.memory_start_mb,
            memory_end_mb=metrics.memory_end_mb,
            memory_delta_mb=metrics.memory_delta_mb,
            memory_percent_peak=metrics.memory_percent_peak,
            tracemalloc_peak_mb=metrics.tracemalloc_peak_mb,
            tracemalloc_current_mb=metrics.tracemalloc_current_mb,
        )


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

    # Performance tracking
    component_performance: dict[
        str, ComponentPerformanceRecord
    ] = {}  # Component name -> performance
    total_execution_time_seconds: float | None = None
    pipeline_memory_peak_mb: float | None = None


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

    async def record_run_completion(
        self, run_id: str, stopped_early: bool = False
    ) -> RunRecord:
        """Record successful completion of a run."""
        record = await self._find_run_record(run_id)
        if record:
            if stopped_early:
                record.status = PipelineRunStatus.STOPPED
            else:
                record.status = PipelineRunStatus.COMPLETED

            record.end_time = datetime.now()

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

    async def record_component_performance(
        self, run_id: str, metrics: ComponentPerformanceMetrics
    ) -> RunRecord:
        """Record performance metrics for a component."""
        record = await self._find_run_record(run_id)
        if record:
            perf_record = ComponentPerformanceRecord.from_metrics(metrics)
            record.component_performance[metrics.component_name] = perf_record
            await self._save_history()
        return record

    async def update_pipeline_memory_peak(
        self, run_id: str, memory_peak_mb: float
    ) -> RunRecord:
        """Update the pipeline-level memory peak."""
        record = await self._find_run_record(run_id)
        if record:
            if (
                record.pipeline_memory_peak_mb is None
                or memory_peak_mb > record.pipeline_memory_peak_mb
            ):
                record.pipeline_memory_peak_mb = memory_peak_mb
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
