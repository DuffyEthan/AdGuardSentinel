from sqlalchemy import select

from app.db.models import Publishers, RawMetrics, ModelLogs
from app.db.session import get_session


def main():
    with get_session() as session:
        # Query publishers
        publishers = session.execute(select(Publishers).limit(5)).fetchall()
        print("=== Publishers ===")
        for row in publishers:
            print(row)
        print(f"Total publishers returned: {len(publishers)}\n")

        # Query raw_metrics (latest 5 by bucket_timestamp)
        metrics = session.execute(
            select(RawMetrics).order_by(RawMetrics.bucket_timestamp.desc()).limit(5)
        ).fetchall()
        print("=== Raw Metrics (latest 5) ===")
        for row in metrics:
            print(row)
        print(f"Total metrics returned: {len(metrics)}\n")

        # Query model_logs (latest 5 by timestamp)
        logs = session.execute(
            select(ModelLogs).order_by(ModelLogs.timestamp.desc()).limit(5)
        ).fetchall()
        print("=== Model Logs (latest 5) ===")
        for row in logs:
            print(row)
        print(f"Total logs returned: {len(logs)}")


if __name__ == "__main__":
    main()
