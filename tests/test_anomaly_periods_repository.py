"""Tests for anomaly_periods_repository.py"""
import uuid
from datetime import datetime, timezone

from app.repositories.anomaly_periods_repository import AnomalyPeriodsRepository
from tests.conftest import CAMP1_ID, CAMP2_ID, PUB1_ID, PUB2_ID


class TestOpenPeriod:
    def test_creates_period(self, db_session, seed_data):
        repo = AnomalyPeriodsRepository(db_session)
        ts = datetime(2026, 1, 1, 2, 0, tzinfo=timezone.utc)
        period = repo.open_period(PUB1_ID, CAMP1_ID, ts, "warning", 0.5)

        assert period.publisher_id == PUB1_ID
        assert period.start_timestamp == ts
        assert period.end_timestamp is None
        assert period.anomaly_type == "warning"
        assert period.avg_score == 0.5
        assert period.max_score == 0.5
        assert period.log_count == 1

    def test_period_id_is_uuid(self, db_session, seed_data):
        repo = AnomalyPeriodsRepository(db_session)
        ts = datetime(2026, 1, 1, 2, 0, tzinfo=timezone.utc)
        period = repo.open_period(PUB1_ID, CAMP1_ID, ts)
        assert isinstance(period.period_id, uuid.UUID)


class TestGetOpenPeriod:
    def test_returns_open_period(self, db_session, seed_data):
        repo = AnomalyPeriodsRepository(db_session)
        ts = datetime(2026, 1, 1, 2, 0, tzinfo=timezone.utc)
        repo.open_period(PUB1_ID, CAMP1_ID, ts, "warning", 0.5)

        found = repo.get_open_period(PUB1_ID, CAMP1_ID)
        assert found is not None
        assert found.end_timestamp is None

    def test_returns_none_when_no_open(self, db_session, seed_data):
        repo = AnomalyPeriodsRepository(db_session)
        assert repo.get_open_period(PUB1_ID, CAMP1_ID) is None

    def test_returns_none_after_close(self, db_session, seed_data):
        repo = AnomalyPeriodsRepository(db_session)
        ts1 = datetime(2026, 1, 1, 2, 0, tzinfo=timezone.utc)
        ts2 = datetime(2026, 1, 1, 4, 0, tzinfo=timezone.utc)

        period = repo.open_period(PUB1_ID, CAMP1_ID, ts1, "warning", 0.5)
        repo.close_period(period, ts2)

        assert repo.get_open_period(PUB1_ID, CAMP1_ID) is None


class TestClosePeriod:
    def test_sets_end_timestamp(self, db_session, seed_data):
        repo = AnomalyPeriodsRepository(db_session)
        ts1 = datetime(2026, 1, 1, 2, 0, tzinfo=timezone.utc)
        ts2 = datetime(2026, 1, 1, 4, 0, tzinfo=timezone.utc)

        period = repo.open_period(PUB1_ID, CAMP1_ID, ts1, "critical", 0.8)
        repo.close_period(period, ts2)

        assert period.end_timestamp == ts2


class TestUpdatePeriodStats:
    def test_increments_count_and_updates_avg(self, db_session, seed_data):
        repo = AnomalyPeriodsRepository(db_session)
        ts1 = datetime(2026, 1, 1, 2, 0, tzinfo=timezone.utc)
        ts2 = datetime(2026, 1, 1, 3, 0, tzinfo=timezone.utc)

        period = repo.open_period(PUB1_ID, CAMP1_ID, ts1, "warning", 0.4)
        # log_count=1, avg=0.4, max=0.4

        repo.update_period_stats(period, 0.6, ts2)
        # log_count=2, avg=(0.4+0.6)/2=0.5, max=0.6

        assert period.log_count == 2
        assert abs(period.avg_score - 0.5) < 0.001
        assert abs(period.max_score - 0.6) < 0.001

    def test_max_tracks_peak(self, db_session, seed_data):
        repo = AnomalyPeriodsRepository(db_session)
        ts = datetime(2026, 1, 1, 2, 0, tzinfo=timezone.utc)

        period = repo.open_period(PUB1_ID, CAMP1_ID, ts, "critical", 0.9)
        repo.update_period_stats(period, 0.75, datetime(2026, 1, 1, 3, 0, tzinfo=timezone.utc))

        assert abs(period.max_score - 0.9) < 0.001  # max stays at initial peak


