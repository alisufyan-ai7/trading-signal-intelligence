from __future__ import annotations

from datetime import datetime, timedelta, timezone

from trading_signal_intelligence.ai_v1.rates_sync_v1_1 import (
    RatesReadState,
    current_h1_open,
    current_h4_open,
    state_matches_current_rates,
    synchronize_rates_snapshot,
)


UTC = timezone.utc
SCAN = datetime(2026, 9, 30, 8, 2, 10, tzinfo=UTC)
H1 = datetime(2026, 9, 30, 8, 0, 0, tzinfo=UTC)
H4 = datetime(2026, 9, 30, 8, 0, 0, tzinfo=UTC)


class Clock:
    def __init__(self) -> None:
        self.value = 0.0

    def monotonic(self) -> float:
        return self.value

    def sleep(self, seconds: float) -> None:
        self.value += seconds


def state(
    *,
    tick: datetime | None = SCAN,
    h1: datetime | None = H1,
    h4: datetime | None = H4,
) -> RatesReadState:
    return RatesReadState(
        observed_at_utc=SCAN,
        latest_tick_utc=tick,
        newest_h1_open_utc=h1,
        newest_h4_open_utc=h4,
        h1_rows=500 if h1 is not None else 0,
        h4_rows=200 if h4 is not None else 0,
    )


def reader(states: list[RatesReadState]):
    remaining = list(states)

    def _read() -> RatesReadState:
        if len(remaining) > 1:
            return remaining.pop(0)
        return remaining[0]

    return _read


def test_expected_h1_h4_buckets_are_utc() -> None:
    value = datetime(2026, 9, 30, 11, 47, 33, tzinfo=UTC)
    assert current_h1_open(value) == datetime(2026, 9, 30, 11, 0, tzinfo=UTC)
    assert current_h4_open(value) == datetime(2026, 9, 30, 8, 0, tzinfo=UTC)


def test_fresh_first_read_is_ready_without_sleep() -> None:
    clock = Clock()
    result = synchronize_rates_snapshot(
        scan_started_utc=SCAN,
        read_state=reader([state()]),
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )
    assert result.ready is True
    assert result.status == "READY"
    assert result.attempts == 1
    assert result.waited_seconds == 0.0


def test_stale_first_read_then_fresh_second_read() -> None:
    clock = Clock()
    stale_h1 = H1 - timedelta(hours=1)
    stale_h4 = H4 - timedelta(hours=4)
    result = synchronize_rates_snapshot(
        scan_started_utc=SCAN,
        read_state=reader(
            [
                state(h1=stale_h1, h4=stale_h4),
                state(),
            ]
        ),
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )
    assert result.ready is True
    assert result.attempts == 2
    assert result.waited_seconds == 1.0
    assert result.saw_current_hour_tick is True


def test_multiple_stale_reads_eventually_become_ready() -> None:
    clock = Clock()
    stale = state(
        h1=H1 - timedelta(hours=1),
        h4=H4 - timedelta(hours=4),
    )
    result = synchronize_rates_snapshot(
        scan_started_utc=SCAN,
        read_state=reader([stale, stale, stale, state()]),
        monotonic=clock.monotonic,
        sleep=clock.sleep,
        max_wait_seconds=10,
        poll_interval_seconds=1,
    )
    assert result.status == "READY"
    assert result.attempts == 4
    assert result.waited_seconds == 3.0


def test_current_tick_but_h4_stale_retries_then_times_out() -> None:
    clock = Clock()
    stale_h4 = state(h4=H4 - timedelta(hours=4))
    result = synchronize_rates_snapshot(
        scan_started_utc=SCAN,
        read_state=reader([stale_h4]),
        monotonic=clock.monotonic,
        sleep=clock.sleep,
        max_wait_seconds=3,
        poll_interval_seconds=1,
    )
    assert result.status == "RATES_NOT_SYNCHRONIZED"
    assert result.ready is False
    assert result.saw_current_hour_tick is True
    assert result.attempts == 4


def test_no_current_hour_tick_fails_closed() -> None:
    clock = Clock()
    old_tick = H1 - timedelta(seconds=1)
    old_state = state(
        tick=old_tick,
        h1=H1 - timedelta(hours=1),
        h4=H4 - timedelta(hours=4),
    )
    result = synchronize_rates_snapshot(
        scan_started_utc=SCAN,
        read_state=reader([old_state]),
        monotonic=clock.monotonic,
        sleep=clock.sleep,
        max_wait_seconds=3,
        poll_interval_seconds=1,
    )
    assert result.status == "NO_CURRENT_H1_TICK"
    assert result.ready is False
    assert result.saw_current_hour_tick is False


def test_state_match_requires_both_h1_and_h4_current_rows() -> None:
    ready, expected_h1, expected_h4, saw_tick = state_matches_current_rates(
        state(h4=H4 - timedelta(hours=4)),
        scan_started_utc=SCAN,
    )
    assert ready is False
    assert saw_tick is True
    assert expected_h1 == H1
    assert expected_h4 == H4
