from __future__ import annotations

import csv
import io
import json
import os
import re
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
RETENTION_MONTHS = 12

RATING_FIELDS = (
    "comprehension_rating",
    "lifecycle_clarity_rating",
    "ai_reasoning_clarity_rating",
)

TRUST_VALUES = {"yes", "somewhat", "no", "unsure"}
ALERT_VALUES = {"telegram", "email", "web", "other", "none"}
WILLINGNESS_VALUES = {"no", "maybe", "yes"}
PRICE_VALUES = {
    "free_only",
    "under_10",
    "10_25",
    "25_50",
    "50_plus",
    "unsure",
}
MISSING_DETAIL_VALUES = {
    "entry_stop_targets",
    "expiry_validity",
    "ai_reasoning",
    "historical_performance",
    "market_context",
    "risk_explanation",
    "other",
}
MARKET_VALUES = {
    "XAUUSD",
    "USTEC",
    "US30",
    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "XAGUSD",
    "US500",
    "USOIL",
}

_ALLOWED_FIELDS = {
    *RATING_FIELDS,
    "immutable_record_trust",
    "missing_details",
    "alert_preference",
    "willingness_to_pay",
    "price_range",
    "market_interests",
    "feedback_text",
}

_SENSITIVE_TEXT = re.compile(
    r"\b(?:password|passcode|api[ _-]?key|secret[ _-]?key|broker[ _-]?login|"
    r"trading[ _-]?login|account[ _-]?(?:id|number)|card[ _-]?number|cvv|"
    r"access[ _-]?token|bearer[ _-]?token)\b",
    flags=re.IGNORECASE,
)


class FeedbackValidationError(ValueError):
    pass


def feedback_db_path(root: Path) -> Path:
    configured = os.getenv("SIGNALPROOF_FEEDBACK_DB_PATH")
    if configured:
        return Path(configured)
    data_mount = Path("/data")
    if data_mount.exists():
        return data_mount / "feedback.sqlite"
    return root / "data" / "feedback.sqlite"


