"""Conservative GFS retention policy for VowSig S02 backup IDs.

PURE local planner. No cloud clients, credentials, disk writes, deletion APIs
or Task Scheduler integration. Its output is NOT deletion authorization.

Retain last 30 days daily, latest of each of eight preceding ISO UTC weeks,
and latest of 12 older UTC calendar months. Protect the first real manual
backup plus two newest successful scheduled backups independently of age.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

BACKUP_ID = re.compile(r"^backup-[0-9a-f]{32}$")
PASS = "BACKUP_AND_INDEPENDENT_DUAL_CLOUD_RECOVERY_VERIFIED"
FIRST_MANUAL_ID = "backup-8bce80179c524ace8f4a52cb702b3716"
DAILY_DAYS = 30
WEEKLY_WEEKS = 8
MONTHLY_MONTHS = 12
MIN_CLOUD_GRACE_DAYS = 7
POLICY = "vowsig-s02-gfs-30d-8w-12m-v1"


class RetentionPlanRejected(RuntimeError):
    """Sanitized error. No private provider metadata is reflected."""


def _datetime(value: str) -> datetime:
    if type(value) is not str or len(value) > 40:
        raise RetentionPlanRejected("invalid UTC audit timestamp")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        raise RetentionPlanRejected("invalid UTC audit timestamp") from None
    if result.tzinfo is None or result.utcoffset() != timedelta(0):
        raise RetentionPlanRejected("audit timestamp must explicitly be UTC")
    return result.astimezone(timezone.utc)


def _month_index(ts: datetime) -> int:
    return 12 * ts.year + ts.month - 1


def _validate_records(
    records: Iterable[dict[str, Any]], now: datetime,
) -> tuple[list[tuple[datetime, str]], bool]:
    if not isinstance(records, (list, tuple)) or len(records) > 20000:
        raise RetentionPlanRejected("bounded history list required")
    verified: list[tuple[datetime, str]] = []
    seen: set[str] = set()
    blocked = False
    for record in records:
        if type(record) is not dict or type(record.get("status")) is not str:
            raise RetentionPlanRejected("invalid audit record")
        status = record["status"]
        if status != PASS:
            # Past credential/source/cloud HOLDs require explicit owner
            # reconciliation. Do not silently treat failed runs as success.
            blocked = True
            continue
        bid = record.get("backup_id")
        if type(bid) is not str or not BACKUP_ID.fullmatch(bid):
            raise RetentionPlanRejected("invalid successful backup ID")
        if bid in seen:
            raise RetentionPlanRejected("duplicate successful backup ID")
        if (record.get("aws_restored") is not True
                or record.get("b2_restored") is not True
                or record.get("scheduled") is not True
                or type(record.get("record_count")) is not int
                or not 0 < record["record_count"] <= 1_000_000):
            raise RetentionPlanRejected("unverified successful audit record")
        ts = _datetime(record.get("at_utc"))
        if ts > now + timedelta(minutes=5):
            raise RetentionPlanRejected("future-dated successful audit record")
        seen.add(bid)
        verified.append((ts, bid))
    verified.sort(key=lambda pair: (pair[0], pair[1]), reverse=True)
    return verified, blocked


def choose_gfs(
    records: Iterable[dict[str, Any]], *,
    as_of_utc: str,
    extra_pinned_ids: Iterable[str] = (),
    review_latch_present: bool = False,
) -> dict[str, Any]:
    """Return proposed KEEP/ELIGIBLE IDs from audited scheduled successes.

    A deletion operator must independently prove complete two-provider
    version inventories, manifest decryptability, both cold restores and a
    separately approved >=7-day plan. 'eligible' NEVER authorizes deletion.
    """
    now = _datetime(as_of_utc)
    if type(review_latch_present) is not bool:
        raise RetentionPlanRejected("review latch state invalid")
    if not isinstance(extra_pinned_ids, (tuple, list, set, frozenset)):
        raise RetentionPlanRejected("invalid pin collection")
    pinned = {FIRST_MANUAL_ID}
    for bid in extra_pinned_ids:
        if type(bid) is not str or not BACKUP_ID.fullmatch(bid):
            raise RetentionPlanRejected("invalid protected backup ID")
        pinned.add(bid)
    items, had_failure = _validate_records(records, now)
    recent = items[:2]
    pinned.update(bid for _, bid in recent)

    cutoff_daily = now - timedelta(days=DAILY_DAYS)
    cutoff_weekly = cutoff_daily - timedelta(weeks=WEEKLY_WEEKS)
    older_month = _month_index(cutoff_weekly)
    earliest_month = older_month - (MONTHLY_MONTHS - 1)
    daily: set[str] = set()
    weeks: dict[tuple[int, int], str] = {}
    months: dict[int, str] = {}

    for ts, bid in items:
        if ts >= cutoff_daily:
            daily.add(bid)
        elif ts >= cutoff_weekly:
            iso = ts.isocalendar()
            wk = (iso.year, iso.week)
            if wk not in weeks:
                weeks[wk] = bid
        else:
            mi = _month_index(ts)
            if earliest_month <= mi <= older_month and mi not in months:
                months[mi] = bid

    # A 56-day sliding window can intersect 9 ISO weeks. Only the 8 most
    # recent weekly buckets are retained under the requested strict cap.
    retained_weeks = set(bid for _, bid in
                         sorted(weeks.items(), reverse=True)[:WEEKLY_WEEKS])
    retained_months = set(months.values())
    kept = daily | retained_weeks | retained_months | pinned
    retained = [bid for _, bid in items if bid in kept]
    eligible = [bid for _, bid in items if bid not in kept]

    # A planning result does not prove old cloud object VersionIds or remote
    # recovery. Even a healthy schedule cannot authorize deletion here.
    age_of_latest = ((now - items[0][0]).total_seconds() / 3600
                     if items else None)
    hold_reasons = []
    if not items:
        hold_reasons.append("NO_VERIFIED_AUTOMATIC_BACKUP_HISTORY")
    elif age_of_latest is None or age_of_latest > 30:
        hold_reasons.append("NO_RECENT_VERIFIED_BACKUP")
    if had_failure:
        hold_reasons.append("UNACKNOWLEDGED_HOLD_PRESENT_IN_HISTORY")
    if review_latch_present:
        hold_reasons.append("OPERATOR_REVIEW_LATCH_PRESENT")
    if eligible:
        hold_reasons.append("DUAL_CLOUD_VERSION_AND_RESTORE_INVENTORY_REQUIRED")
        hold_reasons.append("SEPARATE_7_DAY_OWNER_APPROVAL_REQUIRED")

    body = {
        "policy": POLICY,
        "as_of_utc": now.isoformat(timespec="seconds"),
        "keep_ids": retained,
        "eligible_ids": eligible,
        "protected_ids": sorted(pinned),
        "counts": {
            "history_verified": len(items),
            "daily": len(daily),
            "weekly": len(retained_weeks),
            "monthly": len(retained_months),
            "keep_in_history": len(retained),
            "eligible_in_history": len(eligible),
        },
        "hold_reasons": hold_reasons,
        "provider_deletions_performed": 0,
        "cloud_deletion_authorized": False,
        "minimum_approval_grace_days": MIN_CLOUD_GRACE_DAYS,
    }
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    body["plan_sha256"] = hashlib.sha256(encoded).hexdigest()
    return body
