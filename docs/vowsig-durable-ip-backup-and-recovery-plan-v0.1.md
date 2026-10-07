# VowSig Durable IP Backup and Recovery Plan v0.1

_Status: DESIGN APPROVED FOR DOCUMENTATION / NOT YET IMPLEMENTED_  
_Date: 2026-10-08_  
_Scope: VowSig research evidence, code, model configuration, future training datasets and future proprietary model artifacts_

## 1. Purpose

VowSig is accumulating a body of proprietary research evidence that becomes more valuable over time:

- deterministic strategy evidence;
- AI feature snapshots;
- AI decisions and structured rationales;
- immutable shadow-signal lifecycle events;
- realized shadow-trade outcomes;
- model/provider/policy fingerprints;
- experiment preregistrations and activation anchors;
- evaluation/gate history;
- future derived training datasets;
- future proprietary model checkpoints.

The current private GitHub repository preserves the code, methodology and cryptographic anchors, while the live SQLite evidence databases are intentionally excluded from Git and live on the Windows VPS.

A cryptographic hash or ledger-head anchor proves identity/tampering but **does not reconstruct a lost database**.

This plan therefore defines a durable multi-location backup architecture so that VowSig's accumulated research/evidence cannot be lost because of:

- VPS disk failure;
- accidental deletion;
- database corruption;
- ransomware or host compromise;
- operator error;
- GitHub repository/account loss;
- loss of one cloud provider or cloud account;
- future failure of one storage region;
- destructive application bugs.

This document is a backup/recovery design only. It authorizes no infrastructure creation, credential creation, cloud purchase, scheduler change, database mutation, restore, model change, trading change or broker action.

---

## 2. Core design principle

Use a **3-2-1 style architecture**:

1. keep the live authoritative working copy on the Windows VPS;
2. keep an immutable encrypted primary backup in a different provider/account;
3. keep an independent secondary copy in another provider/security boundary.

Recommended topology:

```text
                         VOWSIG DURABLE IP

                              GitHub
                code / specs / hashes / manifests
                                |
              +-----------------+------------------+
              |                                    |
              v                                    v

        Windows VPS                           AWS S3
       live SQLite data              primary immutable archive
              |                              |
              |                              |
              |                     versioning + Object Lock
              |                     encryption + lifecycle
              |                              |
              +-------------+----------------+
                            |
                            v
                       verification
                            |
                            v
                      Backblaze B2
                 independent secondary copy
```

The primary recommendation is:

- **AWS S3** as the authoritative durable backup vault;
- **Backblaze B2** as the independent second-provider copy;
- **private GitHub** for source, specs, fingerprints, checkpoint manifests and governance records, but not as the primary database backup.

---

## 3. What constitutes the VowSig intellectual-capital package

The durable project asset is not only an AI model.

VowSig's enduring research/intellectual-capital package is the combination of:

1. historical/admitted market data and provenance;
2. deterministic feature-engineering definitions;
3. AI policy/prompt versions;
4. decision schemas;
5. deterministic guardrails;
6. deterministic risk/lifecycle/cost rules;
7. every prospective AI decision;
8. the exact feature state that produced each decision;
9. every shadow-signal lifecycle and realized outcome;
10. S02 benchmark/control evidence;
11. activation anchors and version lineage;
12. experiment preregistrations;
13. gate-review history;
14. future derived training datasets;
15. future proprietary model checkpoints and evaluation packages.

The OpenAI base-model weights are an external provider asset. They are not stored in this repository and are not part of the VowSig backup corpus. VowSig must preserve the exact provider/model identifier, request semantics and its own evidence so future research remains attributable and reproducible.

---

## 4. Current storage reality

### 4.1 GitHub

The private repository currently stores durable methodology and governance artifacts, including:

- source code;
- feature definitions;
- prompts/policies;
- schemas;
- guardrails;
- cost/lifecycle rules;
- model/provider configuration;
- activation anchors;
- correction anchors;
- research preregistrations;
- test suites;
- evaluation methodology;
- ledger-head/checkpoint hashes;
- product/publication evidence.

### 4.2 VPS live evidence

The continuously growing evidence databases are local to the VPS and excluded from Git.

