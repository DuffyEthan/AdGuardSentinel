import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import Row, asc

from app.db.models import ModelLogs, RawMetrics
from app.repositories.base import BaseRepository


class ModelLogsRepository(BaseRepository):
    def get_between(
        self,
        t1: datetime, # inclusive lower bound timestamp
        t2: datetime, # inclusive upper bound timestamp
        publisher_id: uuid.UUID, # filter by publisher_id
        campaign_id: uuid.UUID, # filter by campaign_id (used in join)
    ) -> Sequence[Row[tuple[ModelLogs, RawMetrics]]]:
        query = (
            self.session.query(ModelLogs, RawMetrics)
            .join(
                RawMetrics,
                ModelLogs.publisher_id == RawMetrics.publisher_id
            )
            .filter(
                ModelLogs.publisher_id == publisher_id,
                RawMetrics.campaign_id == campaign_id,
                ModelLogs.timestamp >= t1,
                ModelLogs.timestamp <= t2,
                RawMetrics.bucket_timestamp >= t1,
                RawMetrics.bucket_timestamp <= t2,
            )
        )

        return query.order_by(asc(ModelLogs.timestamp)).all()

    def bulk_insert(self, tuples: list[tuple]) -> None: # Insert model log rows from a list of (timestamp, publisher_id, model_name, score) tuples.
        if not tuples:
            return

        keys = ("timestamp", "publisher_id", "model_name", "score")
        recs = [dict(zip(keys, t)) for t in tuples]

        self.session.bulk_insert_mappings(ModelLogs, recs)
        self.session.flush()
