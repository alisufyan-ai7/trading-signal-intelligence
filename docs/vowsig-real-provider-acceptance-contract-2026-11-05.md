# VowSig real-provider acceptance: public OIDC vs human-account approval

Draft PR #93, 2026-11-05. Public Auth0 metadata is not equivalent to a successful private VowSig registration.

## Preflight that can be fully automated without credentials

`python -m trading_signal_intelligence.product.accounts.auth0_public_acceptance` makes **two fixed, HTTPS GET-only, no-redirect, no-env-proxy** requests to the existing owner-selected Auth0 tenant public discovery and JWKS endpoints in a separately authorized preproduction environment. It requires exact issuer, authorized endpoints, advertised authorization-code and S256 PKCE, client_secret_post, RS256 signature support and parses at least one valid RSA-2048 public signing key. It logs no token, secret, user or JWKS content.

The command is deliberately **not scheduled in GitHub CI** and is not executed against Auth0 in this chat. CI uses a disposable httpx mock with an actual synthetic RSA signing key, tests bad issuer, bad endpoints, missing PKCE/RS256/client_secret_post, duplicate JWK identities, private-key leakage, malformed keys and HTTP errors. A PASS proves only a public metadata read at execution time, not actual customer account integrity.

## Real human/staging provider acceptance still required

In an approved nonproduction candidate with the exact private Railway verified-full app DSN, a verified Auth0 Regular Web Application, and Resend verified custom sender:
1. Confirm callback path `https://vowsig.com/auth/callback` **only for the final production domain** and separately approved nonproduction callback(s) for staging. Never replay production session cookies into staging.
2. Using a new independently controlled test identity, prove pending/unverified email cannot make an application session; then receive an actual Resend/Auth0 verification message with matching recipient, click verified link and prove verified signup creates a verified member record.
3. Prove returning login, duplicate-email different immutable issuer+subject denial, CSRF and callback replay denial, browser session rotation, logout, role/entitlement boundaries, account deletion/export and email consent handling. Do not expose tokens or test mail body in logs.
4. Run `railway_pg_acceptance.py` as the restricted `vowsig_app` role **in the exact candidate image** with existing public pinned CA and `sslmode=verify-full`; verify authenticated SQL privileges, migrations run by separate `vowsig_migrator`, owner-only history writes impossible.
5. Owner enrollment remains **offline two-person signed** (`vowsig_owner_offline_operator.py`) with independent identity re-verification, separate reviewer/operator, already verified member identity, owner-controlled TOTP secret, fresh code confirmation, session revocation and recovery test under authorized migration-only credentials. No public owner-promote endpoint exists.
6. After **all** gates pass, owner signs a precise release SHA, one complete enabled production deployment, and independently rehearsed rollback. This command alone can never authorize release. Keep paid/Auth0 plan changes and broker trading disabled.

## Governance and limits

No real Auth0 login was attempted, no email sent, no restricted Railway SQL queried, no MFA owner promoted, and no production deployment made by this repository-only engineering. The owner-approved Railway PostgreSQL recovery deferral remains first action immediately postlaunch, with `DATABASE_RECOVERY_UNVERIFIED` until an actual independent encrypted S3/B2 cold restore proves recovery.
