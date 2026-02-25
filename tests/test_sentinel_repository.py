from datetime import datetime, timezone

from app.repositories.sentinel_repository import SentinelRepository
from tests.conftest import PUB1_ID, PUB2_ID

AS_OF = datetime(2026, 1, 1, 6, 0, tzinfo=timezone.utc)
SINCE = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)


# ── 2.1 Stats Row ───────────────────────────────────────────────────────


class TestGetPublisherCount:
    def test_returns_correct_count(self, db_session, seed_data):
        repo = SentinelRepository(db_session)
        assert repo.get_publisher_count() == 2

    def test_returns_zero_when_empty(self, db_session):
        repo = SentinelRepository(db_session)
        assert repo.get_publisher_count() == 0


class TestGetSuspiciousPublisherCount:
    def test_counts_only_suspicious(self, db_session, seed_data):
        # PUB1 latest score = 0.12 (not suspicious)
        # PUB2 latest score = 0.45 (suspicious, > 0.3)
        repo = SentinelRepository(db_session)
        assert repo.get_suspicious_publisher_count(SINCE) == 1

    def test_returns_zero_outside_window(self, db_session, seed_data):
        repo = SentinelRepository(db_session)
        future = datetime(2027, 1, 1, 0, 0, tzinfo=timezone.utc)
        assert repo.get_suspicious_publisher_count(future) == 0


class TestGetAvgNetworkCtr:
    def test_computes_correct_ctr(self, db_session, seed_data):
        # PUB1: clicks=8+9+10+8+9+7=51, imp=120+135+110+98+102+88=653
        # PUB2: clicks=5+4+3+3+2+2=19, imp=80+75+60+55+50+48=368
        # total: 70/1021*100 = 6.86%
        repo = SentinelRepository(db_session)
        ctr = repo.get_avg_network_ctr(SINCE)
        assert abs(ctr - 6.86) < 0.01

    def test_returns_zero_when_no_data(self, db_session, seed_data):
        repo = SentinelRepository(db_session)
        future = datetime(2027, 1, 1, 0, 0, tzinfo=timezone.utc)
        assert repo.get_avg_network_ctr(future) == 0.0


class TestGetFraudEventCount:
    def test_counts_all_anomalous_rows(self, db_session, seed_data):
        # PUB1 anomalous: 0.80 (h02), 0.75 (h03) = 2
        # PUB2 anomalous: 0.50 (h02), 0.55 (h03), 0.45 (h04) = 3
        # total = 5
        repo = SentinelRepository(db_session)
        assert repo.get_fraud_event_count(SINCE) == 5

    def test_returns_zero_outside_window(self, db_session, seed_data):
        repo = SentinelRepository(db_session)
        future = datetime(2027, 1, 1, 0, 0, tzinfo=timezone.utc)
        assert repo.get_fraud_event_count(future) == 0


class TestGetNetworkTrustBreakdown:
    def test_correct_breakdown(self, db_session, seed_data):
        # PUB1 latest=0.12 -> trust=88 -> trusted
        # PUB2 latest=0.45 -> trust=55 -> watchlist
        repo = SentinelRepository(db_session)
        breakdown = repo.get_network_trust_breakdown()
        assert breakdown == {"trusted": 1, "watchlist": 1, "fraudulent": 0}

    def test_empty_when_no_logs(self, db_session):
        repo = SentinelRepository(db_session)
        breakdown = repo.get_network_trust_breakdown()
        assert breakdown == {"trusted": 0, "watchlist": 0, "fraudulent": 0}


# ── 2.2 Publisher Table ─────────────────────────────────────────────────


