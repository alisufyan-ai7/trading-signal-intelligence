"""Synthetic-only privacy and fail-closed tests: no live ledgers or sources."""
from __future__ import annotations

import contextlib
import io
import math
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import run_crypto_quality_private_readonly_v0_1 as mod  # noqa: E402


class TestReadOnlyPrivateAggregator(unittest.TestCase):
    def test_private_report_and_debug_output_are_never_printed(self):
        secret = "SENSITIVE-PRIVATE-LEDGER-HASH-SENTINEL"

        def private_builder():
            print("PRIVATE_STDOUT=" + secret)
            print("PRIVATE_STDERR=" + secret, file=sys.stderr)
            return {"ledger_path": secret}

        output = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(err):
            result = mod.generate_sanitized(
                private_builder,
                lambda raw: {"valid_inferences": 10},
            )
        self.assertEqual(result, {"valid_inferences": 10})
        self.assertNotIn(secret, output.getvalue())
        self.assertNotIn(secret, err.getvalue())

    def test_private_source_exception_message_not_repeated(self):
        secret = "PRIVATE-SOURCE-PATH-AND-ACCOUNT-ID"

        def failure():
            raise RuntimeError("untrusted source exception " + secret)

        with self.assertRaises(mod.SafeHold) as caught:
            mod.generate_sanitized(failure, lambda raw: raw)
        self.assertEqual(str(caught.exception), "PRIVATE_REPORT_OR_AGGREGATE_REJECTED")
        self.assertNotIn(secret, str(caught.exception))

    def test_forbidden_ledger_metadata_rejected(self):
        for field in ("ledger_path", "record_hash", "current_head_hash",
                      "raw_confidence", "open_signal_entities"):
            with self.subTest(field=field):
                with self.assertRaises(mod.SafeHold) as caught:
                    mod.generate_sanitized(
                        lambda: {"secret": 1},
                        lambda _: {field: "SENSITIVE"},
                    )
                self.assertEqual(str(caught.exception), "UNEXPECTED_PRIVATE_FIELD")

    def test_invalid_nonfinite_result_not_displayed(self):
        with self.assertRaises(mod.SafeHold):
            mod.generate_sanitized(lambda: {}, lambda _: {"metric": float("nan")})

    def test_failed_git_identity_prevents_live_ledger_read(self):
        actual = {
            ("symbolic-ref", "--short", "HEAD"): "main",
            ("rev-parse", "HEAD"): "0000000000000000000000000000000000000000",
            ("rev-parse", "HEAD^{tree}"): mod.PRODUCTION_TREE,
            ("status", "--porcelain", "--untracked-files=all"): "",
        }
        with patch.object(mod, "_git", side_effect=lambda root, *args: actual[args]):
            with self.assertRaises(mod.SafeHold) as caught:
                mod.approved_source(Path("C:/synthetic"))
        self.assertEqual(str(caught.exception), "PRODUCTION_GIT_DRIFT")


if __name__ == "__main__":
    unittest.main()
