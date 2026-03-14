from unittest.mock import MagicMock

import pytest

from wrench.scheduler.scheduler import CronScheduler, IntervalScheduler


@pytest.fixture()
def mock_pipeline_runner():
    runner = MagicMock()
    runner.run = MagicMock()
    return runner


@pytest.fixture()
def mock_apscheduler():
    scheduler = MagicMock()
    return scheduler


class TestParseISO8601Duration:
    """Test the ISO 8601 duration parser independently.

    We instantiate IntervalScheduler with explicit time units to get
    an instance, then call parse_iso8601_duration directly.
    """

    @pytest.fixture()
    def parser(self, mock_pipeline_runner, mock_apscheduler):
        scheduler = IntervalScheduler(
            pipeline_runner=mock_pipeline_runner,
            scheduler=mock_apscheduler,
            hours=1,
        )
        return scheduler

    @pytest.mark.parametrize(
        "duration,expected",
        [
            ("PT1H", {"hours": 1}),
            ("PT30M", {"minutes": 30}),
            ("PT45S", {"seconds": 45}),
            ("P1D", {"days": 1}),
            ("P2W", {"weeks": 2}),
            ("P1DT12H", {"days": 1, "hours": 12}),
            ("PT1H30M", {"hours": 1, "minutes": 30}),
            ("P1Y", {"days": 365}),
            ("P1M", {"days": 30}),
            ("P1Y6M", {"days": 545}),  # 365 + 180
            ("P1DT1H1M1S", {"days": 1, "hours": 1, "minutes": 1, "seconds": 1}),
        ],
    )
    def test_valid_durations(self, parser, duration, expected):
        result = parser.parse_iso8601_duration(duration)
        assert result == expected

    @pytest.mark.parametrize(
        "duration,match",
        [
            ("", "empty"),
            ("T1H", "start with 'P'"),
            ("P", "at least one valid component"),
            ("PXY", "Expected number"),
            ("P1", "Unexpected end"),
            ("P1X", "Invalid unit"),
        ],
    )
    def test_invalid_durations(self, parser, duration, match):
        with pytest.raises(ValueError, match=match):
            parser.parse_iso8601_duration(duration)

    def test_duplicate_unit_raises(self, parser):
        with pytest.raises(ValueError, match="Duplicate unit"):
            parser.parse_iso8601_duration("PT1H2H")

    def test_lowercase_is_accepted(self, parser):
        """Parser uppercases input, so lowercase should work."""
        result = parser.parse_iso8601_duration("pt1h")
        assert result == {"hours": 1}

    def test_fractional_values(self, parser):
        result = parser.parse_iso8601_duration("PT1.5H")
        assert result == {"hours": 1.5}


class TestCronSchedulerInit:
    def test_cron_expression(self, mock_pipeline_runner, mock_apscheduler):
        scheduler = CronScheduler(
            pipeline_runner=mock_pipeline_runner,
            scheduler=mock_apscheduler,
            cron_expression="0 * * * *",
        )
        assert scheduler.scheduler is mock_apscheduler
        mock_apscheduler.add_job.assert_called_once()

    def test_explicit_time_params_known_limitation(
        self, mock_pipeline_runner, mock_apscheduler
    ):
        """The code passes all time params positionally to CronTrigger,
        including 0 defaults for unused params (year, month, day).
        CronTrigger rejects 0 for these fields (min is 1970 for year,
        1 for month/day). This is a known limitation -- using explicit
        params without valid values for all fields will raise ValueError."""
        with pytest.raises(ValueError):
            CronScheduler(
                pipeline_runner=mock_pipeline_runner,
                scheduler=mock_apscheduler,
                hour=6,
                minute=30,
            )

    def test_both_cron_and_params_raises(self, mock_pipeline_runner, mock_apscheduler):
        with pytest.raises(ValueError, match="Either a valid cron_expression"):
            CronScheduler(
                pipeline_runner=mock_pipeline_runner,
                scheduler=mock_apscheduler,
                cron_expression="0 * * * *",
                hour=6,
            )

    def test_neither_cron_nor_params_raises(
        self, mock_pipeline_runner, mock_apscheduler
    ):
        with pytest.raises(ValueError, match="Either a valid cron_expression"):
            CronScheduler(
                pipeline_runner=mock_pipeline_runner,
                scheduler=mock_apscheduler,
            )


class TestIntervalSchedulerInit:
    def test_explicit_interval_params(self, mock_pipeline_runner, mock_apscheduler):
        IntervalScheduler(
            pipeline_runner=mock_pipeline_runner,
            scheduler=mock_apscheduler,
            hours=1,
            minutes=30,
        )
        mock_apscheduler.add_job.assert_called_once()

    def test_iso8601_interval_string(self, mock_pipeline_runner, mock_apscheduler):
        scheduler = IntervalScheduler(
            pipeline_runner=mock_pipeline_runner,
            scheduler=mock_apscheduler,
            interval="PT2H",
        )
        assert scheduler.duration_dict == {"hours": 2}
        mock_apscheduler.add_job.assert_called_once()

    def test_both_interval_and_params_raises(
        self, mock_pipeline_runner, mock_apscheduler
    ):
        with pytest.raises(ValueError, match="Must provide either"):
            IntervalScheduler(
                pipeline_runner=mock_pipeline_runner,
                scheduler=mock_apscheduler,
                interval="PT1H",
                hours=1,
            )

    def test_neither_interval_nor_params_raises(
        self, mock_pipeline_runner, mock_apscheduler
    ):
        with pytest.raises(ValueError, match="Must provide either"):
            IntervalScheduler(
                pipeline_runner=mock_pipeline_runner,
                scheduler=mock_apscheduler,
            )


class TestSchedulerStartShutdown:
    def test_cron_start(self, mock_pipeline_runner, mock_apscheduler):
        scheduler = CronScheduler(
            pipeline_runner=mock_pipeline_runner,
            scheduler=mock_apscheduler,
            cron_expression="0 * * * *",
        )
        scheduler.start()
        mock_apscheduler.start.assert_called_once()

    def test_cron_shutdown(self, mock_pipeline_runner, mock_apscheduler):
        scheduler = CronScheduler(
            pipeline_runner=mock_pipeline_runner,
            scheduler=mock_apscheduler,
            cron_expression="0 * * * *",
        )
        scheduler.shutdown()
        mock_apscheduler.shutdown.assert_called_once()

    def test_interval_start(self, mock_pipeline_runner, mock_apscheduler):
        scheduler = IntervalScheduler(
            pipeline_runner=mock_pipeline_runner,
            scheduler=mock_apscheduler,
            hours=1,
        )
        scheduler.start()
        mock_apscheduler.start.assert_called_once()

    def test_interval_shutdown(self, mock_pipeline_runner, mock_apscheduler):
        scheduler = IntervalScheduler(
            pipeline_runner=mock_pipeline_runner,
            scheduler=mock_apscheduler,
            hours=1,
        )
        scheduler.shutdown()
        mock_apscheduler.shutdown.assert_called_once()
