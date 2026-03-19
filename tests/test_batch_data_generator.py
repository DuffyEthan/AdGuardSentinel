import uuid
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from app.db.models import Campaigns, Publishers, RawMetrics
from app.ml.batch_data_generator import (
    GeneratorConfig,
    ensure_campaign_exists,
    ensure_publisher_exists,
    fetch_raw_metrics_from_db,
    generate_time_series_batch,
    get_aligned_start_timestamp,
    upsert_raw_metrics,
)


# ── Unit tests (no DB required) ──────────────────────────────────────────────


class TestGenerateTimeSeriesBatch:
    """Tests for generate_time_series_batch (pure computation, no DB)."""

    CONFIG = GeneratorConfig(batch_size=50, interval_minutes=5)
    PUB_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    CAMP_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    START = datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc)

    def _make_batch(self, seed: int = 42) -> pd.DataFrame:
        rng = np.random.default_rng(seed)
        return generate_time_series_batch(
            config=self.CONFIG,
            publisher_id=self.PUB_ID,
            campaign_id=self.CAMP_ID,
            start_timestamp=self.START,
            random_generator=rng,
        )

    def test_dataframe_shape(self):
        df = self._make_batch()

        assert len(df) == self.CONFIG.batch_size
        assert set(df.columns) == {
            "bucket_timestamp",
            "publisher_id",
            "campaign_id",
            "impression_count",
            "click_count",
            "conversion_count",
        }

    def test_columns_contain_uuids(self):
        df = self._make_batch()

        assert (df["publisher_id"] == self.PUB_ID).all()
        assert (df["campaign_id"] == self.CAMP_ID).all()

    def test_anomaly_injected(self):
        df = self._make_batch()

        # At least one impression should exceed baseline * spike_multiplier_min
        threshold = self.CONFIG.impressions_lambda * self.CONFIG.spike_multiplier_min
        assert (df["impression_count"] >= threshold).any()

    def test_timestamps_increment_by_interval(self):
        df = self._make_batch()

        timestamps = df["bucket_timestamp"].tolist()
        expected_delta = timedelta(minutes=self.CONFIG.interval_minutes)

        for i in range(1, len(timestamps)):
            assert timestamps[i] - timestamps[i - 1] == expected_delta

    def test_first_timestamp_matches_start(self):
        df = self._make_batch()

        assert df["bucket_timestamp"].iloc[0] == self.START

    def test_counts_are_non_negative(self):
        df = self._make_batch()

        assert (df["impression_count"] >= 0).all()
        assert (df["click_count"] >= 0).all()
        assert (df["conversion_count"] >= 0).all()


class TestGetAlignedStartTimestamp:
    """Tests for get_aligned_start_timestamp (pure computation, no DB)."""

    def test_aligned_to_interval(self):
        interval = 5
        result = get_aligned_start_timestamp(interval)

        assert result.minute % interval == 0

    def test_seconds_and_microseconds_zeroed(self):
        result = get_aligned_start_timestamp(5)

        assert result.second == 0
        assert result.microsecond == 0

    def test_timezone_is_utc(self):
        result = get_aligned_start_timestamp(10)

        assert result.tzinfo == timezone.utc


# ── Integration tests (require running DB via db_session fixture) ─────────────


# Fresh UUIDs to avoid collisions with seed_data
_TEST_PUB_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
_TEST_CAMP_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


class TestEnsurePublisherExists:
    def test_creates_publisher_when_missing(self, db_session):
        result = ensure_publisher_exists(db_session, _TEST_PUB_ID)

        assert result == _TEST_PUB_ID

        pub = db_session.get(Publishers, _TEST_PUB_ID)
        assert pub is not None
        assert pub.publisher_name == "Test Publisher"

    def test_noop_when_publisher_already_exists(self, db_session):
        # Insert directly first
        db_session.add(Publishers(publisher_id=_TEST_PUB_ID, publisher_name="Existing"))
        db_session.flush()

        # Should not raise and should not overwrite
        result = ensure_publisher_exists(db_session, _TEST_PUB_ID)

        assert result == _TEST_PUB_ID
        pub = db_session.get(Publishers, _TEST_PUB_ID)
        assert pub.publisher_name == "Existing"


class TestEnsureCampaignExists:
    def test_creates_campaign_when_missing(self, db_session):
        # Publisher must exist first (FK constraint)
        ensure_publisher_exists(db_session, _TEST_PUB_ID)

        result = ensure_campaign_exists(db_session, _TEST_CAMP_ID, _TEST_PUB_ID)

        assert result == _TEST_CAMP_ID

        camp = db_session.get(Campaigns, _TEST_CAMP_ID)
        assert camp is not None
        assert camp.publisher_id == _TEST_PUB_ID

    def test_noop_when_campaign_already_exists(self, db_session):
        ensure_publisher_exists(db_session, _TEST_PUB_ID)
        db_session.add(
            Campaigns(
                campaign_id=_TEST_CAMP_ID,
                publisher_id=_TEST_PUB_ID,
                start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
            )
        )
        db_session.flush()

        # Should not raise
        result = ensure_campaign_exists(db_session, _TEST_CAMP_ID, _TEST_PUB_ID)

        assert result == _TEST_CAMP_ID
        camp = db_session.get(Campaigns, _TEST_CAMP_ID)
        # Original start_date should be preserved (not overwritten)
        assert camp.start_date.year == 2025


