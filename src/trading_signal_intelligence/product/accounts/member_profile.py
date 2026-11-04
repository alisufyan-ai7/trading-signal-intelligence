"""Strictly scoped account preference and saved-research validation."""
from __future__ import annotations

from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

LEVELS = frozenset({"beginner", "intermediate", "advanced"})


class InvalidMemberPreference(ValueError):
    pass


def validate_preference_patch(body: Any) -> dict[str, Any]:
    if not isinstance(body, dict) or not body or set(body) - {
        "timezone", "educational_level", "research_updates_opt_in",
    }:
        raise InvalidMemberPreference("Invalid preference fields")
    if "timezone" in body:
        tz = body["timezone"]
        if not isinstance(tz, str) or not 1 <= len(tz) <= 64:
            raise InvalidMemberPreference("Invalid time zone")
        try:
            ZoneInfo(tz)
        except (ZoneInfoNotFoundError, ValueError, KeyError) as exc:
            raise InvalidMemberPreference("Unknown time zone") from exc
    if "educational_level" in body and body["educational_level"] not in LEVELS:
        raise InvalidMemberPreference("Unknown education level")
    if "research_updates_opt_in" in body:
        if type(body["research_updates_opt_in"]) is not bool:
            raise InvalidMemberPreference("Consent must be an explicit boolean")
    return body
