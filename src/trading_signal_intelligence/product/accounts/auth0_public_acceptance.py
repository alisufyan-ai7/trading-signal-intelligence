"""Read-only, public Auth0 OIDC discovery and JWKS acceptance.

No account login, token, email or secret; never infer a successful signup
from publicly visible OIDC metadata. Network is used ONLY by the separately
owner-authorized CLI in its approved staging/operations environment.
"""
from __future__ import annotations

import json
from typing import Any

ISSUER="https://dev-b1aqc523agud2k4p.us.auth0.com/"
DISCOVERY=ISSUER+".well-known/openid-configuration"
AUTHORIZATION=ISSUER+"authorize"
TOKEN=ISSUER+"oauth/token"
JWKS=ISSUER+".well-known/jwks.json"
_MAX_BYTES=96_000
_MAX_KEYS=40


class PublicAuth0AcceptanceHold(ValueError):
    """No provider bodies or untrusted metadata in exceptions/receipts."""


def _object_pairs(pairs: list[tuple[str,Any]]) -> dict[str,Any]:
    out={}
    for key,val in pairs:
        if key in out:
            raise PublicAuth0AcceptanceHold("Duplicate public provider property")
        out[key]=val
    return out


def _json_response(response, *, label: str) -> dict[str,Any]:
    if (response.status_code!=200 or
        not response.headers.get("content-type","").lower().startswith("application/json") or
        not 0<len(response.content)<=_MAX_BYTES or
        response.is_redirect):
        raise PublicAuth0AcceptanceHold(label+" public response refused")
    try:
        result=json.loads(response.content,object_pairs_hook=_object_pairs,
                          parse_constant=lambda _:(_ for _ in ()).throw(ValueError()))
    except (ValueError,UnicodeDecodeError) as exc:
        raise PublicAuth0AcceptanceHold(label+" JSON unacceptable") from exc
    if not isinstance(result,dict):
        raise PublicAuth0AcceptanceHold(label+" body not an object")
    return result


def verify_public_discovery(*, http_client) -> dict[str,Any]:
    """Inspect only two exact Auth0 HTTPS URLs with no redirects or auth.

    Caller should create httpx.Client(follow_redirects=False,trust_env=False).
    The owned live CLI does this. Injected mock clients cannot authorize a
    live-acceptance claim; receipt intentionally records environment limits.
    """
    try:
        discovery=_json_response(http_client.get(DISCOVERY),label="OIDC discovery")
        expected={
            "issuer":ISSUER,
            "authorization_endpoint":AUTHORIZATION,
            "token_endpoint":TOKEN,
            "jwks_uri":JWKS,
        }
        if any(discovery.get(key)!=val for key,val in expected.items()):
            raise PublicAuth0AcceptanceHold("Exact Auth0 issuer/endpoint mismatch")
        pairs=(
            ("response_types_supported","code"),
            ("grant_types_supported","authorization_code"),
            ("id_token_signing_alg_values_supported","RS256"),
            ("token_endpoint_auth_methods_supported","client_secret_post"),
            ("code_challenge_methods_supported","S256"),
        )
        for key,required in pairs:
            value=discovery.get(key)
            if not isinstance(value,list) or required not in value:
                raise PublicAuth0AcceptanceHold("Expected OIDC security method absent")
        keys=_json_response(http_client.get(JWKS),label="Auth0 JWKS").get("keys")
        if not isinstance(keys,list) or not 1<=len(keys)<=_MAX_KEYS:
            raise PublicAuth0AcceptanceHold("JWKS key set invalid")
        # Validate actual public RSA key shapes, not just presence of an alg label.
        from jwt.algorithms import RSAAlgorithm
        usable=0
        seen=set()
        for key in keys:
            if not isinstance(key,dict):
                raise PublicAuth0AcceptanceHold("JWKS key not an object")
            if key.get("kty")!="RSA" or key.get("use","sig")!="sig":
                continue
            if key.get("alg","RS256")!="RS256":
                continue
            kid=key.get("kid")
            if (not isinstance(kid,str) or not 1<=len(kid)<=200 or
                kid in seen or "d" in key or
                any(x in key for x in ("p","q","dp","dq","qi","oth"))):
                raise PublicAuth0AcceptanceHold("Untrusted public signing key")
            try:
                parsed=RSAAlgorithm.from_jwk(json.dumps(key))
                if parsed.key_size<2048:
                    raise ValueError("Small RSA modulus")
            except (ValueError,KeyError,TypeError) as exc:
                raise PublicAuth0AcceptanceHold("Invalid RSA signing key") from exc
            seen.add(kid)
            usable+=1
        if usable<1:
            raise PublicAuth0AcceptanceHold("No approved RSA signing key")
    except PublicAuth0AcceptanceHold:
        raise
    except Exception as exc:
        # Never print proxy, URL/body/header error details.
        raise PublicAuth0AcceptanceHold("Public Auth0 discovery unavailable") from exc
    return {
        "status":"AUTH0_PUBLIC_OIDC_METADATA_AND_JWKS_PASS",
        "issuer":ISSUER,
        "audience_signing_algorithm":"RS256",
        "authorization_code_and_pkce_s256_advertised":True,
        "client_secret_post_advertised":True,
        "validated_public_rsa_keys":usable,
        "actual_authorization_code_redeemed":False,
        "verified_email_signup_tested":False,
        "return_login_and_logout_tested":False,
        "auth0_domain_or_credentials_changed":False,
        "resend_delivery_confirmed_by_this_probe":False,
        "release_provider_acceptance_complete":False,
    }


def main() -> int:
    try:
        import httpx
        with httpx.Client(timeout=httpx.Timeout(6),follow_redirects=False,
                          trust_env=False,headers={"Accept":"application/json"}) as client:
            result=verify_public_discovery(http_client=client)
    except Exception:
        print("VOWSIG_AUTH0_PUBLIC_DISCOVERY=HOLD")
        print("REAL_SIGNUP_EMAIL_MFA_PROVEN=NO")
        return 1
    print("VOWSIG_AUTH0_PUBLIC_DISCOVERY=PASS")
    print("JWT_ALGORITHM=RS256")
    print("RSA_KEY_COUNT="+str(result["validated_public_rsa_keys"]))
    print("REAL_SIGNUP_EMAIL_MFA_PROVEN=NO")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
