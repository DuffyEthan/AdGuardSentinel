from datetime import datetime, timezone

from app.repositories.raw_metrics_repository import RawMetricsRepository
from tests.conftest import PUB1_ID, PUB2_ID


class TestGetLastNBefore:
    def test_returns_n_rows(self, db_session, seed_data):
        repo = RawMetricsRepository(db_session)
        t = datetime(2026, 1, 1, 6, 0, tzinfo=timezone.utc)

        rows = repo.get_last_n_before(t, n=3, publisher_id=PUB1_ID)

        assert len(rows) == 3

    def test_chronological_order(self, db_session, seed_data):
        repo = RawMetricsRepository(db_session)
        t = datetime(2026, 1, 1, 6, 0, tzinfo=timezone.utc)

        rows = repo.get_last_n_before(t, n=4, publisher_id=PUB1_ID)

        timestamps = [r.bucket_timestamp for r in rows]
        assert timestamps == sorted(timestamps)

    def test_excludes_upper_bound(self, db_session, seed_data):
        repo = RawMetricsRepository(db_session)
        t = datetime(2026, 1, 1, 3, 0, tzinfo=timezone.utc)

        rows = repo.get_last_n_before(t, n=100, publisher_id=PUB1_ID)

        returned_ts = {r.bucket_timestamp for r in rows}
        assert t.replace(tzinfo=timezone.utc) not in returned_ts
        assert len(rows) == 3  # hours 00, 01, 02

    def test_filters_by_publisher(self, db_session, seed_data):
        repo = RawMetricsRepository(db_session)
        t = datetime(2026, 1, 1, 6, 0, tzinfo=timezone.utc)

        rows = repo.get_last_n_before(t, n=100, publisher_id=PUB2_ID)

        assert all(r.publisher_id == PUB2_ID for r in rows)
        assert len(rows) == 6

    def test_all_publishers_when_no_filter(self, db_session, seed_data):
        repo = RawMetricsRepository(db_session)
        t = datetime(2026, 1, 1, 6, 0, tzinfo=timezone.utc)

        rows = repo.get_last_n_before(t, n=100, publisher_id=None)

        publisher_ids = {r.publisher_id for r in rows}
        assert publisher_ids == {PUB1_ID, PUB2_ID}
        assert len(rows) == 12

    def test_empty_result(self, db_session, seed_data):
        repo = RawMetricsRepository(db_session)
        t = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)

        rows = repo.get_last_n_before(t, n=100, publisher_id=PUB1_ID)

        assert rows == []

    def test_returns_fewer_than_n_when_not_enough(self, db_session, seed_data):
        repo = RawMetricsRepository(db_session)
        t = datetime(2026, 1, 1, 2, 0, tzinfo=timezone.utc)

        rows = repo.get_last_n_before(t, n=10, publisher_id=PUB1_ID)

        assert len(rows) == 2  # only hours 00, 01 before 02:00
