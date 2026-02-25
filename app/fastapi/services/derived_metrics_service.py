from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

import numpy as np
from sqlalchemy.orm import Session

from app.db.models import DerivedMetrics, RawMetrics
from app.repositories.derived_metrics_repository import DerivedMetricsRepository
from app.repositories.raw_metrics_repository import RawMetricsRepository

SAMPLE_SIZE = 250
MIN_PERIODS = max(5, SAMPLE_SIZE // 10)  # 25


def exclude_outliers_iqr(
    values: np.ndarray,
) -> np.ndarray:  # Remove values outside 1.5 * IQR (interquartile range).
    # Args: values: 1-D array of numeric values. Returns: Filtered array with outliers removed. Returns the original array unchanged if it has fewer than 4 elements (IQR is unreliable).
    if len(values) < 4:
        return values

    q1 = float(np.percentile(values, 25))
    q3 = float(np.percentile(values, 75))
    iqr = q3 - q1

    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr

    mask = (values >= lower) & (values <= upper)
    filtered = values[mask]

    # If IQR filtering removes everything, return the original array
    if len(filtered) == 0:
        return values

    return filtered


def _weighted_mean(values: np.ndarray) -> float:
    # Compute weighted mean with linear weights [1, 2, ..., k]. Older values get lower weight, newer values get higher weight. Assumes *values* is already sorted chronologically (oldest first).
    k = len(values)
    if k == 0:
        return float("nan")
    weights = np.arange(1, k + 1, dtype=float)
    return float(np.sum(weights * values) / np.sum(weights))


def compute_column_stats(
    values: np.ndarray,
) -> tuple[Optional[float], Optional[float], Optional[float]]:
    # Compute mean, std, and weighted mean for a single metric column. The values are first filtered with IQR outlier exclusion, then: - mean and std are computed on the filtered set - weighted mean uses linear weights on the filtered set Args: values: 1-D array of metric values, sorted chronologically. Returns: (mean, std, weighted_mean) — all None if insufficient data.
    if len(values) < MIN_PERIODS:
        return None, None, None

    filtered = exclude_outliers_iqr(values)

    if len(filtered) < MIN_PERIODS:
        return None, None, None

    mean = float(np.mean(filtered))
    std = float(np.std(filtered, ddof=1)) if len(filtered) > 1 else 0.0
    w_mean = _weighted_mean(filtered)

    return mean, std, w_mean


def compute_derived_metrics_from_raw(
    raw_rows: list[RawMetrics],
    publisher_id: uuid.UUID,
    campaign_id: uuid.UUID,
    bucket_timestamp: datetime,
) -> Optional[DerivedMetrics]:
    # Compute derived metrics from a window of raw_metrics rows.
    # raw_rows: up to SAMPLE_SIZE rows, sorted chronologically (oldest first).
    # Returns a DerivedMetrics instance, or None if fewer than MIN_PERIODS rows.
    if len(raw_rows) < MIN_PERIODS:
        return None

    impressions = np.array([r.impression_count for r in raw_rows], dtype=float)
    clicks = np.array([r.click_count for r in raw_rows], dtype=float)
    conversions = np.array([r.conversion_count for r in raw_rows], dtype=float)

    imp_mean, imp_std, imp_wmean = compute_column_stats(impressions)
    clk_mean, clk_std, clk_wmean = compute_column_stats(clicks)
    conv_mean, conv_std, conv_wmean = compute_column_stats(conversions)

    return DerivedMetrics(
        bucket_timestamp=bucket_timestamp,
        publisher_id=publisher_id,
        campaign_id=campaign_id,
        impressions_mean=imp_mean,
        clicks_mean=clk_mean,
        conversions_mean=conv_mean,
        impressions_std=imp_std,
        clicks_std=clk_std,
        conversions_std=conv_std,
        impressions_weighted_mean=imp_wmean,
        clicks_weighted_mean=clk_wmean,
        conversions_weighted_mean=conv_wmean,
        sample_size=len(raw_rows),
    )


def compute_and_store(
    session: Session,
    publisher_id: uuid.UUID,
    campaign_id: uuid.UUID,
    bucket_timestamp: datetime,
) -> Optional[DerivedMetrics]:
    # Main entry point: fetch raw metrics, compute derived stats, persist result.
    # 1. Fetch up to SAMPLE_SIZE raw_metrics rows before bucket_timestamp
    # 2. Compute mean / std / weighted mean (with IQR outlier exclusion)
    # 3. Upsert the result into the derived_metrics table
    # Returns the persisted DerivedMetrics instance, or None if insufficient data.
    raw_repo = RawMetricsRepository(session)
    raw_rows = raw_repo.get_last_n_before(
        t=bucket_timestamp,
        n=SAMPLE_SIZE,
        publisher_id=publisher_id,
        campaign_id=campaign_id,
    )

    derived = compute_derived_metrics_from_raw(
        raw_rows=raw_rows,
        publisher_id=publisher_id,
        campaign_id=campaign_id,
        bucket_timestamp=bucket_timestamp,
    )

    if derived is None:
        return None

    derived_repo = DerivedMetricsRepository(session)
    derived_repo.upsert(derived)
    return derived
