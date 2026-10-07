from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from trading_signal_intelligence.ai_v1.activation_v1_2_1 import (
    EXPANSION_ARTIFACT_PATHS,
    RUNTIME_VERSION,
    build_activation_anchor_preview_v1_2_1,
    preactivation_report_v1_2_1,
)
from trading_signal_intelligence.ai_v1.activation_v1_1 import (
    artifact_hashes,
    git_commit_sha,
)


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    report = preactivation_report_v1_2_1(ROOT)
    if report["preactivation_check"] != "PASS":
        print(
            json.dumps(
                {
                    "package_verification": "FAIL",
                    "preactivation": report,
                },
                indent=2,
                allow_nan=False,
            )
        )
        raise SystemExit(2)

    preview = build_activation_anchor_preview_v1_2_1(
        repo_root=ROOT,
        activated_at_utc=datetime.now(timezone.utc),
    )

    result = {
        "package_verification": "PASS",
        "runtime_version": RUNTIME_VERSION,
        "decision_protocol_version": "AI-v1.0",
        "repository_commit_sha": git_commit_sha(ROOT),
        "preactivation_check": report["preactivation_check"],
        "readiness_evidence": report["readiness_evidence"],
        "predecessor_runtime_version": report["predecessor_runtime_version"],
        "predecessor_activation_anchor": report[
            "predecessor_activation_anchor"
        ],
        "predecessor_activation_anchor_sha256": report[
            "predecessor_activation_anchor_sha256"
        ],
        "predecessor_failure_evidence_sha256": report[
            "predecessor_failure_evidence_sha256"
        ],
        "predecessor_evidence_carry_forward": False,
        "calendar_carry_forward": False,
        "gate_counts_carry_forward": False,
        "backfill_prior_missed": False,
        "successor_ledger_paths_exist": report[
            "expansion_ledger_paths_exist"
        ],
        "successor_activation_anchors": report[
            "expansion_activation_anchors"
        ],
        "artifact_hashes": artifact_hashes(
            ROOT,
            EXPANSION_ARTIFACT_PATHS,
        ),
        "activation_preview": {
            "runtime_version": preview["runtime_version"],
            "decision_protocol_version": preview[
                "decision_protocol_version"
            ],
            "predecessor_runtime_version": preview[
                "predecessor_runtime_version"
            ],
            "predecessor_evidence_carry_forward": preview[
                "predecessor_evidence_carry_forward"
            ],
            "calendar_carry_forward": preview["calendar_carry_forward"],
            "parallel_to_runtime_version": preview[
                "parallel_to_runtime_version"
            ],
            "gate_counts_carry_forward": preview[
                "gate_counts_carry_forward"
            ],
            "backfill_prior_missed": preview["backfill_prior_missed"],
            "provider_call_made": preview["provider_call_made"],
            "public_exposure_enabled": preview[
                "public_exposure_enabled"
            ],
            "broker_execution_enabled": preview[
                "broker_execution_enabled"
            ],
            "ledger_records_created": preview["ledger_records_created"],
            "activation_anchor_written": preview[
                "activation_anchor_written"
            ],
            "scheduler_changed": preview["scheduler_changed"],
            "market_payloads": preview["market_payloads"],
        },
        "provider_call_made": False,
        "mt5_call_made": False,
        "ledger_write_performed": False,
        "activation_performed": False,
        "scheduler_changed": False,
        "public_exposure_changed": False,
        "broker_execution_enabled": False,
    }

    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
