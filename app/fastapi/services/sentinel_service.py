from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db.models import Publishers, ModelLogs
from app.repositories.sentinel_repository import SentinelRepository


def get_trust_score_explanation(
    session: Session,
    publisher_id: uuid.UUID,
    as_of: datetime,
) -> dict:
    repo = SentinelRepository(session)

    publisher = (
        session.query(Publishers)
        .filter(Publishers.publisher_id == publisher_id)
        .first()
    )
    publisher_name = publisher.publisher_name if publisher else "Unknown"

    latest_log = (
        session.query(ModelLogs)
        .filter(
            ModelLogs.publisher_id == publisher_id,
            ModelLogs.log_timestamp <= as_of,
        )
        .order_by(desc(ModelLogs.log_timestamp))
        .first()
    )

    if latest_log is None:
        anomaly_score = 0.0
    else:
        anomaly_score = float(latest_log.score)

    trust_score = round((1 - anomaly_score) * 100)

    derived = repo.get_publisher_latest_derived(publisher_id, as_of)
    baselines = repo.get_network_baselines(as_of)

    findings: list[str] = []

    if (
        derived is not None
        and derived.impressions_mean
        and derived.impressions_mean > 0
    ):
        pub_ctr = (
            (derived.clicks_mean / derived.impressions_mean) * 100
            if derived.clicks_mean is not None
            else 0.0
        )
        pub_cvr = (
            (derived.conversions_mean / derived.clicks_mean) * 100
            if derived.clicks_mean and derived.conversions_mean is not None
            else 0.0
        )

        net_ctr = baselines["avg_ctr"]
        net_cvr = baselines["avg_cvr"]

        findings.append(f"CTR {pub_ctr:.1f}% vs network baseline {net_ctr:.1f}%")
        findings.append(f"CVR {pub_cvr:.1f}% vs network baseline {net_cvr:.1f}%")

        ctr_std = baselines["ctr_std"]
        cvr_std = baselines["cvr_std"]

        if ctr_std > 0 and abs(pub_ctr - net_ctr) > 2 * ctr_std:
            direction = "above" if pub_ctr > net_ctr else "below"
            findings.append(
                f"CTR is significantly {direction} network average "
                f"({abs(pub_ctr - net_ctr) / ctr_std:.1f} standard deviations)"
            )

        if cvr_std > 0 and abs(pub_cvr - net_cvr) > 2 * cvr_std:
            direction = "above" if pub_cvr > net_cvr else "below"
            findings.append(
                f"CVR is significantly {direction} network average "
                f"({abs(pub_cvr - net_cvr) / cvr_std:.1f} standard deviations)"
            )

        net_imp = baselines["avg_impression_count"]
        if net_imp > 0:
            ratio = derived.impressions_mean / net_imp
            if ratio > 2.0:
                findings.append(
                    f"Impression volume {derived.impressions_mean:.0f} is "
                    f"{ratio:.1f}x the network average ({net_imp:.0f})"
                )
            elif ratio < 0.5:
                findings.append(
                    f"Impression volume {derived.impressions_mean:.0f} is "
                    f"significantly below network average ({net_imp:.0f})"
                )
            else:
                findings.append(
                    f"Stable impression volume ({derived.impressions_mean:.0f} "
                    f"vs network avg {net_imp:.0f})"
                )
    else:
        findings.append("Insufficient derived metrics data for detailed analysis")

    if trust_score >= 70:
        findings.append("Publisher is currently classified as Trusted")
    elif trust_score >= 40:
        findings.append("Publisher is on the Watchlist - elevated anomaly indicators")
    elif trust_score >= 20:
        findings.append("Publisher is flagged as Suspicious - review recommended")
    else:
        findings.append(
            "Publisher shows Bot-Like Activity - immediate review recommended"
        )

    return {
        "publisher_name": publisher_name,
        "trust_score": trust_score,
        "anomaly_score": anomaly_score,
        "findings": findings,
    }


def compare_publisher_to_network(
    session: Session,
    publisher_id: uuid.UUID,
    as_of: datetime,
) -> dict:
    repo = SentinelRepository(session)

    publisher = (
        session.query(Publishers)
        .filter(Publishers.publisher_id == publisher_id)
        .first()
    )
    publisher_name = publisher.publisher_name if publisher else "Unknown"

    derived = repo.get_publisher_latest_derived(publisher_id, as_of)
    baselines = repo.get_network_baselines(as_of)

    if (
        derived is not None
        and derived.impressions_mean
        and derived.impressions_mean > 0
    ):
        publisher_ctr = (
            (derived.clicks_mean / derived.impressions_mean) * 100
            if derived.clicks_mean is not None
            else 0.0
        )
        publisher_cvr = (
            (derived.conversions_mean / derived.clicks_mean) * 100
            if derived.clicks_mean and derived.conversions_mean is not None
            else 0.0
        )
        publisher_impressions = derived.impressions_mean
    else:
        publisher_ctr = 0.0
        publisher_cvr = 0.0
        publisher_impressions = 0.0

    net_ctr = baselines["avg_ctr"]
    net_cvr = baselines["avg_cvr"]
    ctr_std = baselines["ctr_std"]
    cvr_std = baselines["cvr_std"]

    ctr_z = (publisher_ctr - net_ctr) / ctr_std if ctr_std > 0 else 0.0
    cvr_z = (publisher_cvr - net_cvr) / cvr_std if cvr_std > 0 else 0.0

    return {
        "publisher_name": publisher_name,
        "publisher_ctr": round(publisher_ctr, 4),
        "network_avg_ctr": round(net_ctr, 4),
        "publisher_cvr": round(publisher_cvr, 4),
        "network_avg_cvr": round(net_cvr, 4),
        "publisher_impressions": round(publisher_impressions, 2),
        "network_avg_impressions": baselines["avg_impression_count"],
        "ctr_z_score": round(ctr_z, 4),
        "cvr_z_score": round(cvr_z, 4),
    }
