"""EXP040 Windows VPS-only, single-invocation SYNTHETIC S3/B2 operator.

Current revision: OFFLINE TEST ONLY. The --cloud-pilot CLI flag is HARD
DISABLED before any prompt, SDK import, client construction or provider call.
A separate exact-SHA change and owner approval are required to activate it.

Not production code. Never run against a real application/market database.
No task installation, secrets file, .env, subprocess, retry, or SDK dependency
in offline mode. No provider SDK is needed for offline tests.
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Any

from trading_signal_intelligence.recovery import b3_synthetic_encrypted_offsite_v0_1 as b3
from trading_signal_intelligence.recovery import b4_synthetic_s3_pilot_v0_1 as b4
from trading_signal_intelligence.recovery import b5_synthetic_s3_call_boundary_v0_1 as b5

# Imports only the existing synthetic fixture/fake clients, not real data.
if __package__:
    from scripts import exp038_offline_synthetic_pilot as offline
else:
    import exp038_offline_synthetic_pilot as offline

# This is a compilation/activation block, not a user-overridable setting.
# A later separately approved and tested GitHub patch is REQUIRED to change it.
REAL_PROVIDER_REQUESTS_ENABLED = False
CLOUD_APPROVAL_PHRASE = "OWNER_APPROVED_EXP040_ONE_SHOT_VPS_SYNTHETIC_ONLY"
ALLOWED_MODES = ("--offline-only", "--cloud-pilot")


class OperatorRejected(RuntimeError):
    """Fixed refusal; do not pass through secret-containing SDK exceptions."""


@dataclass(frozen=True, repr=False)
class Credential:
    access_key_id: str
    secret_access_key: str

    def __post_init__(self) -> None:
        for value in (self.access_key_id, self.secret_access_key):
            if (not isinstance(value, str) or not 8 <= len(value) <= 256
                    or value.strip() != value
                    or any(ord(ch) < 33 or ord(ch) > 126 for ch in value)):
                raise OperatorRejected("invalid masked credential input")

    def __repr__(self) -> str:
        return "<redacted credential>"


def _require_interactive_windows_console() -> None:
    # This is intended for the owner's manually operated Windows VPS RDP.
    # Do not allow a noninteractive pipe to trigger getpass fallback echo.
    if os.name != "nt" or not sys.stdin.isatty() or not sys.stderr.isatty():
        raise OperatorRejected("interactive Windows RDP console required")


def _masked_credentials(label: str, reader: Callable[[str], str]) -> Credential:
    # Prompt the ID too (not only the secret); never print any returned value.
    try:
        access = reader(f"{label} access key ID (masked): ")
        secret = reader(f"{label} secret access key (masked): ")
        return Credential(access_key_id=access, secret_access_key=secret)
    except (EOFError, KeyboardInterrupt):
        raise OperatorRejected("credential entry cancelled") from None


def _construct_explicit_boto3_client(provider: b4.Provider, cred: Credential) -> Any:
    """Future-only: construct explicit-credential SigV4 client, NO request.

    Kept unreachable from published CLI because REAL_PROVIDER_REQUESTS_ENABLED
    is False. No boto3/botocore import occurs for --offline-only/--cloud-pilot.
    """
    if not REAL_PROVIDER_REQUESTS_ENABLED:
        raise OperatorRejected("real cloud client construction not authorized")
    if provider not in (b4.AWS, b4.B2):
        raise OperatorRejected("unapproved provider")
    try:
        import boto3  # optional in future separately approved ISOLATED VPS env
        from botocore.config import Config

        config = Config(
            region_name=provider.region,
            signature_version="s3v4",
            retries={"mode": "standard", "total_max_attempts": 1},
            connect_timeout=5,
            read_timeout=10,
            max_pool_connections=1,
            s3={"addressing_style": "path", "payload_signing_enabled": True},
            proxies={},
        )
        # Session/client MUST receive explicit credentials, never search for
        # a default profile, ambient AWS_* env or instance-role credentials.
        session = boto3.session.Session(
            aws_access_key_id=cred.access_key_id,
            aws_secret_access_key=cred.secret_access_key,
            region_name=provider.region,
        )
        client = session.client(
            "s3",
            endpoint_url=provider.endpoint,
            region_name=provider.region,
            aws_access_key_id=cred.access_key_id,
            aws_secret_access_key=cred.secret_access_key,
            config=config,
            verify=True,
        )
        b4._check_client(client, provider)
        return client
    except OperatorRejected:
        raise
    except Exception:
        raise OperatorRejected("provider client creation failed") from None


def _synthetic_inputs(root: Path) -> tuple[Path, b3.SealedSynthetic, bytes]:
    # The only source is a NEW, explicitly marked local disposable fixture.
    copied = offline._create_disposable_synthetic_fixture(root)
    key = os.urandom(32)  # synthetic-only ephemeral key, no key file
    obj = b3.seal_captured_synthetic_s02(
        root, copied, artifact_id="exp040", key=key
    )
    if len(obj.envelope) > b4.MAX_ENVELOPE_BYTES:
        raise OperatorRejected("synthetic ciphertext size gate failed")
    return copied, obj, key


def _run_pilot_with_clients(
    root: Path, copied: Path, obj: b3.SealedSynthetic, key: bytes,
    aws_writer: Any, aws_reader: Any, b2_writer: Any, b2_reader: Any,
) -> tuple[dict, list[str], list[str]]:
    # The B5 wrappers add role, object, argument and call-order checks
    # to B4's fixed five-method budget and independent restore checks.
    aw, ar, ag = b5.guard_pair(b4.AWS, aws_writer, aws_reader, obj)
    bw, br, bg = b5.guard_pair(b4.B2, b2_writer, b2_reader, obj)
    result = b4.run_two_provider_pilot(
        fixture_root=root, captured_source=copied,
        obj=obj, key=key, aws_writer=aw, aws_reader=ar,
        b2_writer=bw, b2_reader=br,
        network_approved=True, approval_phrase=b4.APPROVAL_PHRASE,
    )
    if (result.get("status") != "SYNTHETIC_ONLY_TWO_REMOTE_PROVIDER_RESTORES"
            or result.get("actual_attempted_requests") != 5
            or ag.calls != ["PUT", "GET"]
            or bg.calls != ["HEAD", "PUT", "GET"]):
        raise OperatorRejected("synthetic restore or S3 method budget failed")
    return result, ag.calls, bg.calls


def offline_preflight() -> dict:
    """Safe on VPS without credentials or provider SDK. Five FAKE calls only."""
    with tempfile.TemporaryDirectory(prefix="vowsig-b1b2-fixture-exp040-") as folder:
        root = Path(folder)
        copied, obj, key = _synthetic_inputs(root)
        aws = offline._MemoryStore(b4.AWS)
        b2 = offline._MemoryStore(b4.B2)
        result, acalls, bcalls = _run_pilot_with_clients(
            root, copied, obj, key,
            offline._MemoryClient(aws, role="writer"),
            offline._MemoryClient(aws, role="reader"),
            offline._MemoryClient(b2, role="writer"),
            offline._MemoryClient(b2, role="reader"),
        )
        if (len(aws.objects) != 1 or len(b2.objects) != 1
                or aws.calls != acalls or b2.calls != bcalls
                or len(result["receipts"]) != 2):
            raise OperatorRejected("offline synthetic fake provider mismatch")
        return {
            "status": "EXP040_OFFLINE_VPS_OPERATOR_PASS",
            "mode": "DISPOSABLE_FAKE_S3_ONLY",
            "fake_s3_method_calls": 5,
            "independent_synthetic_restores": 2,
            "actual_provider_requests": 0,
            "credential_prompts": 0,
            "cloud_mode_enabled": False,
            "real_data_reads": 0,
            "production_modified": False,
        }


def cloud_pilot(*, phrase: str = "", prompt_fn: Callable[[str], str] | None = None) -> dict:
    """UNREACHABLE until separately reviewed source activation.

    Gate FIRST: even correct phrase, --cloud-pilot and stored credentials
    do nothing in this exact revision. Any later activation must additionally
    obtain fresh owner authorization and validate provider billing conditions.
    """
    if not REAL_PROVIDER_REQUESTS_ENABLED:
        raise OperatorRejected("cloud pilot DISABLED; requires separate approved revision")
    if phrase != CLOUD_APPROVAL_PHRASE:
        raise OperatorRejected("missing explicit cloud authorization")
    _require_interactive_windows_console()
    reader = prompt_fn if prompt_fn is not None else getpass.getpass
    with tempfile.TemporaryDirectory(prefix="vowsig-b1b2-fixture-exp040-") as folder:
        root = Path(folder)
        copied, obj, key = _synthetic_inputs(root)
        credentials = (
            _masked_credentials("AWS writer", reader),
            _masked_credentials("AWS reader", reader),
            _masked_credentials("B2 writer", reader),
            _masked_credentials("B2 reader", reader),
        )
        # Four distinct SDK clients, four restricted roles. Real calls would
        # need a separate approved source activation, request-level security
        # proof and explicit owner approval. No automatic retry or deletion.
        try:
            pairs = (
                _construct_explicit_boto3_client(b4.AWS, credentials[0]),
                _construct_explicit_boto3_client(b4.AWS, credentials[1]),
                _construct_explicit_boto3_client(b4.B2, credentials[2]),
                _construct_explicit_boto3_client(b4.B2, credentials[3]),
            )
            result, acalls, bcalls = _run_pilot_with_clients(
                root, copied, obj, key, *pairs
            )
            return {
                "status": "SYNTHETIC_ONLY_TWO_REMOTE_PROVIDER_RESTORES",
                "aws_s3_sdk_method_attempts": len(acalls),
                "b2_s3_sdk_method_attempts": len(bcalls),
                "restored_synthetic_objects": len(result["receipts"]),
                "real_application_backup_verified": False,
            }
        except Exception:
            # Deliberately suppress entire SDK/provider exception chain.
            raise OperatorRejected("one-time synthetic cloud pilot STOPPED") from None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="VPS only; cloud-pilot mode compiled DISABLED"
    )
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--offline-only", action="store_true")
    modes.add_argument("--cloud-pilot", action="store_true")
    args = parser.parse_args(argv)
    if args.cloud_pilot:
        # Call cloud_pilot() only after actual future activation; in this
        # version it deterministically rejects before any prompt/import.
        cloud_pilot()
        return 0
    print(json.dumps(offline_preflight(), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except OperatorRejected:
        # Fixed sanitized message; do not reveal Python/provider exceptions.
        print("EXP040_FINAL=STOPPED; CLOUD_REQUESTS=NONE", file=sys.stderr)
        raise SystemExit(2) from None
