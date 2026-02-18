# from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import Row, asc

from app.db.models import ModelLogs, RawMetrics
from app.repositories.base import BaseRepository


class ModelLogsRepository(BaseRepository):
    def get_between(
        self,
        t1: datetime, # inclusive lower bound timestamp
        t2: datetime, # inclusive upper bound timestamp
        publisher_id: int | None = None, # optionally filter by publisher_id
    # ) -> Sequence[Row[tuple[ModelLogs, RawMetrics]]]:
    ) -> list[ModelLogs]:
        query = (
            self.session.query(ModelLogs
                               # , RawMetrics
                               )
            # .join(
            #     RawMetrics,
            #     ModelLogs.publisher_id == RawMetrics.publisher_id,
            # )
            .filter(
                ModelLogs.timestamp >= t1,
                ModelLogs.timestamp <= t2,
                # RawMetrics.bucket_timestamp >= t1,
                # RawMetrics.bucket_timestamp <= t2,
            )
        )

        if publisher_id is not None:
            query = query.filter(ModelLogs.publisher_id == publisher_id)

        return query.order_by(asc(ModelLogs.timestamp)).all()
