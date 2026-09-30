from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from trading_signal_intelligence.ai_v1.ledger import AILedger
from trading_signal_intelligence.ai_v1.observability import (
    DATABASE_PATHS,
    MARKETS,
)
from trading_signal_intelligence.ai_v1.retirement_v1_0 import (
    build_v1_0_retirement_preview,
)


ACTIVATED = datetime(2026, 9, 28, 15, 56, 16, tzinfo=timezone.utc)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _seed(repo_root: Path, *, open_signal: bool) -> None:
    markets: dict[str, dict] = {}
    for symbol in MARKETS:
        ledger = AILedger(repo_root / DATABASE_PATHS[symbol])
        activation = ledger.append(
            record_type="ACTIVATION",
            entity_id=f"AI-v1.0:{symbol}:ACTIVATION",
            effective_at_utc=ACTIVATED,
            recorded_at_utc=ACTIVATED,
            payload={
                "protocol_version": "AI-v1.0",
                "market": symbol,
                "activated_at_utc": ACTIVATED.isoformat(),
                "broker_execution_enabled": False,
            },
        )
        markets[symbol] = {
            "record_hash": activation["record_hash"],
            "payload": activation["payload"],
        }

    if open_signal:
        xau = AILedger(repo_root / DATABASE_PATHS["XAUUSD"])
        entity = "AI-v1.0:XAUUSD:2026-09-28T17:00:00Z"
        xau.append(
            record_type="INFERENCE",
            entity_id=entity,
            effective_at_utc=ACTIVATED,
            recorded_at_utc=ACTIVATED,
            payload={"normalized_decision": {"decision": "BUY"}},
        )
        xau.append(
            record_type="SIGNAL",
            entity_id=entity,
            effective_at_utc=ACTIVATED,
            recorded_at_utc=ACTIVATED,
            payload={"direction": "BUY", "broker_execution_enabled": False},
        )

    forward = repo_root / "research" / "forward"
    forward.mkdir(parents=True, exist_ok=True)
    (forward / "AI-v1-activation-2026-09-28T155616Z.json").write_text(
        json.dumps(
            {
                "protocol_version": "AI-v1.0",
                "status": "TEST",
                "activated_at_utc": ACTIVATED.isoformat(),
                "provider_call_made": False,
                "broker_execution_enabled": False,
                "artifact_hashes": {},
                "markets": markets,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def test_retirement_preview_is_read_only_and_blocks_open_signal(
    tmp_path: Path,
) -> None:
    _seed(tmp_path, open_signal=True)
    before = {
        symbol: _sha256(tmp_path / DATABASE_PATHS[symbol])
        for symbol in MARKETS
    }

    preview = build_v1_0_retirement_preview(
        tmp_path,
        include_scheduler=False,
        verify_upstream=False,
    )

    after = {
        symbol: _sha256(tmp_path / DATABASE_PATHS[symbol])
        for symbol in MARKETS
    }
    assert before == after
    assert preview["ledger_mutation_performed"] is False
    assert preview["metadata_write_performed"] is False
    assert preview["backfilled_into_ai_v1_1"] is False
    assert preview["performance_bearing_records_observed"] is True
    assert preview["cutover_preconditions"]["unresolved_signal_count"] == 1
    assert preview["cutover_preconditions"]["ready_for_scheduler_cutover"] is False


def test_retirement_preview_allows_zero_unresolved_signals(tmp_path: Path) -> None:
    _seed(tmp_path, open_signal=False)
    preview = build_v1_0_retirement_preview(
        tmp_path,
        include_scheduler=False,
        verify_upstream=False,
    )

    assert preview["cutover_preconditions"]["unresolved_signals_zero"] is True
    assert preview["cutover_preconditions"]["ready_for_scheduler_cutover"] is True
    assert preview["ledgers_preserved"] is True
    assert preview["provider_call_made"] is False
    assert preview["mt5_call_made"] is False
