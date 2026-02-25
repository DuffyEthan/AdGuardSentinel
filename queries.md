# Backend Queries – Sentinel Dashboard

## 1. What's Already Available

### Endpoints (`app/fastapi/main.py`)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/raw-metrics/get-last-n-before` | Up to N raw metric rows before a timestamp, optionally filtered by `publisher_id` / `campaign_id` |
| `GET` | `/model-logs/get-between` | Model predictions joined with raw metrics between two timestamps, filtered by `publisher_id` + `campaign_id` |
| `POST` | `/pipeline/train-model` | Trigger the full isolation-forest training pipeline for a publisher |
| `GET` | `/pipeline/results` | Raw metrics + model predictions for a publisher in a time range, with a summary object |

### Repository methods (`app/repositories/`)

| Class | Method | Description |
|-------|--------|-------------|
| `RawMetricsRepository` | `get_last_n_before(t, n, publisher_id, campaign_id)` | Fetch ≤ N raw metric rows before `t` |
| `ModelLogsRepository` | `get_between(t1, t2, publisher_id, campaign_id)` | Fetch `(ModelLog, RawMetrics)` tuples in `[t1, t2]` |
| `DerivedMetricsRepository` | `get_latest(publisher_id, campaign_id)` | Most recent derived-metrics row for a publisher/campaign |
| `DerivedMetricsRepository` | `get_last_n_before(t, n, publisher_id, campaign_id)` | ≤ N derived-metric rows before `t` |

### Database tables of interest

| Table | Key columns |
|-------|-------------|
| `publishers` | `publisher_id`, `publisher_name` |
| `campaign` | `campaign_id`, `publisher_id` |
| `raw_metrics` | `bucket_timestamp`, `publisher_id`, `campaign_id`, `impression_count`, `click_count`, `conversion_count` |
| `model_logs` | `timestamp`, `publisher_id`, `model_name`, `score` (0–1, higher = more anomalous) |
| `derived_metrics` | `bucket_timestamp`, `publisher_id`, `campaign_id`, plus mean/std/weighted-mean for impressions, clicks, conversions |

**Trust score convention:** `model_logs.score` is the raw anomaly score (0–1). The ML layer normalises it so that ≥ 0.7 = organic / trusted; < 0.7 = suspicious. The dashboard inverts this to a "trust score" on a 0–100 scale: `trust_score = round((1 - anomaly_score) * 100)`.

---

## 2. Queries Needed for the Sentinel Dashboard

Each function below is a new backend query that needs to be implemented. The calling convention matches the existing repository / FastAPI style (SQLAlchemy session injection, `uuid.UUID` identifiers, `datetime` timestamps).

---

### 2.1 Stats Row

```python
def get_publisher_count() -> int:
    """
    Return the total number of publishers in the `publishers` table.
    Used for: 'Publishers Monitored' stat card.
    """

def get_suspicious_publisher_count(since: datetime) -> int:
    """
    Return the number of distinct publishers whose most-recent model_logs.score
    is above the anomaly threshold (i.e. trust_score < 70) within the window
    [since, now].
    Used for: 'Suspicious Publishers' stat card.
    """

def get_avg_network_ctr(since: datetime) -> float:
    """
    Return the network-wide average CTR (click_count / impression_count) across
    all publishers and campaigns, aggregated over all raw_metrics rows where
    bucket_timestamp >= since.
    Returns a percentage value, e.g. 1.9 (meaning 1.9%).
    Used for: 'Avg Network CTR' stat card.
    """

def get_fraud_event_count(since: datetime) -> int:
    """
    Return the total number of model_logs rows whose score exceeds the anomaly
    threshold (score > 0.3, i.e. trust_score < 70) and whose timestamp >= since.
    Each row represents one flagged time-bucket across all publishers.
    Used for: 'Fraud Events (Last 24h)' stat card.
    """

def get_network_trust_breakdown() -> dict:
    """
    For each publisher, determine their current trust category based on their
    most recent model_logs.score. Return counts for each category.

    Returns:
        {
            "trusted":    int,   # trust_score >= 70
            "watchlist":  int,   # 40 <= trust_score < 70
            "fraudulent": int    # trust_score < 40
        }
    Used for: MiniPieChart in the stats row AND PublisherOverviewChart.
    """
```

---

### 2.2 Publisher Table

```python
def get_publisher_trust_summary(as_of: datetime) -> list[dict]:
    """
    For every publisher, return a summary row for the trust-scores table.
    'as_of' is the upper-bound timestamp; use the most recent data available
    before or at that time.

    Each dict should contain:
        {
            "publisher_id":   str (UUID),
            "publisher_name": str,
            "trust_score":    int,    # 0–100, derived from most recent anomaly score
            "anomaly_score":  float,  # raw model_logs.score, 0.0–1.0
            "ctr":            float,  # % from most recent raw_metrics bucket
            "cvr":            float,  # % from most recent raw_metrics bucket
            "status":         str,    # one of: Trusted | Watchlist | Suspicious |
                                      #         Zero Conversions | Bot-Like Activity
            "last_alert_ts":  datetime | None  # timestamp of last anomalous bucket
        }

    Status derivation (suggested thresholds – adjust as needed):
        trust_score >= 70          → "Trusted"
        40 <= trust_score < 70     → "Watchlist"
        20 <= trust_score < 40     → "Suspicious"
        cvr == 0 or conversion_count == 0 (recent window) → "Zero Conversions"
        trust_score < 20           → "Bot-Like Activity"

    Used for: PublisherTable component.
    """

def get_last_alert_timestamp(publisher_id: uuid.UUID) -> datetime | None:
    """
    Return the timestamp of the most recent model_logs row for this publisher
    where score exceeds the anomaly threshold (score > 0.3).
    Returns None if no anomaly has ever been detected.
    Used for: 'Last Alert' column in PublisherTable.
    """
```

