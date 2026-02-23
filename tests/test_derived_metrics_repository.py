from datetime import datetime, timezone

from app.db.models import DerivedMetrics
from app.repositories.derived_metrics_repository import DerivedMetricsRepository
from tests.conftest import CAMP1_ID, PUB1_ID, PUB2_ID

# ---------------------------------------------------------------------------
# upsert
# ---------------------------------------------------------------------------


class TestUpsert:
    def test_insert_new_row(self, db_session, seed_data):
        repo = DerivedMetricsRepository(db_session)

        dm = DerivedMetrics(
            bucket_timestamp=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
            publisher_id=PUB1_ID,
            campaign_id=CAMP1_ID,
            impressions_mean=120.0,
            clicks_mean=9.0,
            conversions_mean=2.5,
            impressions_std=15.0,
            clicks_std=1.5,
            conversions_std=0.8,
            impressions_weighted_mean=125.0,
            clicks_weighted_mean=9.5,
            conversions_weighted_mean=2.7,
            sample_size=250,
        )
        repo.upsert(dm)

        result = repo.get_latest(PUB1_ID, CAMP1_ID)
        assert result is not None
        assert result.bucket_timestamp == datetime(
            2026, 1, 1, 10, 0, tzinfo=timezone.utc
        )
        assert result.impressions_mean == 120.0
        assert result.sample_size == 250

    def test_update_existing_row(self, db_session, seed_data):
        repo = DerivedMetricsRepository(db_session)

        # The seed data has a row at 05:00 for PUB1/CAMP1 — overwrite it
        dm = DerivedMetrics(
            bucket_timestamp=datetime(2026, 1, 1, 5, 0, tzinfo=timezone.utc),
            publisher_id=PUB1_ID,
            campaign_id=CAMP1_ID,
            impressions_mean=999.0,
            clicks_mean=99.0,
            conversions_mean=9.0,
            impressions_std=1.0,
            clicks_std=0.1,
            conversions_std=0.01,
            impressions_weighted_mean=998.0,
            clicks_weighted_mean=98.0,
            conversions_weighted_mean=8.0,
            sample_size=100,
        )
        repo.upsert(dm)

        result = repo.get_latest(PUB1_ID, CAMP1_ID)
        assert result is not None
        assert result.impressions_mean == 999.0
        assert result.sample_size == 100


# ---------------------------------------------------------------------------
# bulk_upsert
# ---------------------------------------------------------------------------


class TestBulkUpsert:
    def test_insert_multiple_rows(self, db_session, seed_data):
        repo = DerivedMetricsRepository(db_session)

        new_rows = [
            DerivedMetrics(
                bucket_timestamp=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
                publisher_id=PUB1_ID,
                campaign_id=CAMP1_ID,
                impressions_mean=100.0,
                clicks_mean=8.0,
                conversions_mean=2.0,
                impressions_std=10.0,
                clicks_std=1.0,
                conversions_std=0.5,
                impressions_weighted_mean=105.0,
                clicks_weighted_mean=8.5,
                conversions_weighted_mean=2.2,
                sample_size=250,
            ),
            DerivedMetrics(
                bucket_timestamp=datetime(2026, 1, 1, 11, 0, tzinfo=timezone.utc),
                publisher_id=PUB1_ID,
                campaign_id=CAMP1_ID,
                impressions_mean=102.0,
                clicks_mean=8.2,
                conversions_mean=2.1,
                impressions_std=10.5,
                clicks_std=1.1,
                conversions_std=0.6,
                impressions_weighted_mean=107.0,
                clicks_weighted_mean=8.7,
                conversions_weighted_mean=2.3,
                sample_size=250,
            ),
        ]
        repo.bulk_upsert(new_rows)

        # Both new rows + 3 seed rows = 5 total for PUB1/CAMP1
        all_rows = repo.get_last_n_before(
            t=datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc),
            n=100,
            publisher_id=PUB1_ID,
            campaign_id=CAMP1_ID,
        )
        assert len(all_rows) == 5

    def test_empty_list_does_nothing(self, db_session, seed_data):
        repo = DerivedMetricsRepository(db_session)
        repo.bulk_upsert([])  # should not raise


