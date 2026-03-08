import uuid
from datetime import datetime

from sqlalchemy import desc

from app.db.models import RawMetrics
from app.repositories.base import BaseRepository


class RawMetricsRepository(BaseRepository):
    def get_last_n_before(
        self,
        t: datetime, # exclusive upper-bound timestamp
        n: int, # maximum number of rows to return
        publisher_id: uuid.UUID | None = None,  # optionally filter by publisher_id
        campaign_id: uuid.UUID | None = None, # optionally filter by campaign_id
    ) -> list[RawMetrics]:
        query = self.session.query(RawMetrics).filter(RawMetrics.bucket_timestamp < t)

        if publisher_id is not None:
            query = query.filter(RawMetrics.publisher_id == publisher_id)

        if campaign_id is not None:
            query = query.filter(RawMetrics.campaign_id == campaign_id)

        rows = query.order_by(desc(RawMetrics.bucket_timestamp)).limit(n).all()
        rows.reverse()  # could be done as a query, but this is simpler

        return rows
