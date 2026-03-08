from datetime import datetime, timezone

from app.fastapi.services.sentinel_service import (
    compare_publisher_to_network,
    get_trust_score_explanation,
)
from tests.conftest import PUB1_ID, PUB2_ID

AS_OF = datetime(2026, 1, 1, 6, 0, tzinfo=timezone.utc)


class TestGetTrustScoreExplanation:
    def test_returns_required_keys(self, db_session, seed_data):
        result = get_trust_score_explanation(db_session, PUB1_ID, AS_OF)
        assert "publisher_name" in result
        assert "trust_score" in result
        assert "anomaly_score" in result
        assert "findings" in result

    def test_pub1_name_and_score(self, db_session, seed_data):
        result = get_trust_score_explanation(db_session, PUB1_ID, AS_OF)
        assert result["publisher_name"] == "Acme Ads"
        assert result["trust_score"] == 88
        assert abs(result["anomaly_score"] - 0.12) < 0.01

    def test_pub1_has_findings(self, db_session, seed_data):
        # PUB1 has derived_metrics so findings should include CTR/CVR comparisons
        result = get_trust_score_explanation(db_session, PUB1_ID, AS_OF)
        assert len(result["findings"]) > 0
        findings_text = " ".join(result["findings"])
        assert "CTR" in findings_text
        assert "Trusted" in findings_text

    def test_pub2_insufficient_derived(self, db_session, seed_data):
        # PUB2 has no derived_metrics
        result = get_trust_score_explanation(db_session, PUB2_ID, AS_OF)
        assert result["publisher_name"] == "BrightMedia"
        assert result["trust_score"] == 55
        findings_text = " ".join(result["findings"])
        assert "Insufficient" in findings_text or "Watchlist" in findings_text

    def test_pub2_watchlist_status(self, db_session, seed_data):
        result = get_trust_score_explanation(db_session, PUB2_ID, AS_OF)
        findings_text = " ".join(result["findings"])
        assert "Watchlist" in findings_text

    def test_findings_is_list_of_strings(self, db_session, seed_data):
        result = get_trust_score_explanation(db_session, PUB1_ID, AS_OF)
        assert isinstance(result["findings"], list)
        for f in result["findings"]:
            assert isinstance(f, str)


class TestComparePublisherToNetwork:
    def test_returns_required_keys(self, db_session, seed_data):
        result = compare_publisher_to_network(db_session, PUB1_ID, AS_OF)
        expected_keys = {
            "publisher_name",
            "publisher_ctr",
            "network_avg_ctr",
            "publisher_cvr",
            "network_avg_cvr",
            "publisher_impressions",
            "network_avg_impressions",
            "ctr_z_score",
            "cvr_z_score",
        }
        assert set(result.keys()) == expected_keys

    def test_pub1_has_nonzero_metrics(self, db_session, seed_data):
        # PUB1 has derived_metrics so publisher rates should be > 0
        result = compare_publisher_to_network(db_session, PUB1_ID, AS_OF)
        assert result["publisher_name"] == "Acme Ads"
        assert result["publisher_ctr"] > 0
        assert result["publisher_cvr"] > 0
        assert result["publisher_impressions"] > 0

    def test_network_averages_positive(self, db_session, seed_data):
        result = compare_publisher_to_network(db_session, PUB1_ID, AS_OF)
        assert result["network_avg_ctr"] > 0
        assert result["network_avg_cvr"] > 0
        assert result["network_avg_impressions"] > 0

    def test_pub2_zero_metrics_without_derived(self, db_session, seed_data):
        # PUB2 has no derived_metrics -> publisher rates should be 0
        result = compare_publisher_to_network(db_session, PUB2_ID, AS_OF)
        assert result["publisher_name"] == "BrightMedia"
        assert result["publisher_ctr"] == 0.0
        assert result["publisher_cvr"] == 0.0
        assert result["publisher_impressions"] == 0.0

    def test_z_scores_are_numeric(self, db_session, seed_data):
        result = compare_publisher_to_network(db_session, PUB1_ID, AS_OF)
        assert isinstance(result["ctr_z_score"], float)
        assert isinstance(result["cvr_z_score"], float)

    def test_pub1_z_scores_near_zero(self, db_session, seed_data):
        # all derived_metrics are from PUB1, so publisher == network -> z near 0
        result = compare_publisher_to_network(db_session, PUB1_ID, AS_OF)
        # with only 3 data points from the same publisher, z-scores should be small
        assert abs(result["ctr_z_score"]) < 3.0
        assert abs(result["cvr_z_score"]) < 3.0
