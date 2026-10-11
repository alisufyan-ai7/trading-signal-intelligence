"""One-time K5 private read-only quality assessment; sanitized stdout only.

No provider calls, no write-mode SQLite, no exported private report files.
Read the existing K5 source through its frozen read-only observability API,
feed its private full report to the frozen-policy aggregate auditor *in memory*.
Only the auditor's explicitly whitelisted returned dict may be displayed.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

PRODUCTION_HEAD = "8ec0e82ea340682d92f9a62acf85171b7715bf5d"
PRODUCTION_TREE = "d24d3736d0bf6633ad0d05c4a1f1373558f813b9"
MARKETS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
EXPECTED_CONFIG_BLOBS = {
    "config/ai_v1_3_crypto_review_gates.json": "e74e4102ec71fdea362a460130bcadee61e1777e",
    "config/ai_v1_3_crypto_cost_policy.json": "3bb18aa5cf416b2b04cd28c53933ba68fd318b50",
}


class SafeHold(RuntimeError):
    pass


def _git(root: Path, *args: str) -> str:
    res = subprocess.run(
        ["git", "-C", str(root), *args], stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, check=True, timeout=20,
    )
    return res.stdout.decode("utf-8", errors="strict").strip()


def approved_source(root: Path) -> None:
    """Git reads only. Any source change means stop before K5 ledger access."""
    try:
        branch = _git(root, "symbolic-ref", "--short", "HEAD")
        head = _git(root, "rev-parse", "HEAD")
        tree = _git(root, "rev-parse", "HEAD^{tree}")
        status = _git(root, "status", "--porcelain", "--untracked-files=all")
        if (branch, head, tree, status) != (
            "main", PRODUCTION_HEAD, PRODUCTION_TREE, ""
        ):
            raise SafeHold("PRODUCTION_GIT_DRIFT")
        for path, blob in EXPECTED_CONFIG_BLOBS.items():
            if _git(root, "hash-object", "--", str(root / path)) != blob:
                raise SafeHold("FROZEN_POLICY_BLOB_DRIFT")
    except (OSError, subprocess.SubprocessError, UnicodeError) as exc:
        raise SafeHold("GIT_PREFLIGHT_UNAVAILABLE") from None


def generate_sanitized(
    report_builder: Callable[[], dict[str, Any]],
    assessor: Callable[[dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    """Keep ALL raw report/output from observed code out of console/logs."""
    hidden_stdout = io.StringIO()
    hidden_stderr = io.StringIO()
    try:
        with contextlib.redirect_stdout(hidden_stdout), contextlib.redirect_stderr(hidden_stderr):
            private = report_builder()
            result = assessor(private)
        if not isinstance(result, dict):
            raise SafeHold("SANITIZED_OUTPUT_INVALID")
        # Explicitly ensure the sanitized consumer did not return raw evidence.
        encoded = json.dumps(result, allow_nan=False)
        forbidden = ("ledger_path", "current_head_hash", "record_hash",
                     "activation_anchor", "open_signal_entities",
                     "request_payload", "response_payload", "raw_confidence")
        if any(token in encoded for token in forbidden):
            raise SafeHold("UNEXPECTED_PRIVATE_FIELD")
        return result
    except SafeHold:
        raise
    except Exception:
        # Never forward private source exception messages or traceback paths.
        raise SafeHold("PRIVATE_REPORT_OR_AGGREGATE_REJECTED") from None
    finally:
        hidden_stdout.close()
        hidden_stderr.close()


def assess_actual(root: Path) -> dict[str, Any]:
    from trading_signal_intelligence.ai_v1.crypto_observability_v1_3 import build_report_v1_3
    from audit_crypto_research_quality_v0_1 import assess
    gates = json.loads((root / "config/ai_v1_3_crypto_review_gates.json").read_text(encoding="utf-8"))
    costs = json.loads((root / "config/ai_v1_3_crypto_cost_policy.json").read_text(encoding="utf-8"))
    return generate_sanitized(
        lambda: build_report_v1_3(
            root, include_scheduler=True, verify_upstream=True
        ),
        lambda full: assess(full, gates, costs),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--production-root", required=True, type=Path)
    args = parser.parse_args(argv)
    stage = "PRECHECK"
    try:
        if os.name != "nt":
            raise SafeHold("NATIVE_WINDOWS_REQUIRED")
        root = args.production_root.resolve(strict=True)
        approved_source(root)
        sys.path.insert(0, str(root / "src"))
        stage = "ASSESSMENT"
        sanitized = assess_actual(root)
        stage = "POSTCHECK"
        approved_source(root)
        if sanitized.get("runtime_healthy_at_observation") is not True:
            print("K5_READONLY_QUALITY=HOLD_OPERATIONAL_HEALTH")
        else:
            print("K5_READONLY_QUALITY=PASS")
        print("PRIVATE_FULL_REPORT_EXPORTED=FALSE")
        print("PROVIDER_CALLS=FALSE")
        print("SCHEDULER_MUTATIONS=FALSE")
        print("PUBLICATION_ATTEMPTED=FALSE")
        print("BROKER_EXECUTION=FALSE")
        print(json.dumps(sanitized, sort_keys=True, indent=2, allow_nan=False))
        return 0 if sanitized.get("runtime_healthy_at_observation") is True else 3
    except SafeHold as exc:
        print("K5_READONLY_QUALITY=HOLD")
        print("STAGE=" + stage)
        print("REASON=" + str(exc))
        print("NO_RAW_PRIVATE_REPORT_PRINTED=TRUE")
        return 2
    except Exception:
        print("K5_READONLY_QUALITY=HOLD")
        print("STAGE=" + stage)
        print("REASON=UNCLASSIFIED_READONLY_FAILURE")
        print("NO_RAW_PRIVATE_REPORT_PRINTED=TRUE")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
