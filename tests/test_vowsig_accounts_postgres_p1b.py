"""Ephemeral PostgreSQL schema/ACL tests. NEVER target Railway/production.

Only executed with an explicit YES_THROWAWAY_DATABASE marker AND loopback DSN.
The GitHub Actions service is a fresh throwaway local PostgreSQL instance.
"""
from __future__ import annotations

import base64
import hashlib
import os
import uuid
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from trading_signal_intelligence.product.accounts.store import PostgresAccountStore

ROOT = Path(__file__).resolve().parents[1]


def _test_dsn():
    if os.getenv("VOWSIG_EPHEMERAL_PG_TEST_CONFIRM") != "YES_THROWAWAY_DATABASE":
        pytest.skip("Ephemeral database test not explicitly enabled")
    dsn = os.getenv("VOWSIG_EPHEMERAL_PG_TEST_DSN", "")
    parsed = urlsplit(dsn)
    if (
        parsed.scheme not in ("postgresql", "postgres")
        or parsed.hostname not in ("127.0.0.1", "localhost")
        or parsed.path != "/vowsig_test"
    ):
        pytest.fail("Refusing to run database schema tests outside loopback vowsig_test")
    return dsn


def test_ephemeral_postgres_account_identity_and_entitlement_contract():
    import psycopg
    from psycopg import errors
    from psycopg.rows import dict_row

    dsn = _test_dsn()
    # Deliberately bypass production store's verify-full TLS configuration
    # *only* for a disposable loopback PostgreSQL CI service. No production
    # connection string or credential is used by this test.
    class EphemeralStore(PostgresAccountStore):
        def __init__(self):
            pass

        def _connect(self):
            return psycopg.connect(dsn, row_factory=dict_row, connect_timeout=3)

    with psycopg.connect(dsn, autocommit=True, row_factory=dict_row) as db:
        for name in (
            "001_accounts_sessions_entitlements_watchlist.sql",
            "002_verified_identity_binding.sql",
            "003_preferences_and_saved_research.sql",
            "004_research_read_model_contract.sql",
            "005_consent_audit_deletion_requests.sql",
            "006_oidc_auth_transactions.sql",
        ):
            sql = (ROOT / "sql" / "accounts" / name).read_text(encoding="utf-8")
            db.execute(sql, prepare=False)

        id_a, id_b = uuid.uuid4(), uuid.uuid4()
        db.execute(
            """INSERT INTO vowsig_accounts (id,email,email_verified_at)
               VALUES (%s,%s,now()),(%s,%s,now())""",
            (id_a, "owner-a@example.test", id_b, "member-b@example.test"),
        )
        db.execute(
            """INSERT INTO vowsig_account_entitlements (account_id)
               VALUES (%s),(%s)""", (id_a, id_b),
        )
        assert db.execute(
            "SELECT count(*) AS n FROM vowsig_account_entitlements WHERE access_tier='research_free'"
        ).fetchone()["n"] == 2

        issuer = "https://identity.example.test"
        db.execute(
            """INSERT INTO vowsig_account_identities (account_id,issuer,subject)
               VALUES (%s,%s,%s),(%s,%s,%s)""",
            (id_a, issuer, "opaque-a", id_b, issuer, "opaque-b"),
        )
        with pytest.raises(errors.UniqueViolation):
            db.execute(
                """INSERT INTO vowsig_account_identities (account_id,issuer,subject)
                   VALUES (%s,%s,%s)""",
                (id_b, issuer, "opaque-a"),
            )

        token_bytes = bytes(range(32))
        token = base64.urlsafe_b64encode(token_bytes).decode().rstrip("=")
        token_sha = hashlib.sha256(token.encode("ascii")).hexdigest()
        db.execute(
            """INSERT INTO vowsig_account_sessions
               (token_sha256,account_id,expires_at)
               VALUES (%s,%s,now()+interval '1 day')""",
            (token_sha,id_a),
        )

    store = EphemeralStore()
    assert store.find_bound_account(issuer, "opaque-a") == str(id_a)
    assert store.find_bound_account(issuer, "opaque-b") == str(id_b)
    assert store.find_bound_account(issuer, "unknown-subject") is None

    identity = store.find_session(token_sha)
    assert identity is not None
    assert identity.account_id == str(id_a)
    assert identity.role == "member"
    assert identity.access_tier == "research_free"

    assert store.save_market(str(id_a), "BTCUSDT") == ["BTCUSDT"]
    assert store.watchlist(str(id_b)) == []
    assert store.save_market(str(id_b), "XAUUSD") == ["XAUUSD"]
    assert store.watchlist(str(id_a)) == ["BTCUSDT"]
    assert store.delete_market(str(id_a), "BTCUSDT") == []
    assert store.watchlist(str(id_b)) == ["XAUUSD"]

    with psycopg.connect(dsn, autocommit=True) as db:
        db.execute(
            "UPDATE vowsig_account_entitlements SET status='revoked' WHERE account_id=%s",
            (id_a,),
        )
    # Entitlement revocation invalidates the existing session access.
    assert store.find_session(token_sha) is None
    assert store.find_bound_account(issuer, "opaque-a") is None
    # Different account remains linked by its own immutable subject.
    assert store.find_bound_account(issuer, "opaque-b") == str(id_b)


    # P1/P4 saved research and preferences must be isolated by account ID.
    assert store.preferences(str(id_a)) == {
        "timezone": "UTC", "educational_level": "beginner",
        "research_updates_opt_in": False,
    }
    updated=store.update_preferences(str(id_a),{
        "timezone":"Asia/Karachi","educational_level":"intermediate",
        "research_updates_opt_in": True,
    })
    assert updated["timezone"] == "Asia/Karachi"
    assert store.preferences(str(id_b))["research_updates_opt_in"] is False
    export_a=store.account_export(str(id_a))
    assert export_a["email"]=="owner-a@example.test"
    assert len(export_a["consent_events"])==1
    assert export_a["consent_events"][0]["opted_in"] is True
    assert store.admin_growth()["verified_accounts"]==2

    store.save_research(str(id_a),"XAUUSD","core-signal-A")
    assert store.saved_research(str(id_a))[0]["signal_id"]=="core-signal-A"
    assert store.saved_research(str(id_b))==[]
    store.unsave_research(str(id_a),"core-signal-A")
    assert store.saved_research(str(id_a))==[]

    # P2 source projection cannot insert nonfinite/non-costed "closed" results.
    with psycopg.connect(dsn, autocommit=True, row_factory=dict_row) as db:
        snap=db.execute(
            """INSERT INTO vowsig_research_source_snapshots
               (source_program_id,model_version,source_snapshot_sha256,observed_at_utc)
               VALUES ('core-ai-shadow','AI-v1.1',%s,now()) RETURNING id""",
            ("a"*64,),
        ).fetchone()["id"]
        with pytest.raises(errors.CheckViolation):
            db.execute(
                """INSERT INTO vowsig_research_outcome_facts
                   (source_snapshot_id,source_program_id,model_version,cohort,
                    entity_id,state,source_record_sha256,exit_at_utc,combined_net_r,
                    cost_model_version,after_costs_verified)
                   VALUES (%s,'core-ai-shadow','AI-v1.1','forward','bad','closed',%s,
                           now(), 'NaN'::float8,'cost-v1',TRUE)""",
                (snap,"b"*64),
            )
        db.execute(
            """INSERT INTO vowsig_research_outcome_facts
               (source_snapshot_id,source_program_id,model_version,cohort,
                entity_id,state,source_record_sha256,exit_at_utc,combined_net_r,
                cost_model_version,after_costs_verified)
               VALUES (%s,'core-ai-shadow','AI-v1.1','forward','good','closed',%s,
                       now(), -1.0,'cost-v1',TRUE)""",
            (snap,"c"*64),
        )

    # A verified OIDC identity can create a real account+session atomically;
    # an unbound subject with an existing email must fail, never auto-link.
    from datetime import datetime, timedelta, timezone
    from trading_signal_intelligence.product.accounts.identity_contract import (
        IdentityProviderConfig, TrustedOidcClaims,
    )
    from trading_signal_intelligence.product.accounts.session_lifecycle import (
        issue_verified_session,
    )
    now=datetime.now(timezone.utc)
    cfg=IdentityProviderConfig("https://idp.example.test","client-vowsig")
    claim=TrustedOidcClaims(
        issuer=cfg.issuer,subject="fresh-subject",audience=cfg.client_id,
        nonce="server-nonce",email="newuser@example.test",email_verified=True,
        issued_at_utc=now-timedelta(seconds=20),expires_at_utc=now+timedelta(minutes=5),
        auth_time_utc=now-timedelta(seconds=30),
    )
    issued=issue_verified_session(claims=claim,configuration=cfg,
        expected_nonce="server-nonce",store=store,now=now)
    signed=store.find_session(hashlib.sha256(issued.token.encode()).hexdigest())
    assert signed is not None
    assert signed.account_id==issued.account_id and signed.access_tier=="research_free"
    assert signed.role=="member"
    assert store.find_bound_account(cfg.issuer,"fresh-subject")==issued.account_id

    from dataclasses import replace
    with pytest.raises(errors.UniqueViolation):
        issue_verified_session(
            claims=replace(claim,subject="other-subject"),
            configuration=cfg,expected_nonce="server-nonce",store=store,now=now,
        )
    assert store.find_bound_account(cfg.issuer,"other-subject") is None

    issued2=issue_verified_session(claims=claim,configuration=cfg,
        expected_nonce="server-nonce",store=store,now=now+timedelta(seconds=30))
    assert issued2.account_id==issued.account_id
    assert store.find_session(hashlib.sha256(issued.token.encode()).hexdigest()) is None
    assert store.revoke_session(
        hashlib.sha256(issued2.token.encode()).hexdigest(),issued2.account_id
    )
    assert store.find_session(hashlib.sha256(issued2.token.encode()).hexdigest()) is None
    deletion=store.request_deletion(issued2.account_id)
    assert deletion["status"]=="pending_reverification"
    assert store.account_export(issued2.account_id)["deletion_request"]["status"]=="pending_reverification"
    assert store.admin_growth()["registered_accounts"]==3



    # P1B-1: state and browser binding are single-use at SQL level.
    state_hash="e"*64
    browser_hash="f"*64
    store.begin_oidc(
        state_sha256=state_hash, browser_sha256=browser_hash,
        code_verifier="v"*43, nonce="n"*43,
    )
    assert store.consume_oidc(state_hash, "a"*64) is None
    recovered=store.consume_oidc(state_hash, browser_hash)
    assert recovered=={"code_verifier":"v"*43,"nonce":"n"*43}
    assert store.consume_oidc(state_hash, browser_hash) is None

    # Expired auth states must fail closed even if the state and browser match.
    store.begin_oidc(
        state_sha256="a"*64,browser_sha256=browser_hash,
        code_verifier="v"*43,nonce="n"*43,
    )
    with psycopg.connect(dsn,autocommit=True) as db:
        # Mutation is confined to this throwaway CI DB.
        db.execute(
            "UPDATE vowsig_oidc_authorizations "
            "SET created_at=now()-interval '20 minutes', "
            "expires_at=now()-interval '11 minutes' "
            "WHERE state_sha256=%s",("a"*64,),
        )
    assert store.consume_oidc("a"*64,browser_hash) is None

    # Concurrent-safe SQL counter rejects request 31 in the same 10-min bucket.
    peer="3"*64
    assert all(store.take_auth_budget(peer) for _ in range(30))
    assert store.take_auth_budget(peer) is False
    assert store.take_auth_budget("4"*64) is True


    # P2 quarantine-only deterministic replay; no public signal release.
    import json
    from trading_signal_intelligence.product.accounts.read_model_replay import (
        replay_quarantined_bundle, ProjectionReplayError,
    )
    from trading_signal_intelligence.product.accounts.read_model import (
        ReadModelValidationError,
    )
    sample={
        "schema_version":1,"source_program_id":"core-ai-shadow",
        "model_version":"AI-v1.1","cohort":"forward-shadow",
        "source_head_hash":"f"*64,
        "records":[{
            "entity_id":"replay-unique-001",
            "source_record_sha256":"e"*64,
            "state":"closed",
            "combined_net_r":-1.25,"after_costs_verified":True,
            "cost_model_version":"costs-v1",
            "exit_at_utc":"2026-11-03T09:00:00Z",
            "program_id":"core-ai-shadow","model_version":"AI-v1.1",
            "cohort":"forward-shadow",
        }],
    }
    raw=json.dumps(sample,sort_keys=True,separators=(",",":")).encode()
    pins={
        "pinned_artifact_sha256":hashlib.sha256(raw).hexdigest(),
        "pinned_source_head_hash":"f"*64,
        "expected_source_records":1,
        "observed_at_utc":"2026-11-04T10:00:00Z",
    }
    with psycopg.connect(dsn,autocommit=True,row_factory=dict_row) as db:
        first=replay_quarantined_bundle(db,raw,**pins)
        second=replay_quarantined_bundle(db,raw,**pins)
        assert first["source_snapshot_id"]==second["source_snapshot_id"]
        assert not first["idempotent_replay"] and second["idempotent_replay"]
        assert first["status"]=="quarantined"
        assert first["source_ledger_independently_reconciled"] is False
        assert first["customer_signal_publication_permitted"] is False
        db_row=db.execute(
            """SELECT ingest_status,completeness_verified
               FROM vowsig_research_source_snapshots WHERE id=%s""",
            (first["source_snapshot_id"],),
        ).fetchone()
        assert db_row["ingest_status"]=="quarantined"
        assert db_row["completeness_verified"] is False

        with pytest.raises(ReadModelValidationError):
            replay_quarantined_bundle(db,raw,**{**pins,"expected_source_records":2})
        # Same-count tampering must also fail rather than silently overwrite.
        db.execute(
            """UPDATE vowsig_research_outcome_facts SET combined_net_r=-9.9
               WHERE source_snapshot_id=%s""",(first["source_snapshot_id"],),
        )
        with pytest.raises(ProjectionReplayError):
            replay_quarantined_bundle(db,raw,**pins)