Current live evidence classes include:

#### S02

- `data/forward.sqlite`
- `data/forward_ustec.sqlite`
- `data/forward_us30.sqlite`

#### AI-v1.1 core lineage

- `data/ai_v1_1_xauusd.sqlite`
- `data/ai_v1_1_ustec.sqlite`
- `data/ai_v1_1_us30.sqlite`

#### AI-v1.2.1 expansion lineage

- `data/ai_v1_2_1_eurusd.sqlite`
- `data/ai_v1_2_1_xagusd.sqlite`
- `data/ai_v1_2_1_usoil.sqlite`

The repository's `.gitignore` intentionally excludes:

- `data/`;
- `*.sqlite`;
- `*.db`.

This is correct for Git hygiene, but it means GitHub is not a complete backup of the growing live evidence.

### 4.3 Failed/superseded evidence

Failed and superseded ledgers/artifacts must remain preserved under the existing archive/governance rules. A backup implementation must discover and include any retained predecessor/archived evidence databases rather than backing up only the currently active six AI databases and three S02 databases.

No failed evidence may be silently discarded because a later version supersedes it.

---

## 5. Backup classes

### Class A — source/methodology/governance

Primary location: private GitHub.

Includes:

- repository history;
- source code;
- policy/prompt text;
- configuration;
- feature/schema definitions;
- research markdown;
- activation/correction anchors;
- test code;
- documented hashes/manifests.

Additional protection:

- periodic encrypted `git bundle --all` or equivalent full repository archive to AWS S3;
- duplicate repository archive to Backblaze B2.

Reason: losing GitHub access must not destroy the complete project history.

### Class B — immutable live research/evidence ledgers

Primary working location: VPS.

Backup locations:

1. AWS S3 immutable/versioned vault;
2. Backblaze B2 independent copy.

Includes every active, retired, failed or superseded SQLite evidence database that is part of the governed research record.

### Class C — derived training/evaluation datasets

Future examples:

- versioned Parquet datasets;
- supervised examples derived from feature state + AI decision + outcome;
- confidence-calibration datasets;
- regime labels;
- benchmark-comparison tables;
- training/validation/test split manifests.

These must become immutable versioned objects with:

- source-ledger manifest;
- generation-code commit;
- dataset SHA-256;
- schema/version;
- creation UTC;
- evaluation split rules.

### Class D — future proprietary model artifacts

Future examples:

- model weights/checkpoints;
- tokenizer/config files if applicable;
- training configuration;
- random seeds;
- optimizer/training metadata where needed for reproduction;
- training-data manifest;
- evaluation report;
- model fingerprint;
- deployment conversion artifacts.

Each promoted model must be recoverable independently of the training machine.

### Class E — public/derived product snapshots

The sanitized public snapshot is not the primary research asset because it can be regenerated from the authoritative evidence.

It may be backed up for operations, but it is lower priority than the ledgers.

### Class F — secrets

Secrets must **not** be bundled with research backups.

Examples:

- OpenAI API key;
- cloud ingest token;
- AWS access keys;
- Backblaze keys;
- broker passwords;
- private signing keys.

Secrets require a separate secrets-management/recovery policy.

---

## 6. Primary backup location — AWS S3

Recommended role:

**authoritative durable VowSig backup vault**.

Recommended controls:

- dedicated backup bucket;
- preferably dedicated AWS account or at minimum a separate security boundary from the production VPS;
- bucket versioning enabled;
- S3 Object Lock enabled;
- encryption at rest;
- TLS in transit;
- MFA on the administrative account;
- least-privilege IAM;
- no public access;
- lifecycle policies for cheaper archival storage;
- audit logging;
- explicit restore credentials separate from routine backup-writer credentials.

### 6.1 Object Lock policy

Recommended rollout:

1. initial implementation/test phase may use Governance-mode retention while restore/delete procedures are being proven;
2. after the backup and restore drills pass, move long-term critical snapshots to an immutable retention policy suitable for the project.

Routine VPS backup credentials must not be able to bypass retention or delete protected historical objects.

### 6.2 Backup-writer permissions

The routine VPS credential should have only the permissions required to:

