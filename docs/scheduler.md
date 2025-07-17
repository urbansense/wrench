# Scheduling

Wrench provides scheduling capabilities for pipeline executions through two specialized schedulers. These schedulers automate the process of running pipelines at predetermined times or intervals.

## Overview

When using Wrench schedulers:

* Schedulers execute within your application's process
* The application process must remain active for scheduled pipelines to run
* Execution can be gracefully terminated with keyboard interrupts (Ctrl+C) or system exits
* Scheduled pipelines run serially (one after another), not in parallel
* When multiple pipelines are scheduled to run simultaneously, they form a queue

## Available Schedulers

Wrench offers two built-in scheduler types:

* [IntervalScheduler](#intervalscheduler): Runs pipelines at fixed time intervals
* [CronScheduler](#cronscheduler): Executes pipelines according to cron-style scheduling expressions

To use a scheduler, you must:

1. Create a scheduler configuration
2. Use the configuration to create a scheduler with a pipeline runner

For a graceful termination, the scheduler automatically handle shutdown procedures when receiving interrupt signals.

### IntervalScheduler

IntervalScheduler uses an interval-based scheduling mechanism. You can provide the desired interval where pipeline runs will execute and the scheduler handles the execution. To initialize an IntervalScheduler, create an IntervalSchedulerConfig and call the `create_scheduler` method. This will initialize an IntervalScheduler which can be used in other parts of your code.

```python
class IntervalSchedulerConfig(BaseSchedulerConfig):
    scheduler_type: Literal["interval"] = "interval"
    weeks: int = 0
    days: int = 0
    hours: int = 0
    minutes: int = 0
    seconds: int = 0
    interval: str | None = None
```

To create an IntervalSchedulerConfig, you need to provide either the interval as an [ISO 8601 duration formatted string](https://docs.digi.com/resources/documentation/digidocs/90001488-13/reference/r_iso_8601_duration_format.htm), or provide the time intervals directly with the time arguments. You cannot define both.

Example:

```python
# the following expression runs the pipeline every 2 weeks, 10 days, 5 hours, 2 minutes and 30 seconds
config = IntervalSchedulerConfig(interval="P2W10DT5H2M30S")
```

### CronScheduler

CronScheduler uses a cron-based scheduling mechanism. You define a certain frequency on how often the pipeline should run. To initialize a CronScheduler, create a CronSchedulerConfig and call the `create_scheduler` method. This will initialize a CronScheduler which can be used in other parts of your code.

```python
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
```

To create a CronSchedulerConfig, you need to provide either a [cron expression](https://crontab.guru/), or provide the time directly with the time arguments. You cannot define both.

Example:

```python
# the following expression runs the pipeline at 10:15 on every Wednesday.
config = CronSchedulerConfig(cron_expression="15 10 * * 3")
```
