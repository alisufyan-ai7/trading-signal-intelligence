from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from trading_signal_intelligence.ai_v1.crypto_activation_v1_3 import (
    ARTIFACT_PATHS,
    CANONICAL_SYMBOLS,
    DATABASE_PATHS,
    MARKETS,
    build_activation_anchor_preview_v1_3,
    build_activation_payload_v1_3,
    crypto_market_specs,
    preactivation_report_v1_3,
)
from trading_signal_intelligence.ai_v1.crypto_cost_v1_3 import (
    CryptoExecutionContext,
)
from trading_signal_intelligence.ai_v1.crypto_runtime_v1_3 import (
    H1_BARS,
    H4_BARS,
    CryptoRuntimeV13Error,
    build_crypto_feature_snapshot_v1_3,
    validate_batch_freeze_v1_3,
)
from trading_signal_intelligence.ai_v1.crypto_runtime_verifier_v1_3 import (
    verify_active_runtime_v1_3,
)
from trading_signal_intelligence.models import Candle

ROOT = Path(__file__).resolve().parents[1]


def _candle(
    *,
    source_symbol: str,
    canonical_symbol: str,
    timeframe: str,
    timestamp: datetime,
    index: int,
    is_closed: bool = True,
) -> Candle:
    base = Decimal(100) + Decimal(index) * Decimal("0.1")
    close = base + Decimal((index % 5) - 2) * Decimal("0.01")
    return Candle(
        source="binance_spot",
        source_symbol=source_symbol,
        symbol=canonical_symbol,
        timeframe=timeframe,
        timestamp_utc=timestamp,
        open=base,
        high=max(base, close) + Decimal("0.25"),
        low=min(base, close) - Decimal("0.25"),
        close=close,
        volume=Decimal(1000 + index),
        volume_kind="base_asset_volume",
        spread=None,
        is_closed=is_closed,
    )