- write objects;
- read only what is necessary for post-upload verification if required;
- list the designated backup prefix if required.

It should not have broad account administration rights.

Administrative/restore/delete permissions should use a separate identity protected by MFA.

---

## 7. Independent secondary location — Backblaze B2

Backblaze B2 is the recommended second-provider disaster-recovery store.

Purpose:

- survive loss/lockout of the AWS account;
- survive AWS-specific operational mistakes;
- reduce one-provider concentration risk.

Security requirements:

- separate account security;
- MFA;
- unique credentials;
- dedicated bucket;
- least-privilege application key;
- encrypted transport;
- versioned/retained historical objects according to the same dataset identities used in S3.

The secondary backup should be created from a verified backup artifact, not from an unknown/corrupt source.

---

## 8. SQLite backup method

Do **not** rely on copying a potentially active SQLite file with a plain filesystem copy.

The backup implementation should use SQLite's online backup mechanism.

Required sequence per database:

```text
live SQLite database
        |
        v
SQLite online backup API
        |
        v
isolated consistent backup file
        |
        +--> PRAGMA integrity_check
        |
        +--> ledger hash-chain verification
        |
        +--> SHA-256
        |
        +--> file size / record counts / ledger head
        |
        v
backup manifest
        |
        v
encrypted/cloud upload
```

A backup is not considered valid merely because an upload command returned success.

---

## 9. Per-database verification requirements

For each copied SQLite database, require:

1. source path exists;
2. online backup completes;
3. `PRAGMA integrity_check` returns `ok`;
4. application-specific ledger verifier returns valid where applicable;
5. database SHA-256 is recorded;
6. file size is recorded;
7. record count is recorded;
8. latest ledger head hash is recorded;
9. latest effective/recorded UTC is recorded where applicable;
10. source repository production commit is recorded;
11. backup UTC is recorded.

Any failed verification must fail closed and must not replace a known-good immutable backup.

---

## 10. Backup manifest

Every backup set should contain a machine-readable manifest.

Illustrative structure:

```json
{
  "backup_schema_version": 1,
  "backup_id": "2026-10-08T03-00-00Z",
  "created_at_utc": "2026-10-08T03:00:00+00:00",
  "production_commit": "<git-sha>",
  "production_tree": "<git-tree-sha>",
  "backup_method": "sqlite_online_backup",
  "databases": {
    "data/ai_v1_1_xauusd.sqlite": {
      "sha256": "<sha256>",
      "size_bytes": 123456,
      "integrity_check": "ok",
      "ledger_valid": true,
      "ledger_records": 123,
      "ledger_head": "<record-hash>"
    }
  }
}
```

The final manifest itself should receive a SHA-256.

Recommended manifest storage:

- stored beside the backup set in AWS;
- duplicated beside the backup set in B2;
- material checkpoint manifests/hashes may be committed to GitHub.

Do not automatically commit every hourly/3-hour manifest to production `main`, because GitHub is the governance/source repository and production deploys are tied to `main`.

---

## 11. Backup cadence

Recommended initial cadence while the ledgers are relatively small:

### Local recovery copy

- every 3 hours;
- retain 7 days.

Purpose: fastest recovery from accidental local damage.

### AWS S3 verified backup

- every 3 hours;
- versioned;
- no overwrite-in-place.

### Daily immutable checkpoint

- once per UTC day;
- retain at least 1 year.

### Weekly archive

- once per week;
- retain at least 3 years.

### Monthly archive

- once per month;
- retain long term.

### Governance checkpoints

Keep indefinitely for:

- activation;
- retirement/supersession;
- A1/A2/A3;
- X1/X2/X3;
- S02 F1/F2/F3;
- material public release/publication;
- model/dataset promotion;
- before/after any governed migration.

### Backblaze B2

- at least daily;
- include all daily/weekly/monthly/governance checkpoints;
- long-term retention independent of AWS.

These retention periods are initial design targets and should be reviewed against storage costs, legal/data-rights requirements and project maturity before implementation.

---

## 12. Recovery objectives

Initial design targets:

