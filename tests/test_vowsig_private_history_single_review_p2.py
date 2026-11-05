"""Synthetic private multi-ledger review, never real owner SQL or signing."""
from __future__ import annotations
from pathlib import Path
import hashlib
import json

import pytest

from trading_signal_intelligence.product.accounts import private_source_freeze as freeze
from scripts import vowsig_private_history_single_review as review
from tests.test_vowsig_private_source_freeze_p2 import _setup


def _frozen(tmp_path,monkeypatch):
    repo,private=_setup(tmp_path,monkeypatch)
    # Synthetic fixture uses a generic "private" name; rename only the
    # disposable test location to match the real owner-restricted path gate.
    private=private.rename(tmp_path/"OriginalLedgerEvidence-synthetic")
    anchor=repo/freeze.CRYPTO_ANCHOR_PATH
    data=json.loads(anchor.read_text())
    data["activated_at_utc"]="2026-11-05T02:00:00Z"
    anchor.write_text(json.dumps(data))
    manifest=freeze.capture_private_frozen_sources(repo,private)
    run=private/manifest["run_id"]
    monkeypatch.setattr(review,"NOV5_OWNER_MANIFEST_SHA256",manifest["manifest_sha256"])
    monkeypatch.setattr(review,"_EXPECTED_EVENT_RECORDS",12)
    return repo,run,manifest


def test_synthetic_freeze_never_promotes_missing_real_trades_or_crypto_cycles(tmp_path,monkeypatch):
    repo,run,m=_frozen(tmp_path,monkeypatch)
    result=review.inspect_original_frozen_history(repo,run,
        independently_recorded_manifest_sha256=m["manifest_sha256"])
    assert result["source_files_sha256_and_chains_rechecked"]==12
    assert result["total_original_event_rows"]==12
    assert result["ai_market_sources_checked"]==9
    assert result["s02_benchmark_sources_excluded_from_ai_performance"]==3
    assert result["ai_cost_arithmetic_market_holds"]==9
    assert result["crypto_internal_epoch_market_holds"]==3
    assert result["historical_performance_certified"] is False
    assert result["platform_history_publication_authorized"] is False
    assert "SYNTHETIC_SECRET_NEVER_EXPORT" not in str(result)


def test_separately_pinned_manifest_or_private_bytes_mismatch_holds(tmp_path,monkeypatch):
    repo,run,m=_frozen(tmp_path,monkeypatch)
    with pytest.raises(review.PrivateHistoryReviewHold):
        review.inspect_original_frozen_history(
            repo,run,independently_recorded_manifest_sha256="f"*64)
    changed=run/"ai_v1_1_xauusd.sqlite"
    changed.chmod(0o600)
    with changed.open("ab") as f:
        f.write(b"tampered")
    with pytest.raises(review.PrivateHistoryReviewHold):
        review.inspect_original_frozen_history(
            repo,run,independently_recorded_manifest_sha256=m["manifest_sha256"])


def test_internal_arithmetic_pass_does_not_certify_human_rights(tmp_path,monkeypatch):
    repo,run,m=_frozen(tmp_path,monkeypatch)
    def arithmetic(file,*,model_version,market,expected_frozen_file_sha256,
                   expected_terminal_record_hash):
        return {"original_event_records":1,"signal_count":1,
                "closed_after_cost_arithmetic_checked":1,
                "closed_signal_count":1,"partial_exit_event_count":0}
    def crypto(file,*,symbol,activated_at_utc):
        return {"status":"FROZEN_CRYPTO_INTERNAL_EPOCH_CONSISTENT_NOT_K5_CERTIFIED",
                "unobserved_internal_h1_closes":0,
                "unmatched_or_duplicate_cycle_entities":0}
    monkeypatch.setattr(review,"audit_frozen_after_costs",arithmetic)
    monkeypatch.setattr(review,"audit_frozen_crypto_epoch",crypto)
    result=review.inspect_original_frozen_history(
        repo,run,independently_recorded_manifest_sha256=m["manifest_sha256"])
    assert result["status"]=="PRIVATE_FROZEN_AI_ARITHMETIC_AND_INTERNAL_EPOCH_PASS_NOT_ATTESTED"
    assert result["ai_closed_outcomes_arithmetic_checked"]==9
    assert result["external_crypto_market_data_opportunity_verified"] is False
    assert result["source_rights_and_human_independent_review_verified"] is False
    assert result["historical_performance_certified"] is False


