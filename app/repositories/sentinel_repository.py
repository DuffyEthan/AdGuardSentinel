import math
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, desc, asc, and_

from app.db.models import Publishers, ModelLogs, RawMetrics, DerivedMetrics
from app.repositories.base import BaseRepository

# A publisher is considered suspicious when its trust score (0–1 from the ML
# model) falls below this value, i.e. anomaly_score = 1 - trust >= 0.7.
TRUST_THRESHOLD = 0.3          # below this → suspicious
ROLLING_WINDOW_HOURS = 24      # look-back window for the weighted average
DECAY_HALF_LIFE_HOURS = 2.0    # how quickly older scores lose weight


class SentinelRepository(BaseRepository):

    def get_sim_time(self) -> datetime:
        """Return the latest log_timestamp in model_logs as the simulation clock.
        Falls back to wall-clock UTC if the table is empty."""
        result = self.session.query(func.max(ModelLogs.log_timestamp)).scalar()
        return result if result is not None else datetime.now(timezone.utc)

    def _time_weighted_trust_score(
        self, publisher_id: uuid.UUID, as_of: datetime
    ) -> float:
        """Exponentially decayed weighted average of trust scores over the
        rolling window.  Returns a value in [0, 1] where 1 = fully trusted."""
        since = as_of - timedelta(hours=ROLLING_WINDOW_HOURS)
        logs = (
            self.session.query(ModelLogs.log_timestamp, ModelLogs.score)
            .filter(
                ModelLogs.publisher_id == publisher_id,
                ModelLogs.log_timestamp >= since,
                ModelLogs.log_timestamp <= as_of,
            )
            .order_by(desc(ModelLogs.log_timestamp))
            .all()
        )
        if not logs:
            return 1.0  # no data → assume trusted until proven otherwise

        weighted_sum = 0.0
        total_weight = 0.0
        for ts, score in logs:
            age_hours = (as_of - ts).total_seconds() / 3600
            weight = math.exp(-age_hours * math.log(2) / DECAY_HALF_LIFE_HOURS)
            weighted_sum += weight * float(score)
            total_weight += weight

        return weighted_sum / total_weight if total_weight > 0 else 1.0

    # ── 2.1 Stats Row ──────────────────────────────────────────────────

    def get_publisher_count(self) -> int:
        return self.session.query(func.count(Publishers.publisher_id)).scalar() or 0

    def get_suspicious_publisher_count(self, since: datetime) -> int:
        # Suspicious = most recent trust score below TRUST_THRESHOLD
        latest_ts = (
            self.session.query(
                ModelLogs.publisher_id,
                func.max(ModelLogs.log_timestamp).label("max_ts"),
            )
            .filter(ModelLogs.log_timestamp >= since)
            .group_by(ModelLogs.publisher_id)
            .subquery()
        )

        count = (
            self.session.query(func.count(ModelLogs.publisher_id))
            .join(
                latest_ts,
                and_(
                    ModelLogs.publisher_id == latest_ts.c.publisher_id,
                    ModelLogs.log_timestamp == latest_ts.c.max_ts,
                ),
            )
            .filter(ModelLogs.score < TRUST_THRESHOLD)
            .scalar()
        )
        return count or 0

    def get_avg_network_ctr(self, since: datetime) -> float:
        result = (
            self.session.query(
                func.sum(RawMetrics.click_count).label("total_clicks"),
                func.sum(RawMetrics.impression_count).label("total_impressions"),
            )
            .filter(RawMetrics.bucket_timestamp >= since)
            .one()
        )
        total_clicks = result.total_clicks or 0
        total_impressions = result.total_impressions or 0
        if total_impressions == 0:
            return 0.0
        return round((total_clicks / total_impressions) * 100, 2)

    def get_fraud_event_count(self, since: datetime) -> int:
        count = (
            self.session.query(func.count())
            .select_from(ModelLogs)
            .filter(
                ModelLogs.score < TRUST_THRESHOLD,
                ModelLogs.log_timestamp >= since,
            )
            .scalar()
        )
        return count or 0

    def get_network_trust_breakdown(self) -> dict:
        latest_ts = (
            self.session.query(
                ModelLogs.publisher_id,
                func.max(ModelLogs.log_timestamp).label("max_ts"),
            )
            .group_by(ModelLogs.publisher_id)
            .subquery()
        )

        latest_scores = (
            self.session.query(ModelLogs.score)
            .join(
                latest_ts,
                and_(
                    ModelLogs.publisher_id == latest_ts.c.publisher_id,
                    ModelLogs.log_timestamp == latest_ts.c.max_ts,
                ),
            )
            .all()
        )

        trusted = 0
        watchlist = 0
        fraudulent = 0
        for (score,) in latest_scores:
            trust_score = round(float(score) * 100)
            if trust_score >= 70:
                trusted += 1
            elif trust_score >= 40:
                watchlist += 1
            else:
                fraudulent += 1

        return {
            "trusted": trusted,
            "watchlist": watchlist,
            "fraudulent": fraudulent,
        }

    # ── 2.2 Publisher Table ─────────────────────────────────────────────

    def get_publisher_trust_summary(self, as_of: datetime) -> list[dict]:
        publishers = self.session.query(Publishers).all()
        result = []

        for pub in publishers:
            latest_log = (
                self.session.query(ModelLogs)
                .filter(
                    ModelLogs.publisher_id == pub.publisher_id,
                    ModelLogs.log_timestamp <= as_of,
                )
                .order_by(desc(ModelLogs.log_timestamp))
                .first()
            )

            # Instant anomaly score for the table column (1 = fully anomalous).
            instant_ml_score = float(latest_log.score) if latest_log else 1.0
            anomaly_score = round(1.0 - instant_ml_score, 4)

            # Trust score: time-weighted rolling average of ML trust scores (0–100).
            weighted_ml = self._time_weighted_trust_score(pub.publisher_id, as_of)
            trust_score = round(weighted_ml * 100)

            latest_raw = (
                self.session.query(RawMetrics)
                .filter(
                    RawMetrics.publisher_id == pub.publisher_id,
                    RawMetrics.bucket_timestamp <= as_of,
                )
                .order_by(desc(RawMetrics.bucket_timestamp))
                .first()
            )

            if latest_raw and latest_raw.impression_count > 0:
                ctr = round(
                    (latest_raw.click_count / latest_raw.impression_count) * 100, 2
                )
            else:
                ctr = 0.0

            if latest_raw and latest_raw.click_count > 0:
                cvr = round(
                    (latest_raw.conversion_count / latest_raw.click_count) * 100, 2
                )
            else:
                cvr = 0.0

            last_alert = self.get_last_alert_timestamp(pub.publisher_id)

            result.append(
                {
                    "publisher_id": str(pub.publisher_id),
                    "publisher_name": pub.publisher_name,
                    "trust_score": trust_score,
                    "anomaly_score": anomaly_score,
                    "ctr": ctr,
                    "cvr": cvr,
                    "fraud_type": latest_log.fraud_type if latest_log else None,
                    "last_alert_ts": last_alert,
                }
            )

        return result

    def get_last_alert_timestamp(self, publisher_id: uuid.UUID) -> Optional[datetime]:
        row = (
            self.session.query(ModelLogs.log_timestamp)
            .filter(
                ModelLogs.publisher_id == publisher_id,
                ModelLogs.score < TRUST_THRESHOLD,
            )
            .order_by(desc(ModelLogs.log_timestamp))
            .first()
        )
        return row[0].astimezone(timezone.utc) if row else None

    # ── 2.3 Trust Score Distribution Chart ──────────────────────────────

    def get_trust_score_distribution(self, as_of: datetime) -> list[dict]:
        latest_ts = (
            self.session.query(
                ModelLogs.publisher_id,
                func.max(ModelLogs.log_timestamp).label("max_ts"),
            )
            .filter(ModelLogs.log_timestamp <= as_of)
            .group_by(ModelLogs.publisher_id)
            .subquery()
        )

        latest_scores = (
            self.session.query(ModelLogs.publisher_id, ModelLogs.score)
            .join(
                latest_ts,
                and_(
                    ModelLogs.publisher_id == latest_ts.c.publisher_id,
                    ModelLogs.log_timestamp == latest_ts.c.max_ts,
                ),
            )
            .all()
        )

        buckets = {
            "0-20": 0,
            "20-40": 0,
            "40-60": 0,
            "60-80": 0,
            "80-90": 0,
            "90-100": 0,
        }

        for _, score in latest_scores:
            ts = round(float(score) * 100)
            if ts < 20:
                buckets["0-20"] += 1
            elif ts < 40:
                buckets["20-40"] += 1
            elif ts < 60:
                buckets["40-60"] += 1
            elif ts < 80:
                buckets["60-80"] += 1
            elif ts < 90:
                buckets["80-90"] += 1
            else:
                buckets["90-100"] += 1

        return [{"range": k, "count": v} for k, v in buckets.items()]

    # ── 2.4 Fraud Events Chart ──────────────────────────────────────────

    def get_daily_fraud_event_counts(self, days: int = 7) -> list[dict]:
        cutoff = self.get_sim_time() - timedelta(days=days)

        day_col = func.date_trunc("day", ModelLogs.log_timestamp).label("day")
        rows = (
            self.session.query(
                day_col,
                func.count().label("events"),
            )
            .filter(
                ModelLogs.score < TRUST_THRESHOLD,
                ModelLogs.log_timestamp >= cutoff,
            )
            .group_by(day_col)
            .order_by(day_col.asc())
            .all()
        )

        day_event_map: dict[str, int] = {}
        for row in rows:
            date_key = row.day.strftime("%Y-%m-%d")
            day_event_map[date_key] = row.events

        result = []
        for i in range(days):
            d = (cutoff + timedelta(days=i)).date()
            date_key = d.strftime("%Y-%m-%d")
            abbr = d.strftime("%a")
            result.append({"day": abbr, "events": day_event_map.get(date_key, 0)})

        return result

    # ── 2.5 Sentinel Assistant (raw DB queries) ─────────────────────────

    def get_anomaly_evidence(
        self,
        publisher_id: uuid.UUID,
        t1: datetime,
        t2: datetime,
    ) -> list[dict]:
        rows = (
            self.session.query(ModelLogs, RawMetrics)
            .join(
                RawMetrics,
                and_(
                    ModelLogs.publisher_id == RawMetrics.publisher_id,
                    func.date_trunc("hour", ModelLogs.log_timestamp)
                    == func.date_trunc("hour", RawMetrics.bucket_timestamp),
                ),
            )
            .filter(
                ModelLogs.publisher_id == publisher_id,
                ModelLogs.score < TRUST_THRESHOLD,
                ModelLogs.log_timestamp >= t1,
                ModelLogs.log_timestamp <= t2,
            )
            .order_by(asc(ModelLogs.log_timestamp))
            .all()
        )

        result = []
        seen_timestamps = set()
        for log, raw in rows:
            ts_key = log.log_timestamp
            if ts_key in seen_timestamps:
                continue
            seen_timestamps.add(ts_key)

            impressions = raw.impression_count
            clicks = raw.click_count
            conversions = raw.conversion_count

            ctr = round((clicks / impressions) * 100, 2) if impressions > 0 else 0.0
            cvr = round((conversions / clicks) * 100, 2) if clicks > 0 else 0.0

            result.append(
                {
                    "timestamp": log.log_timestamp,
                    "anomaly_score": float(log.score),
                    "ctr": ctr,
                    "cvr": cvr,
                    "impressions": impressions,
                    "clicks": clicks,
                    "conversions": conversions,
                }
            )

        return result

    def get_network_baselines(self, as_of: datetime) -> dict:
        result = (
            self.session.query(
                func.avg(
                    DerivedMetrics.clicks_mean / DerivedMetrics.impressions_mean * 100
                ).label("avg_ctr"),
                func.avg(
                    DerivedMetrics.conversions_mean / DerivedMetrics.clicks_mean * 100
                ).label("avg_cvr"),
                func.avg(DerivedMetrics.impressions_mean).label("avg_impression_count"),
                func.stddev(
                    DerivedMetrics.clicks_mean / DerivedMetrics.impressions_mean * 100
                ).label("ctr_std"),
                func.stddev(
                    DerivedMetrics.conversions_mean / DerivedMetrics.clicks_mean * 100
                ).label("cvr_std"),
            )
            .filter(
                DerivedMetrics.bucket_timestamp <= as_of,
                DerivedMetrics.impressions_mean > 0,
                DerivedMetrics.clicks_mean > 0,
            )
            .one()
        )

        return {
            "avg_ctr": round(float(result.avg_ctr or 0), 4),
            "avg_cvr": round(float(result.avg_cvr or 0), 4),
            "avg_impression_count": round(float(result.avg_impression_count or 0), 2),
            "ctr_std": round(float(result.ctr_std or 0), 4),
            "cvr_std": round(float(result.cvr_std or 0), 4),
        }

    def get_publisher_latest_derived(
        self, publisher_id: uuid.UUID, as_of: datetime
    ) -> Optional[DerivedMetrics]:
        return (
            self.session.query(DerivedMetrics)
            .filter(
                DerivedMetrics.publisher_id == publisher_id,
                DerivedMetrics.bucket_timestamp <= as_of,
            )
            .order_by(desc(DerivedMetrics.bucket_timestamp))
            .first()
        )