- **RPO (maximum expected evidence loss): <= 3 hours** under ordinary VPS loss;
- **RTO (target service/evidence restoration): <= 4 hours** for a normal single-host failure once credentials/infrastructure exist.

Governance snapshots at activations/reviews/publications should have effectively zero intentional retention loss because they are retained indefinitely.

RPO/RTO are objectives, not guaranteed SLAs until the implementation and restore drills prove them.

---

## 13. Object naming/layout

Recommended object namespace:

```text
vowsig-backup/
  manifests/
  ledgers/
    s02/
    ai-v1.0-retired/
    ai-v1.1/
    ai-v1.2-failed/
    ai-v1.2.1/
  datasets/
    training/
    evaluation/
  models/
    checkpoints/
    evaluations/
  repository/
    git-bundles/
  governance/
    activation/
    gates/
    publications/
```

Every object path should include a UTC timestamp and version/lineage identity.

Never use only a mutable filename such as `latest.sqlite` as the sole retained object.

A `latest` pointer may exist for convenience, but historical versioned objects remain authoritative.

---

## 14. Encryption and key separation

Required principles:

- TLS for all cloud transfers;
- encryption at rest in both providers;
- separate backup-account credentials from production credentials;
- no secret values written into manifests;
- no API keys embedded in backup scripts or Git;
- MFA on cloud administrative accounts.

Preferred stronger architecture:

- AWS KMS-backed encryption for S3;
- separate key-administration rights from routine backup-writing rights;
- secondary-provider credentials held separately;
- future proprietary model archives may additionally use client-side encryption before multi-provider storage if operational key recovery is mature.

Do not introduce client-side encryption whose only decryption key exists on the same VPS being protected.

---

## 15. Blast-radius separation

The backup system should assume a compromised VPS credential.

Therefore:

- routine VPS backup identity must not be a cloud administrator;
- it must not be able to disable Object Lock;
- it must not be able to destroy all historical versions;
- restore credentials should not be continuously present on the VPS;
- AWS and B2 must use different credentials;
- cloud-admin recovery codes must be stored outside the VPS.

A ransomware process controlling the VPS should be unable to erase the immutable history.

---

## 16. Repository backup

Private GitHub is the canonical source/governance repository, but it also needs an independent copy.

Recommended:

- periodic full `git bundle --all`;
- SHA-256 the bundle;
- store in AWS;
- replicate to B2;
- verify that the bundle can recreate refs/history during periodic restore drills.

Repository backups must include:

- all branches needed for durable history;
- tags;
- main history;
- research branches that contain durable evidence not yet merged.

Do not rely solely on a local working clone as the GitHub disaster-recovery copy.

---

## 17. Future training-dataset lineage

When VowSig starts constructing proprietary training datasets, each dataset release should be immutable.

Each dataset manifest should bind:

- dataset version;
- generation UTC;
- source ledger paths;
- source ledger SHA-256 values;
- source ledger head hashes;
- source runtime/version;
- generating repository commit;
- dataset schema;
- feature version;
- label/outcome definition;
- exclusions;
- train/validation/test split policy;
- final dataset SHA-256.

A later training dataset must not silently replace an earlier dataset version.

Example:

```text
ledgers
  |
  v
training-dataset-v1
  |
  +-- manifest
  +-- sha256
  +-- generation commit
  |
  v
model-v1
```

This preserves reproducibility and protects the accumulated evidence from becoming an undocumented collection of files.

---

## 18. Future proprietary model backup

If/when VowSig trains its own model, backup is required before any model is considered a durable project artifact.

For each model version, preserve:

- model checkpoint/weights;
- training configuration;
- exact training dataset manifest;
- code commit;
- evaluation dataset manifest;
- evaluation report;
- model fingerprint/hash;
- conversion/serving artifacts;
- dependency/runtime environment description.

Promoted model artifacts should be stored in both AWS and B2.

GitHub should store the model manifest/fingerprint and code, not necessarily multi-GB model weights.

---

## 19. Restore procedure

A restore must never directly overwrite the live database as its first step.

Required restore sequence:

