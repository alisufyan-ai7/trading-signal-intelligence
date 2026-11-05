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
        assert sql.startswith(("SELECT","SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
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
    assert conn.statements[0][0]=="SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"
    assert sum("vowsig_research_outcome_facts" in sql for sql,_ in conn.statements)==9


def test_bad_platform_universe_fails_closed_even_if_nine_rows_exist(tmp_path,monkeypatch):
    env=_files(tmp_path)
    monkeypatch.setattr(mod,"verify_signed_history_attestation",
                        lambda doc,reviewer_public_key_pem:{"source_program_id":"wrong"})
    result=mod.load_owner_verified_platform_history(
        lambda:Connection(),settings=env)
    assert result["status"]=="independent_platform_source_evidence_rejected"
    assert result["verified_full_history"] is False


def test_owner_performance_ui_only_displays_nine_market_pass_with_exact_signed_status():
    page=(Path(__file__).resolve().parents[1]/"web/member/member.js").read_text(encoding="utf-8")
    assert "perf.verified_full_history===true" in page
    assert "perf.ai_market_count===9" in page
    assert "perf.market_cohorts.length===9" in page
    assert "Nine original AI market cohorts reviewed" in page
    assert "Automatic production release" in page
    assert "Not authorized" in page
    assert "Source-reconciled performance unavailable" in page


# A complete trusted-signature -> private files -> SQL rows -> real reconciliation
# test, rather than a stubbed verify_all_nine_market_history result.
def _real_signed_fixture(tmp_path):
    from tests.test_vowsig_platform_history_universe_p2 import _make, _signed
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
    universe, inputs, _, source_signer, universe_signer, source_pub, universe_pub = (
        _make(include_signing_material=True)
    )
    from pathlib import Path
    private = tmp_path / "review-private"
    private.mkdir()
    cohort_dir = private / "cohort-signatures"
    cohort_dir.mkdir()
    universe_path = private / "independently-reviewed-universe.signed.json"
    universe_path.write_bytes(_signed(universe_signer, universe, "universe"))
    upath = private / "universe-public.pem"
    upath.write_bytes(universe_pub)
    cpath = private / "cohort-public.pem"
    cpath.write_bytes(source_pub)
    for symbol, record in inputs.items():
        (cohort_dir / (symbol + ".signed.json")).write_bytes(
            record["signed_attestation"]
        )
    settings = {
        mod._ENV[0]: str(universe_path),
        mod._ENV[1]: str(upath),
        mod._ENV[2]: hashlib.sha256(universe_pub).hexdigest(),
        mod._ENV[3]: str(cpath),
        mod._ENV[4]: hashlib.sha256(source_pub).hexdigest(),
        mod._ENV[5]: str(cohort_dir),
        mod._ENV[6]: universe["original_twelve_source_manifest_sha256"],
    }
    return settings, inputs


class _SignedSourceDb:
    def __init__(self, inputs, *, fault=None):
        self.inputs = inputs
        self.fault = fault
        self.sql = []
        self.active = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params=None):
        assert sql.startswith(
            ("SELECT", "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        ), "A source-review request must never write to PostgreSQL"
        self.sql.append((sql, params))
        self.active = (sql, params)
        return self

    def fetchall(self):
        sql, params = self.active
        if "vowsig_research_source_snapshots" in sql:
            matches = [
                symbol for symbol, record in self.inputs.items()
                if (record["source_snapshot"]["source_program_id"],
                    record["source_snapshot"]["model_version"],
                    record["source_snapshot"]["source_snapshot_sha256"]) == params
            ]
            if not matches:
                return []
            symbol = matches[0]
            row = dict(self.inputs[symbol]["source_snapshot"], id=symbol)
            if self.fault == ("duplicate_snapshot", symbol):
                return [row, row]
            return [row]
        if "vowsig_research_outcome_facts" in sql:
            symbol = params[0]
            rows = [dict(r) for r in self.inputs[symbol]["facts"]]
            if self.fault == ("alter_after_cost", symbol):
                rows[0]["combined_net_r"] = 4.0
            if self.fault == ("omit_full_population", symbol):
                return []
            return rows
        raise AssertionError("Unexpected database query")


def test_real_disposable_signatures_reconcile_all_nine_original_cohorts_in_one_snapshot(tmp_path):
    settings, inputs = _real_signed_fixture(tmp_path)
    connection = _SignedSourceDb(inputs)
    result = mod.load_owner_verified_platform_history(
        lambda: connection, settings=settings
    )
    assert result["status"] == "INDEPENDENTLY_SIGNED_NINE_AI_COHORT_UNIVERSE_RECONCILED"
    assert result["verified_full_history"] is True
    assert result["verified_full_cohort_history"] is True
    assert result["ai_market_count"] == 9
    assert len(result["market_cohorts"]) == 9
    assert sum(m["after_cost_closed_outcomes"] for m in result["market_cohorts"]) == 9
    assert result["production_performance_publishing_automatically_authorized"] is False
    assert len(connection.sql) == 19
    assert connection.sql[0][0] == (
        "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"
    )
    assert "test-original" not in str(result)


@pytest.mark.parametrize("fault", [
    ("duplicate_snapshot", "BTCUSDT"),
    ("alter_after_cost", "ETHUSDT"),
    ("omit_full_population", "XAUUSD"),
])
def test_signed_history_rejects_changed_projection_even_with_valid_signatures(
    tmp_path, fault
):
    settings, inputs = _real_signed_fixture(tmp_path)
    connection = _SignedSourceDb(inputs, fault=fault)
    result = mod.load_owner_verified_platform_history(lambda: connection, settings=settings)
    assert result["status"] == "independent_platform_source_evidence_rejected"
    assert result["verified_full_history"] is False
    assert result["performance"] is None
    assert result["production_performance_publishing_automatically_authorized"] is False
