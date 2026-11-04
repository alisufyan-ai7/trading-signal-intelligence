"""P1B-1: real RS256/JWKS verifier tested against a simulated OIDC endpoint."""
from __future__ import annotations

import base64
import hashlib
import json
import time
from dataclasses import replace
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlsplit

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from fastapi.testclient import TestClient

from trading_signal_intelligence.product.accounts.auth_api import create_auth_router
from trading_signal_intelligence.product.accounts.identity_contract import (
    IdentityContractError, TrustedOidcClaims,
)
from trading_signal_intelligence.product.accounts.oidc_provider import (
    OidcSettings, VerifiedOidcProvider, begin_authorization,
)

CONFIG=OidcSettings(
    issuer="https://identity.example.test/tenant/",
    client_id="vowsig-client",
    authorization_endpoint="https://identity.example.test/tenant/authorize",
    token_endpoint="https://identity.example.test/tenant/token",
    jwks_uri="https://identity.example.test/tenant/keys",
    app_origin="https://vowsig.example",
)
NOW=lambda: int(time.time())


def test_oidc_pkce_state_nonce_and_fixed_redirect():
    a=begin_authorization(CONFIG)
    b=begin_authorization(CONFIG)
    assert len({a.state,a.nonce,a.browser,a.code_verifier,b.state,b.nonce})==6
    assert all(len(x)==43 for x in (a.state,a.browser,a.nonce,a.code_verifier))
    u=urlsplit(a.authorization_url)
    q=parse_qs(u.query)
    assert q["response_type"]==["code"] and q["scope"]==["openid email"]
    assert q["redirect_uri"]==["https://vowsig.example/auth/callback"]
    assert q["max_age"]==["600"] and q["state"]==[a.state] and q["nonce"]==[a.nonce]
    assert q["code_challenge_method"]==["S256"]
    assert q["code_challenge"]==[
        base64.urlsafe_b64encode(hashlib.sha256(a.code_verifier.encode()).digest())
            .decode().rstrip("=")
    ]
    assert "client_secret" not in u.query


@pytest.fixture
def mock_provider():
    private=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    public_key_json=json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private.public_key()))
    public_key_json.update({"kid":"fixture-key","alg":"RS256","use":"sig"})
    state={"payload":None,"key":private,"jwks":{"keys":[public_key_json]},
           "calls":[],"http_status":200}

    def exchange(request: httpx.Request):
        state["calls"].append((request.method,str(request.url)))
        if request.method=="POST" and str(request.url)==CONFIG.token_endpoint:
            form=dict(item.split("=",1) for item in request.content.decode().split("&"))
            from urllib.parse import unquote_plus
            form={k:unquote_plus(v) for k,v in form.items()}
            assert form["grant_type"]=="authorization_code"
            assert form["client_id"]==CONFIG.client_id
            assert form["redirect_uri"]=="https://vowsig.example/auth/callback"
            assert len(form["code_verifier"])==43
            return httpx.Response(state["http_status"], json={"id_token":state["payload"]})
        if request.method=="GET" and str(request.url)==CONFIG.jwks_uri:
            return httpx.Response(200,json=state["jwks"])
        raise AssertionError("Unexpected provider endpoint")

    state["client"]=httpx.Client(transport=httpx.MockTransport(exchange))
    def sign(**overrides):
        now=NOW()
        claims={
            "iss":CONFIG.issuer, "sub":"provider-opaque-001",
            "aud":CONFIG.client_id, "iat":now-20, "exp":now+300,
            "auth_time":now-30, "nonce":"nnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnn",
            "email":"person@example.test","email_verified":True,
        }
        claims.update(overrides)
        state["payload"]=jwt.encode(claims,private,algorithm="RS256",
                                     headers={"kid":"fixture-key"})
        return state["payload"]
    state["sign"]=sign
    yield state
    state["client"].close()


def verify(state):
    provider=VerifiedOidcProvider(CONFIG,http_client=state["client"])
    return provider.verify_callback(
        authorization_code="one-use-test-code",
        code_verifier=base64.urlsafe_b64encode(bytes(range(32))).decode().rstrip("="),
        expected_nonce="nnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnn",
    )


def test_signed_oidc_token_checks_signature_claims_and_issuer(mock_provider):
    mock_provider["sign"]()
    verified=verify(mock_provider)
    assert verified.email_verified is True
    assert verified.subject=="provider-opaque-001"
    assert verified.issuer==CONFIG.issuer
    assert [v[0] for v in mock_provider["calls"]]==["POST","GET"]


@pytest.mark.parametrize("claims",[
    {"nonce":"wrong-browser"},
    {"iss":"https://impostor.example.test/"},
    {"aud":"a-different-client"},
    {"email_verified":False},
    {"auth_time":lambda n:n-3600},
    {"exp":lambda n:n-120},
    {"iat":lambda n:n+120},
])
def test_reject_bad_or_expired_id_token_claims(mock_provider,claims):
    replacements={k:(v(NOW()) if callable(v) else v) for k,v in claims.items()}
    mock_provider["sign"](**replacements)
    with pytest.raises(IdentityContractError):
        verify(mock_provider)


def test_reject_wrong_signing_key_kid_and_forged_signature(mock_provider):
    good=mock_provider["sign"]()
    mock_provider["jwks"]={"keys":[]}
    with pytest.raises(IdentityContractError):
        verify(mock_provider)
    jwk=json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(
        rsa.generate_private_key(public_exponent=65537,key_size=2048).public_key()))
    jwk.update({"kid":"fixture-key","alg":"RS256","use":"sig"})
    mock_provider["jwks"]={"keys":[jwk]}
    mock_provider["payload"]=good
    with pytest.raises(IdentityContractError):
        verify(mock_provider)