1. identify the desired backup ID;
2. download into an isolated restore directory;
3. verify object/file SHA-256 against the manifest;
4. decrypt if applicable;
5. run SQLite `PRAGMA integrity_check`;
6. run the VowSig ledger hash-chain verifier;
7. compare ledger heads/anchors against durable GitHub governance evidence;
8. inspect record counts/latest timestamps;
9. prove repository/runtime compatibility;
10. only after explicit owner authorization, pause the relevant scheduler if a live replacement is required;
11. preserve the damaged/current database separately;
12. atomically install the verified restored database;
13. run runtime verification;
14. re-enable only the previously authorized scheduler state;
15. record the recovery as a durable incident/governance artifact.

There must be no automatic destructive restore into production.

---

## 20. Restore testing

A backup is not considered operationally proven until restore testing passes.

Recommended monthly drill:

1. choose a recent backup;
2. restore it into an isolated temporary directory;
3. verify SHA-256;
4. run `PRAGMA integrity_check`;
5. run application ledger verification;
6. verify expected ledger heads;
7. run read-only observability/progress tooling;
8. delete only the temporary restore copy after PASS.

Recommended quarterly extended drill:

- restore a full backup set;
- restore the repository from its git bundle;
- prove that the restored source + data can reproduce read-only observability;
- test AWS-only recovery;
- test B2-only recovery.

No drill should mutate the active production ledgers.

---

## 21. Monitoring and alerting

The implementation should expose backup health independently of trading/model health.

Minimum metrics:

- last successful local backup UTC;
- last successful S3 upload UTC;
- last successful B2 replication UTC;
- latest backup manifest ID;
- number of databases protected;
- verification status;
- latest restore-drill date/status;
- backup age;
- failed upload/verification count.

Alert conditions should include:

- no verified primary backup inside the RPO window;
- B2 replication older than 24 hours;
- integrity-check failure;
- ledger-verification failure;
- manifest mismatch;
- cloud upload failure;
- Object Lock/versioning unexpectedly disabled;
- restore drill overdue.

Backup failure must not modify trading decisions or rewrite evidence.

---

## 22. Failure handling

### Database integrity failure during backup

- fail closed;
- do not promote the broken copy as latest-good;
- preserve diagnostics;
- alert;
- keep prior immutable backups untouched.

### AWS unavailable

- retain local verified copy;
- continue B2 if independent path works;
- alert;
- backfill only backup transfer later, never trading evidence.

### B2 unavailable

- AWS remains primary;
- alert;
- replicate missing verified backup objects later.

### VPS lost

- provision replacement host;
- recover repository;
- recover most recent verified ledger set;
- validate;
- reconcile scheduler state;
- resume only under explicit recovery procedure.

### Cloud credential compromise

- disable/rotate compromised identity;
- preserve immutable objects;
- audit access;
- use separate restore/admin identity.

---

## 23. GitHub anchoring policy

GitHub continues to provide external evidence identity, not bulk-database storage.

Commit durable backup/checkpoint manifests or hashes at material events such as:

- activation;
- retirement/supersession;
- gate audit;
- model/dataset promotion;
- major incident/recovery;
- public production release;
- periodic governance checkpoint.

Do not commit secrets or raw SQLite databases.

Do not create routine high-frequency commits to production `main` merely because a backup occurred.

---

## 24. Current IP-protection gap

As of this plan's creation:

- code/specifications/governance are durable in private GitHub;
- the live SQLite ledgers are hash-chained and externally anchored at material checkpoints;
- `data/` and SQLite files are intentionally ignored by Git;
- the public Railway snapshot has its own durability mechanism, but that sanitized snapshot is not a substitute for the source ledgers;
- this repository does not currently prove that an independent full-database off-VPS backup system is implemented.

Therefore the highest-priority future durability improvement is independent off-VPS backup of the complete governed evidence databases.

---

## 25. Proposed implementation phases

### Phase B0 — inventory and dry-run

- enumerate every active/retired/failed evidence DB;
- classify each database;
- create read-only backup/manifest tooling;
- validate SQLite online backup;
- validate ledger verification;
- perform no cloud upload.

### Phase B1 — local verified backup

- scheduled isolated backups;
- integrity + ledger verification;
- manifest generation;
- retention/cleanup of local temporary backups.