# ---------------------------------------------------------------------------
# get_latest
# ---------------------------------------------------------------------------


class TestGetLatest:
    def test_returns_most_recent(self, db_session, seed_data):
        repo = DerivedMetricsRepository(db_session)

        result = repo.get_latest(PUB1_ID, CAMP1_ID)

        assert result is not None
        assert result.bucket_timestamp == datetime(
            2026, 1, 1, 5, 0, tzinfo=timezone.utc
        )

    def test_returns_none_for_unknown_publisher(self, db_session, seed_data):
        repo = DerivedMetricsRepository(db_session)
        import uuid

        result = repo.get_latest(uuid.uuid4(), CAMP1_ID)

        assert result is None

    def test_returns_none_for_unknown_campaign(self, db_session, seed_data):
        repo = DerivedMetricsRepository(db_session)
        import uuid

        result = repo.get_latest(PUB1_ID, uuid.uuid4())

        assert result is None


# ---------------------------------------------------------------------------
# get_last_n_before
# ---------------------------------------------------------------------------


class TestGetLastNBefore:
    def test_returns_n_rows(self, db_session, seed_data):
        repo = DerivedMetricsRepository(db_session)
        t = datetime(2026, 1, 1, 6, 0, tzinfo=timezone.utc)

        rows = repo.get_last_n_before(
            t, n=2, publisher_id=PUB1_ID, campaign_id=CAMP1_ID
        )

        assert len(rows) == 2

    def test_chronological_order(self, db_session, seed_data):
        repo = DerivedMetricsRepository(db_session)
        t = datetime(2026, 1, 1, 6, 0, tzinfo=timezone.utc)

        rows = repo.get_last_n_before(
            t, n=10, publisher_id=PUB1_ID, campaign_id=CAMP1_ID
        )

        timestamps = [r.bucket_timestamp for r in rows]
        assert timestamps == sorted(timestamps)

    def test_excludes_upper_bound(self, db_session, seed_data):
        repo = DerivedMetricsRepository(db_session)
        # Upper bound at 05:00 — should not include the 05:00 row
        t = datetime(2026, 1, 1, 5, 0, tzinfo=timezone.utc)

        rows = repo.get_last_n_before(
            t, n=100, publisher_id=PUB1_ID, campaign_id=CAMP1_ID
        )

        returned_ts = {r.bucket_timestamp for r in rows}
        assert t.replace(tzinfo=timezone.utc) not in returned_ts
        assert len(rows) == 2  # hours 03, 04

    def test_filters_by_publisher(self, db_session, seed_data):
        repo = DerivedMetricsRepository(db_session)
        t = datetime(2026, 1, 1, 6, 0, tzinfo=timezone.utc)

        rows = repo.get_last_n_before(t, n=100, publisher_id=PUB2_ID)

        # No derived_metrics seeded for publisher 2
        assert len(rows) == 0

    def test_filters_by_campaign(self, db_session, seed_data):
        repo = DerivedMetricsRepository(db_session)
        t = datetime(2026, 1, 1, 6, 0, tzinfo=timezone.utc)

        rows = repo.get_last_n_before(t, n=100, campaign_id=CAMP1_ID)

        assert all(r.campaign_id == CAMP1_ID for r in rows)
        assert len(rows) == 3

    def test_empty_result(self, db_session, seed_data):
        repo = DerivedMetricsRepository(db_session)
        t = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)

        rows = repo.get_last_n_before(t, n=100, publisher_id=PUB1_ID)

        assert rows == []

    def test_returns_fewer_than_n_when_not_enough(self, db_session, seed_data):
        repo = DerivedMetricsRepository(db_session)
        t = datetime(2026, 1, 1, 4, 0, tzinfo=timezone.utc)

        rows = repo.get_last_n_before(
            t, n=10, publisher_id=PUB1_ID, campaign_id=CAMP1_ID
        )

        assert len(rows) == 1  # only hour 03 before 04:00