def test_invalid_provider_config_and_non_json_token_exchange(mock_provider):
    with pytest.raises(IdentityContractError):
        OidcSettings(**{**CONFIG.__dict__,"token_endpoint":"http://internal/steal"})
    mock_provider["sign"]()
    mock_provider["http_status"]=500
    with pytest.raises(IdentityContractError):
        verify(mock_provider)


class FakeStore:
    def __init__(self):
        self.states={}
        self.budget=True
        self.sessions=[]
        self.consume_count=0
    def take_auth_budget(self,peer_digest):
        assert len(peer_digest)==64
        return self.budget
    def begin_oidc(self, **kwargs):
        self.states[(kwargs["state_sha256"],kwargs["browser_sha256"])]={
            "code_verifier":kwargs["code_verifier"],"nonce":kwargs["nonce"],
        }
    def consume_oidc(self,state_sha256,browser_sha256):
        self.consume_count+=1
        return self.states.pop((state_sha256,browser_sha256),None)
    def complete_verified_login(self,**kwargs):
        self.sessions.append(kwargs)
        return "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa"


class FakeVerifier:
    def verify_callback(self,*,authorization_code,code_verifier,expected_nonce):
        assert authorization_code=="good-code"
        assert len(code_verifier)==43
        now=datetime.now(timezone.utc)
        from datetime import timedelta
        return TrustedOidcClaims(
            issuer=CONFIG.issuer,subject="single-verified-user",
            audience=CONFIG.client_id,nonce=expected_nonce,
            email="person@example.test",email_verified=True,
            issued_at_utc=now-timedelta(seconds=20),
            expires_at_utc=now+timedelta(minutes=5),
            auth_time_utc=now-timedelta(seconds=30),
        )


@pytest.fixture
def auth_client():
    s=FakeStore()
    app=FastAPI()
    app.include_router(create_auth_router(
        make_store=lambda:s,settings=CONFIG,verifier=FakeVerifier(),
        csrf_secret="Only-in-tests-this-secret-has-at-least-32-bytes",
    ))
    return s,TestClient(app,base_url="https://vowsig.example")


def test_full_browser_bound_state_flow_one_use_and_host_cookie(auth_client):
    store,client=auth_client
    started=client.get("/auth/start",follow_redirects=False)
    assert started.status_code==302
    assert "Secure" in started.headers["set-cookie"]
    assert "HttpOnly" in started.headers["set-cookie"]
    assert "__Host-vowsig_oidc" in started.headers["set-cookie"]
    state=parse_qs(urlsplit(started.headers["location"]).query)["state"][0]
    finish=client.get("/auth/callback",params={"code":"good-code","state":state},
                      follow_redirects=False)
    assert finish.status_code==303 and finish.headers["location"]=="/app/"
    assert len(store.sessions)==1
    assert len(store.sessions[0]["token_sha256"])==64
    assert "__Host-vowsig_session" in finish.headers.get_list("set-cookie")[0]
    assert "domain=" not in str(finish.headers.get_list("set-cookie")).lower()
    replay=client.get("/auth/callback",params={"code":"good-code","state":state},
                      follow_redirects=False)
    assert replay.status_code==400
    assert len(store.sessions)==1


def test_state_cookie_mismatch_and_duplicate_callback_params(auth_client):
    store,client=auth_client
    started=client.get("/auth/start",follow_redirects=False)
    state=parse_qs(urlsplit(started.headers["location"]).query)["state"][0]
    client.cookies.set("__Host-vowsig_oidc","x"*43)
    wrong=client.get("/auth/callback",params={"code":"good-code","state":state},
                     follow_redirects=False)
    assert wrong.status_code==400 and not store.sessions
    assert store.consume_count==1
    duplicate=client.get(
        "/auth/callback?code=good-code&code=other&state="+state,
        follow_redirects=False,
    )
    assert duplicate.status_code==400


def test_login_throttle_fails_before_creating_transaction(auth_client):
    store,client=auth_client
    store.budget=False
    result=client.get("/auth/start",follow_redirects=False)
    assert result.status_code==429 and store.states=={}


def test_owner_auth0_public_config_exact_boundaries():
    """Public tenant configuration only; no Auth0 HTTP call or client secret."""
    domain = "dev-b1aqc523agud2k4p.us.auth0.com"
    config = OidcSettings(
        issuer=f"https://{domain}/",
        client_id="FMhkJa8azUSjflmNBTDb3keWNCUv6b3w",
        authorization_endpoint=f"https://{domain}/authorize",
        token_endpoint=f"https://{domain}/oauth/token",
        jwks_uri=f"https://{domain}/.well-known/jwks.json",
        app_origin="https://vowsig.com",
    )
    assert config.redirect_uri == "https://vowsig.com/auth/callback"
    auth = begin_authorization(config)
    parsed = urlsplit(auth.authorization_url)
    assert (parsed.scheme, parsed.hostname, parsed.path) == ("https", domain, "/authorize")
    params = parse_qs(parsed.query)
    assert params["client_id"] == ["FMhkJa8azUSjflmNBTDb3keWNCUv6b3w"]
    assert params["redirect_uri"] == [config.redirect_uri]
    assert params["response_type"] == ["code"]
    assert params["code_challenge_method"] == ["S256"]
    assert params["scope"] == ["openid email"]
    assert "client_secret" not in params
    assert "access_token" not in params
    assert len(params["state"][0]) == 43
    assert len(params["nonce"][0]) == 43
