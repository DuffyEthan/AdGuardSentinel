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

        ml_timestamps = {row[0].log_timestamp for row in rows}
        assert t1 in ml_timestamps

    def test_inclusive_upper_bound(self, db_session, seed_data):
        repo = ModelLogsRepository(db_session)
        t1 = datetime(2026, 1, 1, 4, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 1, 1, 5, 0, tzinfo=timezone.utc)

        rows = repo.get_between(t1, t2, publisher_id=PUB1_ID, campaign_id=CAMP1_ID)

        ml_timestamps = {row[0].log_timestamp for row in rows}
        assert t2 in ml_timestamps

    def test_chronological_order(self, db_session, seed_data):
        repo = ModelLogsRepository(db_session)
        t1 = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 1, 1, 5, 0, tzinfo=timezone.utc)

        rows = repo.get_between(t1, t2, publisher_id=PUB1_ID, campaign_id=CAMP1_ID)

        timestamps = [row[0].log_timestamp for row in rows]
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
                log_timestamp=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
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
        assert model_log.log_timestamp == t
        assert model_log.score == Decimal("0.80")
        assert raw_metric.bucket_timestamp == t
        assert raw_metric.impression_count == 110


class TestBulkInsert:
    # Use Feb 2026 timestamps to avoid collisions with seed_data (Jan 2026)
    _BASE_TS = datetime(2026, 2, 1, 0, 0, tzinfo=timezone.utc)
    _TS_1H = datetime(2026, 2, 1, 1, 0, tzinfo=timezone.utc)
    _TS_2H = datetime(2026, 2, 1, 2, 0, tzinfo=timezone.utc)

    def test_inserts_single_tuple(self, db_session, seed_data):
        repo = ModelLogsRepository(db_session)
        tuples = [(self._BASE_TS, PUB1_ID, "markov_v1", Decimal("0.42"))]

        repo.bulk_insert(tuples)

        rows = (
            db_session.query(ModelLogs)
            .filter(
                ModelLogs.publisher_id == PUB1_ID,
                ModelLogs.log_timestamp == self._BASE_TS,
            )
            .all()
        )
        assert len(rows) == 1

    def test_inserts_multiple_tuples(self, db_session, seed_data):
        repo = ModelLogsRepository(db_session)
        tuples = [
            (self._BASE_TS, PUB1_ID, "markov_v1", Decimal("0.10")),
            (self._TS_1H, PUB1_ID, "markov_v1", Decimal("0.20")),
            (self._TS_2H, PUB1_ID, "markov_v1", Decimal("0.30")),
        ]

        repo.bulk_insert(tuples)

        count = (
            db_session.query(ModelLogs)
            .filter(
                ModelLogs.publisher_id == PUB1_ID,
                ModelLogs.log_timestamp >= self._BASE_TS,
                ModelLogs.log_timestamp <= self._TS_2H,
            )
            .count()
        )
        assert count == 3

    def test_fields_stored_correctly(self, db_session, seed_data):
        repo = ModelLogsRepository(db_session)
        tuples = [(self._BASE_TS, PUB1_ID, "isolation_forest_v2", Decimal("0.73"))]

        repo.bulk_insert(tuples)

        row = (
            db_session.query(ModelLogs)
            .filter(
                ModelLogs.publisher_id == PUB1_ID,
                ModelLogs.log_timestamp == self._BASE_TS,
            )
            .one()
        )
        assert row.log_timestamp == self._BASE_TS
        assert row.publisher_id == PUB1_ID
        assert row.model_name == "isolation_forest_v2"
        assert row.score == Decimal("0.73")

    def test_score_boundary_zero(self, db_session, seed_data):
        repo = ModelLogsRepository(db_session)
        tuples = [(self._BASE_TS, PUB1_ID, "markov_v1", Decimal("0.00"))]

        repo.bulk_insert(tuples)

        row = (
            db_session.query(ModelLogs)
            .filter(
                ModelLogs.publisher_id == PUB1_ID,
                ModelLogs.log_timestamp == self._BASE_TS,
            )
            .one()
        )
        assert row.score == Decimal("0.00")

    def test_score_boundary_one(self, db_session, seed_data):
        repo = ModelLogsRepository(db_session)
        tuples = [(self._BASE_TS, PUB1_ID, "markov_v1", Decimal("1.00"))]

        repo.bulk_insert(tuples)

        row = (
            db_session.query(ModelLogs)
            .filter(
                ModelLogs.publisher_id == PUB1_ID,
                ModelLogs.log_timestamp == self._BASE_TS,
            )
            .one()
        )
        assert row.score == Decimal("1.00")

    def test_empty_list_is_noop(self, db_session, seed_data):
        repo = ModelLogsRepository(db_session)

        repo.bulk_insert([])

        # Seed data has 9 model_logs rows; count should be unchanged
        count = db_session.query(ModelLogs).count()
        assert count == 9
