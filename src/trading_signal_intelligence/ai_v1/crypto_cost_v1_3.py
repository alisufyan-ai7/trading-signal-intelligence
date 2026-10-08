from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

POLICY_VERSION = "AI-v1.3-crypto-cost-v0.1"
ALLOWED_MARKETS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")


class CryptoCostPolicyError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class CryptoExecutionContext:
    source: str
    source_symbol: str
    observed_at_utc: datetime
    best_bid: Decimal
    best_ask: Decimal

    @property
    def spread_price(self) -> Decimal:
        return self.best_ask - self.best_bid

    @property
    def midpoint(self) -> Decimal:
        return (self.best_bid + self.best_ask) / Decimal(2)


@dataclass(frozen=True, slots=True)
class CryptoCostBreakdown:
    policy_version: str
    reference_midpoint: Decimal
    reference_spread: Decimal
    fee_rate_per_side: Decimal
    round_trip_fee_price: Decimal
    spread_crossing_price: Decimal
    slippage_buffer_price: Decimal
    total_cost_price: Decimal
    risk_price: Decimal
    estimated_cost_r: Decimal
    max_round_trip_cost_r: Decimal

    @property
    def passes_cost_guard(self) -> bool:
        return self.estimated_cost_r <= self.max_round_trip_cost_r

    def as_payload(self) -> dict[str, Any]:
        return {
            "policy_version": self.policy_version,
            "reference_midpoint": float(self.reference_midpoint),
            "reference_spread": float(self.reference_spread),
            "fee_rate_per_side": float(self.fee_rate_per_side),
            "round_trip_fee_price": float(self.round_trip_fee_price),
            "spread_crossing_price": float(self.spread_crossing_price),
            "slippage_buffer_price": float(self.slippage_buffer_price),
            "total_cost_price": float(self.total_cost_price),
            "risk_price": float(self.risk_price),
            "estimated_cost_r": float(self.estimated_cost_r),
            "max_round_trip_cost_r": float(self.max_round_trip_cost_r),
            "passes_cost_guard": self.passes_cost_guard,
        }


