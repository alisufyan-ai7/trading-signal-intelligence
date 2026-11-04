# VowSig signed offline owner bootstrap and factor recovery — 2026-11-04

## Owner decision and boundary

This is REVIEW-ONLY engineering under draft PR #93. The public web app must not create or promote an owner, enroll/rotate an owner factor, recover an owner without independent approval, or use paid Auth0 MFA. The owner requests one complete enabled release with accounts, full owner/admin, and independently reconciled historical analytics. Newly encrypted Railway PostgreSQL S3/B2 backups are deferred to immediately after go-live by the owner's explicit risk acceptance. Nothing here authorizes a current production deployment.

## Two-person source-of-authority protocol

A distinct human reviewer (not the DB operator) independently re-verifies the actual owner's identity and consent through an offline channel, validates the exact existing Auth0 issuer plus immutable subject (never matching by email alone), and signs a time-limited, one-use Ed25519 approval with a private key kept outside the application, repository and operator environment.

The signed approval envelope has exactly two fields: authorization and signature_ed25519_b64u. The authorization object has exactly: schema_version=1; purpose=VOWSIG_OFFLINE_OWNER_MFA_V1; operation_id as fresh UUIDv4; operation=first_owner or rotate_factor; account_id as the existing canonical UUIDv4; oidc_issuer as the exact provider issuer; oidc_subject_sha256 as SHA256 of the UTF-8 immutable provider subject; reviewer_id; approved_at_utc and expires_at_utc as UTC Z timestamps no more than 60 minutes apart; owner_identity_reverified=true; owner_consent_confirmed=true.

The reviewer runs scripts/vowsig_owner_review_sign_offline.py on an OFFLINE interactive host with a password-encrypted Ed25519 signing key protected as a private local file. That helper refuses CI and Railway, refuses shared-access or unencrypted key files, reads its password invisibly, verifies its newly signed document, and writes a new private (0600) signed file without overwrite. Its public verification key SHA256 is delivered through a separately authenticated channel. Neither its private signing key nor the owner's factors/passwords are written to GitHub or chat.

The separate operator securely obtains the signed document, reviewer's PUBLIC key, a DB migrator secret and a 256-bit owner TOTP master encryption key. Use a verified-full private Railway PostgreSQL DSN as user vowsig_migrator, with the existing owner-pinned public CA and a private secret store; never paste the DSN or key. The default offline command in scripts/vowsig_owner_offline_operator.py is READ-ONLY preview. It enforces reviewer signature and key pin, exact immutable existing Auth0 identity, active verified account and entitlement, global first-owner uniqueness and single-use approval.

After independent approval and explicit human confirmation, the owner enrolls a fresh 160-bit random TOTP secret (generated locally, not in the web app) in their authenticator, and confirms a current six-digit code. To APPLY, the operator must pass --mode apply, their own different --operator-id, and --acknowledge I_APPROVE_ONE_OFF_OWNER_SESSION_REVOCATION. The operator CLI requires a real interactive terminal, prompts invisibly for the new enrolled 32-character Base32 secret and current code, and never prints either value. It is not a production background task.

## Atomic migration operation

Migration 009 creates a new append-only, migrator-only owner provisioning audit record: operation_id, account_id, operation, reviewer ID, distinct operator ID, signed approval SHA256 and number of revoked sessions. Only the migrator can insert and record it; the runtime app has no audit-table DML permissions.

The operator re-verifies the signed approval *within the apply function*, checks current PostgreSQL role vowsig_migrator, locks the owner provisioning audit table to serialize first-owner operations, locks and checks the exact account and immutable identity, rejects replay and checks the owner's live TOTP code. For first_owner it requires NO existing owner and a verified member; inserts the UUID-bound AES-256-GCM encrypted owner factor and grants role=owner. For rotate_factor it requires an already verified owner and existing factor; replaces ciphertext and clears the replay/lock counters. Both revoke ALL existing sessions, append the unique signed approval audit record and commit atomically. A new verified login and fresh TOTP are required. Failure rolls back the entire transaction. The public app cannot mint an owner and cannot read or set the reviewer signing key.

This is not a complete human recovery procedure by itself. Production acceptance still requires independently verifying the actual owner, encrypted signing-key and master-key backup/recovery custody, independent reviewer trust-anchor governance, and real Auth0/recovery/session-replay UAT with a second person. A reviewer signature authenticates approval; it does not automatically prove offline identity checks happened.

## Disposable CI proof

The new synthetic tests verify signed Ed25519 approvals and strict one-hour expiry, duplicate/altered authorization rejection, wrong key pins, exact account identity, replay rejection, first-owner uniqueness, recovered-factor rotation, cross-operator separation, old-session revocation, and denied app-runtime audit writes. The isolated PostgreSQL 18 CI test runs after the 16-table restricted-role and schema test. All identities, TOTP secrets and keys are synthetic; the test never connects to Railway. CI PASS is not evidence of real owner enrollment or live DB authentication.

## Status of the combined VowSig release

One complete feature-enabled customer-facing launch remains required, with full Signal Center and admin analytics plus independently verified original-ledger histories. The offline owner workflow is one security prerequisite; original ledger audit coverage, full historical after-cost reconciliation, functional owner operations, actual Auth0 login and final exact-SHA rollback tests remain separate release requirements. No paid Auth0 tier and no broker execution.
