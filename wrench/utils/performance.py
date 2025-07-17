import gc
import os
import time
import tracemalloc
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Generator, Optional

try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


@dataclass
class MemorySnapshot:
    """Memory usage snapshot at a point in time."""

    rss_mb: float  # Resident Set Size in MB
    vms_mb: float  # Virtual Memory Size in MB
    percent: float  # Memory percentage of system
    timestamp: float


@dataclass
class ComponentPerformanceMetrics:
    """Performance metrics for a pipeline component."""

    component_name: str
    execution_time_seconds: float
    memory_peak_mb: float
    memory_start_mb: float
    memory_end_mb: float
    memory_delta_mb: float
    memory_percent_peak: float
    tracemalloc_peak_mb: Optional[float] = None
    tracemalloc_current_mb: Optional[float] = None


class MemoryMonitor:
    """Monitor memory usage during component execution."""

    def __init__(self, enable_tracemalloc: bool = False):
        """
        Initialize memory monitor.

        Args:
            enable_tracemalloc: Enable detailed Python memory tracking
        """
        self.enable_tracemalloc = enable_tracemalloc
        self._process = None

        if HAS_PSUTIL:
            self._process = psutil.Process(os.getpid())

    def get_memory_snapshot(self) -> MemorySnapshot:
        """Get current memory usage snapshot."""
        if not HAS_PSUTIL:
            # Fallback to basic memory info if psutil not available
            return MemorySnapshot(
                rss_mb=0.0, vms_mb=0.0, percent=0.0, timestamp=time.time()
            )

        memory_info = self._process.memory_info()
        memory_percent = self._process.memory_percent()

        return MemorySnapshot(
            rss_mb=memory_info.rss / 1024 / 1024,  # Convert bytes to MB
            vms_mb=memory_info.vms / 1024 / 1024,
            percent=memory_percent,
            timestamp=time.time(),
        )

    @contextmanager
    def track_component(
        self, component_name: str
    ) -> Generator[ComponentPerformanceMetrics, None, None]:
        """
        Context manager to track performance metrics for a component.

        Args:
            component_name: Name of the component being tracked

        Yields:
            ComponentPerformanceMetrics object that gets populated during execution
        """
        # Force garbage collection before measurement
        gc.collect()

        # Start tracemalloc if enabled
        tracemalloc_started = False
        if self.enable_tracemalloc and not tracemalloc.is_tracing():
            tracemalloc.start()
            tracemalloc_started = True

        # Initial measurements
        start_time = time.time()
        start_memory = self.get_memory_snapshot()

        # Track peak memory usage
        peak_memory = start_memory

        # Create metrics object
        metrics = ComponentPerformanceMetrics(
            component_name=component_name,
            execution_time_seconds=0.0,
            memory_peak_mb=start_memory.rss_mb,
            memory_start_mb=start_memory.rss_mb,
            memory_end_mb=0.0,
            memory_delta_mb=0.0,
            memory_percent_peak=start_memory.percent,
        )

        try:
            yield metrics

            # Update peak memory during execution
            current_memory = self.get_memory_snapshot()
            if current_memory.rss_mb > peak_memory.rss_mb:
                peak_memory = current_memory

        finally:
            # Final measurements
            end_time = time.time()
            end_memory = self.get_memory_snapshot()

            # Update peak one more time
            if end_memory.rss_mb > peak_memory.rss_mb:
                peak_memory = end_memory

            # Get tracemalloc info if available
            tracemalloc_peak_mb = None
            tracemalloc_current_mb = None

            if tracemalloc.is_tracing():
                current, peak = tracemalloc.get_traced_memory()
                tracemalloc_current_mb = current / 1024 / 1024
                tracemalloc_peak_mb = peak / 1024 / 1024

                if tracemalloc_started:
                    tracemalloc.stop()

            # Update metrics
            metrics.execution_time_seconds = end_time - start_time
            metrics.memory_end_mb = end_memory.rss_mb
            metrics.memory_peak_mb = peak_memory.rss_mb
            metrics.memory_delta_mb = end_memory.rss_mb - start_memory.rss_mb
            metrics.memory_percent_peak = peak_memory.percent
            metrics.tracemalloc_peak_mb = tracemalloc_peak_mb
            metrics.tracemalloc_current_mb = tracemalloc_current_mb


def format_memory_size(size_mb: float) -> str:
    """Format memory size in human-readable format."""
    if size_mb < 1.0:
        return f"{size_mb * 1024:.1f} KB"
    elif size_mb < 1024:
        return f"{size_mb:.1f} MB"
    else:
        return f"{size_mb / 1024:.1f} GB"


def log_performance_metrics(metrics: ComponentPerformanceMetrics, logger: Any) -> None:
    """Log performance metrics in a structured format."""
    logger.info(
        f"{metrics.component_name} performance: "
        f"time={metrics.execution_time_seconds:.2f}s, "
        f"memory_peak={format_memory_size(metrics.memory_peak_mb)}, "
        f"memory_delta={format_memory_size(abs(metrics.memory_delta_mb))}"
        f"{'↑' if metrics.memory_delta_mb > 0 else '↓'},"
        f"cpu_percent={metrics.memory_percent_peak:.1f}%"
    )

    if metrics.tracemalloc_peak_mb:
        logger.debug(
            f"{metrics.component_name} Python memory: "
            f"peak={format_memory_size(metrics.tracemalloc_peak_mb)}, "
            f"current={format_memory_size(metrics.tracemalloc_current_mb or 0)}"
        )


# Global memory monitor instance
_default_monitor = MemoryMonitor()


def track_component_performance(component_name: str, enable_tracemalloc: bool = False):
    """
    Decorator to track component performance.

    Args:
        component_name: Name of the component
        enable_tracemalloc: Enable detailed Python memory tracking
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            monitor = MemoryMonitor(enable_tracemalloc=enable_tracemalloc)
            with monitor.track_component(component_name) as metrics:
                result = func(*args, **kwargs)

                # Try to get logger from self if available
                logger = None
                if args and hasattr(args[0], "logger"):
                    logger = args[0].logger

                if logger:
                    log_performance_metrics(metrics, logger)

                # Store metrics in result if it's a dict-like object
                if hasattr(result, "__dict__"):
                    result._performance_metrics = metrics

                return result

        return wrapper

    return decorator
