"""Staging 001-009 SQL must exactly match immutable repo sources, no credentials."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"ops/handoffs/vowsig_staging_pg18_migrate_all_001_009_v0_1.sh"
NAMES=["001_accounts_sessions_entitlements_watchlist.sql","002_verified_identity_binding.sql","003_preferences_and_saved_research.sql","004_research_read_model_contract.sql","005_consent_audit_deletion_requests.sql","006_oidc_auth_transactions.sql","007_restricted_roles_and_grants.sql","008_owner_mfa_stepup.sql","009_owner_offline_provisioning_audit.sql"]
def test_migration_operator_uses_exact_git_repo_source_sql():
    body=SCRIPT.read_text()
    for i,filename in enumerate(NAMES):
        marker="-- SOURCE: sql/accounts/"+filename+"\n"
        assert body.count(marker)==1
        source=(ROOT/"sql/accounts"/filename).read_text().rstrip()+"\n"
        after=body.split(marker,1)[1]
        assert after.startswith(source),filename
    assert [body.index("-- SOURCE: sql/accounts/"+p) for p in NAMES]==sorted(
           body.index("-- SOURCE: sql/accounts/"+p) for p in NAMES)
def test_atomic_scope_and_read_write_denials():
    body=SCRIPT.read_text()
    assert "BEGIN;" in body and "COMMIT;" in body
    assert body.index("BEGIN;")<body.index("SET ROLE vowsig_migrator;")
    assert body.index("SET ROLE vowsig_migrator;")<body.index("-- SOURCE: sql/accounts/001_")
    assert body.index("-- SOURCE: sql/accounts/009_")<body.index("COMMIT;")
    assert "ON_ERROR_STOP=1" in body and "<<'VOWSIG_SQL'" in body
    for item in ('vowsig-staging-20261105','vowsig-staging-pg18','vowsig_staging',
                 'vowsig_staging_admin','current_setting(\'ssl\')',
                 'vowsig_research_outcome_facts','secret_ciphertext','backup_writes=DENIED'):
        assert item in body
    assert "postgres.railway.internal" not in body
    assert "curl" not in body and "git clone" not in body and "POSTGRES_PASSWORD=" not in body
