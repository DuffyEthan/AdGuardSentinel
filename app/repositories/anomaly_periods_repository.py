import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import asc, desc
from sqlalchemy.dialects.postgresql import insert

from app.db.models import AnomalyPeriods
from app.repositories.base import BaseRepository


class AnomalyPeriodsRepository(BaseRepository):
    """CRUD operations for the anomaly_periods table."""

    # ── Queries ─────────────────────────────────────────────────────────

    def get_open_period(
        self,
        publisher_id: uuid.UUID,
        campaign_id: uuid.UUID,
    ) -> Optional[AnomalyPeriods]:
        """Return the currently-open anomaly period (end_timestamp IS NULL)."""
        return (
            self.session.query(AnomalyPeriods)
            .filter(
                AnomalyPeriods.publisher_id == publisher_id,
                AnomalyPeriods.campaign_id == campaign_id,
                AnomalyPeriods.end_timestamp.is_(None),
            )
            .order_by(desc(AnomalyPeriods.start_timestamp))
            .first()
        )

    def get_periods_between(
        self,
        publisher_id: uuid.UUID,
        campaign_id: uuid.UUID,
        t1: datetime,
        t2: datetime,
    ) -> list[AnomalyPeriods]:
        """Return all anomaly periods that overlap [t1, t2]."""
        return (
            self.session.query(AnomalyPeriods)
            .filter(
                AnomalyPeriods.publisher_id == publisher_id,
                AnomalyPeriods.campaign_id == campaign_id,
                AnomalyPeriods.start_timestamp <= t2,
                # open periods (end_timestamp IS NULL) or periods ending after t1
                (AnomalyPeriods.end_timestamp >= t1)
                | (AnomalyPeriods.end_timestamp.is_(None)),
            )
            .order_by(asc(AnomalyPeriods.start_timestamp))
            .all()
        )

    def get_all_periods(
        self,
        publisher_id: uuid.UUID,
        campaign_id: uuid.UUID,
    ) -> list[AnomalyPeriods]:
        """Return every anomaly period for a publisher, oldest first."""
        return (
            self.session.query(AnomalyPeriods)
            .filter(
                AnomalyPeriods.publisher_id == publisher_id,
                AnomalyPeriods.campaign_id == campaign_id,
            )
            .order_by(asc(AnomalyPeriods.start_timestamp))
            .all()
        )

    # ── Mutations ───────────────────────────────────────────────────────

    def open_period(
        self,
        publisher_id: uuid.UUID,
        campaign_id: uuid.UUID,
        start_timestamp: datetime,
        anomaly_type: str = "anomaly",
        score: float = 0.0,
    ) -> AnomalyPeriods:
        """Create a new open anomaly period."""
        period = AnomalyPeriods(
            period_id=uuid.uuid4(),
            publisher_id=publisher_id,
            campaign_id=campaign_id,
            anomaly_type=anomaly_type,
            start_timestamp=start_timestamp,
            end_timestamp=None,
            avg_score=score,
            max_score=score,
            log_count=1,
        )
        self.session.add(period)
        self.session.flush()
        return period

    def close_period(
        self,
        period: AnomalyPeriods,
        end_timestamp: datetime,
    ) -> None:
        """Close an anomaly period by setting end_timestamp."""
        period.end_timestamp = end_timestamp
        self.session.flush()

    def update_period_stats(
        self,
        period: AnomalyPeriods,
        new_score: float,
        new_timestamp: datetime,
    ) -> None:
        """Accumulate a new anomaly log entry into the running period stats."""
        old_count = period.log_count
        old_avg = period.avg_score or 0.0

        new_count = old_count + 1
        new_avg = (old_avg * old_count + new_score) / new_count

        period.avg_score = new_avg
        period.max_score = max(period.max_score or 0.0, new_score)
        period.log_count = new_count
        # extend the period's end to the latest seen timestamp (still open)
        self.session.flush()

    def upsert(self, period: AnomalyPeriods) -> None:
        """Insert-or-update an anomaly period by period_id."""
        stmt = insert(AnomalyPeriods).values(
            period_id=period.period_id,
            publisher_id=period.publisher_id,
            campaign_id=period.campaign_id,
            anomaly_type=period.anomaly_type,
            start_timestamp=period.start_timestamp,
            end_timestamp=period.end_timestamp,
            avg_score=period.avg_score,
            max_score=period.max_score,
            log_count=period.log_count,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="anomaly_periods_pkey",
            set_={
                "end_timestamp": stmt.excluded.end_timestamp,
                "avg_score": stmt.excluded.avg_score,
                "max_score": stmt.excluded.max_score,
                "log_count": stmt.excluded.log_count,
                "anomaly_type": stmt.excluded.anomaly_type,
            },
        )
        self.session.execute(stmt)
        self.session.flush()

