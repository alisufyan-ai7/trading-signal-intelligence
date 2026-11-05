"""Read-only staging HTTP acceptance with simulated endpoints; no real network."""
from __future__ import annotations

from datetime import datetime,timedelta,timezone
import hashlib

import httpx
import pytest

from trading_signal_intelligence.product.accounts import staging_http_acceptance as smoke

ORIGIN="https://staging.example.org"
PIN=hashlib.sha256(ORIGIN.encode()).hexdigest()
NOW=datetime(2026,11,5,5,30,tzinfo=timezone.utc)
MARKETS=("XAUUSD","USTEC","US30","EURUSD","XAGUSD","USOIL","BTCUSDT","ETHUSDT","SOLUSDT")


def _client(*, fault=None):
    paths=[]
    def respond(request):
        assert request.method=="GET"
        assert not request.headers.get("authorization")
        assert not request.headers.get("cookie")
        paths.append(request.url.path)
        if request.url.path=="/healthz":
            headers=({"set-cookie":"__Host-session=not-allowed; Secure"}
                     if fault=="set_cookie" else {})
            return httpx.Response(200,json={"ok":True,"service":"vowsig"},
                                  headers=headers)
        if request.url.path=="/api/health":
            freshness="stale" if fault=="stale" else "fresh"
            time=NOW-timedelta(minutes=4)
            if fault=="future":
                time=NOW+timedelta(hours=1)
            return httpx.Response(200,json={
                "product":"VowSig Research Beta","snapshot_pending":False,
                "snapshot_freshness":freshness,
                "snapshot_generated_at_utc":time.isoformat(),
            })
        if request.url.path=="/api/v2/public/markets":
            rows=[{"symbol":s,"research_only":True,
                   "commercial_customer_eligible":False,
                   "research_signal_detail_available":(
                       fault=="exposure" and s=="BTCUSDT"),
                   "current_signal_present":False} for s in MARKETS]
            if fault=="missing_market":
                rows.pop()
            return httpx.Response(200,json={
                "schema_version":1,"commercial_customer_eligible":False,
                "markets":rows})
        if fault=="auth_exposed" and request.url.path=="/admin/":
            return httpx.Response(200,content=b"<html>private</html>",
                                  headers={"content-type":"text/html"})
        if fault=="redirect" and request.url.path=="/admin/":
            return httpx.Response(302,headers={"location":"https://evil.example/"})
        return httpx.Response(401,content=b'{"detail":"Verified sign-in required"}',
                              headers={"content-type":"application/json",
                                       "x-robots-tag":"noindex, nofollow, noarchive"})
    return httpx.Client(transport=httpx.MockTransport(respond),
                        follow_redirects=False,trust_env=False),paths


@pytest.mark.parametrize("phase",["candidate","post_rollback"])
def test_staging_get_only_receipt_does_not_claim_actual_rollback(phase):
    client,paths=_client()
    with client:
        report=smoke.inspect_staging_public_surface(
            ORIGIN,PIN,client=client,now=NOW,phase=phase)
    assert report["tested_paths"]==7
    assert len(paths)==7
    assert report["public_market_count"]==9
    assert report["guest_member_and_owner_paths_denied"] is True
    assert report["actual_rollback_attested"] is False
    assert report["network_methods_used"]==["GET"]
    assert report["owner_release_approval_granted"] is False
    assert "example.org" not in str(report)


@pytest.mark.parametrize("fault",[
    "stale","future","missing_market","exposure","auth_exposed","redirect","set_cookie",
])
def test_readonly_staging_fails_closed_on_runtime_drift(fault):
    client,_=_client(fault=fault)
    with client,pytest.raises(smoke.StagingHttpHold):
        smoke.inspect_staging_public_surface(ORIGIN,PIN,client=client,now=NOW)


@pytest.mark.parametrize("bad_origin",[
    "https://vowsig.com","https://www.vowsig.com",
    "http://staging.example.org","https://staging.example.org/other",
    "https://user:password@staging.example.org",
    "https://localhost","https://127.0.0.1",
])
def test_production_and_unsafe_origins_denied_before_http(bad_origin):
    client,paths=_client()
    with client,pytest.raises(smoke.StagingHttpHold):
        smoke.inspect_staging_public_surface(
            bad_origin,hashlib.sha256(bad_origin.encode()).hexdigest(),
            client=client,now=NOW)
    assert paths==[]


def test_wrong_independent_stage_pin_or_unknown_phase_denied():
    client,paths=_client()
    with client:
        with pytest.raises(smoke.StagingHttpHold):
            smoke.inspect_staging_public_surface(ORIGIN,"0"*64,client=client,now=NOW)
        with pytest.raises(smoke.StagingHttpHold):
            smoke.inspect_staging_public_surface(ORIGIN,PIN,client=client,phase="live",now=NOW)
    assert paths==[]
