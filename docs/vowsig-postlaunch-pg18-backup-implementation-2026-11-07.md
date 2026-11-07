# VowSig postlaunch PostgreSQL 18 backup and recovery — 2026-11-07

## Current verified production state

GitHub PR #93 is merged. Final production receipt: https://github.com/alisufyan-ai7/trading-signal-intelligence/pull/93#issuecomment-6686667690.

Read-only Railway state, 2026-11-07: production app tradingtop-early-access ONLINE (source commit aa74a9b11de96a2f254c1ad9f90bc3c3dfa88dbe, deployment c154324e-a18a-44ee-858d-e64dbd62aec9); Postgres PG18 ONLINE. Both persistent volumes remain mounted; there are zero pending changes and no reported recent failures. Older launch-pending sections in some runbooks are superseded by this live receipt. DO NOT rerun production PG migrations 001–010, role/password creation, or existing owner-reported TLS/privilege checks. DO NOT redeploy the web app merely for documentation.

**DATABASE_RECOVERY_UNVERIFIED** is the current honest state: no real encrypted production copy and no independently verified isolated cold restore have yet been proven.

## Implemented in this engineering branch

1. ops/pg_recovery/backup.py: native PG18 pg_dump -Fc of the entire accessible logical database with restricted vowsig_backup role and postgres.railway.internal TLS verify-full using pinned public CA. Plaintext passes in process memory directly to age X25519 encryption, never a plaintext disk archive.
2. ops/pg_recovery/Dockerfile: a dedicated finite cron worker, postgres:18-bookworm, Python, boto3 and age, non-root, carrying only the public pinned CA; not the public web image.
3. One unique encrypted ciphertext and a non-sensitive SHA256/UTC manifest are placed at independent AWS S3 and Backblaze B2 paths beneath vowsig/railway-pg18/customer-db/v1/. The worker downloads the *entire ciphertext* separately from each provider to hash/size verify it, and compares stored manifest bytes; either failure exits nonzero. No overwrites, cloud delete code or retention pruning.
4. ops/pg_recovery/verify_restore.py: independent owner-held private-age-key decrypt and pg_restore into a NEW, disposable loopback-only PG18 database, with strict name guard, explicit confirmation and required VowSig account/session/watchlist/consent schema checks. It cannot connect to Railway or replace existing databases.
5. tests/test_vowsig_pg_backup_worker.py: offline mocks for dual copy equality, second-provider corruption refusal, restricted SSL/role guard, and isolated restore guard. Locally: four pytest tests PASS. This is NOT a provider, production backup or real restore acceptance.

## One consolidated owner-controlled activation

This branch must be reviewed before deploying a separate production Railway worker. Never paste DSNs/passwords, API keys, private age key, OAuth/TOTP secrets or customer data into this chat or GitHub.

- Generate an owner-held age identity on trusted hardware using: age-keygen -o vowsig-pg18-recovery.agekey . Preserve the private file offline and provide ONLY its age1... public recipient to worker variable AGE_BACKUP_RECIPIENT. The backup worker never contains the age private key.
- In existing Railway positioning-engine-cron / production, provision a SEPARATE cron worker from this repository with Dockerfile path ops/pg_recovery/Dockerfile, daily schedule 15 3 * * * UTC, one replica, restart NEVER. Do not change tradingtop-early-access, Postgres, /data, the current publisher or VPS tasks. Treat this as a production deployment requiring separate explicit approval. GitHub main merges may automatically redeploy the app; do not merge solely as a documentation update.
- Configure dedicated worker-only private variables: VOWSIG_PG_BACKUP_DSN (existing vowsig_backup role, not app or migrator, private DNS, sslmode=verify-full and sslrootcert=/app/config/tls/railway-postgres-root-ca-20261104.pem), AGE_BACKUP_RECIPIENT, AWS_BACKUP_REGION, AWS_BACKUP_BUCKET, AWS_BACKUP_ACCESS_KEY_ID, AWS_BACKUP_SECRET_ACCESS_KEY, B2_BACKUP_ENDPOINT (HTTPS *.backblazeb2.com), B2_BACKUP_REGION, B2_BACKUP_BUCKET, B2_BACKUP_KEY_ID, B2_BACKUP_APP_KEY. Reuse authorized buckets only with separately restricted PutObject/GetObject prefixes and no DeleteObject; never mix with existing Windows S02 credential scope.
- Run one real job and retain sanitized status DUAL_CIPHERTEXT_UPLOAD_VERIFIED, UTC ID, ciphertext SHA, provider evidence. Its successful encrypted cloud read-back is NOT equivalent to actual cold restore.

## Mandatory independent dual-provider recovery

Retrieve a selected matching encrypted object and JSON manifest separately from each provider. On owner-controlled isolated disposable local PostgreSQL 18 with age, createdb, pg_restore, psql and Python 3.11+, keep the PRIVATE age identity on that host only. Privately set VOWSIG_LOCAL_RESTORE_CONFIRM=YES_ISOLATED_THROWAWAY_PG18 and VOWSIG_LOCAL_RESTORE_PASSWORD for the local temporary Postgres superuser; run the verifier on the AWS pair, using a new unique destination of form vowsig_restore_verify_aws_aabbccdd, and on the B2 pair with a different new destination vowsig_restore_verify_b2_11223344. Example invocation:

    python ops/pg_recovery/verify_restore.py aws.age aws.json owner.agekey vowsig_restore_verify_aws_aabbccdd

The helper never drops a database, only creates a brand new loopback-local database. Its checks cannot certify role/global-object restoration, Auth0 state, TOTP key custody or the web /data volume; those require the separate full disaster recovery runbook. Private customer records in the isolated restored database must be handled confidentially and securely disposed of after explicit cleanup approval. A real restore PASS requires actual production-origin backups from BOTH providers, independently decrypted and restored. Until then, keep DATABASE_RECOVERY_UNVERIFIED.

## Remaining acceptance: alerting and retention

Railway cron runs without user login; monitor nonzero execution failure and backup age under 36 hours. **BACKUP_ALERT_DELIVERY=HOLD**: no independent email/incident alert delivery has been configured or tested by this branch; add a separate owner-approved Railway or Resend failure notification before declaring automatic backups fully operational. The proposed PG backup retention selection is 30 daily, 8 weekly, 12 monthly; existing approval of this policy was specific to S02 backup data, NOT permission for PG cloud pruning. This worker stores every backup and performs ZERO provider deletions. Pruning requires independent owner approval, a signed list of versions, seven-day grace and proof of retained restores.

No production service, credentials, database, AWS/B2 object or scheduler was modified by creating this engineering branch. Next step is review exact PR HEAD and CI, obtain owner production-worker authorization, run the first encrypted paired backup and independently verify two cold restores, then document honest live receipts. Only then continue pending real production member and first-owner MFA acceptance.
