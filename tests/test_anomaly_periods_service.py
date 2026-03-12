"""Tests for anomaly_periods_service.py"""
from datetime import datetime, timezone

from app.fastapi.services.anomaly_periods_service import (
    LOW_THRESHOLD,
    HIGH_THRESHOLD,
    classify_score,
    process_new_log,
    backfill_anomaly_periods,
    get_anomaly_periods_for_chart,
)
from app.repositories.anomaly_periods_repository import AnomalyPeriodsRepository
from tests.conftest import PUB1_ID, PUB2_ID


# ── classify_score ──────────────────────────────────────────────────────


class TestClassifyScore:
    def test_critical(self):
        assert classify_score(0.85) == "critical"
        assert classify_score(0.71) == "critical"

    def test_warning(self):
        assert classify_score(0.50) == "warning"
        assert classify_score(0.31) == "warning"

    def test_normal(self):
        assert classify_score(0.30) is None
        assert classify_score(0.10) is None
        assert classify_score(0.00) is None

    def test_boundary_values(self):
        assert classify_score(HIGH_THRESHOLD) == "warning"  # 0.7 exactly → > LOW but not > HIGH
        assert classify_score(LOW_THRESHOLD) is None        # 0.3 exactly → not anomalous
        assert classify_score(HIGH_THRESHOLD + 0.01) == "critical"
        assert classify_score(LOW_THRESHOLD + 0.01) == "warning"


# ── process_new_log ─────────────────────────────────────────────────────


class TestProcessNewLog:
    def test_normal_score_no_open_period(self, db_session, seed_data):
        result = process_new_log(
            db_session, PUB1_ID,
            datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
            0.10,
        )
        assert result is None

    def test_anomalous_score_opens_period(self, db_session, seed_data):
        ts = datetime(2026, 1, 1, 2, 0, tzinfo=timezone.utc)
        result = process_new_log(db_session, PUB1_ID, ts, 0.80)

        assert result is not None
        assert result.anomaly_type == "critical"
        assert result.start_timestamp == ts
        assert result.end_timestamp is None
        assert result.log_count == 1

    def test_second_anomalous_extends_period(self, db_session, seed_data):
        ts1 = datetime(2026, 1, 1, 2, 0, tzinfo=timezone.utc)
        ts2 = datetime(2026, 1, 1, 3, 0, tzinfo=timezone.utc)

        p1 = process_new_log(db_session, PUB1_ID, ts1, 0.80)
        p2 = process_new_log(db_session, PUB1_ID, ts2, 0.75)

        assert p1.period_id == p2.period_id
        assert p2.log_count == 2
        assert p2.end_timestamp is None

    def test_normal_score_closes_period(self, db_session, seed_data):
        ts1 = datetime(2026, 1, 1, 2, 0, tzinfo=timezone.utc)
        ts2 = datetime(2026, 1, 1, 3, 0, tzinfo=timezone.utc)
        ts3 = datetime(2026, 1, 1, 4, 0, tzinfo=timezone.utc)

        process_new_log(db_session, PUB1_ID, ts1, 0.80)
        process_new_log(db_session, PUB1_ID, ts2, 0.75)
        result = process_new_log(db_session, PUB1_ID, ts3, 0.20)

        assert result is None

        repo = AnomalyPeriodsRepository(db_session)
        assert repo.get_open_period(PUB1_ID) is None

        periods = repo.get_all_periods(PUB1_ID)
        assert len(periods) == 1
        assert periods[0].end_timestamp == ts3

    def test_type_change_closes_and_opens(self, db_session, seed_data):
        ts1 = datetime(2026, 1, 1, 2, 0, tzinfo=timezone.utc)
        ts2 = datetime(2026, 1, 1, 3, 0, tzinfo=timezone.utc)

        p1 = process_new_log(db_session, PUB1_ID, ts1, 0.50)  # warning
        p2 = process_new_log(db_session, PUB1_ID, ts2, 0.85)  # critical

        assert p1.period_id != p2.period_id
        assert p1.anomaly_type == "warning"
        assert p2.anomaly_type == "critical"
        assert p1.end_timestamp == ts2  # old period closed
        assert p2.end_timestamp is None  # new period open

    def test_avg_and_max_tracked(self, db_session, seed_data):
        ts1 = datetime(2026, 1, 1, 2, 0, tzinfo=timezone.utc)
        ts2 = datetime(2026, 1, 1, 3, 0, tzinfo=timezone.utc)
        ts3 = datetime(2026, 1, 1, 4, 0, tzinfo=timezone.utc)

        process_new_log(db_session, PUB1_ID, ts1, 0.80)
        process_new_log(db_session, PUB1_ID, ts2, 0.90)
        p = process_new_log(db_session, PUB1_ID, ts3, 0.75)

        assert p.log_count == 3
        assert abs(p.max_score - 0.90) < 0.001
        expected_avg = (0.80 + 0.90 + 0.75) / 3
        assert abs(p.avg_score - expected_avg) < 0.001


# ── backfill_anomaly_periods ────────────────────────────────────────────