def _rating(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 5:
        raise FeedbackValidationError(f"{key} must be an integer from 1 to 5")
    return value


def _enum(payload: dict[str, Any], key: str, allowed: set[str]) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or value not in allowed:
        raise FeedbackValidationError(f"Invalid {key}")
    return value


def _list_of_enum(
    payload: dict[str, Any],
    key: str,
    allowed: set[str],
    *,
    minimum: int,
    maximum: int,
) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise FeedbackValidationError(f"{key} must be a list")
    if not minimum <= len(value) <= maximum:
        raise FeedbackValidationError(
            f"{key} must contain between {minimum} and {maximum} selections"
        )
    if any(not isinstance(item, str) or item not in allowed for item in value):
        raise FeedbackValidationError(f"Invalid {key} selection")
    if len(set(value)) != len(value):
        raise FeedbackValidationError(f"{key} contains duplicate selections")
    return value


def validate_feedback_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise FeedbackValidationError("JSON object required")

    extra = set(payload) - _ALLOWED_FIELDS
    if extra:
        raise FeedbackValidationError(
            "Unexpected feedback fields: " + ", ".join(sorted(extra))
        )

    normalized: dict[str, Any] = {
        key: _rating(payload, key)
        for key in RATING_FIELDS
    }
    normalized["immutable_record_trust"] = _enum(
        payload, "immutable_record_trust", TRUST_VALUES
    )
    normalized["missing_details"] = _list_of_enum(
        payload,
        "missing_details",
        MISSING_DETAIL_VALUES,
        minimum=0,
        maximum=len(MISSING_DETAIL_VALUES),
    )
    normalized["alert_preference"] = _enum(
        payload, "alert_preference", ALERT_VALUES
    )
    normalized["willingness_to_pay"] = _enum(
        payload, "willingness_to_pay", WILLINGNESS_VALUES
    )
    normalized["price_range"] = _enum(payload, "price_range", PRICE_VALUES)
    normalized["market_interests"] = _list_of_enum(
        payload,
        "market_interests",
        MARKET_VALUES,
        minimum=1,
        maximum=len(MARKET_VALUES),
    )

    text = payload.get("feedback_text", "")
    if text is None:
        text = ""
    if not isinstance(text, str):
        raise FeedbackValidationError("feedback_text must be text")
    text = text.strip()
    if len(text) > 1200:
        raise FeedbackValidationError("feedback_text must be 1200 characters or fewer")
    if _SENSITIVE_TEXT.search(text):
        raise FeedbackValidationError(
            "Do not submit credentials, account identifiers, tokens, or payment-card data"
        )
    normalized["feedback_text"] = text

    return normalized


def init_feedback_store(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback_submissions (
                submission_id TEXT PRIMARY KEY,
                submitted_at_utc TEXT NOT NULL,
                schema_version INTEGER NOT NULL,
                comprehension_rating INTEGER NOT NULL,
                lifecycle_clarity_rating INTEGER NOT NULL,
                ai_reasoning_clarity_rating INTEGER NOT NULL,
                immutable_record_trust TEXT NOT NULL,
                missing_details_json TEXT NOT NULL,
                alert_preference TEXT NOT NULL,
                willingness_to_pay TEXT NOT NULL,
                price_range TEXT NOT NULL,
                market_interests_json TEXT NOT NULL,
                feedback_text TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS feedback_submitted_at_idx
            ON feedback_submissions(submitted_at_utc)
            """
        )
        connection.commit()


def submit_feedback(
    path: Path,
    payload: dict[str, Any],
    *,
    submitted_at_utc: str | None = None,
    submission_id: str | None = None,
) -> dict[str, str]:
    normalized = validate_feedback_payload(payload)
    init_feedback_store(path)

    timestamp = submitted_at_utc or datetime.now(timezone.utc).isoformat()
    identifier = submission_id or f"fb_{secrets.token_urlsafe(12)}"

    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            INSERT INTO feedback_submissions (
                submission_id,
                submitted_at_utc,
                schema_version,
                comprehension_rating,
                lifecycle_clarity_rating,
                ai_reasoning_clarity_rating,
                immutable_record_trust,
                missing_details_json,
                alert_preference,
                willingness_to_pay,
                price_range,
                market_interests_json,
                feedback_text
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                identifier,
                timestamp,
                SCHEMA_VERSION,
                normalized["comprehension_rating"],
                normalized["lifecycle_clarity_rating"],
                normalized["ai_reasoning_clarity_rating"],
                normalized["immutable_record_trust"],
                json.dumps(normalized["missing_details"], separators=(",", ":")),
                normalized["alert_preference"],
                normalized["willingness_to_pay"],
                normalized["price_range"],
                json.dumps(normalized["market_interests"], separators=(",", ":")),
                normalized["feedback_text"],
            ),
        )
        connection.commit()

    return {
        "submission_id": identifier,
        "submitted_at_utc": timestamp,
    }


def _decode_row(row: sqlite3.Row) -> dict[str, Any]:
    result = dict(row)
    result["missing_details"] = json.loads(result.pop("missing_details_json"))
    result["market_interests"] = json.loads(result.pop("market_interests_json"))
    return result


def export_feedback_rows(path: Path) -> list[dict[str, Any]]:
    init_feedback_store(path)
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT
                submission_id,
                submitted_at_utc,
                schema_version,
                comprehension_rating,
                lifecycle_clarity_rating,
                ai_reasoning_clarity_rating,
                immutable_record_trust,
                missing_details_json,
                alert_preference,
                willingness_to_pay,
                price_range,
                market_interests_json,
                feedback_text
            FROM feedback_submissions
            ORDER BY submitted_at_utc ASC, submission_id ASC
            """
        ).fetchall()
    return [_decode_row(row) for row in rows]


def feedback_summary(path: Path) -> dict[str, Any]:
    rows = export_feedback_rows(path)

    def counts(key: str) -> dict[str, int]:
        result: dict[str, int] = {}
        for row in rows:
            value = str(row[key])
            result[value] = result.get(value, 0) + 1
        return dict(sorted(result.items()))

    def average(key: str) -> float | None:
        if not rows:
            return None
        return round(sum(int(row[key]) for row in rows) / len(rows), 2)

    market_counts: dict[str, int] = {}
    missing_counts: dict[str, int] = {}
    for row in rows:
        for market in row["market_interests"]:
            market_counts[market] = market_counts.get(market, 0) + 1
        for detail in row["missing_details"]:
            missing_counts[detail] = missing_counts.get(detail, 0) + 1

    return {
        "schema_version": SCHEMA_VERSION,
        "submission_count": len(rows),
        "average_ratings": {
            key: average(key)
            for key in RATING_FIELDS
        },
        "immutable_record_trust": counts("immutable_record_trust"),
        "alert_preference": counts("alert_preference"),
        "willingness_to_pay": counts("willingness_to_pay"),
        "price_range": counts("price_range"),
        "market_interests": dict(sorted(market_counts.items())),
        "missing_details": dict(sorted(missing_counts.items())),
        "retention_months": RETENTION_MONTHS,
    }


def export_feedback_csv(path: Path) -> str:
    rows = export_feedback_rows(path)
    output = io.StringIO()
    fieldnames = [
        "submission_id",
        "submitted_at_utc",
        "schema_version",
        "comprehension_rating",
        "lifecycle_clarity_rating",
        "ai_reasoning_clarity_rating",
        "immutable_record_trust",
        "missing_details",
        "alert_preference",
        "willingness_to_pay",
        "price_range",
        "market_interests",
        "feedback_text",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        encoded = dict(row)
        encoded["missing_details"] = json.dumps(
            encoded["missing_details"], separators=(",", ":")
        )
        encoded["market_interests"] = json.dumps(
            encoded["market_interests"], separators=(",", ":")
        )
        writer.writerow(encoded)
    return output.getvalue()


def owner_token_valid(
    authorization: str | None,
    expected_token: str | None,
) -> bool:
    if not expected_token:
        return False
    prefix = "Bearer "
    supplied = (
        authorization[len(prefix):]
        if authorization and authorization.startswith(prefix)
        else ""
    )
    return secrets.compare_digest(supplied, expected_token)
