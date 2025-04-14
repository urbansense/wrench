from abc import abstractmethod
from typing import Any, Literal

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pydantic import BaseModel, Field

from wrench.pipeline.config.runner import PipelineRunner

from .scheduler import CronScheduler, IntervalScheduler


# Base class for scheduler configs
class BaseSchedulerConfig(BaseModel):
    scheduler_type: str

    @abstractmethod
    def create_scheduler(self, runner: PipelineRunner, inputs: dict[str, Any] = {}):
        pass


# Specific configurations with appropriate type hints
class IntervalSchedulerConfig(BaseSchedulerConfig):
    scheduler_type: Literal["interval"] = "interval"
    weeks: int = 0
    days: int = 0
    hours: int = 0
    minutes: int = 0
    seconds: int = 0
    interval: str | None = None

    def create_scheduler(self, runner: PipelineRunner, inputs: dict[str, Any] = {}):
        return IntervalScheduler(
            runner,
            AsyncIOScheduler(),
            weeks=self.weeks,
            days=self.days,
            hours=self.hours,
            minutes=self.minutes,
            seconds=self.seconds,
            interval=self.interval,
            inputs=inputs,
        )


class CronSchedulerConfig(BaseSchedulerConfig):
    scheduler_type: Literal["cron"] = "cron"
    year: int = 0
    month: int = 0
    day: int = 0
    week: int = 0
    day_of_week: int | str = None
    hour: int = 0
    minute: int = 0
    second: int = 0
    cron_expression: str | None = None

    def create_scheduler(self, runner: PipelineRunner, inputs: dict[str, Any] = {}):
        return CronScheduler(
            runner,
            AsyncIOScheduler(),
            year=self.year,
            month=self.month,
            day=self.day,
            week=self.week,
            day_of_week=self.day_of_week,
            hour=self.hour,
            minute=self.minute,
            second=self.second,
            cron_expression=self.cron_expression,
            inputs=inputs,
        )


class SchedulerConfig(BaseModel):
    type: CronSchedulerConfig | IntervalSchedulerConfig = Field(
        discriminator="scheduler_type"
    )