### Phase B2 — AWS primary vault

- create dedicated S3 bucket/account boundary;
- versioning;
- encryption;
- Object Lock;
- least-privilege writer;
- upload + post-upload verification;
- lifecycle rules.

### Phase B3 — independent B2 replication

- separate account/credentials;
- upload verified daily/governance snapshots;
- verify object identity.

### Phase B4 — restore drills

- automated isolated restore verifier;
- monthly drill;
- quarterly full-system drill;
- evidence recorded.

### Phase B5 — dataset/model vault

When proprietary training begins:

- dataset versioning;
- dataset manifests;
- model checkpoint retention;
- reproducibility packages.

---

## 26. Acceptance criteria for a future implementation milestone

Do not call the backup system production-ready until all are true:

- [ ] complete governed database inventory is frozen;
- [ ] SQLite online backup used for live DB copies;
- [ ] every backup receives `PRAGMA integrity_check`;
- [ ] every governed ledger receives hash-chain verification;
- [ ] SHA-256 + ledger head + file size + record count recorded;
- [ ] backup manifest schema tested;
- [ ] AWS bucket versioning enabled;
- [ ] Object Lock/immutable retention enabled for critical classes;
- [ ] AWS encryption enabled;
- [ ] routine writer cannot delete protected history;
- [ ] B2 independent copy operational;
- [ ] backup credentials excluded from Git;
- [ ] no backup contains provider/broker/cloud secrets;
- [ ] RPO monitoring implemented;
- [ ] alerts implemented;
- [ ] repository git-bundle backup verified;
- [ ] one isolated AWS restore drill PASS;
- [ ] one isolated B2 restore drill PASS;
- [ ] restored ledgers pass application verification;
- [ ] active production ledgers remain byte-identical during backup/restore testing;
- [ ] scheduler definitions remain unchanged during testing;
- [ ] restore runbook reviewed;
- [ ] exact costs/retention reviewed by owner before long-term commitment.

---

## 27. Non-goals / safety boundaries

This plan does not authorize:

- changing S02 strategy logic;
- changing AI-v1.1 or AI-v1.2.1 decisions;
- changing prompts, features, guardrails or lifecycle rules;
- retraining or fine-tuning a model;
- broker execution;
- public signal expansion;
- ledger rewriting/backfill;
- restoring over a live production database;
- uploading secrets;
- redistributing raw market data;
- purchasing/creating AWS or Backblaze resources without separate owner authorization.

Backup code must be operational infrastructure only.

---

## 28. Recommended target state

The desired mature architecture is:

```text
                    VOWSIG IP / EVIDENCE VAULT

      Private GitHub
      - code
      - configs
      - prompts/policies
      - research specs
      - activation anchors
      - checkpoint manifests/hashes
                 |
                 |
                 +-----------------------------+
                                               |
                                               v
 Windows VPS --------------------------> AWS S3 backup account
 live append-only ledgers                - versioning
 - S02                                    - Object Lock
 - AI-v1.1                                - encryption
 - AI-v1.2.1                              - lifecycle/archive
 - future lineages                              |
       |                                        |
       | verified SQLite backup                 |
       +----------------------------------------+
                                                |
                                                v
                                          Backblaze B2
                                     independent verified copy

 Future:
 ledgers -> immutable dataset versions -> proprietary model versions
                   |                         |
                   +------ S3 + B2 ----------+
```

This design makes the continuously accumulating VowSig evidence a recoverable, versioned asset rather than a dataset that exists only on one VPS.

---

## 29. Decision summary

Recommended durable storage hierarchy:

1. **Windows VPS** — live authoritative operational databases;
2. **AWS S3 + versioning + Object Lock** — primary immutable backup vault;
3. **Backblaze B2** — independent second-provider disaster-recovery copy;
4. **private GitHub** — source/methodology/governance/checkpoint hashes and selected manifests;
5. **future S3/B2 model vault** — immutable derived training datasets and proprietary model checkpoints.

Key rule:

> A ledger hash proves identity, but only a verified independent copy provides recovery.

The backup system should therefore protect both the **VowSig methodology** and the **VowSig accumulated experience**.
