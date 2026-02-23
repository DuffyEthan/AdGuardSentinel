import uuid
from datetime import datetime, timezone

import numpy as np
import pytest

from app.services.derived_metrics_service import (
    MIN_PERIODS,
    SAMPLE_SIZE,
    compute_column_stats,
    compute_derived_metrics_from_raw,
    exclude_outliers_iqr,
    _weighted_mean,
)
from app.db.models import RawMetrics

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PUB_ID = uuid.UUID("a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11")
CAMP_ID = uuid.UUID("c2aade11-be2d-6a1a-dd8f-8ddbdf5a2c33")


def _make_raw_row(
    ts: datetime,
    impressions: int = 100,
    clicks: int = 10,
    conversions: int = 2,
) -> RawMetrics:
    # Create a RawMetrics instance for testing (not persisted).
    return RawMetrics(
        bucket_timestamp=ts,
        publisher_id=PUB_ID,
        campaign_id=CAMP_ID,
        impression_count=impressions,
        click_count=clicks,
        conversion_count=conversions,
    )


def _make_raw_rows(n: int, base_impressions: int = 100) -> list[RawMetrics]:
    # Generate n RawMetrics rows with sequential timestamps.
    return [
        _make_raw_row(
            ts=datetime(2026, 1, 1, i // 60, i % 60, tzinfo=timezone.utc),
            impressions=base_impressions + i,
            clicks=10 + (i % 5),
            conversions=2 + (i % 3),
        )
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# Tests: exclude_outliers_iqr
# ---------------------------------------------------------------------------


class TestExcludeOutliersIqr:
    def test_removes_extreme_values(self):
        values = np.array([10, 11, 12, 13, 14, 15, 100])
        filtered = exclude_outliers_iqr(values)

        assert 100 not in filtered
        assert len(filtered) < len(values)

    def test_keeps_normal_values(self):
        values = np.array([10, 11, 12, 13, 14, 15, 16])
        filtered = exclude_outliers_iqr(values)

        np.testing.assert_array_equal(filtered, values)

    def test_small_array_unchanged(self):
        # Arrays with fewer than 4 elements are returned unchanged.
        values = np.array([1, 2, 3])
        filtered = exclude_outliers_iqr(values)

        np.testing.assert_array_equal(filtered, values)

    def test_empty_array(self):
        values = np.array([])
        filtered = exclude_outliers_iqr(values)

        assert len(filtered) == 0

    def test_all_same_values(self):
        # When all values are identical, IQR = 0; nothing should be removed.
        values = np.array([5.0, 5.0, 5.0, 5.0, 5.0])
        filtered = exclude_outliers_iqr(values)

        np.testing.assert_array_equal(filtered, values)

    def test_symmetric_outliers(self):
        # Both low and high outliers should be removed.
        values = np.array([-100, 10, 11, 12, 13, 14, 200])
        filtered = exclude_outliers_iqr(values)

        assert -100 not in filtered
        assert 200 not in filtered

    def test_returns_original_if_all_filtered(self):
        # If IQR filtering would remove everything, return original.
        # This is an edge case — all values the same except one "outlier"
        # that is the only non-identical value. In practice IQR = 0 so
        # only the identical values survive, but the function should not
        # return an empty array.
        values = np.array([5.0, 5.0, 5.0, 5.0])
        filtered = exclude_outliers_iqr(values)

        assert len(filtered) > 0


# ---------------------------------------------------------------------------
# Tests: _weighted_mean
# ---------------------------------------------------------------------------


class TestWeightedMean:
    def test_uniform_values(self):
        # When all values are equal, weighted mean equals that value.
        values = np.array([10.0, 10.0, 10.0, 10.0])
        assert _weighted_mean(values) == pytest.approx(10.0)

    def test_linear_weights_bias_toward_end(self):
        # Weighted mean should be biased toward later (higher-weight) values.
        values = np.array([0.0, 0.0, 0.0, 100.0])
        result = _weighted_mean(values)
        simple_mean = np.mean(values)

        assert result > simple_mean  # biased toward the last value (100)

    def test_known_calculation(self):
        # Test with hand-calculated expected value.
        # values = [1, 2, 3], weights = [1, 2, 3]
        # weighted_mean = (1*1 + 2*2 + 3*3) / (1+2+3) = (1+4+9)/6 = 14/6
        values = np.array([1.0, 2.0, 3.0])
        expected = 14.0 / 6.0

        assert _weighted_mean(values) == pytest.approx(expected)

    def test_empty_array_returns_nan(self):
        values = np.array([])
        assert np.isnan(_weighted_mean(values))

    def test_single_value(self):
        values = np.array([42.0])
        assert _weighted_mean(values) == pytest.approx(42.0)


# ---------------------------------------------------------------------------
# Tests: compute_column_stats
# ---------------------------------------------------------------------------


class TestComputeColumnStats:
    def test_returns_none_when_insufficient_data(self):
        values = np.array([1.0, 2.0, 3.0])  # fewer than MIN_PERIODS (25)
        mean, std, wmean = compute_column_stats(values)

        assert mean is None
        assert std is None
        assert wmean is None

    def test_returns_values_with_enough_data(self):
        rng = np.random.default_rng(42)
        values = rng.normal(loc=100, scale=10, size=250)
        mean, std, wmean = compute_column_stats(values)

        assert mean is not None
        assert std is not None
        assert wmean is not None
        assert mean == pytest.approx(100, abs=5)
        assert std == pytest.approx(10, abs=5)

    def test_std_is_zero_for_identical_values(self):
        # std should be 0 when all values in the filtered set are identical.
        values = np.full(30, 50.0)
        mean, std, wmean = compute_column_stats(values)

        assert mean == pytest.approx(50.0)
        assert std == pytest.approx(0.0)
        assert wmean == pytest.approx(50.0)

    def test_outliers_excluded_from_stats(self):
        # Outliers should not influence the computed mean.
        rng = np.random.default_rng(42)
        normal_values = rng.normal(loc=100, scale=5, size=200)
        # Inject extreme outliers
        outliers = np.array([1000, 2000, -500, -800])
        values = np.concatenate([normal_values, outliers])

        mean, std, wmean = compute_column_stats(values)

        # mean should be close to 100 (not pulled by outliers)
        assert mean is not None
        assert mean == pytest.approx(100, abs=5)

    def test_returns_none_if_filtered_below_min_periods(self):
        # If IQR filtering reduces the set below MIN_PERIODS, return None.
        # Create MIN_PERIODS values where most are outliers after IQR
        # Actually this is hard to construct since IQR is robust. Use a
        # borderline case: exactly MIN_PERIODS rows, some of which are outliers.
        values = np.concatenate(
            [
                np.full(MIN_PERIODS - 2, 50.0),
                np.array([50000.0, 50000.0]),
            ]
        )
        # After IQR filtering, the two outliers are removed, leaving
        # MIN_PERIODS - 2 values which is < MIN_PERIODS.
        mean, std, wmean = compute_column_stats(values)

        assert mean is None
        assert std is None
        assert wmean is None


# ---------------------------------------------------------------------------
# Tests: compute_derived_metrics_from_raw
# ---------------------------------------------------------------------------


class TestComputeDerivedMetricsFromRaw:
    def test_returns_none_with_insufficient_rows(self):
        rows = _make_raw_rows(5)
        ts = datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc)

        result = compute_derived_metrics_from_raw(rows, PUB_ID, CAMP_ID, ts)

        assert result is None

    def test_returns_derived_metrics_with_enough_rows(self):
        rows = _make_raw_rows(250)
        ts = datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc)

        result = compute_derived_metrics_from_raw(rows, PUB_ID, CAMP_ID, ts)

        assert result is not None
        assert result.publisher_id == PUB_ID
        assert result.campaign_id == CAMP_ID
        assert result.bucket_timestamp == ts
        assert result.sample_size == 250

    def test_all_stat_columns_populated(self):
        rows = _make_raw_rows(250)
        ts = datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc)

        result = compute_derived_metrics_from_raw(rows, PUB_ID, CAMP_ID, ts)

        assert result is not None
        # All stat columns should be non-None for a full 250-row window
        assert result.impressions_mean is not None
        assert result.impressions_std is not None
        assert result.impressions_weighted_mean is not None
        assert result.clicks_mean is not None
        assert result.clicks_std is not None
        assert result.clicks_weighted_mean is not None
        assert result.conversions_mean is not None
        assert result.conversions_std is not None
        assert result.conversions_weighted_mean is not None

    def test_mean_values_reasonable(self):
        # Means should be close to the actual data center.
        rows = _make_raw_rows(250, base_impressions=100)
        ts = datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc)

        result = compute_derived_metrics_from_raw(rows, PUB_ID, CAMP_ID, ts)

        assert result is not None
        # Impressions range from 100 to 349 (100 + i for i in 0..249)
        # Mean should be around 224.5
        assert result.impressions_mean is not None
        assert 100 < result.impressions_mean < 350

    def test_weighted_mean_biased_toward_recent(self):
        # Weighted mean should be higher than simple mean for ascending data.
        rows = _make_raw_rows(250, base_impressions=100)
        ts = datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc)

        result = compute_derived_metrics_from_raw(rows, PUB_ID, CAMP_ID, ts)

        assert result is not None
        assert result.impressions_mean is not None
        assert result.impressions_weighted_mean is not None
        # For strictly ascending data, weighted mean > simple mean
        assert result.impressions_weighted_mean > result.impressions_mean

    def test_at_min_periods_boundary(self):
        # Exactly MIN_PERIODS rows should produce results.
        rows = _make_raw_rows(MIN_PERIODS)
        ts = datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc)

        result = compute_derived_metrics_from_raw(rows, PUB_ID, CAMP_ID, ts)

        assert result is not None
        assert result.sample_size == MIN_PERIODS

    def test_below_min_periods_returns_none(self):
        rows = _make_raw_rows(MIN_PERIODS - 1)
        ts = datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc)

        result = compute_derived_metrics_from_raw(rows, PUB_ID, CAMP_ID, ts)

        assert result is None


# ---------------------------------------------------------------------------
# Tests: constants
# ---------------------------------------------------------------------------


class TestConstants:
    def test_sample_size(self):
        assert SAMPLE_SIZE == 250

    def test_min_periods(self):
        assert MIN_PERIODS == 25
