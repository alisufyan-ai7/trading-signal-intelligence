# VowSig — owner-approved single-founder initial owner MFA exception

**Date:** 2026-11-06. **Status: proposed staging-only implementation in DRAFT PR #93; NOT YET EXECUTED, NOT a waiver of independent source-history attestation, NOT production approval.**

## Owner decision

The product owner explicitly indicated they are the **sole founder/operator**, already possess the verified member account and a Google Authenticator app, and request self-authorization rather than recruiting a second human for initial owner promotion. This is an **explicit exception** to the original two-person reviewer/operator requirement of `docs/vowsig-owner-bootstrap-recovery-signed-operator-2026-11-04.md`. It has **lower human separation-of-duties assurance** and must be labeled accurately in logs, the operator receipt and the release evidence. No invented alternate reviewer/operator identity is permitted.

This is **not** an exception for rotating an existing owner factor, account recovery, new owners, paying features, cloud/SQL privilege bypass, historical rights proof, independent crypto K5 review or production release. Those remain separate.

## The narrow technical implementation

- `first_owner_solo` is an **explicit signed one-use operation**, not a general permission flag or HTTP endpoint. The approval still names an existing canonical UUIDv4, exact OIDC issuer and SHA256 of immutable OIDC subject, owner verified and consenting, bounded UTC approval expiry no longer than 1 hour and a pinned independent-from-web-runtime Ed25519 key held by the founder privately.
- The offline operator CLI requires `--solo-founder-first-owner` and `--acknowledge-solo I_ACCEPT_FIRST_OWNER_SELF_AUTHORIZATION_NO_INDEPENDENT_REVIEW`, in addition to the existing `--mode apply`, interactive terminal and `--acknowledge I_APPROVE_ONE_OFF_OWNER_SESSION_REVOCATION`.
- The signed approval's `reviewer_id` and the operator's `--operator-id` **must be the same truthful founder identity**. The pre-existing normal `first_owner` and `rotate_factor` continue to require **different persons**.
- Server-side offline apply still verifies no owner exists, exact verified/active member, migrator-only SQL role, single-use approval under locked transaction, fresh Google Authenticator TOTP, AES-256-GCM encryption under 256-bit master key, session revocation, immutable audit entry and fresh login; it does not expose the factor to GitHub, HTTP logs or chat.
- Migration `sql/accounts/010_single_founder_first_owner_exception.sql` changes only the audit table's operation/actor constraints, allowing `first_owner_solo` + same actor and preserving the original separation constraint for other operations. No new role grants, public endpoint, login change or original data-migration rerun. **Apply this migration ONLY once to staging first, after exact-HEAD CI and secure migrator operator review.**
- The original offline signing helper requires an encrypted Ed25519 key and a private interactive workstation; neither an AI assistant nor CI is a trusted human reviewer. Founder self-signature is specifically labeled **self-approved**, not independently reviewed.
- Enrolled TOTP secret and its 256-bit encryption master key must remain safely recoverable **outside GitHub, chat and public sites**. The web-runtime must receive only its needed encryption master key through approved secure Railway configuration after staging review; an improperly configured key causes owner step-up to fail closed.

## Required safe staging execution sequence

1. Review and independently validate the new GitHub code and 010 migration; ensure CI passes and staging postgres is still a restricted migrator-owned 001–009 schema.
2. Confirm the existing staging verified Auth0 member **exact issuer and immutable subject hash/account UUID** via legitimate authenticated session and restricted DB access (never use email address as identity binding; do not paste raw identity hashes or account IDs in public GitHub comments).
3. Founder generates and securely retains an encrypted offline Ed25519 signing key and pinned public key, 256-bit owner encryption master key, and a **new** random TOTP 160-bit secret; adds the 32-character Base32 value manually in Google Authenticator using a private secure interface.
4. Founder signs a one-use, max-60-minute `first_owner_solo` approval for that exact account. Do not store passwords/keys/TOTP secret in PR, chat, logs or shell command history.
5. **Staging ONLY:** execute 010 under the dedicated `vowsig_migrator` with verified-full private TLS, then run offline provisioning in PREVIEW, then founder explicitly executes APPLY with both acknowledgements in a real secure interactive operator terminal. This cannot be performed directly from the Windows production VPS using `postgres.railway.internal`; that private hostname resolves only on the appropriate Railway network. Do not expose the staging PG server publicly merely to satisfy this procedure. If secure operator access inside the staging private network is unavailable, **HOLD and arrange a supported safe access path**, not an open TCP proxy.
6. Existing member sessions are revoked at promotion. The owner logs in again using real Auth0, confirms Google Authenticator step-up, tests `/admin/`, views true unavailable state for uncertified Performance Lab metrics, and confirms guest/nonowner HTTP 401/403.
7. Preserve a sanitized receipt with `operation=first_owner_solo`, `solo_founder_exception=true`, `independent_reviewer_involved=false`; do not claim the original two-person gate passed.

## Remaining release policy alignment

The older one-release signed receipt gate `src/trading_signal_intelligence/product/accounts/release_acceptance.py` still expects **two-person** evidence for MFA enrollment and factor recovery. Before **any** final production release signature, the owner needs a separately reviewed, explicit exception amendment in that gate with a truthful single-founder receipt type and stated reduced assurance. **This draft does not silently make the existing signed release gate PASS.**

This exception does not amend independent nine-market original source rights/K5/after-cost verification or distinct signed cohort/universe requirements. The owner explicitly wants launch quickly, but no unsupported historical figures or bypassed role controls are allowed. The separate new Railway PostgreSQL encrypted offsite cold restore remains the already-approved first immediate postlaunch task.

**No production or staging database role has been changed merely by adding this code.**