def test_accepts_both_reviewed_private_run_prefixes_and_rejects_unreviewed(tmp_path,monkeypatch):
    repo,run,m=_frozen(tmp_path,monkeypatch)
    renamed=run.with_name("freeze-"+run.name.removeprefix("source-freeze-"))
    run.rename(renamed)
    report=review.inspect_original_frozen_history(
        repo,renamed,independently_recorded_manifest_sha256=m["manifest_sha256"])
    assert report["source_files_sha256_and_chains_rechecked"]==12
    assert report["historical_performance_certified"] is False
    unapproved=renamed.with_name("random-"+renamed.name)
    renamed.rename(unapproved)
    with pytest.raises(review.PrivateHistoryReviewHold):
        review.inspect_original_frozen_history(
            repo,unapproved,independently_recorded_manifest_sha256=m["manifest_sha256"])


def _convert_package_to_real_owner_inline_layout(run):
    manifest=run/"manifest.preliminary.json"
    package=json.loads(manifest.read_text())
    rows=[]
    for item in package["rows"]:
        entry={
            "model_version":item["model_version"],
            "market":item["market"],
            "source_path":item["source_relative_path"],
            "private_file":item["private_copy_name"],
            "frozen_file_sha256":item["frozen_file_sha256"],
            "rows":item["rows"],
            "terminal_sequence":item["terminal_sequence"],
            "terminal_record_hash":item["terminal_record_hash"],
            "event_counts":item["event_counts"],
            "sequence_chain_sha256":item["sequence_chain_sha256"],
            "prior_observed_prefix_match":True,
            "self_consistent_full_chain":True,
            "crypto_activation_match_not_k5":item["model_version"]=="AI-v1.3",
        }
        rows.append(entry)
    converted={
        "schema_version":1,
        "status":"PRIVATE_FROZEN_COPIES_SELF_VERIFIED_EXTERNAL_REVIEW_REQUIRED",
        "count":12,"synchronized_all_markets_at_one_instant":False,
        "ledgers":rows,
    }
    manifest.chmod(0o600)
    manifest.write_text(json.dumps(converted,sort_keys=True,separators=(",",":")))
    return hashlib.sha256(manifest.read_bytes()).hexdigest()


def test_actual_owner_native_windows_manifest_shape_reverifies_read_only(tmp_path,monkeypatch):
    repo,run,m=_frozen(tmp_path,monkeypatch)
    owner_run=run.with_name("freeze-"+run.name.removeprefix("source-freeze-"))
    run.rename(owner_run)
    sha=_convert_package_to_real_owner_inline_layout(owner_run)
    monkeypatch.setattr(review,"NOV5_OWNER_MANIFEST_SHA256",sha)
    result=review.inspect_original_frozen_history(
        repo,owner_run,independently_recorded_manifest_sha256=sha)
    assert result["source_files_sha256_and_chains_rechecked"]==12
    assert result["total_original_event_rows"]==12
    assert result["historical_performance_certified"] is False


def test_owner_inline_manifest_false_crypto_anchor_check_refused(tmp_path,monkeypatch):
    repo,run,m=_frozen(tmp_path,monkeypatch)
    owner_run=run.with_name("freeze-"+run.name.removeprefix("source-freeze-"))
    run.rename(owner_run)
    _convert_package_to_real_owner_inline_layout(owner_run)
    manifest=owner_run/"manifest.preliminary.json"
    obj=json.loads(manifest.read_text())
    obj["ledgers"][6]["crypto_activation_match_not_k5"]=False
    manifest.write_text(json.dumps(obj,sort_keys=True,separators=(",",":")))
    sha=hashlib.sha256(manifest.read_bytes()).hexdigest()
    monkeypatch.setattr(review,"NOV5_OWNER_MANIFEST_SHA256",sha)
    with pytest.raises(review.PrivateHistoryReviewHold):
        review.inspect_original_frozen_history(
            repo,owner_run,independently_recorded_manifest_sha256=sha)
