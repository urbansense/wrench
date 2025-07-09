from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from apscheduler.schedulers.base import BaseScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from wrench.pipeline.config.runner import PipelineRunner


class Scheduler(ABC):
    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def shutdown(self):
        pass


class CronScheduler(Scheduler):
    def __init__(
        self,
        pipeline_runner: PipelineRunner,
        scheduler: BaseScheduler,
        year: int = 0,
        month: int = 0,
        day: int = 0,
        week: int = 0,
        day_of_week: int | str = None,
        hour: int = 0,
        minute: int = 0,
        second: int = 0,
        cron_expression: str | None = None,
        inputs: dict[str, Any] = {},
    ):
        self.scheduler = scheduler

        if cron_expression and not any(
            [year, month, day, week, day_of_week, hour, minute, second]
        ):
            trigger = CronTrigger.from_crontab(cron_expression)
        elif not cron_expression and any(
            [year, month, day, week, day_of_week, hour, minute, second]
        ):
            trigger = CronTrigger(
                year,
                month,
                day,
                week,
                day_of_week,
                hour,
                minute,
                second,
            )
        else:
            raise ValueError(
                """Either a valid cron_expression or at least one time parameter must
                    be provided."""
            )
        self.scheduler.add_job(
            func=pipeline_runner.run,
            trigger=trigger,
            kwargs={"user_input": inputs},
            next_run_time=datetime.now(),
        )

    def start(self):
        self.scheduler.start()

    def shutdown(self):
        self.scheduler.shutdown()


class IntervalScheduler(Scheduler):
    def __init__(
        self,
        pipeline_runner: PipelineRunner,
        scheduler: BaseScheduler,
        weeks: int = 0,
        days: int = 0,
        hours: int = 0,
        minutes: int = 0,
        seconds: int = 0,
        interval: str | None = None,
        inputs: dict[str, Any] = {},
    ):
        self.scheduler = scheduler
        if interval and not any([weeks, days, hours, minutes, seconds]):
            self.duration_dict = self.parse_iso8601_duration(interval)
            trigger = IntervalTrigger(**self.duration_dict)
        elif not interval and any([weeks, days, hours, minutes, seconds]):
            trigger = IntervalTrigger(weeks, days, hours, minutes, seconds)
        else:
            raise ValueError(
                """Must provide either an interval string or at
                least one time unit (weeks/days/etc)."""
            )

        self.scheduler.add_job(
            func=pipeline_runner.run,
            trigger=trigger,
            kwargs={"user_input": inputs},
            next_run_time=datetime.now(),
        )

    def start(self):
        self.scheduler.start()

    def shutdown(self):
        self.scheduler.shutdown()

    def parse_iso8601_duration(self, duration: str):
        if not duration:
            raise ValueError("Duration string is empty")

        duration = duration.upper()

        if duration[0] != "P":
            raise ValueError("Duration must start with 'P'")

        index = 1
        time_section = False
        value = ""
        result = {
            "years": 0,
            "months": 0,
            "weeks": 0,
            "days": 0,
            "hours": 0,
            "minutes": 0,
            "seconds": 0,
        }

        component_map = {
            "Y": "years",
            "M": "months",  # can also be 'minutes' in time part
            "W": "weeks",
            "D": "days",
            "H": "hours",
            "S": "seconds",
        }

        while index < len(duration):
            char = duration[index]

            if char == "T":
                time_section = True
                index += 1
                continue

            # Accumulate numeric value
            value = ""
            while index < len(duration) and (
                duration[index].isdigit() or duration[index] == "."
            ):
                value += duration[index]
                index += 1

            if not value:
                raise ValueError(f"Expected number at position {index} in '{duration}'")

            if index >= len(duration):
                raise ValueError(f"Unexpected end of string after '{value}'")

            unit = duration[index]
            index += 1

            if unit not in component_map:
                raise ValueError(f"Invalid unit '{unit}' in duration")

            key = component_map[unit]
            # Disambiguate 'M' between months and minutes
            if unit == "M":
                key = "minutes" if time_section else "months"

            if result[key] != 0:
                raise ValueError(f"Duplicate unit '{unit}' in duration")

            try:
                result[key] = float(value) if "." in value else int(value)
            except ValueError:
                raise ValueError(f"Invalid number '{value}' in duration")

        # assume 365 days per year and 30 days per month
        # since timedelta doesn't work with months and years
        result["days"] = result["days"] + 365 * result["years"] + 30 * result["months"]
        result["years"] = 0
        result["months"] = 0

        # Remove unused (zero) components
        result = {k: v for k, v in result.items() if v != 0}

        if not result:
            raise ValueError("Duration must include at least one valid component")

        return result
