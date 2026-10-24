# VowSig manual dual-cloud S02 backup + disaster restore — operator handbook

Status: **REAL-CLOUD-CAPABLE CODE IN DRAFT PR #85; NOT YET TESTED AGAINST ACTUAL ACCOUNTS OR DEPLOYED.** A synthetic/fake test or source code alone is not proof of live backup. Owner 2026-10-24 decision permits **minimal charges**; $0 is preferred, NOT a mandatory absolute spending gate. Earlier Issue #67 hard $0 restrictions were superseded.

## Outcome and supported data scope

This practical v0.1 implementation is for ONE specific application SQLite database **`data/forward.sqlite` (S02)**, max **16 MiB plaintext per backup**. It does not silently pull `data/research.sqlite`, raw MT5 feeds, private external market streams, customer archives or every SQLite in the repository. The current project owner requested backup of the app's own S02 evidence and accepts minimal provider costs. Third-party license terms remain an operational responsibility; only include legally permitted content. There is no automatic license verification or invented assurance.

Two independently scoped accounts/destinations:

- AWS S3: private `vowsig-backup-s3-2026`, region `us-east-1`, SigV4 endpoint `https://s3.us-east-1.amazonaws.com`.
- Backblaze B2: private `vowsig-backup-b2-2026`, region `us-east-005`, S3 API endpoint `https://s3.us-east-005.backblazeb2.com`.

Both data and manifest keys use owner-confirmed scoped `pilot/` prefixes. A uniquely random run ID makes cross-run overwrite extremely unlikely. AWS PUT uses conditional `IfNoneMatch="*"`. B2 compatible S3 API uses preflight HEAD then PUT (not an atomic no-overwrite guarantee); duplicate runs never reuse IDs and the code does not intentionally overwrite, retry, delete or prune. Each PUT must return an **exact object VersionId** and pass a separate reader identity's versioned GET byte-for-byte readback.

### Encryption and independent recovery

- The application SQLite file is captured with read-only online SQLite backup; integrity, append-only triggers and canonical record hashes are validated. A fresh 256-bit random data key encrypts the snapshot with P1 AES-256-GCM; no plaintext is uploaded.
- A recovery manifest contains the random data key and both provider exact VersionIds, object SHA, private key, count and run identity **inside an AES-256-GCM encrypted envelope**. Its encryption key is derived using `hashlib.scrypt` with fresh salt from an **owner-entered 16+-character recovery passphrase**, which is **never saved by the program or displayed**. The owner MUST separately retain this passphrase in an off-VPS password manager; loss makes backups undecryptable.
- The same sealed manifest is stored and read back from **both AWS/B2**, under `pilot/vowsig/backup-receipts/v1/<backup_id>.aesgcm`; also retained as a local encrypted contingency file outside the repository. At least one independent cloud manifest plus one accessible provider data version plus passphrase allows disaster recovery. This is genuinely different from prior P7 fake-only receipt callbacks.
- The restore command takes the printed nonsensitive `backup_id`, owner-entered **reader-only** keys and passphrase; decrypts/authenticates the cloud manifest, requests each exact pinned data VersionId from AWS/B2, decrypts and rechecks the full S02 SQLite chain from independent memory/temporary scratch, then writes one new SQLite file **with no overwrite**. One-provider-only restore reports `BACKUP_RECOVERY_DEGRADED_ONE_PROVIDER`, not dual success.
- No default AWS credentials, network action on import, environment passwords, `.env`, CLI secrets, persistent credential files or scheduled tasks. Four owner-held keypairs are entered only via masked RDP console prompts for backup (AWS writer, AWS reader, B2 writer, B2 reader); recovery prompts only AWS/B2 reader keypairs.

### Explicit real operation path — only after final reviewed acceptance

Run from manually started **interactive Windows VPS PowerShell**, in a SHA-verified disposable checkout using the previously existing Python 3.12 and locally installed exact pinned seven AWS SDK wheels, with `PYTHONPATH` set to disposable `src` and pinned SDK packages. **DO NOT** run the operator as scheduled/automated service. Do not put any credential/passphrase in command-line arguments, stdin pipes, environment variables, files, logs or GitHub.

Offline status command (zero provider calls):

`python scripts/vowsig_dual_cloud_backup.py status`

Real one-shot backup (intentional real AWS/B2 network operations and possible small charges):

`python scripts/vowsig_dual_cloud_backup.py backup --repo-root "C:\Users\Administrator\Desktop\Signal Projects\trading-signal-intelligence" --receipt-dir "C:\Users\Administrator\AppData\Local\VowSig\EncryptedBackupReceipts" --acknowledge-real-cloud-cost I_ACCEPT_MINIMAL_CLOUD_COSTS --acknowledge-s02-only APPROVED_S02_DATABASE_ONLY`

Exact-version recovery to NEW file; use the `backup_id` in sanitized success output and **the same passphrase**:

`python scripts/vowsig_dual_cloud_backup.py restore --backup-id backup-<32-hex> --output "C:\Users\Administrator\Desktop\vowsig-recovered-s02.sqlite" --acknowledge-real-cloud-cost I_ACCEPT_MINIMAL_CLOUD_COSTS`

A `--local-receipt <path>` option allows independently decrypting the encrypted VPS contingency file, but no live-source checkout or writer credential is required for cloud restore. **Do not ever restore directly over production `data/forward.sqlite`.**

### Failure, cost, and retention

