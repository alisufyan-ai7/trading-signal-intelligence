"""Auth0 public discovery: exact origin, PKCE/RS256 and real RSA JWKS only."""
from __future__ import annotations

import base64
import json

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from trading_signal_intelligence.product.accounts import auth0_public_acceptance as mod


def _b64(n):
    width=(n.bit_length()+7)//8
    return base64.urlsafe_b64encode(n.to_bytes(width,"big")).decode().rstrip("=")


@pytest.fixture(scope="module")
def rsa_key():
    pub=rsa.generate_private_key(public_exponent=65537,key_size=2048).public_key().public_numbers()
    return {"kty":"RSA","use":"sig","alg":"RS256","kid":"k1","n":_b64(pub.n),"e":_b64(pub.e)}


def _discovery():
    return {
        "issuer":mod.ISSUER,
        "authorization_endpoint":mod.AUTHORIZATION,
        "token_endpoint":mod.TOKEN,
        "jwks_uri":mod.JWKS,
        "response_types_supported":["code"],
        "grant_types_supported":["authorization_code"],
        "id_token_signing_alg_values_supported":["RS256"],
        "token_endpoint_auth_methods_supported":["client_secret_post"],
        "code_challenge_methods_supported":["S256"],
    }


def _probe(rsa_key, *, mutate=None, jwks=None, discovery_status=200):
    document=_discovery()
    if mutate:
        mutate(document)
    payloads={
        mod.DISCOVERY:(discovery_status,document),
        mod.JWKS:(200,{"keys":[rsa_key] if jwks is None else jwks}),
    }
    paths=[]
    def handler(request):
        paths.append(str(request.url))
        code,data=payloads.get(str(request.url),(404,{}))
        return httpx.Response(code,json=data)
    with httpx.Client(transport=httpx.MockTransport(handler),
                      follow_redirects=False,trust_env=False) as client:
        result=mod.verify_public_discovery(http_client=client)
    assert paths==[mod.DISCOVERY,mod.JWKS]
    return result


def test_strict_public_oidc_contract_and_jwks_do_not_authorize_signup(rsa_key):
    result=_probe(rsa_key)
    assert result["status"]=="AUTH0_PUBLIC_OIDC_METADATA_AND_JWKS_PASS"
    assert result["validated_public_rsa_keys"]==1
    for field in ("verified_email_signup_tested","return_login_and_logout_tested",
                  "actual_authorization_code_redeemed","release_provider_acceptance_complete"):
        assert result[field] is False
    assert "n" not in result and "e" not in result and "kid" not in result


@pytest.mark.parametrize("mutation",[
    lambda d:d.update(issuer="https://evil.example/"),
    lambda d:d.update(jwks_uri="https://evil.example/keys"),
    lambda d:d.update(token_endpoint_auth_methods_supported=["client_secret_basic"]),
    lambda d:d.update(code_challenge_methods_supported=["plain"]),
    lambda d:d.update(id_token_signing_alg_values_supported=["HS256"]),
    lambda d:d.pop("grant_types_supported"),
])
def test_metadata_drift_fails_closed(rsa_key,mutation):
    with pytest.raises(mod.PublicAuth0AcceptanceHold):
        _probe(rsa_key,mutate=mutation)


def test_bad_rsa_jwks_and_http_error_fail_closed(rsa_key):
    with pytest.raises(mod.PublicAuth0AcceptanceHold):
        _probe(rsa_key,jwks=[dict(rsa_key, n="not-a-number")])
    with pytest.raises(mod.PublicAuth0AcceptanceHold):
        _probe(rsa_key,jwks=[rsa_key,rsa_key])
    with pytest.raises(mod.PublicAuth0AcceptanceHold):
        _probe(rsa_key,jwks=[dict(rsa_key,d="private-must-never-be-present")])
    with pytest.raises(mod.PublicAuth0AcceptanceHold):
        _probe(rsa_key,discovery_status=401)
