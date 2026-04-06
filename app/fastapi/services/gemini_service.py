"""
Gemini AI service for the Sentinel Assistant chatbot.

Calls the Gemini REST API directly (no SDK) to avoid heavy dependency
conflicts with pinned protobuf versions.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load env from .secrets/.env (Docker injects it too, but this covers local dev)
_secrets_env = os.path.join(
    os.path.dirname(__file__), os.pardir, os.pardir, os.pardir, ".secrets", ".env"
)
load_dotenv(_secrets_env, override=False)

_API_KEY = os.environ.get("GEMINI_API_KEY", "")
_MODEL_NAME = "gemini-2.5-flash"
_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{_MODEL_NAME}:generateContent"

if not _API_KEY:
    logger.warning("GEMINI_API_KEY not set – assistant chat will return a fallback.")

# System prompt that gives Gemini the role context
_SYSTEM_PROMPT = """\
You are the **Sentinel Assistant**, an AI analyst embedded in the AdGuard Sentinel \
ad-fraud detection dashboard.

Your job is to help ad-ops analysts understand publisher trust scores, anomaly \
detection results, and fraud indicators.

Guidelines:
- Be concise and direct. Prefer bullet points over long paragraphs.
- Reference specific numbers from the context data when answering.
- If the data does not contain enough info to answer, say so honestly.
- Use plain language; avoid jargon unless the user seems technical.
- When discussing trust scores: 90-100 = Trusted, 60-89 = Watchlist, \
  20-59 = Suspicious, 0-19 = Bot-Like / Fraudulent.
- Always ground your answers in the provided context data. Do not invent metrics.
"""


def _build_context_block(context: dict[str, Any]) -> str:
    """Format the ML context data into a text block for the prompt."""
    parts: list[str] = []

    if "trust_buckets" in context:
        parts.append("## Trust Score Distribution")
        for bucket in context["trust_buckets"]:
            parts.append(f"  - {bucket['range']}: {bucket['count']} publishers")

    if "fraud_events" in context:
        parts.append("\n## Recent Fraud Events (daily)")
        for evt in context["fraud_events"]:
            parts.append(f"  - {evt['day']}: {evt['events']} events")

    if "publishers" in context:
        parts.append("\n## Publisher Data")
        for pub in context["publishers"]:
            line = f"  - {pub.get('name', 'Unknown')}: "
            details = []
            if "trustScore" in pub:
                details.append(f"trust={pub['trustScore']}")
            if "ctr" in pub:
                details.append(f"CTR={pub['ctr']}%")
            if "cvr" in pub:
                details.append(f"CVR={pub['cvr']}%")
            if "status" in pub:
                details.append(f"status={pub['status']}")
            if "anomalyScore" in pub:
                details.append(f"anomaly={pub['anomalyScore']}")
            line += ", ".join(details)
            parts.append(line)

    if "explanation" in context:
        parts.append("\n## Trust Score Explanation (from ML pipeline)")
        expl = context["explanation"]
        parts.append(f"  Publisher: {expl.get('publisher_name', 'N/A')}")
        parts.append(f"  Trust Score: {expl.get('trust_score', 'N/A')}")
        parts.append(f"  Anomaly Score: {expl.get('anomaly_score', 'N/A')}")
        for finding in expl.get("findings", []):
            parts.append(f"  - {finding}")

    if "comparison" in context:
        parts.append("\n## Network Comparison")
        comp = context["comparison"]
        parts.append(f"  Publisher: {comp.get('publisher_name', 'N/A')}")
        parts.append(
            f"  Publisher CTR: {comp.get('publisher_ctr', 'N/A')}% "
            f"vs Network: {comp.get('network_avg_ctr', 'N/A')}%"
        )
        parts.append(
            f"  Publisher CVR: {comp.get('publisher_cvr', 'N/A')}% "
            f"vs Network: {comp.get('network_avg_cvr', 'N/A')}%"
        )
        parts.append(f"  CTR Z-score: {comp.get('ctr_z_score', 'N/A')}")
        parts.append(f"  CVR Z-score: {comp.get('cvr_z_score', 'N/A')}")

    return "\n".join(parts) if parts else "(No context data provided)"


def chat(
    message: str,
    context: dict[str, Any] | None = None,
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """
    Send a user message to Gemini with ML context and return the response.

    Returns a dict with:
        content: str       - the main response text
        bullets: list[str] - extracted bullet points (if any)
        isWarning: bool    - True if the response mentions fraud/anomalies
    """
    if not _API_KEY:
        return {
            "content": "Gemini API key is not configured. Please set GEMINI_API_KEY in your environment.",
            "bullets": [],
            "isWarning": True,
        }

    context_block = _build_context_block(context or {})

    # Build the full user prompt with context
    full_prompt = (
        f"--- CONTEXT DATA ---\n{context_block}\n"
        f"--- END CONTEXT ---\n\n"
        f"User question: {message}"
    )

    # Build the request contents array for the REST API
    contents: list[dict] = []

    # Add conversation history
    if history:
        for msg in history:
            role = "user" if msg.get("role") == "user" else "model"
            contents.append(
                {
                    "role": role,
                    "parts": [{"text": msg.get("content", "")}],
                }
            )

    # Add the current user message
    contents.append(
        {
            "role": "user",
            "parts": [{"text": full_prompt}],
        }
    )

    payload = {
        "contents": contents,
        "systemInstruction": {
            "parts": [{"text": _SYSTEM_PROMPT}],
        },
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 1024,
        },
    }

    try:
        resp = requests.post(
            _API_URL,
            params={"key": _API_KEY},
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )

        if resp.status_code != 200:
            error_detail = resp.text[:300]
            logger.error("Gemini API error %s: %s", resp.status_code, error_detail)
            return {
                "content": f"Gemini API returned an error (HTTP {resp.status_code}).",
                "bullets": [],
                "isWarning": True,
            }

        data = resp.json()

        # Extract text from the response
        candidates = data.get("candidates", [])
        if not candidates:
            return {
                "content": "No response received from Gemini.",
                "bullets": [],
                "isWarning": False,
            }

        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts).strip()

        if not text:
            return {
                "content": "Received an empty response from Gemini.",
                "bullets": [],
                "isWarning": False,
            }

        # Parse bullets: lines starting with - or * or bullet char
        lines = text.split("\n")
        bullets: list[str] = []
        content_lines: list[str] = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith(("- ", "* ", "• ")):
                bullets.append(stripped.lstrip("-*• ").strip())
            else:
                content_lines.append(line)

        content = "\n".join(content_lines).strip()
        if not content and bullets:
            content = "Here are the key findings:"

        # Detect warning-worthy content
        warning_keywords = [
            "fraud",
            "suspicious",
            "anomal",
            "bot-like",
            "spike",
            "flag",
        ]
        is_warning = any(kw in text.lower() for kw in warning_keywords)

        return {
            "content": content,
            "bullets": bullets,
            "isWarning": is_warning,
        }

    except requests.exceptions.Timeout:
        logger.warning("Gemini API request timed out")
        return {
            "content": "The request to the AI service timed out. Please try again.",
            "bullets": [],
            "isWarning": True,
        }
    except Exception as exc:
        logger.exception("Gemini API call failed: %s", exc)
        return {
            "content": f"Sorry, I encountered an error: {str(exc)}",
            "bullets": [],
            "isWarning": True,
        }