def canonical_policy_sha256(policy: dict[str, Any]) -> str:
    encoded = json.dumps(
        policy,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_crypto_cost_policy(path: Path) -> dict[str, Any]:
    policy = json.loads(path.read_text(encoding="utf-8"))
    validate_crypto_cost_policy(policy)
    return policy


def validate_crypto_cost_policy(policy: dict[str, Any]) -> None:
    if policy.get("policy_version") != POLICY_VERSION:
        raise CryptoCostPolicyError("unexpected crypto cost policy version")
    if policy.get("status") != "frozen_preactivation":
        raise CryptoCostPolicyError("crypto cost policy is not frozen preactivation")
    if tuple(policy.get("markets", [])) != ALLOWED_MARKETS:
        raise CryptoCostPolicyError("crypto cost policy market set/order mismatch")
    if policy.get("execution_venue_reference") != "binance_spot":
        raise CryptoCostPolicyError("crypto cost policy venue mismatch")
    if policy.get("broker_execution_authority") is not False:
        raise CryptoCostPolicyError("crypto cost policy must not authorize execution")

    fee = policy.get("fee_policy") or {}
    if fee.get("account_tier_assumption") != "regular_user":
        raise CryptoCostPolicyError("fee tier must remain regular_user")
    if fee.get("liquidity_role_assumption_entry") != "taker":
        raise CryptoCostPolicyError("entry fee role must remain taker")
    if fee.get("liquidity_role_assumption_exit") != "taker":
        raise CryptoCostPolicyError("exit fee role must remain taker")
    if Decimal(str(fee.get("fee_rate_per_side_fraction"))) != Decimal("0.001"):
        raise CryptoCostPolicyError("fee rate per side must remain 0.001")
    if fee.get("bnb_discount_assumed") is not False:
        raise CryptoCostPolicyError("BNB discount must remain disabled")
    if fee.get("vip_discount_assumed") is not False:
        raise CryptoCostPolicyError("VIP discount must remain disabled")
    if fee.get("pair_promotion_discount_assumed") is not False:
        raise CryptoCostPolicyError("promotion discount must remain disabled")

    spread = policy.get("spread_policy") or {}
    if spread.get("source") != "prospective_binance_top_of_book":
        raise CryptoCostPolicyError("spread source must remain Binance top-of-book")
    if Decimal(str(spread.get("round_trip_crossing_spread_multiplier"))) != Decimal(1):
        raise CryptoCostPolicyError("spread crossing multiplier must remain 1.0")

    slippage = policy.get("slippage_policy") or {}
    if slippage.get("source") != "preregistered_research_assumption_not_binance":
        raise CryptoCostPolicyError("slippage source annotation mismatch")
    if Decimal(str(slippage.get("buffer_multiplier_of_entry_spread"))) != Decimal(1):
        raise CryptoCostPolicyError("slippage spread multiplier must remain 1.0")

    guard = policy.get("guard_policy") or {}
    if Decimal(str(guard.get("max_round_trip_cost_r"))) != Decimal("0.15"):
        raise CryptoCostPolicyError("crypto max round-trip cost guard must remain 0.15R")

    promotion = policy.get("promotion_policy") or {}
    if (
        promotion.get(
            "temporary_zero_fee_or_discounted_pair_promotions_reduce_research_cost"
        )
        is not False
    ):
        raise CryptoCostPolicyError("temporary promotions must not reduce research cost")


def validate_execution_context(
    context: CryptoExecutionContext,
    *,
    source_symbol: str,
    now_utc: datetime,
    max_age_seconds: float,
) -> None:
    if source_symbol not in ALLOWED_MARKETS:
        raise CryptoCostPolicyError(f"unsupported crypto market: {source_symbol}")
    if context.source != "binance_spot":
        raise CryptoCostPolicyError("execution context source must be binance_spot")
    if context.source_symbol != source_symbol:
        raise CryptoCostPolicyError("execution context source symbol mismatch")
    if context.observed_at_utc.tzinfo is None or now_utc.tzinfo is None:
        raise CryptoCostPolicyError("execution-context timestamps must be timezone-aware")

    observed = context.observed_at_utc.astimezone(UTC)
    now = now_utc.astimezone(UTC)
    age_seconds = (now - observed).total_seconds()
    if not math.isfinite(age_seconds) or age_seconds < 0 or age_seconds > max_age_seconds:
        raise CryptoCostPolicyError(
            f"execution context age {age_seconds:.6f}s outside 0..{max_age_seconds}"
        )

    if context.best_bid <= 0 or context.best_ask <= 0:
        raise CryptoCostPolicyError("best bid/ask must be positive")
    if context.best_ask < context.best_bid:
        raise CryptoCostPolicyError("best ask must be greater than or equal to best bid")
    if context.spread_price < 0:
        raise CryptoCostPolicyError("spread cannot be negative")
    if context.midpoint <= 0:
        raise CryptoCostPolicyError("midpoint must be positive")


def calculate_crypto_cost(
    *,
    policy: dict[str, Any],
    context: CryptoExecutionContext,
    source_symbol: str,
    atr_14: float,
    stop_atr: float,
    now_utc: datetime,
    max_data_age_seconds: float,
) -> CryptoCostBreakdown:
    validate_crypto_cost_policy(policy)
    validate_execution_context(
        context,
        source_symbol=source_symbol,
        now_utc=now_utc,
        max_age_seconds=max_data_age_seconds,
    )

    atr = Decimal(str(atr_14))
    stop = Decimal(str(stop_atr))
    if not atr.is_finite() or atr <= 0:
        raise CryptoCostPolicyError("ATR must be finite and positive")
    if not stop.is_finite() or stop <= 0:
        raise CryptoCostPolicyError("stop_atr must be finite and positive")

    fee_rate = Decimal(str(policy["fee_policy"]["fee_rate_per_side_fraction"]))
    spread_multiplier = Decimal(
        str(policy["spread_policy"]["round_trip_crossing_spread_multiplier"])
    )
    slippage_multiplier = Decimal(
        str(policy["slippage_policy"]["buffer_multiplier_of_entry_spread"])
    )
    max_cost_r = Decimal(str(policy["guard_policy"]["max_round_trip_cost_r"]))

    midpoint = context.midpoint
    spread = context.spread_price
    round_trip_fee = Decimal(2) * fee_rate * midpoint
    spread_crossing = spread_multiplier * spread
    slippage_buffer = slippage_multiplier * spread
    total_cost = round_trip_fee + spread_crossing + slippage_buffer
    risk_price = atr * stop
    estimated_cost_r = total_cost / risk_price

    return CryptoCostBreakdown(
        policy_version=POLICY_VERSION,
        reference_midpoint=midpoint,
        reference_spread=spread,
        fee_rate_per_side=fee_rate,
        round_trip_fee_price=round_trip_fee,
        spread_crossing_price=spread_crossing,
        slippage_buffer_price=slippage_buffer,
        total_cost_price=total_cost,
        risk_price=risk_price,
        estimated_cost_r=estimated_cost_r,
        max_round_trip_cost_r=max_cost_r,
    )
