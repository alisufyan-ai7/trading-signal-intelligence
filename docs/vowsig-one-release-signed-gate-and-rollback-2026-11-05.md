# VowSig single coordinated fully enabled release — owner-signed preflight boundary

2026-11-05. Implementation in draft PR #93, NOT a launch or provider-verification claim.

The owner explicitly rejects a feature-disabled live deployment. The only planned go-live includes Free Auth0 signup, verified sessions, Resend delivery, fully working Signal Center and owner diagnostics/Performance Lab with independently certified source histories. Broker execution remains off and six noncore markets cannot expose unapproved per-signal details. The separate new Railway PostgreSQL automatic encrypted offsite backup is **first immediate postlaunch** by explicit owner-accepted temporary data-loss risk; status stays `DATABASE_RECOVERY_UNVERIFIED`.

## Strict one-signature evidence bundle

`src/trading_signal_intelligence/product/accounts/release_acceptance.py` and its manual CLI reject any bundle unless:
- an externally obtained **owner-trusted reviewer public Ed25519 PEM** has an independently pinned SHA256; signature over canonical JSON validates, reviewer cannot be the independent source-history reviewer; no signer private key is distributed in app/CI;
- exact 40-character candidate Git SHA and existing `main` SHA match the reviewed bundle; PR #93, single full release, SHADOW_ONLY, original source independently reviewed, customer exposure and postlaunch recovery policy are all explicit;
- every mandatory gate below has one private full receipt SHA256, timestamp, distinct human reviewer identity, exact candidate SHA, typed origin, `PASS` and independent evidence custody: exact-head CI, public Auth0 issuer/JWKS, real verified signup, unverified/collision/replay denial, real return login/logout, actual Resend delivery, real Railway app SQL verified-full/role and migration-role isolation, offline two-person owner factor enrollment and step-up/recovery, all nine original AI ledgers' complete after-cost rights review, natural crypto K5 H1/H4 opportunity census, independently signed full-universe manifest, actual owner/admin performance and nine market reliability, customer entitlements/privacy, fresh public publisher continuity, staging browser/security, and an exact-candidate rollback rehearsal;
- evidence is recent and the reviewer signed **after** the newest receipt. Extra keys and unknown fields are refused to avoid accidentally embedding email, account identifiers, secrets or misleading flags.

A PASS from this program certifies only *that a trusted named reviewer signed those complete declared evidence fields*, not the truth of providers or source rights. The reviewer must separately inspect the exact protected receipts and real running systems. The tool returns `production_release_automatically_authorized=false` and `owner_exact_sha_merge_deploy_approval_still_required=true` **unconditionally**.

Run only after all underlying tests have occurred, with independently trusted public key and signed bytes stored privately:

```text
python -m trading_signal_intelligence.product.accounts.release_acceptance --signed-receipts <PRIVATE_SIGNED_JSON> --trusted-public-key <REVIEWED_PUBLIC_PEM> --trusted-public-key-sha256 <PIN_FROM_SEPARATE_CUSTODY> --expected-candidate-sha <EXACT_TESTED_PR_HEAD> --expected-main-sha <EXACT_UNCHANGED_MAIN_SHA>
```

No actual release manifests, reviewer key or credential is created by PR. The synthetic CI generates disposable Ed25519 keys and explicitly proves all safety/availability gates fail closed when missing, forged, stale, old HEAD or wrongly scoped. **Do not use CI's synthetic signatures to authorize production.**

## Coordinated staging and rollback

In one approved preproduction candidate deployment, verify immutable image digest and exact PR SHA, migrations with separate vowsig_migrator role, real Auth0 email/Resend flow, restricted PG SQL, signed owner MFA offline enrollment and live session rotation, original reviewed historical cohort ingestion (no public unapproved signals), all owner and Free member paths, publisher freshness and safe 429 diagnostics. Rehearse rollback restoring old public image and prior app behavior WITHOUT downgrading/rewriting database state or stopping Windows scanner/publisher tasks; make migration compatibility explicit. Test release/rollback against the **same** candidate digest. Then the human owner must approve an exact SHA and a single fully enabled go-live. Never interpret a signed test receipt as permission to merge/deploy.

### What cannot be completed solely from GitHub

Actual Auth0 signup/verified email, Resend delivery, authenticated private Railway app SQL, human identity attestation and authenticator enrollment, independent outside-source market data/rights review, and an actual staging+rollback session cannot be claimed from GitHub synthetic CI. They require the owner/provider-controlled test environment and confidential receipts. No provider account has been changed, migrations not applied to Railway, and no production features enabled here.
