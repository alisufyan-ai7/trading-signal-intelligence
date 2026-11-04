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
