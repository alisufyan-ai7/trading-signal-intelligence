# VowSig account infrastructure: PostgreSQL 18, Auth0 and Resend pre-production checkpoint

**Date:** 2026-11-04. **Scope:** Owner authorized infrastructure tests and Auth0/Resend setup preparation in parallel. This document is the no-secrets release handoff. The production VowSig website, runtime, trading system and `main` branch remain untouched. Customer registration is disabled.

## 1. PostgreSQL service and safe verification boundary

Already provisioned in the existing Railway project `positioning-engine-cron`, `production`, Singapore:
- PostgreSQL **18.6** server, from `ghcr.io/railwayapp-templates/postgres-ssl:18`; database service `74a3e855-d97c-4b81-8a27-092f048f9af3`, 5 GB persistent volume, internal-only DNS; no public proxy.
- Running / 1 replica healthy. Live VowSig `tradingtop-early-access` deployment unchanged; no app connection string or account feature flags added.
- This PR's isolated PostgreSQL CI service is now **`postgres:18-alpine`** for schema and account regression. The CI instance is an explicitly disposable local fixture and cannot connect to Railway.
- Railway logs show generated **self-signed certificate `CN=localhost`**, not the actual private Railway service DNS identity. Do not silently downgrade the production store's `sslmode=verify-full`, or assume that a certificate generated for localhost verifies the private hostname.
- No authenticated SQL, customer schema migration, least-privilege role, certificate chain/SAN, automated recovery or restore has yet been demonstrated on the new Railway database.
- No paid automatic backups available on current plan (confirmed by owner screenshot). No real customer information allowed until independent recoverable backups/restore tests and verified TLS.
- Before a SQL or application connection, select and test an audited certificate/hostname remedy: a server certificate with SAN matching the exact private hostname, trusted issuer/CA delivered privately to the client, consistent service lifecycle and renewal, and **active** validation of `sslmode=verify-full` from the application's network. Replacement images/cert rotation on an existing database with no backup must not be attempted as ad hoc production changes. A newly provisioned isolated disposable staging DB/service with a compatible image/cert chain is an acceptable experiment, not a customer rollout.
- Runtime app role cannot own schema or perform DDL; separate migration role. Test migrations 001–006, rollback and isolation only after transport, restore and role security are established.

## 2. Auth0 owner setup (not provisioned in this turn)

**Selected plan:** Managed Auth0 tenant for OIDC authorization code + PKCE. User creates and controls tenant. No Auth0 admin connector is installed, therefore this chat cannot create the tenant or configure its dashboard without the user connecting a suitable provider management capability.

Proposed **Regular Web Application**, name **VowSig Web**, callback URLs and origins:

| Auth0 field | Proposed value |
| --- | --- |
| Application Type | Regular Web Application |
| Allowed Callback URLs | `https://vowsig.com/auth/callback` |
| Allowed Logout URLs | `https://vowsig.com/` |
| Allowed Web Origins | `https://vowsig.com` |
| Application Login URI (if supported) | `https://vowsig.com/auth/start` |
| ID token signing | RS256 (as currently verified by adapter) |
| OAuth/OIDC flow | Authorization Code + PKCE S256, `openid email` |
| Email requirement | Verified email from trusted provider claims, immutable issuer+subject linking |
| Owner admin access | Separate approved MFA evidence; no automatic owner role bootstrap |

The deployed application must use **the exact Auth0 issuer, client ID, HTTPS authorization endpoint, token endpoint, JWKS URI, app origin and protected client secret** in provider-side environment variables. These are not available yet. Enable email verification at the provider, enforce anti-abuse and verify real callback/claim behavior. **Do not** paste client secrets into GitHub or chat.

Adapter configuration already exists in PR #93: `VOWSIG_OIDC_AUTH_ENABLED=0` by default and the separate `VOWSIG_ACCOUNTS_FOUNDATION_ENABLED=0`. Both must remain OFF until full launch review.

## 3. Resend sending domain (CREATED but DNS unverified)

A **dedicated transactional subdomain** `mail.vowsig.com` was created in the connected Resend account in **`ap-northeast-1`** under domain ID `10686485-4582-4912-884f-7d746fd73e56`; status initially `not_started`. Sending enabled, receiving disabled. Open/click tracking OFF; outgoing TLS opportunistic (recipient compatibility; application-to-provider API TLS separately validated).

DNS entries returned by the provider for the `vowsig.com` DNS zone:

| Type | Relative host | Value | Other |
| --- | --- | --- | --- |
| TXT (DKIM) | `resend._domainkey.mail` | Owner-visible generated public DKIM record from Resend console/chat (do not confuse with secret keys) | TTL auto |
| MX (return-path, NOT website mail) | `send.mail` | `feedback-smtp.ap-northeast-1.amazonses.com` | Priority 10, TTL auto |
| TXT (SPF) | `send.mail` | `v=spf1 include:amazonses.com ~all` | TTL auto |
| CNAME | `rsend.mail` | `send.forge.rmta.net` | TTL auto |

Do not alter existing root/apex MX, website A/CNAME or other application records. User with DNS access must add these records and confirm. Then run Resend domain verification using the connected app; verify DKIM/SPF status before enabling email sending. A Resend sending account/domain is not an OIDC identity provider and does not itself implement Auth0 signup or MFA.

Do not issue a Resend sending API key or send messages before DNS verification, sender policy and an approved integration. Configure transactional sender e.g. `accounts@mail.vowsig.com` only after verification, and privacy-safe templates without research/trading signals.

## 4. Parallel release gates and controls

- **Done:** PostgreSQL service online and private; Resend sending domain registered; CI PostgreSQL 18 compatibility regression launched; Auth0 setup contract recorded.
- **Pending:** authenticated SQL, verified strict TLS, least-privilege roles, actual migration/revert, tested cold backup/restore, Auth0 tenant and real email verification/MFA, Resend DNS verified and end-to-end sending, user-facing policy/consent UAT.
- **No merge or deployment:** PR #93 stays DRAFT/unmerged. Never activate account flags or customer signup merely because isolated CI succeeded. Product per-signal access and broker execution remain unchanged.
- **Owner external actions:** Add four DNS records; create Auth0 tenant + Regular Web Application and share only nonsensitive issuer domain/application ID (not secret). Railway database security, backup and integration work can proceed as separate isolated experiments.

This document is operational progress, not a production-security certification or approval for onboarding customers.
