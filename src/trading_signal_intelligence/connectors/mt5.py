from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from trading_signal_intelligence.models import Candle, Quote


_TIMEFRAME_NAMES = {
    "M1": "TIMEFRAME_M1",
    "M5": "TIMEFRAME_M5",
    "M15": "TIMEFRAME_M15",
    "H1": "TIMEFRAME_H1",
    "H4": "TIMEFRAME_H4",
    "D1": "TIMEFRAME_D1",
}


@dataclass(slots=True)
class MT5Connector:
    """Thin adapter around the official MetaTrader5 Python package.

    This connector is intentionally source-specific. Downstream research code should
    consume normalized Candle/Quote objects rather than importing MetaTrader5 directly.
    """

    source_name: str = "mt5"

    def _mt5(self) -> Any:
        try:
            import MetaTrader5 as mt5  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "MetaTrader5 package is not installed. On the Windows MT5 research host, "
                "install the project with the 'mt5' extra."
            ) from exc
        return mt5

    def connect(self, terminal_path: str | None = None) -> None:
        mt5 = self._mt5()
        ok = mt5.initialize(path=terminal_path) if terminal_path else mt5.initialize()
        if not ok:
            raise RuntimeError(f"MT5 initialize() failed: {mt5.last_error()}")

    def disconnect(self) -> None:
        self._mt5().shutdown()

    def terminal_info(self) -> Any:
        return self._mt5().terminal_info()

    def account_info(self) -> Any:
        return self._mt5().account_info()

    def symbols(self) -> tuple[Any, ...]:
        result = self._mt5().symbols_get()
        if result is None:
            raise RuntimeError(f"MT5 symbols_get() failed: {self._mt5().last_error()}")
        return result

    def latest_quote(self, source_symbol: str, canonical_symbol: str) -> Quote:
        mt5 = self._mt5()
        tick = mt5.symbol_info_tick(source_symbol)
        if tick is None:
            raise RuntimeError(f"No MT5 tick for {source_symbol}: {mt5.last_error()}")
        ts = datetime.fromtimestamp(int(tick.time), tz=timezone.utc)
        return Quote(
            source=self.source_name,
            source_symbol=source_symbol,
            symbol=canonical_symbol,
            timestamp_utc=ts,
            bid=Decimal(str(tick.bid)) if tick.bid else None,
            ask=Decimal(str(tick.ask)) if tick.ask else None,
            last=Decimal(str(tick.last)) if tick.last else None,
        )

    def bars_from_pos(
        self,
        source_symbol: str,
        canonical_symbol: str,
        timeframe: str,
        start_pos: int,
        count: int,
        *,
        current_bar_is_closed: bool = False,
    ) -> list[Candle]:
        mt5 = self._mt5()
        constant_name = _TIMEFRAME_NAMES.get(timeframe.upper())
        if constant_name is None:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
        mt5_timeframe = getattr(mt5, constant_name)
        rows = mt5.copy_rates_from_pos(source_symbol, mt5_timeframe, start_pos, count)
        if rows is None:
            raise RuntimeError(
                f"MT5 copy_rates_from_pos() failed for {source_symbol}: {mt5.last_error()}"
            )

        candles: list[Candle] = []
        for index, row in enumerate(rows):
            is_current = start_pos == 0 and index == len(rows) - 1
            candles.append(
                Candle(
                    source=self.source_name,
                    source_symbol=source_symbol,
                    symbol=canonical_symbol,
                    timeframe=timeframe.upper(),
                    timestamp_utc=datetime.fromtimestamp(int(row["time"]), tz=timezone.utc),
                    open=Decimal(str(row["open"])),
                    high=Decimal(str(row["high"])),
                    low=Decimal(str(row["low"])),
                    close=Decimal(str(row["close"])),
                    volume=Decimal(str(row["tick_volume"])),
                    volume_kind="tick_volume",
                    spread=Decimal(str(row["spread"])),
                    is_closed=current_bar_is_closed if is_current else True,
                )
            )
        return candles