class TestGetPublisherTrustSummary:
    def test_returns_all_publishers(self, db_session, seed_data):
        repo = SentinelRepository(db_session)
        rows = repo.get_publisher_trust_summary(AS_OF)
        assert len(rows) == 2

    def test_contains_required_keys(self, db_session, seed_data):
        repo = SentinelRepository(db_session)
        rows = repo.get_publisher_trust_summary(AS_OF)
        expected_keys = {
            "publisher_id",
            "publisher_name",
            "trust_score",
            "anomaly_score",
            "ctr",
            "cvr",
            "status",
            "last_alert_ts",
        }
        for row in rows:
            assert set(row.keys()) == expected_keys

    def test_pub1_values(self, db_session, seed_data):
        repo = SentinelRepository(db_session)
        rows = repo.get_publisher_trust_summary(AS_OF)
        pub1 = next(r for r in rows if r["publisher_id"] == str(PUB1_ID))

        assert pub1["publisher_name"] == "Acme Ads"
        assert pub1["trust_score"] == 88  # round((1-0.12)*100)
        assert abs(pub1["anomaly_score"] - 0.12) < 0.01
        # latest raw (h05): clk=7, imp=88 -> ctr=7.95%
        assert abs(pub1["ctr"] - 7.95) < 0.01
        # latest raw (h05): conv=1, clk=7 -> cvr=14.29%
        assert abs(pub1["cvr"] - 14.29) < 0.01
        assert pub1["status"] == "Trusted"

    def test_pub2_zero_conversions_status(self, db_session, seed_data):
        repo = SentinelRepository(db_session)
        rows = repo.get_publisher_trust_summary(AS_OF)
        pub2 = next(r for r in rows if r["publisher_id"] == str(PUB2_ID))

        # PUB2 latest=0.45 -> trust=55 -> would be Watchlist
        # but latest raw (h05): conv=0 -> Zero Conversions takes priority
        assert pub2["trust_score"] == 55
        assert pub2["status"] == "Zero Conversions"

    def test_pub1_has_last_alert(self, db_session, seed_data):
        repo = SentinelRepository(db_session)
        rows = repo.get_publisher_trust_summary(AS_OF)
        pub1 = next(r for r in rows if r["publisher_id"] == str(PUB1_ID))
        assert pub1["last_alert_ts"] is not None


class TestGetLastAlertTimestamp:
    def test_pub1_last_alert(self, db_session, seed_data):
        # PUB1 anomalous scores: 0.80 (h02), 0.75 (h03) -> latest is h03
        repo = SentinelRepository(db_session)
        ts = repo.get_last_alert_timestamp(PUB1_ID)
        assert ts == datetime(2026, 1, 1, 3, 0, tzinfo=timezone.utc)

    def test_pub2_last_alert(self, db_session, seed_data):
        # PUB2 anomalous: 0.50 (h02), 0.55 (h03), 0.45 (h04) -> latest is h04
        repo = SentinelRepository(db_session)
        ts = repo.get_last_alert_timestamp(PUB2_ID)
        assert ts == datetime(2026, 1, 1, 4, 0, tzinfo=timezone.utc)

    def test_returns_none_for_unknown_publisher(self, db_session, seed_data):
        import uuid

        repo = SentinelRepository(db_session)
        ts = repo.get_last_alert_timestamp(uuid.uuid4())
        assert ts is None


# ── 2.3 Trust Score Distribution ────────────────────────────────────────


class TestGetTrustScoreDistribution:
    def test_correct_buckets(self, db_session, seed_data):
        # PUB1 trust=88 -> "80-90"
        # PUB2 trust=55 -> "40-60"
        repo = SentinelRepository(db_session)
        dist = repo.get_trust_score_distribution(AS_OF)

        by_range = {d["range"]: d["count"] for d in dist}
        assert by_range["80-90"] == 1
        assert by_range["40-60"] == 1
        assert by_range["0-20"] == 0
        assert by_range["20-40"] == 0
        assert by_range["60-80"] == 0
        assert by_range["90-100"] == 0

    def test_returns_six_buckets(self, db_session, seed_data):
        repo = SentinelRepository(db_session)
        dist = repo.get_trust_score_distribution(AS_OF)
        assert len(dist) == 6

    def test_all_zero_when_no_logs(self, db_session):
        repo = SentinelRepository(db_session)
        dist = repo.get_trust_score_distribution(AS_OF)
        assert all(d["count"] == 0 for d in dist)


# ── 2.4 Fraud Events Chart ─────────────────────────────────────────────


class TestGetDailyFraudEventCounts:
    def test_returns_correct_number_of_days(self, db_session, seed_data):
        repo = SentinelRepository(db_session)
        result = repo.get_daily_fraud_event_counts(days=7)
        assert len(result) == 7

    def test_each_entry_has_day_and_events(self, db_session, seed_data):
        repo = SentinelRepository(db_session)
        result = repo.get_daily_fraud_event_counts(days=7)
        for entry in result:
            assert "day" in entry
            assert "events" in entry
            assert isinstance(entry["events"], int)

    def test_events_are_non_negative(self, db_session, seed_data):
        repo = SentinelRepository(db_session)
        result = repo.get_daily_fraud_event_counts(days=7)
        for entry in result:
            assert entry["events"] >= 0


