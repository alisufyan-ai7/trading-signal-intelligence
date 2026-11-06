"""P1B-1: strict configurable OIDC code+PKCE verifier; no provider selected here.

Provider URLs and client IDs are operator-configured HTTPS values, NEVER
derived from request parameters. Token/jwks responses may contain untrusted data;
only cryptographically validated RS256 ID tokens yield TrustedOidcClaims.
The authorization transaction's one-time state and browser binding are enforced
by the separate database layer BEFORE this verifier is called.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode, urlsplit

from trading_signal_intelligence.product.accounts.identity_contract import (
    IdentityContractError, IdentityProviderConfig, TrustedOidcClaims,
    validate_verified_claims,
)

_B64 = re.compile(r"^[A-Za-z0-9_-]{43}$")
_ALGORITHM = "RS256"
_CALLBACK_PATH = "/auth/callback"
_MAX_JSON = 65536


def _static_https(value: str) -> None:
    if not isinstance(value, str) or len(value) > 2000:
        raise IdentityContractError("Static HTTPS identity endpoint required")
    u = urlsplit(value)
    if (u.scheme != "https" or not u.hostname or u.username or u.password
        or u.query or u.fragment or u.hostname in ("localhost", "127.0.0.1", "::1")):
        raise IdentityContractError("Untrusted identity endpoint")
    if u.port not in (None, 443):
        raise IdentityContractError("Non-standard identity endpoint port refused")


@dataclass(frozen=True)
class OidcSettings:
    issuer: str
    client_id: str
    authorization_endpoint: str
    token_endpoint: str
    jwks_uri: str
    app_origin: str
    client_secret: str | None = None

    @property
    def redirect_uri(self) -> str:
        return self.app_origin + _CALLBACK_PATH

    def __post_init__(self) -> None:
        IdentityProviderConfig(issuer=self.issuer, client_id=self.client_id)
        for endpoint in (self.issuer, self.authorization_endpoint,
                         self.token_endpoint, self.jwks_uri, self.app_origin):
            _static_https(endpoint)
        parsed = urlsplit(self.app_origin)
        if parsed.path not in ("", "/") or self.app_origin.endswith("/"):
            raise IdentityContractError("Application origin must be exact HTTPS origin")
        if self.client_secret is not None and len(self.client_secret) < 16:
            raise IdentityContractError("OIDC client secret too short")


@dataclass(frozen=True)
class OidcAuthorization:
    state: str
    browser: str
    nonce: str
    code_verifier: str
    authorization_url: str


def begin_authorization(settings: OidcSettings) -> OidcAuthorization:
    state = secrets.token_urlsafe(32)
    browser = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(32)
    assert all(_B64.fullmatch(x) for x in (state, browser, nonce, verifier))
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode("ascii")).digest()
    ).decode("ascii").rstrip("=")
    params = {
        "response_type": "code", "scope": "openid email",
        "client_id": settings.client_id, "redirect_uri": settings.redirect_uri,
        "state": state, "nonce": nonce, "code_challenge": challenge,
        "code_challenge_method": "S256", "max_age": "600",
    }
    separator = "&" if "?" in settings.authorization_endpoint else "?"
    return OidcAuthorization(
        state=state, browser=browser, nonce=nonce, code_verifier=verifier,
        authorization_url=settings.authorization_endpoint + separator + urlencode(params),
    )


def _unix_datetime(value: Any, claim: str) -> datetime:
    if type(value) not in (int, float):
        raise IdentityContractError(f"Invalid {claim} timestamp")
    try:
        return datetime.fromtimestamp(value, tz=timezone.utc)
    except (OverflowError, ValueError, OSError) as exc:
        raise IdentityContractError(f"Invalid {claim} timestamp") from exc


class VerifiedOidcProvider:
    """Synchronous issuer-pinned verifier. Provide an httpx.Client for mocked tests."""

    def __init__(self, settings: OidcSettings, *, http_client=None):
        self.settings = settings
        self._client = http_client

    def verify_callback(
        self, *, authorization_code: str, code_verifier: str, expected_nonce: str,
    ) -> TrustedOidcClaims:
        if (
            not isinstance(authorization_code, str)
            or not 1 <= len(authorization_code) <= 2048
            or not isinstance(code_verifier, str)
            or not _B64.fullmatch(code_verifier)
            or not isinstance(expected_nonce, str)
            or not _B64.fullmatch(expected_nonce)
        ):
            raise IdentityContractError("Invalid code, verifier or nonce")
        import httpx
        from jwt import InvalidTokenError, algorithms, decode, get_unverified_header

        owns_client = self._client is None
        client = self._client or httpx.Client(
            timeout=httpx.Timeout(5), follow_redirects=False, trust_env=False,
            headers={"Accept": "application/json"},
        )
        try:
            data = {
                "grant_type": "authorization_code",
                "code": authorization_code,
                "redirect_uri": self.settings.redirect_uri,
                "client_id": self.settings.client_id,
                "code_verifier": code_verifier,
            }
            if self.settings.client_secret:
                data["client_secret"] = self.settings.client_secret
            token_response = client.post(self.settings.token_endpoint, data=data)
            if (token_response.status_code != 200 or len(token_response.content) > _MAX_JSON
                    or not token_response.headers.get("content-type", "").lower().startswith("application/json")):
                raise IdentityContractError("Identity token exchange rejected")
            payload = token_response.json()
            id_token = payload.get("id_token") if isinstance(payload, dict) else None
            if not isinstance(id_token, str) or not 20 <= len(id_token) <= 15000:
                raise IdentityContractError("Missing bounded signed ID token")
            try:
                header = get_unverified_header(id_token)
                if (header.get("alg") != _ALGORITHM
                    or not isinstance(header.get("kid"), str)
                    or not 1 <= len(header["kid"]) <= 200):
                    raise IdentityContractError("Unsupported OIDC token algorithm/key")
            except InvalidTokenError as exc:
                raise IdentityContractError("Malformed identity token header") from exc
            keys_response = client.get(self.settings.jwks_uri)
            if (keys_response.status_code != 200
                or len(keys_response.content) > _MAX_JSON
                or not keys_response.headers.get("content-type", "").lower().startswith("application/json")):
                raise IdentityContractError("Identity signing keys unavailable")
            keys_json = keys_response.json()
            keys = keys_json.get("keys") if isinstance(keys_json, dict) else None
            if not isinstance(keys, list) or not 1 <= len(keys) <= 20:
                raise IdentityContractError("Invalid OIDC signing key set")
            matched = [x for x in keys if isinstance(x, dict)
                       and x.get("kid") == header["kid"]
                       and x.get("kty") == "RSA"
                       and x.get("use", "sig") == "sig"
                       and x.get("alg", _ALGORITHM) == _ALGORITHM]
            if len(matched) != 1:
                raise IdentityContractError("Unknown/ambiguous OIDC signing key")
            try:
                pubkey = algorithms.RSAAlgorithm.from_jwk(json.dumps(matched[0]))
                claims = decode(
                    id_token, pubkey, algorithms=[_ALGORITHM],
                    audience=self.settings.client_id, issuer=self.settings.issuer,
                    options={"require": [
                        "iss", "sub", "aud", "iat", "exp", "nonce", "auth_time",
                        "email", "email_verified",
                    ]},
                )
            except (InvalidTokenError, ValueError, TypeError) as exc:
                raise IdentityContractError("Identity signature or claims rejected") from exc
            # OIDC azp must name this client when a token has multiple audiences.
            if isinstance(claims.get("aud"), list):
                if claims.get("azp") != self.settings.client_id:
                    raise IdentityContractError("OIDC multi-audience azp rejected")
            identity = TrustedOidcClaims(
                issuer=claims["iss"], subject=claims["sub"],
                audience=self.settings.client_id, nonce=claims["nonce"],
                email=claims["email"], email_verified=claims["email_verified"],
                issued_at_utc=_unix_datetime(claims["iat"], "iat"),
                expires_at_utc=_unix_datetime(claims["exp"], "exp"),
                auth_time_utc=_unix_datetime(claims["auth_time"], "auth_time"),
            )
            validate_verified_claims(
                identity,
                IdentityProviderConfig(self.settings.issuer, self.settings.client_id),
                expected_nonce=expected_nonce,
            )
            return identity
        except (httpx.HTTPError, ValueError, KeyError, json.JSONDecodeError) as exc:
            # Never surface raw provider errors, tokens, headers or bodies.
            raise IdentityContractError("Identity provider verification unavailable") from exc
        finally:
            if owns_client:
                client.close()
