"""Public root and environment-bound STAGING TLS/SQL contract tests, no network."""
from pathlib import Path
import hashlib
import ssl

import pytest

from trading_signal_intelligence.product.accounts import staging_pg_acceptance as st

ROOT=Path(__file__).resolve().parents[1]
CA=ROOT/"config/tls/railway-staging-pg-root-ca-20261105.pem"
TEST_DSN=(
    "postgresql://vowsig_app:TEST_ONLY_NO_PROVIDER_SECRET@"
    "vowsig-staging-pg18.railway.internal:5432/vowsig_staging"
    "?sslmode=verify-full&sslrootcert="
    "/app/config/tls/railway-staging-pg-root-ca-20261105.pem"
)

def env(dsn=TEST_DSN):
    return {**st._EXPECTED_ENV,"VOWSIG_ACCOUNTS_DATABASE_URL":dsn}

def test_staging_root_exact_public_digest_and_self_signature():
    pem=st.public_ca_pem(CA)
    assert st.CA_SHA256=="b8caee0016fc06dafa6251212717a9d536216a1ccd8a8754deaf6a68d5dc0441"
    assert hashlib.sha256(ssl.PEM_cert_to_DER_cert(pem)).hexdigest()==st.CA_SHA256
    assert st.HOST=="vowsig-staging-pg18.railway.internal"
    assert st.LEAF_SHA256=="aa98817c212a1b080fa6af1a96691fb5e4ad878231d6e477faeb381a0febc7f0"
    assert st.CA_FILE==Path("/app/config/tls/railway-staging-pg-root-ca-20261105.pem")

def test_invalid_ca_fails_before_network(tmp_path):
    c=tmp_path/"wrong.pem"
    c.write_text(CA.read_text().replace("MIIDBTCCAe2g","MIIDBTCCAe2h"))
    with pytest.raises(st.StagingAcceptanceHold):
        st.public_ca_pem(c)
    c.write_text(CA.read_text()+"-----BEGIN PRIVATE KEY-----")
    with pytest.raises(st.StagingAcceptanceHold):
        st.public_ca_pem(c)

def test_exact_identity_tls_and_restricted_role():
    assert st.require_staging_runtime(env())==TEST_DSN
    assert st._EXPECTED_ENV["VOWSIG_ACCOUNTS_FOUNDATION_ENABLED"]=="0"
    assert st._EXPECTED_ENV["VOWSIG_OIDC_AUTH_ENABLED"]=="0"

@pytest.mark.parametrize("mutation",[
    ("RAILWAY_PROJECT_ID","af8ed976-9971-4f5a-a304-3d8984df1565"),
    ("RAILWAY_SERVICE_NAME","Postgres"),
    ("VOWSIG_ACCOUNTS_FOUNDATION_ENABLED","1"),
    ("VOWSIG_OIDC_AUTH_ENABLED","1"),
])
def test_other_environment_or_enabled_account_refused(mutation):
    d=env()
    d[mutation[0]]=mutation[1]
    with pytest.raises(st.StagingAcceptanceHold):
        st.require_staging_runtime(d)

@pytest.mark.parametrize("dsn",[
    TEST_DSN.replace("vowsig_app","vowsig_staging_admin"),
    TEST_DSN.replace("vowsig-staging-pg18","postgres"),
    TEST_DSN.replace("verify-full","require"),
    TEST_DSN.replace("/vowsig_staging?","/railway?"),
    TEST_DSN+"&sslmode=disable",
    TEST_DSN.replace("postgresql://","http://"),
    TEST_DSN.replace("/app/config/tls/railway-staging-pg-root-ca-20261105.pem",
                     "/app/config/tls/railway-postgres-root-ca-20261104.pem"),
])
def test_bad_user_db_tls_root_and_scheme_refused(dsn):
    with pytest.raises(st.StagingAcceptanceHold) as exc:
        st.require_staging_runtime(env(dsn))
    assert "TEST_ONLY" not in str(exc.value)

def test_no_prod_or_network_probe_from_wrong_host():
    with pytest.raises(st.StagingAcceptanceHold):
        st.verify_peer(st.public_ca_pem(CA),host="postgres.railway.internal")

def test_docker_image_packs_only_public_staging_certificate():
    content=(ROOT/"Dockerfile").read_text()
    assert "COPY config ./config" in content
    assert CA.is_file()
    assert "PRIVATE KEY" not in CA.read_text()