class TestBackfillAnomalyPeriods:
    def test_backfill_pub1(self, db_session, seed_data):
        """PUB1 scores: 0.10, 0.15, 0.80, 0.75, 0.20, 0.12
        Anomalous (>0.3): h02 (0.80 critical), h03 (0.75 critical)
        → 1 contiguous critical period [h02, h04-closed]
        """
        periods = backfill_anomaly_periods(db_session, PUB1_ID)

        assert len(periods) == 1
        p = periods[0]
        assert p.anomaly_type == "critical"
        assert p.start_timestamp == datetime(2026, 1, 1, 2, 0, tzinfo=timezone.utc)
        assert p.end_timestamp == datetime(2026, 1, 1, 4, 0, tzinfo=timezone.utc)
        assert p.log_count == 2
        assert abs(p.max_score - 0.80) < 0.001

    def test_backfill_pub2(self, db_session, seed_data):
        """PUB2 scores: 0.50 (h02), 0.55 (h03), 0.45 (h04)
        All > 0.3 and ≤ 0.7 → all "warning"
        → 1 contiguous warning period [h02, still open]
        (no normal score follows to close it)
        """
        periods = backfill_anomaly_periods(db_session, PUB2_ID)

        assert len(periods) == 1
        p = periods[0]
        assert p.anomaly_type == "warning"
        assert p.start_timestamp == datetime(2026, 1, 1, 2, 0, tzinfo=timezone.utc)
        assert p.end_timestamp is None  # still open
        assert p.log_count == 3

    def test_backfill_idempotent(self, db_session, seed_data):
        """Running backfill twice produces the same result."""
        periods1 = backfill_anomaly_periods(db_session, PUB1_ID)
        periods2 = backfill_anomaly_periods(db_session, PUB1_ID)

        assert len(periods1) == len(periods2)
        assert periods2[0].anomaly_type == periods1[0].anomaly_type

    def test_backfill_since_filters(self, db_session, seed_data):
        """Backfill from h03 onward for PUB1: 0.75 (critical), 0.20, 0.12
        → 1 period (h03 closed at h04)
        """
        since = datetime(2026, 1, 1, 3, 0, tzinfo=timezone.utc)
        periods = backfill_anomaly_periods(db_session, PUB1_ID, since=since)

        assert len(periods) == 1
        assert periods[0].start_timestamp == datetime(2026, 1, 1, 3, 0, tzinfo=timezone.utc)


# ── get_anomaly_periods_for_chart ───────────────────────────────────────


class TestGetAnomalyPeriodsForChart:
    def test_returns_chart_format(self, db_session, seed_data):
        backfill_anomaly_periods(db_session, PUB1_ID)

        t1 = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 1, 1, 6, 0, tzinfo=timezone.utc)
        chart_data = get_anomaly_periods_for_chart(db_session, PUB1_ID, t1, t2)

        assert len(chart_data) == 1
        entry = chart_data[0]
        assert "x1" in entry
        assert "x2" in entry
        assert "label" in entry
        assert "fill" in entry
        assert "stroke" in entry
        assert "anomaly_type" in entry
        assert "avg_score" in entry
        assert "max_score" in entry
        assert "log_count" in entry

    def test_critical_has_red_fill(self, db_session, seed_data):
        backfill_anomaly_periods(db_session, PUB1_ID)

        t1 = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 1, 1, 6, 0, tzinfo=timezone.utc)
        chart_data = get_anomaly_periods_for_chart(db_session, PUB1_ID, t1, t2)

        assert "rgba(255, 0, 0" in chart_data[0]["fill"]
        assert chart_data[0]["stroke"] == "#cc0000"

    def test_warning_has_orange_fill(self, db_session, seed_data):
        backfill_anomaly_periods(db_session, PUB2_ID)

        t1 = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 1, 1, 6, 0, tzinfo=timezone.utc)
        chart_data = get_anomaly_periods_for_chart(db_session, PUB2_ID, t1, t2)

        assert "rgba(255, 165, 0" in chart_data[0]["fill"]
        assert chart_data[0]["stroke"] == "#cc8800"

    def test_open_period_uses_t2_as_end(self, db_session, seed_data):
        backfill_anomaly_periods(db_session, PUB2_ID)

        t1 = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 1, 1, 6, 0, tzinfo=timezone.utc)
        chart_data = get_anomaly_periods_for_chart(db_session, PUB2_ID, t1, t2)

        # open period → x2 should be t2
        assert chart_data[0]["x2"] == t2.isoformat()
        # but end_timestamp metadata is None
        assert chart_data[0]["end_timestamp"] is None

    def test_empty_when_no_periods(self, db_session, seed_data):
        t1 = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 1, 1, 6, 0, tzinfo=timezone.utc)
        chart_data = get_anomaly_periods_for_chart(db_session, PUB1_ID, t1, t2)
        assert chart_data == []

    def test_label_includes_peak(self, db_session, seed_data):
        backfill_anomaly_periods(db_session, PUB1_ID)

        t1 = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 1, 1, 6, 0, tzinfo=timezone.utc)
        chart_data = get_anomaly_periods_for_chart(db_session, PUB1_ID, t1, t2)

        label = chart_data[0]["label"]
        assert "Critical" in label
        assert "peak" in label.lower()



