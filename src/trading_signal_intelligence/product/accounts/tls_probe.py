"""Read-only PostgreSQL private-network TLS identity probe.

PostgreSQL SSLRequest handshake only. No startup packet, credentials, SQL,
database mutations, public proxy, or secret logging. An authentic PostgreSQL
libpq/psycopg `sslmode=verify-full` connection is still required for release.

Run in the Railway *application* Console once this candidate is installed:
  python -m trading_signal_intelligence.product.accounts.tls_probe
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import socket
import ssl
import struct

TARGET = "postgres.railway.internal"
CA_FILE = Path("/app/config/tls/railway-postgres-root-ca-20261104.pem")
EXPECTED_CA_SHA256 = "2de2743af645b4ea1780ff9f333bc7e25c1897483ac462ebc8756b4fab11baa8"
SSL_REQUEST = struct.pack("!II", 8, 80877103)


class TlsIdentityError(RuntimeError):
    pass


def verify_ca_pem(pem: str) -> str:
    """Refuse a changed/incorrect root before trusting it for private DNS."""
    if "PRIVATE KEY" in pem:
        raise TlsIdentityError("CA input cannot contain private key material")
    try:
        cert = ssl.PEM_cert_to_DER_cert(pem)
    except (ValueError, ssl.SSLError) as exc:
        raise TlsIdentityError("Invalid public CA PEM") from exc
    digest = hashlib.sha256(cert).hexdigest()
    if digest != EXPECTED_CA_SHA256:
        raise TlsIdentityError("Pinned PostgreSQL CA fingerprint mismatch")
    return digest


def probe(*, ca_file: Path = CA_FILE, host: str = TARGET, port: int = 5432) -> dict[str, str]:
    if host != TARGET or type(port) is not int or not 1 <= port <= 65535:
        raise TlsIdentityError("Refusing unreviewed private target")
    cert_pem = ca_file.read_text(encoding="ascii")
    root_sha = verify_ca_pem(cert_pem)
    context = ssl.create_default_context(cadata=cert_pem)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.verify_mode = ssl.CERT_REQUIRED
    context.check_hostname = True
    with socket.create_connection((host, port), timeout=6) as raw:
        raw.settimeout(6)
        raw.sendall(SSL_REQUEST)
        if raw.recv(1) != b"S":
            raise TlsIdentityError("Server refused PostgreSQL TLS negotiation")
        with context.wrap_socket(raw, server_hostname=host) as tls:
            # SSL handshake performs full CA chain + private-DNS hostname checks.
            cert = tls.getpeercert()
            if not cert:
                raise TlsIdentityError("Peer certificate not verified")
            peer_der = tls.getpeercert(binary_form=True)
            return {
                "status": "PASS",
                "target": host,
                "tls_version": tls.version() or "unknown",
                "trusted_root_sha256": root_sha,
                "peer_leaf_sha256": hashlib.sha256(peer_der).hexdigest(),
            }


def main() -> None:
    try:
        result = probe(port=int(os.getenv("PGPORT", "5432")))
    except (OSError, ValueError, ssl.SSLError, TlsIdentityError) as exc:
        # Do not print environment values, database DSNs, or private keys.
        print("VOWSIG_APP_NETWORK_TLS_IDENTITY=FAIL")
        print("REASON_TYPE=" + type(exc).__name__)
        raise SystemExit(1) from None
    print("VOWSIG_APP_NETWORK_TLS_IDENTITY=PASS")
    for key in ("target", "tls_version", "trusted_root_sha256", "peer_leaf_sha256"):
        print(key.upper() + "=" + result[key])


if __name__ == "__main__":
    main()
