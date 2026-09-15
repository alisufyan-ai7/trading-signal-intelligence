from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import timedelta

from trading_signal_intelligence.models import Candle


@dataclass(frozen=True, slots=True)
class QualityReport:
    duplicate_timestamps: int
    non_monotonic_pairs: int
    unexpected_gaps: int

    @property
    def ok(self) -> bool:
        return (
            self.duplicate_timestamps == 0
            and self.non_monotonic_pairs == 0
            and self.unexpected_gaps == 0
        )


def check_bar_sequence(candles: Sequence[Candle], expected_interval: timedelta) -> QualityReport:
    duplicates = 0
    non_monotonic = 0
    gaps = 0

    for previous, current in zip(candles, candles[1:]):
        delta = current.timestamp_utc - previous.timestamp_utc
        if delta.total_seconds() == 0:
            duplicates += 1
        elif delta.total_seconds() < 0:
            non_monotonic += 1
        elif delta > expected_interval:
            gaps += 1

    return QualityReport(
        duplicate_timestamps=duplicates,
        non_monotonic_pairs=non_monotonic,
        unexpected_gaps=gaps,
    )
