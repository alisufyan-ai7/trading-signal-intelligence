"""Strict staging-only PostgreSQL SSLRequest + authenticated read-only SQL proof.

Uses an independently owner-supplied PUBLIC root CA pinned by SHA256 and the
observed staging TLS leaf fingerprint. No production host, account mutations,
credentials in output, user records, or feature activation.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import socket
import ssl
import struct
from urllib.parse import parse_qs, urlsplit

CA_FILE=Path("/app/config/tls/railway-staging-pg-root-ca-20261105.pem")
CA_SHA256="b8caee0016fc06dafa6251212717a9d536216a1ccd8a8754deaf6a68d5dc0441"
LEAF_SHA256="aa98817c212a1b080fa6af1a96691fb5e4ad878231d6e477faeb381a0febc7f0"
HOST="vowsig-staging-pg18.railway.internal"
PORT=5432
_DB="vowsig_staging"
_EXPECTED_ENV={
    "RAILWAY_PROJECT_ID":"58dc28d4-af4a-45b3-b82c-ab4dbb34cf8f",
    "RAILWAY_ENVIRONMENT_ID":"c197637f-a9ab-4a1a-875f-4de65ee14f9e",
    "RAILWAY_SERVICE_ID":"557de60f-97b8-4512-be7b-55e63932b95d",
    "RAILWAY_PROJECT_NAME":"vowsig-staging-20261105",
    "RAILWAY_ENVIRONMENT_NAME":"staging",
    "RAILWAY_SERVICE_NAME":"vowsig-pr93-staging-app",
    "VOWSIG_ACCOUNTS_FOUNDATION_ENABLED":"0",
    "VOWSIG_OIDC_AUTH_ENABLED":"0",
}
_SSL_REQUEST=struct.pack("!II",8,80877103)


class StagingAcceptanceHold(ValueError):
    """No credentials or raw provider/network errors in messages."""


def public_ca_pem(path: Path=CA_FILE) -> str:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding, rsa

    if path.is_symlink() or not path.is_file() or not 500<=path.stat().st_size<16000:
        raise StagingAcceptanceHold("Staging public CA missing or not regular")
    try:
        pem=path.read_text(encoding="ascii")
        if pem.count("-----BEGIN CERTIFICATE-----")!=1 or "PRIVATE KEY" in pem:
            raise StagingAcceptanceHold("Root CA must be one public certificate")
        cert=x509.load_pem_x509_certificate(pem.encode("ascii"))
        if (cert.fingerprint(hashes.SHA256()).hex()!=CA_SHA256
            or cert.subject!=cert.issuer
            or not cert.extensions.get_extension_for_class(
                x509.BasicConstraints).value.ca
            or not isinstance(cert.public_key(),rsa.RSAPublicKey)
            or cert.public_key().key_size<2048):
            raise StagingAcceptanceHold("Untrusted staging public root certificate")
        now=datetime.now(timezone.utc)
        if not cert.not_valid_before_utc<=now<=cert.not_valid_after_utc:
            raise StagingAcceptanceHold("Staging root expired or not yet valid")
        cert.public_key().verify(
            cert.signature,cert.tbs_certificate_bytes,
            padding.PKCS1v15(),cert.signature_hash_algorithm,
        )
    except StagingAcceptanceHold:
        raise
    except Exception as exc:
        raise StagingAcceptanceHold("Malformed or invalid pinned public root") from exc
    return pem


def require_staging_runtime(environ: dict[str,str]) -> str:
    if any(environ.get(k)!=v for k,v in _EXPECTED_ENV.items()):
        raise StagingAcceptanceHold("Wrong Railway environment or account flags")
    dsn=environ.get("VOWSIG_ACCOUNTS_DATABASE_URL","")
    if not isinstance(dsn,str) or not 65<=len(dsn)<=8192:
        raise StagingAcceptanceHold("Missing restricted database connection")
    try:
        p=urlsplit(dsn)
        query=parse_qs(p.query,strict_parsing=True,keep_blank_values=True)
        if (p.scheme!="postgresql" or p.hostname!=HOST or p.port!=PORT
            or p.username!="vowsig_app" or not p.password or p.path!="/"+_DB
            or p.fragment or p.query.count("sslmode=")!=1
            or p.query.count("sslrootcert=")!=1 or set(query)!={"sslmode","sslrootcert"}
            or query["sslmode"]!=["verify-full"]
            or query["sslrootcert"]!=[str(CA_FILE)]):
            raise StagingAcceptanceHold("Unapproved PostgreSQL user/host/TLS parameters")
    except (TypeError,ValueError) as exc:
        raise StagingAcceptanceHold("Invalid private staging SQL connection") from exc
    return dsn


def verify_peer(pem: str, *, host: str=HOST, port: int=PORT) -> dict[str,str]:
    if host!=HOST or port!=PORT or type(port) is not int:
        raise StagingAcceptanceHold("Unapproved TLS network destination")
    ctx=ssl.create_default_context(cadata=pem)
    ctx.minimum_version=ssl.TLSVersion.TLSv1_2
    ctx.check_hostname=True
    ctx.verify_mode=ssl.CERT_REQUIRED
    try:
        with socket.create_connection((host,port),timeout=6) as raw:
            raw.settimeout(6)
            raw.sendall(_SSL_REQUEST)
            if raw.recv(1)!=b"S":
                raise StagingAcceptanceHold("PostgreSQL SSL negotiation rejected")
            with ctx.wrap_socket(raw,server_hostname=host) as tls:
                cert=tls.getpeercert(binary_form=True)
                if not cert or hashlib.sha256(cert).hexdigest()!=LEAF_SHA256:
                    raise StagingAcceptanceHold("Staging server leaf pin mismatch")
                return {"host":host,"tls_version":tls.version() or "unknown"}
    except StagingAcceptanceHold:
        raise
    except Exception as exc:
        raise StagingAcceptanceHold("Verified private PostgreSQL TLS unavailable") from exc


def inspect_staging(*, environ: dict[str,str], ca_file: Path=CA_FILE)->dict[str,object]:
    dsn=require_staging_runtime(environ)
    pem=public_ca_pem(ca_file)
    peer=verify_peer(pem)
    try:
        import psycopg
        from trading_signal_intelligence.product.accounts.railway_pg_acceptance import (
            inspect_authenticated_app_connection,
        )
        with psycopg.connect(dsn,connect_timeout=5) as conn:
            conn.execute("SET TRANSACTION READ ONLY")
            receipt=inspect_authenticated_app_connection(conn)
    except Exception as exc:
        raise StagingAcceptanceHold("Authenticated restricted staging SQL unavailable") from exc
    if receipt.get("status")!="AUTHENTICATED_APP_ROLE_RESTRICTED_SQL_READ_ONLY_PASS":
        raise StagingAcceptanceHold("Restricted SQL role privileges not accepted")
    return {
        "status":"STAGING_PRIVATE_TLS_AND_RESTRICTED_SQL_PASS",
        "environment":"staging",
        "verified_hostname":HOST,
        "tls_version":peer["tls_version"],
        "root_ca_sha256":CA_SHA256,
        "leaf_sha256":LEAF_SHA256,
        "role":"vowsig_app",
        "sql_read_only":True,
        "owner_mfa_and_customer_signup_tested":False,
        "auth0_real_email_tested":False,
        "production_modified":False,
    }


def main()->int:
    try:
        receipt=inspect_staging(environ=dict(os.environ))
    except StagingAcceptanceHold as exc:
        # All custom messages are fixed code literals, never provider replies.
        print("VOWSIG_STAGING_TLS_AND_RESTRICTED_SQL=HOLD")
        print("HOLD_REASON="+str(exc))
        print("ACCOUNT_FEATURES_MUST_REMAIN_DISABLED=YES")
        return 1
    except Exception:
        print("VOWSIG_STAGING_TLS_AND_RESTRICTED_SQL=HOLD")
        print("HOLD_REASON=Unexpected validation failure")
        print("ACCOUNT_FEATURES_MUST_REMAIN_DISABLED=YES")
        return 1
    print("VOWSIG_STAGING_TLS_AND_RESTRICTED_SQL=PASS")
    print("HOST="+receipt["verified_hostname"])
    print("TLS_VERSION="+receipt["tls_version"])
    print("ROLE=vowsig_app")
    print("REAL_AUTH0_SIGNUP_EMAIL_AND_OWNER_MFA_TESTED=NO")
    print("PRODUCTION_MODIFIED=NO")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
