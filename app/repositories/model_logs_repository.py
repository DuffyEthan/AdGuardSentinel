from datetime import datetime

from sqlalchemy import asc

from app.db.models import ModelLogs
from app.repositories.base import BaseRepository


class ModelLogsRepository(BaseRepository):
    def get_between(
        self,
        t1: datetime, # inclusive lower bound timestamp
        t2: datetime, # inclusive upper bound timestamp
        publisher_id: int | None = None, # optionally filter by publisher_id
    ) -> list[ModelLogs]:

        query = self.session.query(ModelLogs).filter(
            ModelLogs.timestamp >= t1,
            ModelLogs.timestamp <= t2,
        )

        if publisher_id is not None:
            query = query.filter(ModelLogs.publisher_id == publisher_id)

        return query.order_by(asc(ModelLogs.timestamp)).all()