class TestUpsertRawMetrics:
    def _setup_publisher_and_campaign(self, db_session):
        ensure_publisher_exists(db_session, _TEST_PUB_ID)
        ensure_campaign_exists(db_session, _TEST_CAMP_ID, _TEST_PUB_ID)

    def _make_batch(self, size: int = 10, seed: int = 42) -> pd.DataFrame:
        config = GeneratorConfig(batch_size=size, interval_minutes=5)
        rng = np.random.default_rng(seed)
        return generate_time_series_batch(
            config=config,
            publisher_id=_TEST_PUB_ID,
            campaign_id=_TEST_CAMP_ID,
            start_timestamp=datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc),
            random_generator=rng,
        )

    def test_inserts_batch(self, db_session):
        self._setup_publisher_and_campaign(db_session)
        df = self._make_batch(size=10)

        count = upsert_raw_metrics(db_session, df)

        assert count == 10

        rows = (
            db_session.query(RawMetrics)
            .filter(
                RawMetrics.publisher_id == _TEST_PUB_ID,
                RawMetrics.campaign_id == _TEST_CAMP_ID,
            )
            .all()
        )
        assert len(rows) == 10

    def test_upsert_overwrites_on_conflict(self, db_session):
        self._setup_publisher_and_campaign(db_session)

        ts = datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc)
        df1 = pd.DataFrame(
            [
                {
                    "bucket_timestamp": ts,
                    "publisher_id": _TEST_PUB_ID,
                    "campaign_id": _TEST_CAMP_ID,
                    "impression_count": 100,
                    "click_count": 10,
                    "conversion_count": 1,
                }
            ]
        )
        upsert_raw_metrics(db_session, df1)

        # Upsert again with different values for the same key
        df2 = pd.DataFrame(
            [
                {
                    "bucket_timestamp": ts,
                    "publisher_id": _TEST_PUB_ID,
                    "campaign_id": _TEST_CAMP_ID,
                    "impression_count": 999,
                    "click_count": 88,
                    "conversion_count": 7,
                }
            ]
        )
        upsert_raw_metrics(db_session, df2)

        row = (
            db_session.query(RawMetrics)
            .filter(
                RawMetrics.publisher_id == _TEST_PUB_ID,
                RawMetrics.campaign_id == _TEST_CAMP_ID,
                RawMetrics.bucket_timestamp == ts,
            )
            .one()
        )
        assert row.impression_count == 999
        assert row.click_count == 88
        assert row.conversion_count == 7

    def test_empty_dataframe_returns_zero(self, db_session):
        df = pd.DataFrame(
            columns=[
                "bucket_timestamp",
                "publisher_id",
                "campaign_id",
                "impression_count",
                "click_count",
                "conversion_count",
            ]
        )

        count = upsert_raw_metrics(db_session, df)

        assert count == 0


class TestFetchRawMetricsFromDb:
    def _setup_and_insert(self, db_session, n: int = 10) -> pd.DataFrame:
        ensure_publisher_exists(db_session, _TEST_PUB_ID)
        ensure_campaign_exists(db_session, _TEST_CAMP_ID, _TEST_PUB_ID)

        config = GeneratorConfig(batch_size=n, interval_minutes=5)
        rng = np.random.default_rng(99)
        df = generate_time_series_batch(
            config=config,
            publisher_id=_TEST_PUB_ID,
            campaign_id=_TEST_CAMP_ID,
            start_timestamp=datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc),
            random_generator=rng,
        )
        upsert_raw_metrics(db_session, df)
        return df

    def test_fetch_returns_correct_data(self, db_session):
        original_df = self._setup_and_insert(db_session, n=10)

        result_df = fetch_raw_metrics_from_db(
            db_session, publisher_id=_TEST_PUB_ID, campaign_id=_TEST_CAMP_ID
        )

        assert len(result_df) == 10
        assert set(result_df.columns) == {
            "bucket_timestamp",
            "publisher_id",
            "campaign_id",
            "impression_count",
            "click_count",
            "conversion_count",
        }
        # Verify impression values match what was inserted
        original_imps = sorted(original_df["impression_count"].tolist())
        result_imps = sorted(result_df["impression_count"].tolist())
        assert original_imps == result_imps

    def test_fetch_empty_returns_empty_dataframe(self, db_session):
        nonexistent_pub = uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
        nonexistent_camp = uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")

        result_df = fetch_raw_metrics_from_db(
            db_session, publisher_id=nonexistent_pub, campaign_id=nonexistent_camp
        )

        assert result_df.empty
        assert set(result_df.columns) == {
            "bucket_timestamp",
            "publisher_id",
            "campaign_id",
            "impression_count",
            "click_count",
            "conversion_count",
        }

    def test_fetch_respects_limit(self, db_session):
        self._setup_and_insert(db_session, n=20)

        result_df = fetch_raw_metrics_from_db(
            db_session,
            publisher_id=_TEST_PUB_ID,
            campaign_id=_TEST_CAMP_ID,
            limit=5,
        )

        assert len(result_df) == 5

    def test_fetch_returns_chronological_order(self, db_session):
        self._setup_and_insert(db_session, n=15)

        result_df = fetch_raw_metrics_from_db(
            db_session, publisher_id=_TEST_PUB_ID, campaign_id=_TEST_CAMP_ID
        )

        timestamps = result_df["bucket_timestamp"].tolist()
        assert timestamps == sorted(timestamps)
