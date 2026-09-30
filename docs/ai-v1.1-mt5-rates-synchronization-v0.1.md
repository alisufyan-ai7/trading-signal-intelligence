# AI-v1.1 MT5 Rates Synchronization Correction v0.1

_Status: PRE-ACTIVATION IMPLEMENTATION IN PROGRESS — NOT ACTIVE_  
_Date: 2026-09-30_  
_GitHub issue: #15_

## Purpose

Correct the AI-v1.0 index data-read defect prospectively without rewriting or backfilling any v1.0 evidence.

The evidence from Issues #10–#14 establishes an operational defect class: USTEC/US30 frequently fail to expose the just-completed H1 opportunity to the AI runtime on the first scheduled snapshot even though the scheduler, market cycle, provider path and tick activity are otherwise healthy.

The exact internal MT5 cache-refresh mechanism is not fully observable from retained evidence. The correction therefore does not attempt to infer MT5 internals. It makes rates-read readiness explicit and deterministic.

## Versioning decision

This correction can change which hourly opportunities reach the AI model.

It is therefore decision-affecting and must not be patched into the activated AI-v1.0 runtime.

AI-v1.1 must be prospective and separately activated.

AI-v1.0:

- remains immutable;
- keeps all existing missed records;
- receives no backfill;
- keeps its own activation/evidence lineage;
- does not contribute gate counts to AI-v1.1 after replacement.

## Unchanged decision system

AI-v1.1 keeps unchanged:

- model `gpt-5.4-2026-03-05`;
- reasoning effort / provider parameters;
- prompt/policy and JSON schema;
- XAUUSD / USTEC / US30 universe;
- completed H1/H4 feature definitions;
- hourly near-:02 cadence;
- BUY / SELL / NO_TRADE semantics;
- deterministic decision validation;
- stop / TP1 / TP2 / lifecycle rules;
- 1.25x spread cost;
- same-bar stop-first;
- 24-H1 maximum hold;
- 300-second maximum source-bar age;
- broker execution disabled.

## New data-read readiness rule

Before any feature snapshot or provider call:

1. observe the latest MT5 tick timestamp;
2. require a tick belonging to the current UTC H1 hour;
3. derive the expected current H1 row open from that tick hour;
4. derive the expected current H4 row open from the tick's four-hour UTC bucket;
5. read H1 and H4 rates;
6. require the newest H1 and H4 rows to match those expected opens;
7. if not ready, poll deterministically;
8. never call the provider while rates remain unsynchronized;
9. after readiness, pass the bars to the unchanged feature/decision path;
10. the final source-bar age must still be <=300 seconds.

## Bounded poll

Frozen pre-activation design target:

- maximum wait: 30 seconds;
- polling interval: 1 second.

These values are represented by:

- `SYNC_MAX_WAIT_SECONDS = 30.0`
- `SYNC_POLL_INTERVAL_SECONDS = 1.0`

They must not change after activation without a new governed version.

## Fail-closed outcomes

The standalone helper returns only:

- `READY`
- `NO_CURRENT_H1_TICK`
- `RATES_NOT_SYNCHRONIZED`

`NO_CURRENT_H1_TICK` covers conditions such as a normal session break where no current-hour tradable row exists.

`RATES_NOT_SYNCHRONIZED` means a current-hour tick was observed but the newest H1/H4 rate rows did not become current within the bounded wait.

Neither fail-closed outcome authorizes a provider call or later backfill.

## Current implementation

Committed but not integrated:

- `src/trading_signal_intelligence/ai_v1/rates_sync_v1_1.py`
- `tests/test_ai_v1_rates_sync_v1_1.py`

The helper uses injected read, clock and sleep functions. Unit tests therefore exercise synchronization semantics without touching MT5, OpenAI, broker state or AI-v1.0 ledgers.

## Required pre-activation work

1. pass focused synchronization tests;
2. add a versioned v1.1 runtime path without modifying the activated v1.0 runtime artifact;
3. add MT5 read-state adapter for latest tick + raw H1/H4 newest-row timestamps;
4. test stale-first-read -> fresh-later-read behavior;
5. test timeout paths and prove provider is never called on unsynchronized data;
6. preserve the existing <=300-second freshness rule after synchronization;
7. create separate v1.1 ledger paths;
8. create v1.1 activation/supersession metadata;
9. verify frozen model/prompt/features/risk hashes unchanged;
10. review exact v1.0 -> v1.1 diff before activation.

## Activation rule

No AI-v1.1 scheduler activation occurs automatically.

The owner must review the final implementation/activation plan before the v1.1 activation anchor is created and before any scheduler is switched.

Until then AI-v1.0 remains the live shadow collector.


## Version-isolated runtime path

The pre-activation implementation now distinguishes:

- **runtime/evidence lineage:** `AI-v1.1`;
- **model/feature/decision protocol:** `AI-v1.0`.

This is intentional. The data-read correction changes collection readiness only; the model contract, prompt, feature schema, decision schema and guardrails remain frozen.

New v1.1 evidence identity:

- entity prefix: `AI-v1.1:`;
- XAUUSD ledger: `data/ai_v1_1_xauusd.sqlite`;
- USTEC ledger: `data/ai_v1_1_ustec.sqlite`;
- US30 ledger: `data/ai_v1_1_us30.sqlite`.

New pre-activation modules:

- `mt5_rates_adapter_v1_1.py`;
- `engine_v1_1.py`;
- `shadow_runtime_v1_1.py`.

The live AI-v1.0 runner does not import these modules.

No v1.1 activation anchor, scheduled task, or live ledger has been authorized yet.
