"""Isolated guarded three-program snapshot export with explicit registry attestation.

Reuses the independently qualified current core/expansion snapshot; attaches
crypto only after full K5 observational validation. This is NOT the deployed
old public exporter, and never contacts providers or hosts directly.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from trading_signal_intelligence.product.app import ROOT
from trading_signal_intelligence.product.ai_insights import (
    _verify_crypto_validation_adapter_source,
)
from trading_signal_intelligence.product.crypto_validation import (
    build_crypto_public_validation_program,
    crypto_activation_state,
)
from export_guarded_core_expansion_v0_2 import build_core_expansion_snapshot


def build_guarded_full_snapshot(root: Path) -> dict:
    payload = build_core_expansion_snapshot(root)
    state = crypto_activation_state(root)
    if not state["any_state"] or not state["complete_shape"]:
        raise RuntimeError("crypto shadow activation incomplete")
    _verify_crypto_validation_adapter_source(root)
    crypto = build_crypto_public_validation_program(
        root, include_scheduler=True, verify_upstream=True,
    )
    if crypto.get("health", {}).get("healthy") is not True:
        raise RuntimeError("crypto shadow validation unhealthy")
    if crypto.get("public_signal_exposure") is not False:
        raise RuntimeError("crypto public signals are disabled")
    payload["validation_programs"].append(crypto)
    if {x.get("program_id") for x in payload["validation_programs"]} != {
        "core-ai-shadow", "market-expansion-1", "crypto-expansion-1"
    }:
        raise RuntimeError("guarded validation program cohort mismatch")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    dest = Path(args.output)
    if dest.exists():
        raise SystemExit("refuse overwrite of existing staging output")
    payload = build_guarded_full_snapshot(ROOT)
    dest.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({
        "validation_program_count": len(payload["validation_programs"]),
        "generated_at_utc": payload["generated_at_utc"],
        "raw_market_data_included": False,
    }))


if __name__ == "__main__":
    main()