---

### 2.3 Trust Score Distribution Chart

```python
def get_trust_score_distribution(as_of: datetime) -> list[dict]:
    """
    Bucket all publishers by their current trust score and return a count per
    bucket, suitable for the bar chart.

    Returns a list in display order:
        [
            {"range": "0–20",    "count": int},
            {"range": "20–40",   "count": int},
            {"range": "40–60",   "count": int},
            {"range": "60–80",   "count": int},
            {"range": "80–90",   "count": int},
            {"range": "90–100",  "count": int},
        ]

    Each publisher contributes exactly one bucket entry based on
    their most recent model_logs.score before `as_of`.
    Used for: TrustDistributionChart component.
    """
```

---

### 2.4 Fraud Events Chart

```python
def get_daily_fraud_event_counts(days: int = 7) -> list[dict]:
    """
    Count anomalous model_logs rows per calendar day over the past `days` days.
    A row is 'anomalous' if score > 0.3 (trust_score < 70).
    Aggregate across all publishers.

    Returns a list ordered oldest → newest:
        [
            {"day": "Mon", "events": int},
            {"day": "Tue", "events": int},
            ...  # `days` entries total
        ]

    'day' should be the abbreviated weekday name of the bucket's date in UTC.
    Used for: FraudEventsChart component.
    """
```

---

### 2.5 Sentinel Assistant

```python
def get_trust_score_explanation(publisher_id: uuid.UUID, as_of: datetime) -> dict:
    """
    Produce a structured explanation of why a publisher has their current trust
    score, by comparing their recent metrics against the network baseline.

    Returns:
        {
            "publisher_name": str,
            "trust_score":    int,
            "anomaly_score":  float,
            "findings": list[str]   # human-readable bullet points, e.g.:
                                    # "CTR 8.9% vs baseline 1.5%"
                                    # "CVR 0.4% vs baseline 2.1% (recent drop)"
                                    # "Stable impression volume in last 4h"
        }

    Suggested approach: compare publisher's derived_metrics (mean/std) against
    the network-wide derived_metrics aggregates from get_network_baselines().
    Used for: SentinelAssistant 'Explain trust score' action.
    """

def get_anomaly_evidence(publisher_id: uuid.UUID, t1: datetime, t2: datetime) -> list[dict]:
    """
    Return the individual anomalous time-buckets for a publisher in [t1, t2],
    with the raw metric values that triggered the flag.

    Each item:
        {
            "timestamp":     datetime,
            "anomaly_score": float,
            "ctr":           float,
            "cvr":           float,
            "impressions":   int,
            "clicks":        int,
            "conversions":   int,
        }

    Used for: SentinelAssistant 'Show anomalies & evidence' action.
    """

def get_network_baselines(as_of: datetime) -> dict:
    """
    Return network-wide aggregate statistics to use as a comparison baseline.
    Computed from derived_metrics across all publishers.

    Returns:
        {
            "avg_ctr":              float,
            "avg_cvr":              float,
            "avg_impression_count": float,
            "ctr_std":              float,
            "cvr_std":              float,
        }

    Used for: get_trust_score_explanation() and
              SentinelAssistant 'Compare against network' action.
    """

def compare_publisher_to_network(
    publisher_id: uuid.UUID, as_of: datetime
) -> dict:
    """
    Compare a single publisher's recent derived_metrics against the network
    baselines returned by get_network_baselines().

    Returns:
        {
            "publisher_name":     str,
            "publisher_ctr":      float,
            "network_avg_ctr":    float,
            "publisher_cvr":      float,
            "network_avg_cvr":    float,
            "publisher_impressions": float,
            "network_avg_impressions": float,
            "ctr_z_score":        float,   # (pub_ctr - net_avg) / net_std
            "cvr_z_score":        float,
        }

    Used for: SentinelAssistant 'Compare against network' action.
    """
```

---

## 3. Suggested Endpoint Wrappers

Once the repository/service methods above are implemented, expose them via FastAPI at these paths (following the existing pattern in `app/fastapi/main.py`):

| Method | Path | Calls |
|--------|------|-------|
| `GET` | `/sentinel/stats` | `get_publisher_count`, `get_suspicious_publisher_count`, `get_avg_network_ctr`, `get_fraud_event_count`, `get_network_trust_breakdown` |
| `GET` | `/sentinel/publishers` | `get_publisher_trust_summary` |
| `GET` | `/sentinel/trust-distribution` | `get_trust_score_distribution` |
| `GET` | `/sentinel/fraud-events` | `get_daily_fraud_event_counts` |
| `GET` | `/sentinel/assistant/explain/{publisher_id}` | `get_trust_score_explanation` |
| `GET` | `/sentinel/assistant/evidence/{publisher_id}` | `get_anomaly_evidence` |
| `GET` | `/sentinel/assistant/compare/{publisher_id}` | `compare_publisher_to_network` |
