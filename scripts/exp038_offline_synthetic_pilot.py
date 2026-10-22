"""EXP038 operator preflight: disposable SYNTHETIC SQLite + in-memory S3 ONLY.

No boto3, HTTP, socket, provider secrets, network client, credential loader,
persistent key file, CLI cloud mode, scheduler integration or VPS database reads.
The B4 explicit authorization interlock is supplied ONLY to fake memory clients.
To execute actual remote API requests would require A DIFFERENT owner-approved
operator driver; this script has no such capability.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace

from trading_signal_intelligence.recovery import b1b2_synthetic_v0_1 as b1
from trading_signal_intelligence.recovery import b3_synthetic_encrypted_offsite_v0_1 as b3
from trading_signal_intelligence.recovery import b4_synthetic_s3_pilot_v0_1 as b4

TEST_TIME_UTC = "2026-10-23T00:00:00+00:00"
OFFLINE_ONLY_FLAG = "--offline-only"


class OfflinePreflightRejected(RuntimeError):
    """Fixed error class; no provider credentials or internal data can be exposed."""


class _MemoryNotFound(Exception):
    response = {
        "Error": {"Code": "404"},
        "ResponseMetadata": {"HTTPStatusCode": 404},
    }


class _MemoryStore:
    def __init__(self, provider: b4.Provider) -> None:
        self.provider = provider
        self.objects: dict[str, tuple[bytes, str]] = {}
        self.calls: list[str] = []


class _MemoryClient:
    """A fake S3 interface. It CANNOT construct an HTTP request."""

    def __init__(self, store: _MemoryStore, *, role: str) -> None:
        if role not in ("writer", "reader"):
            raise OfflinePreflightRejected("invalid synthetic client role")
        self.store = store
        self.role = role
        self.meta = SimpleNamespace(
            endpoint_url=store.provider.endpoint,
            region_name=store.provider.region,
            config=SimpleNamespace(
                retries={"total_max_attempts": 1},
                signature_version="s3v4",
                connect_timeout=5,
                read_timeout=10,
            ),
        )

    def head_object(self, **kwargs: object) -> dict:
        if self.role != "reader" or kwargs.get("Bucket") != self.store.provider.bucket:
            raise OfflinePreflightRejected("forbidden fake head")
        key = kwargs.get("Key")
        self.store.calls.append("HEAD")
        if key in self.store.objects:
            return {"ResponseMetadata": {"HTTPStatusCode": 200}}
        raise _MemoryNotFound()

    def put_object(self, **kwargs: object) -> dict:
        if self.role != "writer" or kwargs.get("Bucket") != self.store.provider.bucket:
            raise OfflinePreflightRejected("forbidden fake put")
        key = kwargs.get("Key")
        body = kwargs.get("Body")
        if (not isinstance(key, str)
                or not isinstance(body, bytes)
                or kwargs.get("ContentLength") != len(body)
                or key in self.store.objects
                or (kwargs.get("IfNoneMatch") == "*") != (self.store.provider == b4.AWS)):
            raise OfflinePreflightRejected("invalid fake object or overwrite")
        self.store.calls.append("PUT")
        self.store.objects[key] = (body, "synthetic-offline-v1")
        return {"VersionId": "synthetic-offline-v1"}

    def get_object(self, **kwargs: object) -> dict:
        if self.role != "reader" or kwargs.get("Bucket") != self.store.provider.bucket:
            raise OfflinePreflightRejected("forbidden fake get")
        key = kwargs.get("Key")
        if not isinstance(key, str) or key not in self.store.objects:
            raise OfflinePreflightRejected("fake object unavailable")
        content, version = self.store.objects[key]
        if kwargs.get("VersionId") != version:
            raise OfflinePreflightRejected("wrong fake object version")
        self.store.calls.append("GET")
        return {"VersionId": version, "ContentLength": len(content),
                "Body": io.BytesIO(content)}


def _create_disposable_synthetic_fixture(root: Path) -> Path:
    if not root.name.startswith("vowsig-b1b2-fixture-"):
        raise OfflinePreflightRejected("invalid disposable fixture root")
    (root / b1.FIXTURE_FILE).write_text(b1.FIXTURE_MARKER, encoding="utf-8")
    source = root / "forward.sqlite"
    # sqlite3.Connection.__exit__ commits but does NOT close its file handle.
    # On Windows, an open handle prevents TemporaryDirectory cleanup (WinError 32).
    # Keep both the transactional context and deterministic close, even on errors.
    with closing(sqlite3.connect(source)) as con, con:
        con.execute(
            "CREATE TABLE vowsig_synthetic_fixture_only "
            "(synthetic_token TEXT NOT NULL)"
        )
        con.execute(
            "INSERT INTO vowsig_synthetic_fixture_only VALUES (?)",
            (b1.FIXTURE_MARKER.strip(),),
        )
        con.execute(
            "CREATE TABLE forward_records ("
            "sequence INTEGER PRIMARY KEY, record_id TEXT, record_type TEXT, "
            "entity_id TEXT, recorded_at_utc TEXT, effective_at_utc TEXT, "
            "payload_json TEXT, previous_hash TEXT, record_hash TEXT)"
        )
        prev = None
        for sequence in (1, 2):
            material = {
                "record_id": f"exp038-fake-{sequence}",
                "record_type": "ACTIVATION" if sequence == 1 else "NO_TRADE",
                "entity_id": f"fake-market-{sequence}",
                "recorded_at_utc": TEST_TIME_UTC,
                "effective_at_utc": TEST_TIME_UTC,
                "payload_json": json.dumps(
                    {"synthetic_only": True, "ordinal": sequence},
                    sort_keys=True, separators=(",", ":"),
                ),
                "previous_hash": prev,
            }
            record_hash = hashlib.sha256(b1.canonical_bytes(material)).hexdigest()
            con.execute(
                "INSERT INTO forward_records VALUES (?,?,?,?,?,?,?,?,?)",
                (sequence, *material.values(), record_hash),
            )
            prev = record_hash
    b1.capture_synthetic_set(
        root, [b1.SyntheticSpec("s02fake", "forward.sqlite", "S02")],
        set_id="set038",
    )
    return root / "captured" / "set038" / "forward.sqlite"


def run_offline_synthetic_preflight() -> dict:
    """Always fake in-memory providers, even when called from another module."""
    with tempfile.TemporaryDirectory(prefix="vowsig-b1b2-fixture-exp038-") as temp:
        root = Path(temp)
        copied = _create_disposable_synthetic_fixture(root)
        # Ephemeral key intentionally exists only during this invocation.
        key = os.urandom(32)
        artifact = b3.seal_captured_synthetic_s02(
            root, copied, artifact_id="exp038", key=key)
        if len(artifact.envelope) > b4.MAX_ENVELOPE_BYTES:
            raise OfflinePreflightRejected("synthetic envelope exceeds byte ceiling")

        aws_store, b2_store = _MemoryStore(b4.AWS), _MemoryStore(b4.B2)
        # The B4 interlock is for in-process fake clients ONLY:
        # no code path here constructs a remote client or accesses credentials.
        result = b4.run_two_provider_pilot(
            fixture_root=root, captured_source=copied,
            obj=artifact, key=key,
            aws_writer=_MemoryClient(aws_store, role="writer"),
            aws_reader=_MemoryClient(aws_store, role="reader"),
            b2_writer=_MemoryClient(b2_store, role="writer"),
            b2_reader=_MemoryClient(b2_store, role="reader"),
            network_approved=True, approval_phrase=b4.APPROVAL_PHRASE,
        )
        if (result.get("status") != "SYNTHETIC_ONLY_TWO_REMOTE_PROVIDER_RESTORES"
                or result.get("actual_attempted_requests") != 5
                or len(aws_store.objects) != 1 or len(b2_store.objects) != 1
                or aws_store.calls != ["PUT", "GET"]
                or b2_store.calls != ["HEAD", "PUT", "GET"]
                or not (root / "restored" / "awsrestore" / "forward.sqlite").is_file()
                or not (root / "restored" / "b2restore" / "forward.sqlite").is_file()):
            raise OfflinePreflightRejected("fake two-provider recovery invariant failed")
        return {
            "status": "EXP038_OFFLINE_SYNTHETIC_PREFLIGHT_PASS",
            "mode": "IN_MEMORY_FAKE_PROVIDERS_ONLY",
            "remote_network_requests": 0,
            "actual_provider_calls": 0,
            "fake_provider_calls": 5,
            "aws_fake_calls": len(aws_store.calls),
            "b2_fake_calls": len(b2_store.calls),
            "independent_authenticated_restores": 2,
            "synthetic_records_per_restore": artifact.record_count,
            "max_cloud_object_bytes_by_future_adapter": b4.MAX_ENVELOPE_BYTES,
            "secrets_loaded": False,
            "real_vps_database_reads": 0,
            "real_cloud_spend": 0,
            "cloud_pilot_authorized": False,
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="EXP038 LOCAL IN-MEMORY ONLY, no provider network or secrets")
    parser.add_argument(
        OFFLINE_ONLY_FLAG, action="store_true",
        help="Run disposable in-memory fake-provider backup/restore checks",
    )
    args = parser.parse_args(argv)
    if args.offline_only is not True:
        parser.error("must pass --offline-only; there is no remote execution mode")
    output = run_offline_synthetic_preflight()
    print(json.dumps(output, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
