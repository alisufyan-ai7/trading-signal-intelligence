from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable


SYNC_MAX_WAIT_SECONDS = 30.0
SYNC_POLL_INTERVAL_SECONDS = 1.0


class RatesSynchronizationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class RatesReadState:
    observed_at_utc: datetime
    latest_tick_utc: datetime | None
    newest_h1_open_utc: datetime | None
    newest_h4_open_utc: datetime | None
    h1_rows: int
    h4_rows: int

    def __post_init__(self) -> None:
        for value in (
            self.observed_at_utc,
            self.latest_tick_utc,
            self.newest_h1_open_utc,
            self.newest_h4_open_utc,
        ):
            if value is not None and value.tzinfo is None:
                raise ValueError("all timestamps must be timezone-aware")


@dataclass(frozen=True, slots=True)
class RatesSynchronizationResult:
    status: str
    attempts: int
    waited_seconds: float
    saw_current_hour_tick: bool
    expected_h1_open_utc: datetime | None
    expected_h4_open_utc: datetime | None
    final_state: RatesReadState

    @property
    def ready(self) -> bool:
        return self.status == "READY"


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc)


def current_h1_open(value: datetime) -> datetime:
    value = _as_utc(value)
    return value.replace(minute=0, second=0, microsecond=0)


def current_h4_open(value: datetime) -> datetime:
    value = _as_utc(value)
    hour = (value.hour // 4) * 4
    return value.replace(hour=hour, minute=0, second=0, microsecond=0)


def state_matches_current_rates(
    state: RatesReadState,
    *,
    scan_started_utc: datetime,
) -> tuple[bool, datetime | None, datetime | None, bool]:
    scan = _as_utc(scan_started_utc)
    tick = state.latest_tick_utc
    if tick is None:
        return False, None, None, False

    tick = _as_utc(tick)
    scan_h1 = current_h1_open(scan)
    tick_h1 = current_h1_open(tick)
    saw_current_hour_tick = tick_h1 == scan_h1
    if not saw_current_hour_tick:
        return False, None, None, False

    expected_h1 = tick_h1
    expected_h4 = current_h4_open(tick)
    ready = (
        state.h1_rows > 0
        and state.h4_rows > 0
        and state.newest_h1_open_utc is not None
        and state.newest_h4_open_utc is not None
        and _as_utc(state.newest_h1_open_utc) == expected_h1
        and _as_utc(state.newest_h4_open_utc) == expected_h4
    )
    return ready, expected_h1, expected_h4, True


def synchronize_rates_snapshot(
    *,
    scan_started_utc: datetime,
    read_state: Callable[[], RatesReadState],
    monotonic: Callable[[], float],
    sleep: Callable[[float], None],
    max_wait_seconds: float = SYNC_MAX_WAIT_SECONDS,
    poll_interval_seconds: float = SYNC_POLL_INTERVAL_SECONDS,
) -> RatesSynchronizationResult:
    if max_wait_seconds <= 0:
        raise ValueError("max_wait_seconds must be positive")
    if poll_interval_seconds <= 0:
        raise ValueError("poll_interval_seconds must be positive")

    scan_started = _as_utc(scan_started_utc)
    started = float(monotonic())
    deadline = started + float(max_wait_seconds)

    attempts = 0
    saw_current_hour_tick = False
    expected_h1: datetime | None = None
    expected_h4: datetime | None = None
    last_state: RatesReadState | None = None

    while True:
        attempts += 1
        last_state = read_state()
        ready, h1_expected, h4_expected, saw_tick = state_matches_current_rates(
            last_state,
            scan_started_utc=scan_started,
        )
        saw_current_hour_tick = saw_current_hour_tick or saw_tick
        if h1_expected is not None:
            expected_h1 = h1_expected
        if h4_expected is not None:
            expected_h4 = h4_expected

        now = float(monotonic())
        waited = max(0.0, now - started)

        if ready:
            return RatesSynchronizationResult(
                status="READY",
                attempts=attempts,
                waited_seconds=waited,
                saw_current_hour_tick=saw_current_hour_tick,
                expected_h1_open_utc=expected_h1,
                expected_h4_open_utc=expected_h4,
                final_state=last_state,
            )

        if now >= deadline:
            status = (
                "RATES_NOT_SYNCHRONIZED"
                if saw_current_hour_tick
                else "NO_CURRENT_H1_TICK"
            )
            return RatesSynchronizationResult(
                status=status,
                attempts=attempts,
                waited_seconds=waited,
                saw_current_hour_tick=saw_current_hour_tick,
                expected_h1_open_utc=expected_h1,
                expected_h4_open_utc=expected_h4,
                final_state=last_state,
            )

        remaining = deadline - now
        sleep(min(float(poll_interval_seconds), remaining))
