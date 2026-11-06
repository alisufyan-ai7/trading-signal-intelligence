# P1B-1 provider-neutral OIDC authorization-code integration — review gate

**2026-11-04.** Implementation on draft PR #93; **not merged or deployed**. Railway PostgreSQL remains the approved destination for customer-account storage, but no provider service has been provisioned and no production credentials have been configured. Authentication is **explicitly OFF by default** even if the accounts foundation is enabled.

## What is implemented (owner-independent)

- `accounts/oidc_provider.py`: exact operator-specified HTTPS issuer, authorization, token and JWKS URLs; authorization-code flow with S256 PKCE, 32-byte CSPRNG state, nonce, browser binding and code verifier. Authorization requests use `max_age=600`; only `openid email` scopes and fixed first-party callback. All redirects are fixed, not chosen by request data.
- Callback uses an **atomic PostgreSQL DELETE ... RETURNING** of one-time authorization state, matched with the 32-byte server-issued `__Host-vowsig_oidc` browser cookie, Secure/HttpOnly/Path=/SameSite=Lax and ten-minute expiry. A duplicate callback or wrong browser cannot complete the session.
- HTTP token exchange uses fixed HTTPS endpoints, TLS, bounded short timeouts and rejects redirects, oversized JSON, unknown public keys, malformed content and provider errors. Signed ID-token signature is verified with the exact configured issuer, client ID audience, allowlisted **RS256** algorithm and exact `kid` JWKS key; mandatory `iat`, `exp`, `nonce`, `auth_time`, `email`, `email_verified`, `sub`, `aud`, `iss`. Multiple audiences require exact `azp`. No raw provider token, secret or request metadata is persisted in customer database or exposed in responses.
- Only after signature, issuer/audience, nonce, verified email and freshness checks does `issue_verified_session` transactionally create/reuse an exact issuer+subject-bound member account and issue a 32-byte opaque server session. The browser receives `__Host-vowsig_session` (Secure/HttpOnly/SameSite=Lax/Path=/). A new login revokes older sessions. No owner role or MFA grant is derived from an ID token.
- `sql/accounts/006_oidc_auth_transactions.sql` adds bounded auth-state and coarse ten-minute SQL peer rate-window tables (30 login starts per window). Peer ID is HMAC-hashed; no plaintext IP is stored. Use the trusted ASGI peer, not user-controlled X-Forwarded-For.
- Tests include local/mock RS256 signing and negative JWT signature, issuer, audience, expiry, email and nonce checks; state-cookie binding, replay, duplicate callback params, rate limits and disposable PostgreSQL expiry/consume logic.
- **Feature flags:** `VOWSIG_ACCOUNTS_FOUNDATION_ENABLED=0` and independently `VOWSIG_OIDC_AUTH_ENABLED=0` by default. OIDC routes do not exist unless *both* are separately enabled and all required provider settings are present. Existing public v1 APIs, Windows scanners, S02 backups and trading execution remain untouched.

## Configuration contract (no values are set here)

`VOWSIG_OIDC_ISSUER`, `VOWSIG_OIDC_CLIENT_ID`, `VOWSIG_OIDC_AUTHORIZATION_ENDPOINT`, `VOWSIG_OIDC_TOKEN_ENDPOINT`, `VOWSIG_OIDC_JWKS_URI` and optional `VOWSIG_OIDC_CLIENT_SECRET` must be exact values from the provider's registration. Application origin comes from the existing `VOWSIG_ACCOUNTS_APP_ORIGIN` and callback is always `/auth/callback`. The provider must support RS256 ID-token signatures, verified email and OIDC `auth_time` on a `max_age` request. A provider requiring a different algorithm/claim contract requires explicit reviewed implementation—not permissive fallback.

## Remaining release gates (not coding blockers for other priorities)

Provider selection + verified sender, owner MFA enrollment/recent auth proof, real provider claims and JWKS rotation test, TLS/DNS/network and Railway Postgres CA/rollback/backup/restore, browser cross-device/race validation and abuse throttling behind the real reverse proxy, legal/privacy review, origin/HTTPS settings and production canary. Client-secret management must use provider secret storage; do not paste it in chat or GitHub. This contract does not claim real provider verification, email deliverability or production signup availability.

**Owner-independent progress should continue** with the source-hash-reconciled read-model ingestion framework, mobile/browser E2E QA and release-candidate checks in the same PR. No new PR or production deployment is needed to test this code in isolated CI.