# ── 2.5 Sentinel Assistant ──────────────────────────────────────────────


class TestGetAnomalyEvidence:
    def test_pub1_anomalous_buckets(self, db_session, seed_data):
        # PUB1 anomalous: h02 (0.80), h03 (0.75)
        repo = SentinelRepository(db_session)
        t1 = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 1, 1, 5, 0, tzinfo=timezone.utc)
        evidence = repo.get_anomaly_evidence(PUB1_ID, t1, t2)

        assert len(evidence) == 2
        scores = [e["anomaly_score"] for e in evidence]
        assert 0.80 in scores
        assert 0.75 in scores

    def test_evidence_contains_required_keys(self, db_session, seed_data):
        repo = SentinelRepository(db_session)
        t1 = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 1, 1, 5, 0, tzinfo=timezone.utc)
        evidence = repo.get_anomaly_evidence(PUB1_ID, t1, t2)

        expected_keys = {
            "timestamp",
            "anomaly_score",
            "ctr",
            "cvr",
            "impressions",
            "clicks",
            "conversions",
        }
        for e in evidence:
            assert set(e.keys()) == expected_keys

    def test_returns_empty_for_no_anomalies(self, db_session, seed_data):
        repo = SentinelRepository(db_session)
        # narrow window with no anomalous PUB1 scores
        t1 = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 1, 1, 1, 0, tzinfo=timezone.utc)
        evidence = repo.get_anomaly_evidence(PUB1_ID, t1, t2)
        assert evidence == []

    def test_chronological_order(self, db_session, seed_data):
        repo = SentinelRepository(db_session)
        t1 = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 1, 1, 5, 0, tzinfo=timezone.utc)
        evidence = repo.get_anomaly_evidence(PUB1_ID, t1, t2)

        timestamps = [e["timestamp"] for e in evidence]
        assert timestamps == sorted(timestamps)


class TestGetNetworkBaselines:
    def test_returns_required_keys(self, db_session, seed_data):
        repo = SentinelRepository(db_session)
        baselines = repo.get_network_baselines(AS_OF)
        expected_keys = {
            "avg_ctr",
            "avg_cvr",
            "avg_impression_count",
            "ctr_std",
            "cvr_std",
        }
        assert set(baselines.keys()) == expected_keys

    def test_values_are_positive(self, db_session, seed_data):
        # derived_metrics exist for PUB1 with positive means
        repo = SentinelRepository(db_session)
        baselines = repo.get_network_baselines(AS_OF)
        assert baselines["avg_ctr"] > 0
        assert baselines["avg_cvr"] > 0
        assert baselines["avg_impression_count"] > 0

    def test_avg_impression_count_reasonable(self, db_session, seed_data):
        # 3 derived rows with imp_mean: 110.5, 111.0, 108.0 -> avg ~109.83
        repo = SentinelRepository(db_session)
        baselines = repo.get_network_baselines(AS_OF)
        assert abs(baselines["avg_impression_count"] - 109.83) < 0.1


class TestGetPublisherLatestDerived:
    def test_pub1_latest(self, db_session, seed_data):
        # PUB1 derived at h03, h04, h05 -> latest is h05
        repo = SentinelRepository(db_session)
        derived = repo.get_publisher_latest_derived(PUB1_ID, AS_OF)
        assert derived is not None
        assert derived.bucket_timestamp == datetime(
            2026, 1, 1, 5, 0, tzinfo=timezone.utc
        )
        assert derived.impressions_mean == 108.0

    def test_pub2_no_derived(self, db_session, seed_data):
        repo = SentinelRepository(db_session)
        derived = repo.get_publisher_latest_derived(PUB2_ID, AS_OF)
        assert derived is None

    def test_respects_as_of_cutoff(self, db_session, seed_data):
        repo = SentinelRepository(db_session)
        # as_of before any derived rows exist
        early = datetime(2026, 1, 1, 2, 0, tzinfo=timezone.utc)
        derived = repo.get_publisher_latest_derived(PUB1_ID, early)
        assert derived is None
