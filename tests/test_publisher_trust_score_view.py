from __future__ import annotations

import math
import uuid

from sqlalchemy import text


PUB_A = uuid.UUID("11111111-1111-1111-1111-111111111111")
PUB_B = uuid.UUID("22222222-2222-2222-2222-222222222222")
PUB_C = uuid.UUID("33333333-3333-3333-3333-333333333333")


def _weight(hours_ago: float) -> float:
    # Matches the view's 24-hour quadratic decay: (1 - age_days)^2.
    age_days = hours_ago / 24.0
    return (1.0 - age_days) ** 2


def _expected_trust(scores_with_hours: list[tuple[float, float]]) -> float:
    numerator = 0.0
    denominator = 0.0
    for score, hours_ago in scores_with_hours:
        w = _weight(hours_ago)
        numerator += ((1.0 - score) * 100.0) * w
        denominator += w
    return numerator / denominator


class TestPublisherTrustScoreView:
    def test_view_computes_weighted_24h_trust_scores(self, db_session):
        db_session.execute(
            text(
                """
                INSERT INTO publishers (publisher_id, publisher_name)
                VALUES
                    (:pub_a, 'Trust Test A'),
                    (:pub_b, 'Trust Test B'),
                    (:pub_c, 'Trust Test C');
                """
            ),
            {
                "pub_a": PUB_A,
                "pub_b": PUB_B,
                "pub_c": PUB_C,
            },
        )

        db_session.execute(
            text(
                """
                INSERT INTO model_logs (log_timestamp, publisher_id, model_name, fraud_type, score)
                VALUES
                    (NOW() - INTERVAL '1 hour', :pub_a, 'dummy_model', 'test', 0.10),
                    (NOW() - INTERVAL '6 hour', :pub_a, 'dummy_model', 'test', 0.40),
                    (NOW() - INTERVAL '20 hour', :pub_a, 'dummy_model', 'test', 0.90),
                    -- Excluded from A's window (older than A.latest_ts - 24h)
                    (NOW() - INTERVAL '30 hour', :pub_a, 'dummy_model', 'test', 0.05),

                    (NOW() - INTERVAL '2 hour', :pub_b, 'dummy_model', 'test', 0.70),
                    -- At B's lower bound (age 24h from B.latest_ts), weight is 0
                    (NOW() - INTERVAL '26 hour', :pub_b, 'dummy_model', 'test', 0.20),

                    -- C has one old row globally, but it is C.latest_ts so it is included
                    (NOW() - INTERVAL '40 hour', :pub_c, 'dummy_model', 'test', 0.10);
                """
            ),
            {
                "pub_a": PUB_A,
                "pub_b": PUB_B,
                "pub_c": PUB_C,
            },
        )
        db_session.flush()

        rows = db_session.execute(
            text(
                """
                SELECT publisher_id, trust_score::double precision AS trust_score, latest_ts
                FROM publisher_trust_score
                WHERE publisher_id IN (:pub_a, :pub_b, :pub_c)
                ORDER BY publisher_id
                """
            ),
            {
                "pub_a": PUB_A,
                "pub_b": PUB_B,
                "pub_c": PUB_C,
            },
        ).mappings().all()

        assert [r["publisher_id"] for r in rows] == [PUB_A, PUB_B, PUB_C]

        by_publisher = {r["publisher_id"]: r for r in rows}

        expected_a = _expected_trust(
            [
                (0.10, 0.0),
                (0.40, 5.0),
                (0.90, 19.0),
            ]
        )
        expected_b = _expected_trust(
            [
                (0.70, 0.0),
                (0.20, 24.0),
            ]
        )
        expected_c = _expected_trust([(0.10, 0.0)])

        assert math.isclose(
            by_publisher[PUB_A]["trust_score"], expected_a, rel_tol=1e-12, abs_tol=1e-12
        )
        assert math.isclose(
            by_publisher[PUB_B]["trust_score"], expected_b, rel_tol=1e-12, abs_tol=1e-12
        )
        assert math.isclose(
            by_publisher[PUB_C]["trust_score"], expected_c, rel_tol=1e-12, abs_tol=1e-12
        )

        # latest_ts should be the most recent model_logs timestamp per publisher.
        latest = db_session.execute(
            text(
                """
                SELECT publisher_id, MAX(log_timestamp) AS max_ts
                FROM model_logs
                GROUP BY publisher_id
                """
            )
        ).mappings().all()
        latest_by_pub = {r["publisher_id"]: r["max_ts"] for r in latest}

        assert by_publisher[PUB_A]["latest_ts"] == latest_by_pub[PUB_A]
        assert by_publisher[PUB_B]["latest_ts"] == latest_by_pub[PUB_B]
        assert by_publisher[PUB_C]["latest_ts"] == latest_by_pub[PUB_C]
