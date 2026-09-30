from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from trading_signal_intelligence.ai_v1.activation_v1_1 import (
    build_activation_anchor_preview_v1_1,
    preactivation_report_v1_1,
)
from trading_signal_intelligence.ai_v1.active_observability import (
    detect_active_runtime,
    v1_1_state,
)
from trading_signal_intelligence.ai_v1.retirement_v1_0 import (
    build_v1_0_retirement_preview,
)


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build a no-mutation AI-v1.0 -> AI-v1.1 cutover preview. "
            "No provider/MT5 call, ledger/anchor write, or scheduler mutation occurs."
        )
    )
    parser.add_argument(
        "--activated-at-utc",
        default=None,
        help="Optional prospective v1.1 activation timestamp for preview only.",
    )
    args = parser.parse_args()

    activated = (
        datetime.fromisoformat(args.activated_at_utc.replace("Z", "+00:00"))
        if args.activated_at_utc
        else datetime.now(timezone.utc)
    )
    if activated.tzinfo is None:
        raise SystemExit("--activated-at-utc must be timezone-aware")

    active_runtime = detect_active_runtime(ROOT)
    state = v1_1_state(ROOT)
    preactivation = preactivation_report_v1_1(ROOT)
    retirement = build_v1_0_retirement_preview(ROOT)
    activation = build_activation_anchor_preview_v1_1(
        repo_root=ROOT,
        activated_at_utc=activated,
    )

    payload = {
        "cutover_preview_version": "AI-v1.1-Cutover-Preview-v0.1",
        "current_active_runtime": active_runtime,
        "v1_1_state": state,
        "preactivation": preactivation,
        "v1_0_retirement_preview": retirement,
        "v1_1_activation_preview": activation,
        "planned_scheduler_transition": {
            "legacy_task": "SignalProof AI-v1 Shadow Scan",
            "replacement_task": "SignalProof AI-v1.1 Shadow Scan",
            "replacement_runner": "scripts/run_ai_v1_1_shadow_task.cmd",
            "legacy_must_be_disabled_before_install": True,
            "parallel_collection_allowed": False,
            "cadence": "hourly near minute 02",
        },
        "planned_public_transition": {
            "snapshot_key": "ai_v1",
            "active_runtime_field": "runtime_version",
            "decision_protocol_field": "decision_protocol_version",
            "legacy_lineage_separate": True,
            "gate_counts_merged": False,
            "partial_transition_cloud_overwrite_allowed": False,
        },
        "cutover_preconditions_currently_met": (
            active_runtime == "AI-v1.0"
            and preactivation["preactivation_check"] == "PASS"
            and retirement["cutover_preconditions"][
                "ready_for_scheduler_cutover"
            ]
            and not state["any_state"]
        ),
        "provider_call_made": False,
        "mt5_call_made": False,
        "ledger_write_made": False,
        "activation_anchor_written": False,
        "retirement_metadata_written": False,
        "scheduler_changed": False,
        "cloud_snapshot_pushed": False,
    }
    print(json.dumps(payload, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
