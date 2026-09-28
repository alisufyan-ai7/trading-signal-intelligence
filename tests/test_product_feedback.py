from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import pytest

from trading_signal_intelligence.product.feedback import (
    FeedbackValidationError,
    export_feedback_csv,
    export_feedback_rows,
    feedback_summary,
    owner_token_valid,
    submit_feedback,
    validate_feedback_payload,
)


GOOD = {
    "comprehension_rating": 4,
    "lifecycle_clarity_rating": 3,
    "ai_reasoning_clarity_rating": 5,
    "immutable_record_trust": "yes",
    "missing_details": ["expiry_validity", "market_context"],
    "alert_preference": "telegram",
    "willingness_to_pay": "maybe",
    "price_range": "10_25",
    "market_interests": ["XAUUSD", "USTEC"],
    "feedback_text": "I would like clearer expiry examples.",
}


def test_validate_feedback_payload_accepts_intended_schema() -> None:
    normalized = validate_feedback_payload(dict(GOOD))
    assert normalized["market_interests"] == ["XAUUSD", "USTEC"]
    assert normalized["feedback_text"] == "I would like clearer expiry examples."


@pytest.mark.parametrize(
    "patch",
    [
        {"comprehension_rating": 0},
        {"comprehension_rating": 6},
        {"alert_preference": "sms"},
        {"market_interests": []},
        {"market_interests": ["XAUUSD", "XAUUSD"]},
        {"missing_details": ["not_allowed"]},
        {"unexpected": "field"},
    ],
)
def test_validate_feedback_payload_rejects_invalid_input(patch: dict) -> None:
    payload = dict(GOOD)
    payload.update(patch)
    with pytest.raises(FeedbackValidationError):
        validate_feedback_payload(payload)


@pytest.mark.parametrize(
    "text",
    [
        "My password is abc",
        "API key: sk-example",
        "broker login 12345",
        "account id 445566",
        "card number 4111 1111 1111 1111",
        "access token: example",
    ],
)
def test_feedback_text_rejects_obvious_sensitive_data(text: str) -> None:
    payload = dict(GOOD)
    payload["feedback_text"] = text
    with pytest.raises(FeedbackValidationError, match="Do not submit credentials"):
        validate_feedback_payload(payload)


def test_submit_feedback_is_append_only_and_exportable(tmp_path: Path) -> None:
    path = tmp_path / "feedback.sqlite"

    first = submit_feedback(
        path,
        GOOD,
        submitted_at_utc="2026-09-29T00:00:00+00:00",
        submission_id="fb_first",
    )
    second_payload = dict(GOOD)
    second_payload["willingness_to_pay"] = "yes"
    second_payload["price_range"] = "25_50"
    second_payload["market_interests"] = ["US30"]
    second = submit_feedback(
        path,
        second_payload,
        submitted_at_utc="2026-09-29T00:01:00+00:00",
        submission_id="fb_second",
    )

    assert first["submission_id"] == "fb_first"
    assert second["submission_id"] == "fb_second"

    rows = export_feedback_rows(path)
    assert [row["submission_id"] for row in rows] == ["fb_first", "fb_second"]
    assert rows[0]["missing_details"] == ["expiry_validity", "market_context"]
    assert rows[1]["market_interests"] == ["US30"]

    with pytest.raises(Exception):
        submit_feedback(
            path,
            GOOD,
            submitted_at_utc="2026-09-29T00:02:00+00:00",
            submission_id="fb_first",
        )


def test_feedback_summary_contains_aggregate_only(tmp_path: Path) -> None:
    path = tmp_path / "feedback.sqlite"
    submit_feedback(
        path,
        GOOD,
        submitted_at_utc="2026-09-29T00:00:00+00:00",
        submission_id="fb_first",
    )
    result = feedback_summary(path)

    assert result["submission_count"] == 1
    assert result["average_ratings"]["comprehension_rating"] == 4.0
    assert result["willingness_to_pay"] == {"maybe": 1}
    assert result["market_interests"] == {"USTEC": 1, "XAUUSD": 1}
    assert "feedback_text" not in json.dumps(result)


def test_csv_export_round_trips_expected_fields(tmp_path: Path) -> None:
    path = tmp_path / "feedback.sqlite"
    submit_feedback(
        path,
        GOOD,
        submitted_at_utc="2026-09-29T00:00:00+00:00",
        submission_id="fb_first",
    )
    csv_text = export_feedback_csv(path)
    rows = list(csv.DictReader(io.StringIO(csv_text)))

    assert len(rows) == 1
    assert rows[0]["submission_id"] == "fb_first"
    assert json.loads(rows[0]["market_interests"]) == ["XAUUSD", "USTEC"]


def test_owner_token_is_separate_bearer_secret() -> None:
    assert owner_token_valid("Bearer owner-secret", "owner-secret") is True
    assert owner_token_valid("Bearer ingest-secret", "owner-secret") is False
    assert owner_token_valid(None, "owner-secret") is False
    assert owner_token_valid("Bearer owner-secret", None) is False
