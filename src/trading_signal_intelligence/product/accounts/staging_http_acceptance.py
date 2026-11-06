"""VowSig pre-release and post-rollback staging HTTP read-only acceptance.

No login initiation, cookies, credentials, POST requests, bearer tokens,
secrets, provider calls or customer records. Deliberately refuses the
production domain. A PASS proves ONLY the listed uncredentialed HTTP
contracts at one instant; never asserts a rollback actually happened.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import re
from typing import Any
from urllib.parse import urlsplit


class StagingHttpHold(ValueError):
    """Fail closed without revealing response payloads or internal URLs."""


_ALLOWED_MARKETS = frozenset({
    "XAUUSD","USTEC","US30","EURUSD","XAGUSD","USOIL",
    "BTCUSDT","ETHUSDT","SOLUSDT",
})
_RESTRICTED = _ALLOWED_MARKETS - {"XAUUSD","USTEC","US30"}
_PROBE_PATHS = (
    "/healthz", "/api/health", "/api/v2/public/markets",
    "/api/v2/me", "/app/", "/admin/", "/api/v2/admin/performance",
)


def _validate_target(origin: str, expected_pin: str) -> str:
    if not isinstance(origin,str) or not 8<=len(origin)<=400:
        raise StagingHttpHold("Explicit staging origin required")
    if (not isinstance(expected_pin,str)
        or not re.fullmatch(r"[0-9a-f]{64}",expected_pin)
        or hashlib.sha256(origin.encode("utf-8")).hexdigest()!=expected_pin):
        raise StagingHttpHold("Staging origin independent pin mismatch")
    try:
        p=urlsplit(origin)
        host=p.hostname or ""
        port=p.port
    except ValueError as exc:
        raise StagingHttpHold("Staging endpoint invalid") from exc
    if (p.scheme!="https" or not host or
        p.username is not None or p.password is not None or
        p.path not in ("","/") or p.query or p.fragment or
        origin.endswith("/") or port not in (None,443) or
        host.lower() in ("vowsig.com","www.vowsig.com","api.vowsig.com") or
        host.lower() in ("localhost","127.0.0.1","::1") or
        re.fullmatch(r"[0-9.]+",host) or
        not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]{3,250}",host)):
        raise StagingHttpHold("Production or unapproved staging URL refused")
    return origin


def _read_json(response, *, label: str):
    if (response.status_code!=200 or response.is_redirect or
        not response.headers.get("content-type","").lower().startswith("application/json") or
        not 0<len(response.content)<65536):
        raise StagingHttpHold(label+" protected response refused")
    try:
        return json.loads(
            response.content,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
        )
    except (ValueError,UnicodeDecodeError) as exc:
        raise StagingHttpHold(label+" invalid public JSON") from exc


def inspect_staging_public_surface(
    origin: str, expected_origin_sha256: str, *,
    client, phase: str="candidate", now: datetime|None=None,
) -> dict[str,Any]:
    """Client must be configured with follow_redirects=False and trust_env=False."""
    _validate_target(origin,expected_origin_sha256)
    if phase not in ("candidate","post_rollback"):
        raise StagingHttpHold("Unknown passive acceptance phase")
    moment=now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        raise StagingHttpHold("Reference UTC time required")
    moment=moment.astimezone(timezone.utc)
    replies={}
    try:
        for path in _PROBE_PATHS:
            if getattr(client,"cookies",None):
                raise StagingHttpHold("Probe must not carry authentication cookies")
            response=client.get(origin+path,headers={
                "Accept":"application/json" if path.startswith("/api/") or path=="/healthz"
                else "text/html",
                "Cache-Control":"no-store",
            })
            if (response.is_redirect or
                response.status_code not in (200,401,403)):
                raise StagingHttpHold("Unexpected staging response")
            # This intentionally unauthenticated probe may not acquire or
            # replay an application session from a public GET response.
            if response.headers.get("set-cookie"):
                raise StagingHttpHold("Unexpected unauthenticated Set-Cookie")
            replies[path]=response
    except StagingHttpHold:
        raise
    except Exception as exc:
        raise StagingHttpHold("Staging HTTP endpoint unavailable") from exc
    healthz=_read_json(replies["/healthz"],label="healthz")
    health=_read_json(replies["/api/health"],label="public snapshot")
    catalog=_read_json(replies["/api/v2/public/markets"],label="public markets")
    if healthz!={"ok":True,"service":"vowsig"}:
        raise StagingHttpHold("Unexpected staging health service")
    if (not isinstance(health,dict) or
        health.get("product")!="VowSig Research Beta" or
        health.get("snapshot_pending") is not False or
        health.get("snapshot_freshness")!="fresh"):
        raise StagingHttpHold("Public research snapshot not fresh")
    timestamp=health.get("snapshot_generated_at_utc")
    if not isinstance(timestamp,str):
        raise StagingHttpHold("Snapshot timestamp unavailable")
    try:
        stamp=datetime.fromisoformat(timestamp.replace("Z","+00:00"))
    except ValueError as exc:
        raise StagingHttpHold("Snapshot timestamp malformed") from exc
    if (stamp.tzinfo is None or stamp.utcoffset()!=timedelta(0) or
        stamp>moment+timedelta(minutes=2) or
        moment-stamp>=timedelta(minutes=90)):
        raise StagingHttpHold("Snapshot timestamp not independently fresh")
    if (not isinstance(catalog,dict) or catalog.get("schema_version")!=1
        or not isinstance(catalog.get("markets"),list)
        or len(catalog["markets"])!=9 or
        catalog.get("commercial_customer_eligible") is not False):
        raise StagingHttpHold("Public market directory incomplete")
    symbols=set()
    for market in catalog["markets"]:
        if (not isinstance(market,dict) or
            market.get("symbol") not in _ALLOWED_MARKETS or
            market["symbol"] in symbols or
            market.get("research_only") is not True or
            market.get("commercial_customer_eligible") is not False):
            raise StagingHttpHold("Unapproved public market identity")
        symbols.add(market["symbol"])
        if (market["symbol"] in _RESTRICTED and
            (market.get("research_signal_detail_available") is not False
             or market.get("current_signal_present") is not False)):
            raise StagingHttpHold("Restricted research signals accidentally exposed")
    if symbols!=_ALLOWED_MARKETS:
        raise StagingHttpHold("Missing catalog markets")
    for path in ("/api/v2/me","/app/","/admin/","/api/v2/admin/performance"):
        response=replies[path]
        if response.status_code not in (401,403):
            raise StagingHttpHold("Unauthenticated member or owner page exposed")
        if "noindex" not in response.headers.get("x-robots-tag","").lower():
            raise StagingHttpHold("Protected API/page not marked noindex")
        if len(response.content)>8192:
            raise StagingHttpHold("Protected denial response unexpectedly large")
    return {
        "status":"STAGING_HTTP_PUBLIC_AND_DENIAL_CONTRACT_PASS_NOT_RELEASE_PROOF",
        "phase":phase,"tested_paths":len(replies),
        "public_market_count":len(symbols),
        "restricted_market_details_exposed":False,
        "guest_member_and_owner_paths_denied":True,
        "fresh_snapshot_checked":True,
        "network_methods_used":["GET"],
        "auth0_signup_login_or_email_tested":False,
        "railway_sql_authentication_tested":False,
        "owner_mfa_enrollment_tested":False,
        "rollback_action_executed_by_probe":False,
        "actual_rollback_attested":False,
        "owner_release_approval_granted":False,
        "raw_provider_or_customer_responses_exported":False,
    }


def main()->int:
    import argparse
    parser=argparse.ArgumentParser(description="Staging-only GET/denial preflight")
    parser.add_argument("--staging-origin",required=True)
    parser.add_argument("--staging-origin-sha256",required=True)
    parser.add_argument("--phase",choices=("candidate","post_rollback"),required=True)
    args=parser.parse_args()
    try:
        import httpx
        with httpx.Client(
            follow_redirects=False,trust_env=False,
            timeout=httpx.Timeout(8),headers={"User-Agent":"VowSig-release-readonly-preflight/1"},
        ) as client:
            receipt=inspect_staging_public_surface(
                args.staging_origin,args.staging_origin_sha256,
                phase=args.phase,client=client,
            )
    except Exception:
        print("VOWSIG_STAGING_HTTP_PREFLIGHT=HOLD")
        print("PRODUCTION_RELEASE_AUTHORIZED=NO")
        return 1
    print(json.dumps(receipt,sort_keys=True,separators=(",",":")))
    print("PRODUCTION_RELEASE_AUTHORIZED=NO")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
