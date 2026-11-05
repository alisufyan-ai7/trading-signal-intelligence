"""PG18 runtime role preflight: synthetic cursor, fail-closed, zero DSN disclosure."""
from __future__ import annotations
from pathlib import Path
import pytest
from trading_signal_intelligence.product.accounts import railway_pg_acceptance as ra


class Cursor:
    def __init__(self, answers):
        self.answers=iter(answers)
        self.statements=[]
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def execute(self,s):
        assert s.startswith("SELECT")
        assert "password" not in s
        self.statements.append(s)
    def fetchone(self):return next(self.answers)


class Connection:
    def __init__(self,answers):self.cur=Cursor(answers)
    def cursor(self):return self.cur


def answers(role="vowsig_app",path="vowsig, pg_catalog",
            ssl=True,priv=(False,False,False,False),
            grants=(True,False,True,False),writes=(False,False,False)):
    return [(role,path,ssl,"TLSv1.3"),priv,grants,writes]


def test_restricted_psycopg_facts_are_safe_and_read_only():
    conn=Connection(answers())
    result=ra.inspect_authenticated_app_connection(conn)
    assert result["status"]=="AUTHENTICATED_APP_ROLE_RESTRICTED_SQL_READ_ONLY_PASS"
    assert result["customer_signup_end_to_end_verified"] is False
    assert result["database_backup_cold_restore_verified"] is False
    assert len(conn.cur.statements)==4


@pytest.mark.parametrize("responses",[
    answers(role="postgres"),answers(path="public"),
    answers(ssl=False),answers(priv=(True,False,False,False)),
    answers(grants=(True,True,True,True)),
    # Accidental broad UPDATE grant to vowsig_accounts is a fail-closed denial.
    answers(grants=(True,False,True,True)),
    answers(writes=(True,False,False)),
])
def test_mismatched_target_or_role_privileges_never_pass(responses):
    with pytest.raises(ra.PgAcceptanceError):
        ra.inspect_authenticated_app_connection(Connection(responses))


def test_dsn_policy_never_discloses_credentials(tmp_path):
    ca=tmp_path/"ca.pem"
    ca.write_text("not a real CA")
    dsns=[
        "postgresql://vowsig_app:secret@localhost:5432/railway?sslmode=verify-full",
        "postgresql://postgres:secret@postgres.railway.internal/railway?sslmode=verify-full",
        "postgresql://vowsig_app:secret@postgres.railway.internal/railway?sslmode=require",
        "postgresql://vowsig_app:secret@postgres.railway.internal/railway?sslmode=verify-full",
    ]
    for dsn in dsns:
        with pytest.raises(ra.PgAcceptanceError) as exc:
            ra.validate_private_runtime_dsn(dsn,ca_file=ca)
        assert "secret" not in str(exc.value)
