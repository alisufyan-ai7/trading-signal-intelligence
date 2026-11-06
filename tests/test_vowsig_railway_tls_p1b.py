"""Release gate: owner supplied public Railway CA pin and build availability."""
from __future__ import annotations

import hashlib
from pathlib import Path
import ssl

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes

from trading_signal_intelligence.product.accounts.tls_probe import (
    TARGET, SSL_REQUEST, TlsIdentityError, verify_ca_pem, probe
)

ROOT=Path(__file__).resolve().parents[1]
CA=ROOT/"config"/"tls"/"railway-postgres-root-ca-20261104.pem"
EXPECTED="2de2743af645b4ea1780ff9f333bc7e25c1897483ac462ebc8756b4fab11baa8"


def test_public_ca_is_exact_authenticated_owner_supplied_x509():
    pem=CA.read_text(encoding="ascii")
    assert pem.startswith("-----BEGIN CERTIFICATE-----\n")
    assert pem.count("-----BEGIN CERTIFICATE-----")==1
    assert "PRIVATE KEY" not in pem
    assert verify_ca_pem(pem)==EXPECTED
    public_der=ssl.PEM_cert_to_DER_cert(pem)
    assert hashlib.sha256(public_der).hexdigest()==EXPECTED
    cert=x509.load_pem_x509_certificate(pem.encode("ascii"))
    assert cert.fingerprint(hashes.SHA256()).hex()==EXPECTED
    assert cert.subject==cert.issuer
    assert cert.extensions.get_extension_for_class(x509.BasicConstraints).value.ca is True
    assert cert.not_valid_after_utc.isoformat()=="2029-02-01T12:51:46+00:00"


def test_private_dns_and_tls_handshake_always_strict():
    assert TARGET=="postgres.railway.internal"
    assert SSL_REQUEST==bytes.fromhex("0000000804d2162f")
    with pytest.raises(TlsIdentityError,match="fingerprint"):
        verify_ca_pem(CA.read_text().replace("MIIDBTCCAe2g", "MIIDBTCCAe2h"))
    with pytest.raises(TlsIdentityError,match="private key"):
        verify_ca_pem(CA.read_text()+"-----BEGIN PRIVATE KEY-----")
    with pytest.raises(TlsIdentityError,match="private target"):
        probe(ca_file=CA,host="localhost",port=5432)
    with pytest.raises(TlsIdentityError,match="private target"):
        probe(ca_file=CA,host=TARGET,port=0)


def test_release_dockerfile_packages_accounts_and_public_ca():
    docker=(ROOT/"Dockerfile").read_text()
    assert "COPY config ./config" in docker
    assert 'pip install --no-cache-dir -e ".[app,accounts]"' in docker
    assert CA.is_file()
