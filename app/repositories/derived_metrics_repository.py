import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import desc
from sqlalchemy.dialects.postgresql import insert

from app.db.models import DerivedMetrics
from app.repositories.base import BaseRepository


class DerivedMetricsRepository(BaseRepository):
    def upsert(self, metrics: DerivedMetrics) -> None:
        # Insert or update a single derived_metrics row.
        # Uses ON CONFLICT DO UPDATE to make the operation idempotent.
        stmt = insert(DerivedMetrics).values(
            bucket_timestamp=metrics.bucket_timestamp,
            publisher_id=metrics.publisher_id,
            campaign_id=metrics.campaign_id,
            impressions_mean=metrics.impressions_mean,
            clicks_mean=metrics.clicks_mean,
            conversions_mean=metrics.conversions_mean,
            impressions_std=metrics.impressions_std,
            clicks_std=metrics.clicks_std,
            conversions_std=metrics.conversions_std,
            impressions_weighted_mean=metrics.impressions_weighted_mean,
            clicks_weighted_mean=metrics.clicks_weighted_mean,
            conversions_weighted_mean=metrics.conversions_weighted_mean,
            sample_size=metrics.sample_size,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="derived_metrics_pkey",
            set_={
                "impressions_mean": stmt.excluded.impressions_mean,
                "clicks_mean": stmt.excluded.clicks_mean,
                "conversions_mean": stmt.excluded.conversions_mean,
                "impressions_std": stmt.excluded.impressions_std,
                "clicks_std": stmt.excluded.clicks_std,
                "conversions_std": stmt.excluded.conversions_std,
                "impressions_weighted_mean": stmt.excluded.impressions_weighted_mean,
                "clicks_weighted_mean": stmt.excluded.clicks_weighted_mean,
                "conversions_weighted_mean": stmt.excluded.conversions_weighted_mean,
                "sample_size": stmt.excluded.sample_size,
            },
        )
        self.session.execute(stmt)
        self.session.flush()
        self.session.expire_all()

    def bulk_upsert(self, metrics_list: list[DerivedMetrics]) -> None:
        # Upsert multiple derived_metrics rows in a single statement.
        if not metrics_list:
            return

        rows = [
            {
                "bucket_timestamp": m.bucket_timestamp,
                "publisher_id": m.publisher_id,
                "campaign_id": m.campaign_id,
                "impressions_mean": m.impressions_mean,
                "clicks_mean": m.clicks_mean,
                "conversions_mean": m.conversions_mean,
                "impressions_std": m.impressions_std,
                "clicks_std": m.clicks_std,
                "conversions_std": m.conversions_std,
                "impressions_weighted_mean": m.impressions_weighted_mean,
                "clicks_weighted_mean": m.clicks_weighted_mean,
                "conversions_weighted_mean": m.conversions_weighted_mean,
                "sample_size": m.sample_size,
            }
            for m in metrics_list
        ]

        stmt = insert(DerivedMetrics).values(rows)
        stmt = stmt.on_conflict_do_update(
            constraint="derived_metrics_pkey",
            set_={
                "impressions_mean": stmt.excluded.impressions_mean,
                "clicks_mean": stmt.excluded.clicks_mean,
                "conversions_mean": stmt.excluded.conversions_mean,
                "impressions_std": stmt.excluded.impressions_std,
                "clicks_std": stmt.excluded.clicks_std,
                "conversions_std": stmt.excluded.conversions_std,
                "impressions_weighted_mean": stmt.excluded.impressions_weighted_mean,
                "clicks_weighted_mean": stmt.excluded.clicks_weighted_mean,
                "conversions_weighted_mean": stmt.excluded.conversions_weighted_mean,
                "sample_size": stmt.excluded.sample_size,
            },
        )
        self.session.execute(stmt)
        self.session.flush()
        self.session.expire_all()

    def get_latest(
        self,
        publisher_id: uuid.UUID,
        campaign_id: uuid.UUID,
    ) -> Optional[DerivedMetrics]:
        # Return the most recent derived_metrics row for a publisher + campaign.
        return (
            self.session.query(DerivedMetrics)
            .filter(
                DerivedMetrics.publisher_id == publisher_id,
                DerivedMetrics.campaign_id == campaign_id,
            )
            .order_by(desc(DerivedMetrics.bucket_timestamp))
            .first()
        )

    def get_last_n_before(
        self,
        t: datetime,  # exclusive upper-bound timestamp
        n: int,  # maximum number of rows to return
        publisher_id: Optional[uuid.UUID] = None,
        campaign_id: Optional[uuid.UUID] = None,
    ) -> list[DerivedMetrics]:
        # Return up to n derived_metrics rows before timestamp t.
        # Results are returned in chronological order (oldest first).
        query = self.session.query(DerivedMetrics).filter(
            DerivedMetrics.bucket_timestamp < t
        )

        if publisher_id is not None:
            query = query.filter(DerivedMetrics.publisher_id == publisher_id)

        if campaign_id is not None:
            query = query.filter(DerivedMetrics.campaign_id == campaign_id)

        rows = query.order_by(desc(DerivedMetrics.bucket_timestamp)).limit(n).all()
        rows.reverse()

        return rows
