"""Reviewable fixed-target, explicit-only four-client AWS/B2 SDK factory.

No default-provider credential discovery, no environment files, no network on
import. Real creation is COMPILED OFF until separate release evidence is
verified and exact-source manual activation is approved. Never log secrets.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from importlib import metadata
from typing import Any

from . import live_dual_provider_transport_v0_1 as transport

REAL_CLIENT_CREATION_ENABLED = False
PINNED = {
    "boto3": "1.43.114",
    "botocore": "1.43.114",
    "jmespath": "1.0.1",
    "s3transfer": "0.19.3",
    "python-dateutil": "2.9.0.post0",
    "urllib3": "2.8.0",
    "six": "1.17.0",
}


class ExplicitClientRejected(RuntimeError):
    """Fixed exception; never stringify sensitive input or SDK exceptions."""


@dataclass(frozen=True, repr=False)
class EphemeralS3Credential:
    access_id: str = field(repr=False)
    secret: str = field(repr=False)

    def __repr__(self) -> str:
        return "<EphemeralS3Credential REDACTED>"

    def validate(self) -> None:
        for value in (self.access_id, self.secret):
            if (type(value) is not str or not 8 <= len(value) <= 256
                    or any(ord(ch) < 33 or ord(ch) > 126 for ch in value)):
                raise ExplicitClientRejected("invalid masked identity input")


def construct_four_explicit_clients(
    *, aws_writer: EphemeralS3Credential,
    aws_reader: EphemeralS3Credential,
    b2_writer: EphemeralS3Credential,
    b2_reader: EphemeralS3Credential,
) -> tuple[Any, Any, Any, Any]:
    # No extra keyword, command flag or environment setting can bypass the
    # compiled-off gate; don't even import boto3 before exact release approval.
    if not REAL_CLIENT_CREATION_ENABLED:
        raise ExplicitClientRejected("real SDK client construction compiled OFF")
    credentials = (aws_writer, aws_reader, b2_writer, b2_reader)
    if not all(type(v) is EphemeralS3Credential for v in credentials):
        raise ExplicitClientRejected("four explicit provider identities required")
    for item in credentials:
        item.validate()
    if len({v.access_id for v in credentials}) != 4:
        raise ExplicitClientRejected("writer/reader account identities reused")
    try:
        if any(metadata.version(name) != pin for name, pin in PINNED.items()):
            raise ExplicitClientRejected("pinned SDK dependency mismatch")
        import boto3
        from botocore.config import Config
        result = []
        for provider, cred in zip(
            (transport.AWS, transport.AWS, transport.B2, transport.B2),
            credentials,
        ):
            config = Config(
                region_name=provider.region,
                signature_version="s3v4",
                retries={"mode": "standard", "total_max_attempts": 1},
                connect_timeout=5, read_timeout=10,
                max_pool_connections=1,
                s3={"addressing_style": "path",
                    "payload_signing_enabled": True},
                request_checksum_calculation="when_required",
                response_checksum_validation="when_required",
                proxies={},
            )
            session = boto3.session.Session(
                aws_access_key_id=cred.access_id,
                aws_secret_access_key=cred.secret,
                region_name=provider.region,
            )
            client = session.client(
                "s3", endpoint_url=provider.endpoint,
                region_name=provider.region,
                aws_access_key_id=cred.access_id,
                aws_secret_access_key=cred.secret,
                config=config, verify=True,
            )
            transport._client_checked(client, provider)
            result.append(client)
        return tuple(result)
    except Exception:
        raise ExplicitClientRejected("explicit fixed-target cloud client preparation failed") from None