def _history(
    symbol: str,
    *,
    latest_h1_open: datetime,
) -> tuple[list[Candle], list[Candle]]:
    canonical = CANONICAL_SYMBOLS[symbol]
    h1_start = latest_h1_open - timedelta(hours=H1_BARS - 1)
    h1 = [
        _candle(
            source_symbol=symbol,
            canonical_symbol=canonical,
            timeframe="H1",
            timestamp=h1_start + timedelta(hours=index),
            index=index,
        )
        for index in range(H1_BARS)
    ]
    h1.append(
        _candle(
            source_symbol=symbol,
            canonical_symbol=canonical,
            timeframe="H1",
            timestamp=latest_h1_open + timedelta(hours=1),
            index=H1_BARS,
            is_closed=False,
        )
    )

    latest_h4_open = latest_h1_open.replace(
        hour=(latest_h1_open.hour // 4) * 4,
    )
    if latest_h4_open + timedelta(hours=4) > latest_h1_open + timedelta(hours=1):
        latest_h4_open -= timedelta(hours=4)
    h4_start = latest_h4_open - timedelta(hours=4 * (H4_BARS - 1))
    h4 = [
        _candle(
            source_symbol=symbol,
            canonical_symbol=canonical,
            timeframe="H4",
            timestamp=h4_start + timedelta(hours=4 * index),
            index=index,
        )
        for index in range(H4_BARS)
    ]
    return h1, h4


def _context(
    symbol: str,
    *,
    observed_at: datetime,
    midpoint: Decimal = Decimal(1000),
    spread: Decimal = Decimal("0.01"),
) -> CryptoExecutionContext:
    half = spread / Decimal(2)
    return CryptoExecutionContext(
        source="binance_spot",
        source_symbol=symbol,
        observed_at_utc=observed_at,
        best_bid=midpoint - half,
        best_ask=midpoint + half,
    )


def test_crypto_package_preactivation_is_exact_and_nonactivating() -> None:
    report = preactivation_report_v1_3(ROOT)

    assert report["preactivation_check"] == "PASS"
    assert report["runtime_version"] == "AI-v1.3"
    assert report["decision_protocol_version"] == "AI-v1.0"
    assert report["program_id"] == "crypto-expansion-1"
    assert report["frozen_ai_v1_0_decision_lineage_match"] is True
    assert report["parallel_core_anchor"].endswith(
        "AI-v1.1-activation-2026-09-30T114412Z.json"
    )
    assert report["parallel_expansion_anchor"].endswith(
        "AI-v1.2.1-expansion-activation-2026-10-07T093543Z.json"
    )
    assert report["provider_call_made"] is False
    assert report["binance_call_made"] is False
    assert report["ledger_write_performed"] is False
    assert report["activation_performed"] is False
    assert report["scheduler_changed"] is False
    assert report["public_signal_exposure_changed"] is False
    assert report["broker_execution_enabled"] is False
    assert not any(report["crypto_ledger_paths_exist"].values())
    assert report["crypto_activation_anchors"] == []
    assert set(report["artifact_hashes"]) == set(ARTIFACT_PATHS)
    for required_artifact in (
        "compatibility_plan",
        "activation_plan",
        "ai_ledger_source",
        "lifecycle_evaluator_source",
        "provider_neutral_inference_source",
        "openai_adapter_source",
        "preactivation_verify_script",
    ):
        assert required_artifact in report["artifact_hashes"]

    provider = report["provider_identity"]
    assert provider["provider"] == "openai"
    assert provider["model_id"] == "gpt-5.4-2026-03-05"
    assert len(provider["model_parameter_fingerprint"]) == 64


def test_crypto_market_specs_are_separate_binance_usdt_markets() -> None:
    specs = crypto_market_specs(ROOT)

    assert set(specs) == set(MARKETS)
    assert specs["BTCUSDT"].canonical_symbol == "BTC/USDT"
    assert specs["ETHUSDT"].canonical_symbol == "ETH/USDT"
    assert specs["SOLUSDT"].canonical_symbol == "SOL/USDT"
    assert specs["BTCUSDT"].database_path == ROOT / DATABASE_PATHS["BTCUSDT"]
    assert specs["ETHUSDT"].database_path == ROOT / DATABASE_PATHS["ETHUSDT"]
    assert specs["SOLUSDT"].database_path == ROOT / DATABASE_PATHS["SOLUSDT"]


def test_crypto_batch_freeze_requires_all_three_markets_and_common_close() -> None:
    latest_open = datetime(2026, 10, 8, 22, 0, tzinfo=UTC)
    frozen = datetime(2026, 10, 8, 23, 4, 0, tzinfo=UTC)
    inputs = {}
    for symbol in MARKETS:
        h1, h4 = _history(symbol, latest_h1_open=latest_open)
        inputs[symbol] = (
            h1,
            h4,
            _context(symbol, observed_at=frozen - timedelta(seconds=2)),
        )

    result = validate_batch_freeze_v1_3(
        inputs,
        batch_frozen_at_utc=frozen,
    )

    assert result["batch_ready_before_provider_calls"] is True
    assert result["common_source_bar_close_utc"] == "2026-10-08T23:00:00+00:00"
    assert set(result["markets"]) == set(MARKETS)
    assert all(
        item["closed_h1_bars"] == H1_BARS
        for item in result["markets"].values()
    )
    assert all(
        item["closed_h4_bars"] == H4_BARS
        for item in result["markets"].values()
    )

    incomplete = dict(inputs)
    incomplete.pop("SOLUSDT")
    with pytest.raises(CryptoRuntimeV13Error, match="market set mismatch"):
        validate_batch_freeze_v1_3(
            incomplete,
            batch_frozen_at_utc=frozen,
        )


def test_crypto_feature_wrapper_uses_top_of_book_spread_and_crypto_schema() -> None:
    symbol = "ETHUSDT"
    latest_open = datetime(2026, 10, 8, 22, 0, tzinfo=UTC)
    inference_started = datetime(2026, 10, 8, 23, 4, 0, tzinfo=UTC)
    h1, h4 = _history(symbol, latest_h1_open=latest_open)
    context = _context(
        symbol,
        observed_at=inference_started - timedelta(seconds=1),
        midpoint=Decimal(2500),
        spread=Decimal("0.03"),
    )

    snapshot = build_crypto_feature_snapshot_v1_3(
        h1_all=h1,
        h4_all=h4,
        execution_context=context,
        inference_started_utc=inference_started,
        source_symbol=symbol,
        canonical_symbol=CANONICAL_SYMBOLS[symbol],
    )

    assert snapshot.payload["feature_schema_version"] == "AI-crypto-v1.0"
    assert snapshot.payload["source_symbol"] == symbol
    assert snapshot.payload["canonical_symbol"] == "ETH/USDT"
    assert snapshot.payload["source_bar_close_utc"] == "2026-10-08T23:00:00Z"
    assert snapshot.payload["spread_price"] == pytest.approx(0.03)
    assert len(snapshot.sha256) == 64


def test_activation_preview_has_no_side_effect_authority() -> None:
    activated = datetime(2026, 10, 9, 0, 0, tzinfo=UTC)
    preview = build_activation_anchor_preview_v1_3(
        repo_root=ROOT,
        activated_at_utc=activated,
    )

    assert preview["anchor_preview_only"] is True
    assert preview["ledger_records_created"] == 0
    assert preview["activation_anchor_written"] is False
    assert preview["provider_call_made"] is False
    assert preview["binance_call_made"] is False
    assert preview["scheduler_changed"] is False
    assert preview["public_signal_exposure_enabled"] is False
    assert preview["broker_execution_enabled"] is False
    assert set(preview["market_payloads"]) == set(MARKETS)

    for symbol in MARKETS:
        payload = build_activation_payload_v1_3(
            repo_root=ROOT,
            market=symbol,
            activated_at_utc=activated,
        )
        assert payload["market"] == symbol
        assert payload["canonical_symbol"] == CANONICAL_SYMBOLS[symbol]
        assert payload["provider"] == "openai"
        assert payload["model_id"] == "gpt-5.4-2026-03-05"
        assert len(payload["model_parameter_fingerprint"]) == 64
        assert payload["provider_call_made_at_activation"] is False
        assert payload["binance_call_made_at_activation"] is False
        assert payload["public_signal_exposure_enabled"] is False
        assert payload["broker_execution_enabled"] is False
        assert len(payload["activation_bundle_sha256"]) == 64


def test_future_live_runner_freezes_all_market_data_before_provider_adapter() -> None:
    source = (ROOT / "scripts" / "run_ai_v1_3_crypto_live.py").read_text(
        encoding="utf-8"
    )

    collection_loop = source.index("for symbol in MARKETS:")
    batch_validation = source.index("validate_batch_freeze_v1_3(")
    adapter_creation = source.index("OpenAIResponsesAdapter.from_environment(")
    market_cycles = source.rindex("for symbol in MARKETS:")

    assert collection_loop < batch_validation < adapter_creation < market_cycles
    assert "batch_collection" in source
    assert "FAIL_CLOSED_BEFORE_PROVIDER" in source


def test_activation_and_scheduler_scripts_remain_guarded_and_noninstalled() -> None:
    activation = (ROOT / "scripts" / "activate_ai_v1_3_crypto.py").read_text(
        encoding="utf-8"
    )
    installer = (
        ROOT / "scripts" / "install_ai_v1_3_crypto_shadow_task.ps1"
    ).read_text(encoding="utf-8")
    runner = (
        ROOT / "scripts" / "run_ai_v1_3_crypto_shadow_task.cmd"
    ).read_text(encoding="utf-8")

    assert "ACTIVATE-AI-V1.3-CRYPTO-LEDGERS" in activation
    assert "OpenAIResponsesAdapter" not in activation
    assert "BinanceSpotConnector" not in activation

    assert "ConfirmActivatedRuntime" in installer
    assert 'AddMinutes(4)' in installer
    assert "SignalProof AI-v1.1 Shadow Scan" in installer
    assert "VowSig AI-v1.2.1 Expansion Shadow Scan" in installer
    assert "Register-ScheduledTask" in installer

    assert "run_ai_v1_3_crypto_live.py" in runner
    assert "verify_ai_v1_3_crypto_runtime.py" in runner


def test_runtime_verifier_contract_with_synthetic_reports(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import trading_signal_intelligence.ai_v1.crypto_runtime_verifier_v1_3 as module

    parallel = {
        "runtime_verification": "PASS",
        "broker_execution_disabled": True,
    }
    report = {
        "runtime_version": "AI-v1.3",
        "decision_protocol_version": "AI-v1.0",
        "program_id": "crypto-expansion-1",
        "health": {
            "ledgers_valid": True,
            "activation_anchor_matches_ledgers": True,
            "crypto_artifacts_valid": True,
            "activation_anchor_upstream_valid": True,
            "scheduler_healthy": True,
            "public_signal_exposure_disabled": True,
            "broker_execution_disabled": True,
        },
        "markets": {
            symbol: {
                "counts_by_type": {"ACTIVATION": 1},
            }
            for symbol in MARKETS
        },
    }

    monkeypatch.setattr(
        module,
        "verify_active_runtime_registry_compat_v1_2_1",
        lambda *args, **kwargs: parallel,
    )
    monkeypatch.setattr(
        module,
        "build_report_v1_3",
        lambda *args, **kwargs: report,
    )

    result = verify_active_runtime_v1_3(
        ROOT,
        require_activation_only=True,
        include_scheduler=True,
        verify_upstream=True,
    )

    assert result["runtime_verification"] == "PASS"
    assert result["broker_execution_disabled"] is True
    assert result["public_signal_exposure_disabled"] is True