- One run is at most 16 MiB plaintext encrypted, two data PUTs, two encrypted manifest PUTs, B2 existence checks, and bounded exact-version reads/restores. **Small cost intended, not mathematically guaranteed zero**; provider pricing, versions retained, retrieval and API transactions may incur charges. Run manually, check AWS Cost Explorer/B2 reports and free usage before enabling any repetition. There is currently no automatic retention cleanup—versions accumulate. Do not claim an annual $0 budget.
- Any ambiguous partial upload fails with fixed `DATA_UPLOAD_PARTIAL_OR_UNKNOWN` or `RECEIPT_UPLOAD_PARTIAL_OR_UNKNOWN` and prints a nonsensitive run ID; **do not retry blindly**, because data may have been stored already. The encrypted local receipt is preserved after full data upload before cloud-manifest writes; collect exact provider versions via private owner tools if investigating a partial attempt. No deleted/rewritten historical evidence.
- Python/GCM temporary plaintext copies exist on the Windows VPS during capture and restore; encryption does not erase NTFS temp blocks/pagefiles. Review Windows ACLs/volume encryption and RDP privacy before handling sensitive regulated data; this v0.1 only handles the bounded user-selected S02 evidence. Secrets may remain transiently in memory.
- The one-shot manual backup can become **live** only when a Windows acceptance passes and an actual signed/verified AWS+B2 backup, redundant receipt persistence and independently verified restore are observed. An unattended production schedule would need a *separate* secure short-lived/service credential custody design and owner-approved task scope. Never install a task silently.

### Minimal owner actions to enable the first actual backup

Use the four credentials the owner previously confirmed (hold them privately, never paste into chat). Save a unique 16+-character recovery passphrase securely OFF the VPS. Choose the single copy-paste SHA-pinned final review/backup command only after the exact integrated PR passes one consolidated VPS code check and the user has an opportunity to confirm they are ready for minimal possible provider charges and the scoped S02 content. No new endless P9/P10 artificial stages.

**What is not included**: all-DB backup, unattended scheduler, automatic retention cleanup, guaranteed $0 charges, B2 atomic conditional write guarantee, restoration of app services beyond S02 SQLite, or real provider proof until executed. The user-requested first working deliverable is a manual, encrypted, versioned **dual-cloud S02 backup with a real recovery command**.


## 2026-10-24 Option 2 — Windows Credential Manager instead of masked cloud-key prompts

**Owner decision:** Keep one-time cloud credentials encrypted under the Windows user account rather than struggle with pasting access IDs and secrets into interactive PowerShell. The operator CLI now has a `credential-status` **read-only** command. The `backup` and `restore` commands load only four fixed `CredReadW` Generic credential targets from the signed-in Windows account; no credential values are passed through commands, files, environment variables, subprocess pipes or test logs. The **recovery passphrase is deliberately NOT saved in the same VPS credential vault**: retain it independently off VPS and enter it at the masked passphrase prompt.

### Once, using GUI on the Windows VPS (not PowerShell secret pastes)

1. Abort the previous paused CLI with `Ctrl+C`; before all four cloud IDs are entered it has made no real upload. Then run **`control.exe /name Microsoft.CredentialManager`** from that VPS session.
2. In **Credential Manager > Windows Credentials > Add a generic credential**, add FOUR Generic credentials. For every entry set **Internet or network address** to the exact target below; put the corresponding cloud **access key ID** in **User name**, and the cloud **secret access key** in **Password**. Do NOT type the actual IAM account friendly name as User name: it needs the actual access key ID for the AWS/B2 signing algorithm.
   - `VowSig.S02.AWS.Writer.v1` — AWS S3 writer's access key ID and secret.
   - `VowSig.S02.AWS.Reader.v1` — AWS S3 restore reader's access key ID and secret.
   - `VowSig.S02.B2.Writer.v1` — Backblaze B2 writer's application key ID and application key.
   - `VowSig.S02.B2.Reader.v1` — Backblaze B2 restore reader's application key ID and application key.
3. Sign in as the **same Windows user** that runs `python scripts/vowsig_dual_cloud_backup.py`. Current live PowerShell prompt in owner-provided output uses `Administrator`; credentials stored under a different Windows account/user profile will not be found. Generic entries are retrievable by programs running as that signed-in account; do not pretend protection against malware running as the same Windows user.
4. Verify presence **without external network or secret output**: `python scripts/vowsig_dual_cloud_backup.py credential-status` from a disposable, SHA-pinned candidate checkout with the pinned Python environment and `PYTHONPATH` preconfigured. Required result: `backup_roles_ready=true`, `restore_roles_ready=true`, four `roles` booleans true and `network_requests=0`. If false, correct target label, username/key values or Windows account **in the GUI**. Never display or paste actual values into GitHub/chat.
5. Future manual **backup/restore commands** keep the same operator options and masked **passphrase** prompt, but **do not ask for any AWS/B2 access ID or secret**. A new native Windows acceptance is still required for the revised exact GitHub code; preserve P1–P8 and prior 153-PASS tests as historical separate heads.
6. DPAPI/Windows Credential Manager is an **on-VPS at-rest custody convenience, not independent offsite recovery**. Back up secrets and recovery passphrase in an independent MFA-protected password manager. Windows Task Scheduler running as a different Windows account, without a loaded user profile, or under an incompatible service account, may not be able to read these entries. No autonomous scheduler is installed by this change.

**Only source-scope change since the initial 153-test pass:** one added module `windows_credential_manager_v0_1.py`, one added corresponding offline-test module, one amended CLI to use `CredReadW` and `credential-status`, and this updated runbook. No production task or installed package changed.
