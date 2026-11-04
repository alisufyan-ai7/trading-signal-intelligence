# VowSig Auth0 tenant binding — owner-supplied public configuration

**2026-11-04.** Owner supplied the Auth0 tenant domain and Regular Web Application Client ID. Both identifiers are public configuration, **not passwords/secrets**. Auth0 dashboard screenshots showed the three expected callback/origin fields. They do not independently prove a completed Auth0 login, issuer discovery, signing-key rotation, application type or client authentication method.

## Supplied Auth0 public details (expected, pending live verification)

| Field | Value |
| --- | --- |
| Domain | `dev-b1aqc523agud2k4p.us.auth0.com` |
| Client ID | `FMhkJa8azUSjflmNBTDb3keWNCUv6b3w` |
| Proposed issuer | `https://dev-b1aqc523agud2k4p.us.auth0.com/` (**trailing slash matters**) |
| Proposed authorize | `https://dev-b1aqc523agud2k4p.us.auth0.com/authorize` |
| Proposed token exchange | `https://dev-b1aqc523agud2k4p.us.auth0.com/oauth/token` |
| Proposed JWKS | `https://dev-b1aqc523agud2k4p.us.auth0.com/.well-known/jwks.json` |
| OIDC discovery | `https://dev-b1aqc523agud2k4p.us.auth0.com/.well-known/openid-configuration` |
| App origin | `https://vowsig.com` |
| Exact callback | `https://vowsig.com/auth/callback` |
| Allowed logout | `https://vowsig.com/` |
| Allowed web origin | `https://vowsig.com` |

**Verification limitation:** Public Auth0 discovery and JWKS endpoints were requested on 2026-11-04 but external HTTP retrieval was unavailable from the tools. The endpoints above follow Auth0's expected path structure and owner-provided domain; they are **not yet live-discovered or certified**. Before release, fetch and compare the actual `.well-known/openid-configuration` issuer, authorization, token, JWKS, supported RS256 signing and token-endpoint auth methods. The issuer must match the ID token `iss` **byte-for-byte**. Reject mismatches; never infer a different issuer or pin an unverified signing key.

## Mapping to VowSig's actual environment variable names

The owner may have generic `AUTH0_DOMAIN` / `AUTH0_CLIENT_ID` example variables. **VowSig does not read those names.** It reads:

```dotenv
VOWSIG_ACCOUNTS_APP_ORIGIN=https://vowsig.com
VOWSIG_OIDC_ISSUER=https://dev-b1aqc523agud2k4p.us.auth0.com/
VOWSIG_OIDC_CLIENT_ID=FMhkJa8azUSjflmNBTDb3keWNCUv6b3w
VOWSIG_OIDC_AUTHORIZATION_ENDPOINT=https://dev-b1aqc523agud2k4p.us.auth0.com/authorize
VOWSIG_OIDC_TOKEN_ENDPOINT=https://dev-b1aqc523agud2k4p.us.auth0.com/oauth/token
VOWSIG_OIDC_JWKS_URI=https://dev-b1aqc523agud2k4p.us.auth0.com/.well-known/jwks.json
VOWSIG_ACCOUNTS_FOUNDATION_ENABLED=0
VOWSIG_OIDC_AUTH_ENABLED=0
```

**Intentionally excluded:** `VOWSIG_OIDC_CLIENT_SECRET`, `VOWSIG_ACCOUNTS_CSRF_SECRET`, `VOWSIG_ACCOUNTS_DATABASE_URL` and provider API keys. These are secrets and must be generated/stored only in the approved secret store. Do not paste them in chat, GitHub, CI logs, or shell. No variables were added to the actual Railway VowSig application in this step.

The preexisting provider-neutral OIDC implementation uses static HTTPS endpoints, code+PKCE S256, nonce/state and browser binding, RS256/JWKS validation, verified-email checks and a secure opaque server session. **The Auth0 application must support confidential Regular Web Application auth-code exchange with `client_secret_post` (or adapter must be explicitly changed and retested for the configured token endpoint auth method).** Confirm code grant, RS256 and allowed callback before testing; do not enable implicit/password grants for this integration.

## Live provider setup still required

1. In Auth0, confirm **Regular Web Application**, authorization code enabled, signing algorithm RS256, callback URL saved, and token endpoint authentication method compatible with `client_secret_post`. Do not expose client secret.
2. In Authentication -> Database, enable a secure user/password connection only if that signup method is intended, configure **email verification**, login/attack rate limits, recovery behavior and social connection policy. An unverified `email_verified=false` must not create an application session.
3. Resend `mail.vowsig.com` exists but remains pending DNS verification. Add provider-generated DNS records before configuring Auth0's custom email provider. Do not send verification emails or use an unverified sender.
4. Real token exchange/PKCE/signature/JWKS/nonce/emails and owner **MFA** remain untested. Registration and login stay OFF.
5. PostgreSQL 18 runs privately on Railway, but `CN=localhost` self-signed certificate still fails the needed real-private-hostname `sslmode=verify-full` assurance. No verified live SQL access, least-privilege role, migration, independently restored backup or production accounts. No unbacked customer data allowed.

**GitHub integration acceptance:** `tests/test_vowsig_oidc_p1b.py::test_owner_auth0_public_config_exact_boundaries` checks configuration construction and deterministic redirect/PKCE bounds offline. It **cannot** attest to Auth0 account ownership, discovery availability or actual authentication.

**Production isolation:** keep PR #93 DRAFT and unmerged, `main` unchanged, live Railway deployment unchanged, feature gates OFF, and all trading/public signal policies unchanged. 
