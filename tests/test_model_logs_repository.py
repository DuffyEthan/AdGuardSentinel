from datetime import datetime, timezone
from decimal import Decimal

from app.db.models import ModelLogs, RawMetrics
from app.repositories.model_logs_repository import ModelLogsRepository
from tests.conftest import CAMP1_ID, CAMP2_ID, PUB1_ID, PUB2_ID


class TestGetBetween:
    def test_returns_joined_results(self, db_session, seed_data):
        repo = ModelLogsRepository(db_session)
        t1 = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 1, 1, 5, 0, tzinfo=timezone.utc)

        rows = repo.get_between(t1, t2, publisher_id=PUB1_ID, campaign_id=CAMP1_ID)

        assert len(rows) > 0
        for row in rows:
            model_log, raw_metric = row
            assert isinstance(model_log, ModelLogs)
            assert isinstance(raw_metric, RawMetrics)

    def test_inclusive_lower_bound(self, db_session, seed_data):
        repo = ModelLogsRepository(db_session)
        t1 = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 1, 1, 1, 0, tzinfo=timezone.utc)

        rows = repo.get_between(t1, t2, publisher_id=PUB1_ID, campaign_id=CAMP1_ID)

        ml_timestamps = {row[0].timestamp for row in rows}
        assert t1 in ml_timestamps

    def test_inclusive_upper_bound(self, db_session, seed_data):
        repo = ModelLogsRepository(db_session)
        t1 = datetime(2026, 1, 1, 4, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 1, 1, 5, 0, tzinfo=timezone.utc)

        rows = repo.get_between(t1, t2, publisher_id=PUB1_ID, campaign_id=CAMP1_ID)

        ml_timestamps = {row[0].timestamp for row in rows}
        assert t2 in ml_timestamps

    def test_chronological_order(self, db_session, seed_data):
        repo = ModelLogsRepository(db_session)
        t1 = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 1, 1, 5, 0, tzinfo=timezone.utc)

        rows = repo.get_between(t1, t2, publisher_id=PUB1_ID, campaign_id=CAMP1_ID)

        timestamps = [row[0].timestamp for row in rows]
        assert timestamps == sorted(timestamps)

    def test_filters_by_publisher(self, db_session, seed_data):
        repo = ModelLogsRepository(db_session)
        t1 = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 1, 1, 5, 0, tzinfo=timezone.utc)

        rows = repo.get_between(t1, t2, publisher_id=PUB2_ID, campaign_id=CAMP2_ID)

        assert len(rows) > 0
        assert all(row[0].publisher_id == PUB2_ID for row in rows)
        assert all(row[1].publisher_id == PUB2_ID for row in rows)

    def test_empty_result_outside_range(self, db_session, seed_data):
        repo = ModelLogsRepository(db_session)
        t1 = datetime(2025, 6, 1, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2025, 6, 1, 23, 0, tzinfo=timezone.utc)

        rows = repo.get_between(t1, t2, publisher_id=PUB1_ID, campaign_id=CAMP1_ID)

        assert rows == []

    def test_inner_join_excludes_logs_without_raw_metrics(self, db_session, seed_data):
        # model log at hour 10 has no matching raw_metrics row
        db_session.add(
            ModelLogs(
                timestamp=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
                publisher_id=PUB1_ID,
                model_name="markov_v1",
                score=Decimal("0.90"),
            )
        )
        db_session.flush()

        repo = ModelLogsRepository(db_session)
        t1 = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)

        rows = repo.get_between(t1, t2, publisher_id=PUB1_ID, campaign_id=CAMP1_ID)

        assert rows == []

    def test_narrow_window(self, db_session, seed_data):
        repo = ModelLogsRepository(db_session)
        t = datetime(2026, 1, 1, 2, 0, tzinfo=timezone.utc)

        rows = repo.get_between(t, t, publisher_id=PUB1_ID, campaign_id=CAMP1_ID)

        assert len(rows) == 1
        model_log, raw_metric = rows[0]
        assert model_log.timestamp == t
        assert model_log.score == Decimal("0.80")
        assert raw_metric.bucket_timestamp == t
        assert raw_metric.impression_count == 110
