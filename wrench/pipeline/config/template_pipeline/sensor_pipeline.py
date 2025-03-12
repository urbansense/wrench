from typing import ClassVar

from wrench.pipeline.config.base import AbstractConfig


class SensorRegistrationPipelineConfig(AbstractConfig):
    """Template configuration for sensor registration pipeline."""

    COMPONENTS: ClassVar[list[str]] = [
        "harvester",
        "grouper",
        "metadata_builder",
        "cataloger",
    ]
