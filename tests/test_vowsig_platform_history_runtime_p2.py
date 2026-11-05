"""Mocked DB adapter tests: never fetch live Railway or contact providers."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from trading_signal_intelligence.product.accounts import platform_history_runtime as mod
from trading_signal_intelligence.product.accounts.source_inventory import SOURCES


def test_absent_or_partial_platform_config_never_promotes_history():
    def forbidden():
        raise AssertionError("No SQL access without all reviewer receipts")
    missing=mod.load_owner_verified_platform_history(forbidden,settings={})
    assert missing["verified_full_history"] is False
    assert missing["performance"] is None
    partial=mod.load_owner_verified_platform_history(
        forbidden,settings={mod._ENV[0]:"/x/universe.json"})
    assert partial["status"]=="independent_platform_source_configuration_incomplete"


def test_unknown_unpinned_or_relative_review_files_fail_without_sql(tmp_path):
    env={k:"placeholder" for k in mod._ENV}
    env[mod._ENV[0]]="relative.json"
    def forbidden():
        raise AssertionError("Must reject before SQL")
    result=mod.load_owner_verified_platform_history(forbidden,settings=env)
    assert result["status"]=="independent_platform_source_evidence_rejected"
    assert result["verified_full_history"] is False


class Connection:
    def __init__(self):
        self.statements=[]
        self.current=None
    def __enter__(self):
        return self
    def __exit__(self,*_):
        return False
    def execute(self,sql,params=None):
        assert sql.startswith(("SELECT","SET TRANSACTION READ ONLY"))
        assert not any(w in sql.upper() for w in ("INSERT INTO","UPDATE ","DELETE FROM","CREATE TABLE"))
        self.statements.append((sql,params))
        self.current=(sql,params)
        return self
    def fetchall(self):
        if "vowsig_research_source_snapshots" in self.current[0]:
            return [{
                "id":"test-id",
                "source_program_id":self.current[1][0],
                "model_version":self.current[1][1],
                "source_snapshot_sha256":self.current[1][2],
                "source_head_hash":"a"*64,
                "ingest_status":"verified","completeness_verified":True,
            }]
        return [{
            "entity_id":"synthetic","source_record_sha256":"a"*64,
            "state":"closed","combined_net_r":-0.1,"cohort":"test",
            "exit_at_utc":"2026-11-05T00:00:00Z",
            "after_costs_verified":True,"cost_model_version":"test",
        }]


def _files(tmp_path):
    private=tmp_path/"private"
    private.mkdir()
    docs=private/"nine"
    docs.mkdir()
    uni=private/"universe.signed.json"
    uni.write_bytes(b'{"synthetic":true}')
    upem=private/"u.pem"
    upem.write_bytes(b"u-public-key-only")
    cpem=private/"c.pem"
    cpem.write_bytes(b"c-public-key-only")
    for spec in SOURCES:
        if spec.program!="s02-forward":
            (docs/(spec.symbol+".signed.json")).write_bytes(spec.symbol.encode())
    return {
        mod._ENV[0]:str(uni),mod._ENV[1]:str(upem),
        mod._ENV[2]:hashlib.sha256(upem.read_bytes()).hexdigest(),
        mod._ENV[3]:str(cpem),
        mod._ENV[4]:hashlib.sha256(cpem.read_bytes()).hexdigest(),
        mod._ENV[5]:str(docs),mod._ENV[6]:"a"*64,
    }


def test_exact_nine_scoped_readonly_database_queries_and_no_global_auto_release(tmp_path,monkeypatch):
    env=_files(tmp_path)
    def signed(doc,reviewer_public_key_pem):
        symbol=doc.decode()
        spec=next(s for s in SOURCES if s.symbol==symbol and s.program!="s02-forward")
        return {
            "source_program_id":spec.program,
            "model_version":spec.model_version,
            "source_snapshot_sha256":hashlib.sha256(symbol.encode()).hexdigest(),
        }
    def verified(**kw):
        assert set(kw["scoped_private_cohorts"])=={
            s.symbol for s in SOURCES if s.program!="s02-forward"}
        assert kw["owner_recorded_original_manifest_sha256"]=="a"*64
        return {
            "verified_full_history":True,
            "ai_market_count":9,
            "s02_benchmark_is_not_ai_history":True,
            "market_cohorts":[{"market":s.symbol,"original_outcomes":1,
                               "after_cost_closed_outcomes":1,
                               "cohort":"test","program":s.program,
                               "model_version":s.model_version,
                               "verified_cohort":True}
                              for s in SOURCES if s.program!="s02-forward"],
            "production_performance_publishing_automatically_authorized":False,
        }
    monkeypatch.setattr(mod,"verify_signed_history_attestation",signed)
    monkeypatch.setattr(mod,"verify_all_nine_market_history",verified)
    conn=Connection()
    result=mod.load_owner_verified_platform_history(lambda:conn,settings=env)
    assert result["verified_full_history"] is True
    assert result["ai_market_count"]==9
    assert result["performance"] is None
    assert result["production_performance_publishing_automatically_authorized"] is False
    assert len(conn.statements)==19
    assert conn.statements[0][0]=="SET TRANSACTION READ ONLY"
    assert sum("vowsig_research_outcome_facts" in sql for sql,_ in conn.statements)==9


def test_bad_platform_universe_fails_closed_even_if_nine_rows_exist(tmp_path,monkeypatch):
    env=_files(tmp_path)
    monkeypatch.setattr(mod,"verify_signed_history_attestation",
                        lambda doc,reviewer_public_key_pem:{"source_program_id":"wrong"})
    result=mod.load_owner_verified_platform_history(
        lambda:Connection(),settings=env)
    assert result["status"]=="independent_platform_source_evidence_rejected"
    assert result["verified_full_history"] is False
