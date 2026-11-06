"""Static-only production operator review. NEVER executes this operator in CI."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "ops/handoffs/vowsig_production_pg18_one_transaction_accounts_001_010_20261106.sh"


def test_ten_exact_migrations_in_one_sql_transaction():
    script = SCRIPT.read_text()
    sources = sorted((ROOT / "sql/accounts").glob("0??_*.sql"))
    assert len(sources) == 10
    for source in sources:
        path = source.relative_to(ROOT).as_posix()
        content = source.read_text().strip()
        if source.name.startswith("010_"):
            assert content.count("\nBEGIN;\n") == 1
            assert content.endswith("\nCOMMIT;")
            content = content.replace("\nBEGIN;\n", "\n", 1)
            content = content[:-len("\nCOMMIT;")].strip()
            assert f"-- START_EXACT_MIGRATION {path}\n{content}\n-- END_EXACT_MIGRATION {path}" in script
        else:
            assert f"-- SOURCE: {path}\n{content}" in script
    assert len(re.findall(r"^BEGIN;$", script, flags=re.MULTILINE)) == 1
    assert len(re.findall(r"^COMMIT;$", script, flags=re.MULTILINE)) == 1
    assert "PROD_VOWSIG_001_010_COMMITTED=PASS" in script


def test_prod_pins_and_private_restricted_role_guards():
    script = SCRIPT.read_text()
    for constraint in (
        "positioning-engine-cron", "RAILWAY_ENVIRONMENT_NAME",
        "RAILWAY_SERVICE_NAME", "'Postgres'",
        "postgres.railway.internal", "42574eca8c9afa481beefb2c3ea6b508bcd3e6c27e1b287d20274d72458e9526",
        "ALREADY_CONFIGURED_OR_PARTIAL_STATE_HOLD_NO_RERUN",
        "CREATE SCHEMA vowsig AUTHORIZATION vowsig_migrator",
        "CREATE ROLE vowsig_app LOGIN PASSWORD",
        "CREATE ROLE vowsig_migrator LOGIN PASSWORD",
        "CREATE ROLE vowsig_backup LOGIN PASSWORD",
        "NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS",
        "SET ROLE vowsig_migrator",
        "has_table_privilege('vowsig_app','vowsig.vowsig_accounts','UPDATE')",
        "has_column_privilege('vowsig_app','vowsig.vowsig_owner_totp_credentials','secret_ciphertext','UPDATE')",
        "vowsig_owner_actor_policy_check",
        "PRODUCTION_ACCOUNT_FEATURE_ENABLED=NO",
    ):
        assert constraint in script
    assert "TRADING_PUBLISHER_OR_WEB_CHANGED=NO" in script
    assert "\\getenv app_password VOWSIG_APP_ROLE_PASSWORD" in script
    assert "\\getenv migrator_password VOWSIG_MIGRATOR_ROLE_PASSWORD" in script
    assert "\\getenv backup_password VOWSIG_BACKUP_ROLE_PASSWORD" in script
    assert "read -r -s VOWSIG_APP_ROLE_PASSWORD </dev/tty" in script
    assert "INIT_PROD_VOWSIG_001_010" in script
    assert "sslmode=disable" not in script
    assert "DROP TABLE" not in script.upper()
    assert "DROP SCHEMA" not in script.upper()


def test_production_app_role_tls_acceptance_is_read_only_pinned_and_private():
    script_path = ROOT / "ops/handoffs/vowsig_production_app_role_tls_readonly_20261106.sh"
    script = script_path.read_text()
    ca = (ROOT / "config/tls/railway-postgres-root-ca-20261104.pem").read_text().strip()
    assert ca + "\\nVOWSIG_PINNED_PUBLIC_CA" not in script  # escaped literal cannot match
    assert ca + "\nVOWSIG_PINNED_PUBLIC_CA" in script
    assert "2de2743af645b4ea1780ff9f333bc7e25c1897483ac462ebc8756b4fab11baa8" in script
    for required in (
        "positioning-engine-cron",
        "RAILWAY_ENVIRONMENT_NAME",
        "RAILWAY_SERVICE_NAME",
        '"Postgres"',
        "postgres.railway.internal",
        "sslmode=verify-full",
        "user=vowsig_app",
        "BEGIN READ ONLY;",
        "ROLLBACK;",
        "PRIVATE_DNS_VERIFY_FULL=PASS",
        "PRODUCTION_DATABASE_WRITES=NONE",
    ):
        assert required in script
    assert "read -r -s APP_ROLE_PASSWORD < /dev/tty" in script
    assert "CREATE ROLE" not in script
    assert "CREATE TABLE" not in script
    assert "DROP TABLE" not in script
    assert "PRODUCTION_WEB_APP_DEPLOYED=NO" in script