class TestGetPeriodsBetween:
    def test_finds_overlapping_periods(self, db_session, seed_data):
        repo = AnomalyPeriodsRepository(db_session)

        # Period 1: 02:00-04:00
        p1 = repo.open_period(PUB1_ID, CAMP1_ID, datetime(2026, 1, 1, 2, 0, tzinfo=timezone.utc))
        repo.close_period(p1, datetime(2026, 1, 1, 4, 0, tzinfo=timezone.utc))

        # Period 2: 06:00-08:00
        p2 = repo.open_period(PUB1_ID, CAMP1_ID, datetime(2026, 1, 1, 6, 0, tzinfo=timezone.utc))
        repo.close_period(p2, datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc))

        # Query 03:00-07:00 → should get both
        result = repo.get_periods_between(
            PUB1_ID,
            CAMP1_ID,
            datetime(2026, 1, 1, 3, 0, tzinfo=timezone.utc),
            datetime(2026, 1, 1, 7, 0, tzinfo=timezone.utc),
        )
        assert len(result) == 2

    def test_excludes_non_overlapping(self, db_session, seed_data):
        repo = AnomalyPeriodsRepository(db_session)

        p = repo.open_period(PUB1_ID, CAMP1_ID, datetime(2026, 1, 1, 2, 0, tzinfo=timezone.utc))
        repo.close_period(p, datetime(2026, 1, 1, 3, 0, tzinfo=timezone.utc))

        # Query 05:00-06:00 → no overlap
        result = repo.get_periods_between(
            PUB1_ID,
            CAMP1_ID,
            datetime(2026, 1, 1, 5, 0, tzinfo=timezone.utc),
            datetime(2026, 1, 1, 6, 0, tzinfo=timezone.utc),
        )
        assert len(result) == 0

    def test_includes_open_periods(self, db_session, seed_data):
        repo = AnomalyPeriodsRepository(db_session)

        # Open period starting at 04:00, no end
        repo.open_period(PUB1_ID, CAMP1_ID, datetime(2026, 1, 1, 4, 0, tzinfo=timezone.utc))

        result = repo.get_periods_between(
            PUB1_ID,
            CAMP1_ID,
            datetime(2026, 1, 1, 5, 0, tzinfo=timezone.utc),
            datetime(2026, 1, 1, 6, 0, tzinfo=timezone.utc),
        )
        assert len(result) == 1
        assert result[0].end_timestamp is None

    def test_chronological_order(self, db_session, seed_data):
        repo = AnomalyPeriodsRepository(db_session)

        p2 = repo.open_period(PUB1_ID, CAMP1_ID, datetime(2026, 1, 1, 6, 0, tzinfo=timezone.utc))
        repo.close_period(p2, datetime(2026, 1, 1, 7, 0, tzinfo=timezone.utc))

        p1 = repo.open_period(PUB1_ID, CAMP1_ID, datetime(2026, 1, 1, 2, 0, tzinfo=timezone.utc))
        repo.close_period(p1, datetime(2026, 1, 1, 3, 0, tzinfo=timezone.utc))

        result = repo.get_periods_between(
            PUB1_ID,
            CAMP1_ID,
            datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc),
        )
        assert result[0].start_timestamp < result[1].start_timestamp


class TestGetAllPeriods:
    def test_returns_all(self, db_session, seed_data):
        repo = AnomalyPeriodsRepository(db_session)

        repo.open_period(PUB1_ID, CAMP1_ID, datetime(2026, 1, 1, 2, 0, tzinfo=timezone.utc))
        repo.open_period(PUB1_ID, CAMP1_ID, datetime(2026, 1, 1, 6, 0, tzinfo=timezone.utc))

        assert len(repo.get_all_periods(PUB1_ID, CAMP1_ID)) == 2

    def test_scoped_to_publisher(self, db_session, seed_data):
        repo = AnomalyPeriodsRepository(db_session)

        repo.open_period(PUB1_ID, CAMP1_ID, datetime(2026, 1, 1, 2, 0, tzinfo=timezone.utc))
        repo.open_period(PUB2_ID, CAMP2_ID, datetime(2026, 1, 1, 3, 0, tzinfo=timezone.utc))

        assert len(repo.get_all_periods(PUB1_ID, CAMP1_ID)) == 1
        assert len(repo.get_all_periods(PUB2_ID, CAMP2_ID)) == 1


