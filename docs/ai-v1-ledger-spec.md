# AI-v1 immutable ledger specification

_Status: FROZEN PRE-ACTIVATION — 2026-09-28_

## Isolation

AI-v1 must not reuse or mutate any existing S02 forward database.

Frozen AI-v1 database paths:

- XAUUSD: `data/ai_v1_xauusd.sqlite`
- USTEC: `data/ai_v1_ustec.sqlite`
- US30: `data/ai_v1_us30.sqlite`

Each market has an independent append-only hash chain.

## Hash-chain model

Reuse the proven S02 ledger integrity pattern:

- SQLite append-only table;
- monotonically increasing sequence;
- UUID record ID;
- record type;
- entity ID;
- recorded UTC;
- effective UTC;
- canonical JSON payload;
- previous record hash;
- current SHA-256 record hash;
- UPDATE trigger rejects mutation;
- DELETE trigger rejects mutation.

Canonical JSON:

- keys sorted;
- compact separators;
- UTF-8;
- NaN / Infinity forbidden.

Record hash material:

- record_id
- record_type
- entity_id
- recorded_at_utc
- effective_at_utc
- payload_json
- previous_hash

The AI ledger implementation may share generic hash utilities with S02 only if doing so does not modify activated S02 semantics or databases.

## Entity IDs

Activation:

`AI-v1.0:<SYMBOL>:ACTIVATION`

Inference cycle:

`AI-v1.0:<SYMBOL>:<SOURCE_BAR_CLOSE_UTC>`

The source-bar close timestamp must be normalized to UTC and uniquely identifies one scheduled AI-v1 decision opportunity per market/H1 close.

All lifecycle records for one inference/signal use the same cycle entity ID.

## Record types and frozen minimum payloads

### ACTIVATION

Required:

- protocol_version;
- market;
- activation timestamp;
- repository commit SHA;
- activation bundle SHA-256;
- exact provider;
- exact model ID;
- model parameter fingerprint;
- policy SHA-256;
- feature-definition SHA-256;
- feature-schema SHA-256;
- decision-schema SHA-256;
- guardrail-config SHA-256;
- feature-builder source SHA-256;
- inference-adapter source SHA-256;
- AI-ledger source SHA-256;
- lifecycle-evaluator source SHA-256;
- cost-policy fingerprint (AI-v1.0 uses the frozen 1.25× spread-cost multiplier);
- broker_execution_enabled=false.

### INFERENCE

One valid provider response was obtained.

Required:

- source_bar_open_utc;
- source_bar_close_utc;
- inference_started_utc;
- inference_completed_utc;
- latency_ms;
- feature_snapshot_sha256;
- policy_sha256;
- provider;
- model_id;
- model_parameter_fingerprint;
- raw structured response;
- normalized decision;
- raw_confidence;
- provider request identifier if available and non-secret;
- token/usage metadata if available;
- estimated inference cost if available.

No API key, authorization header or provider secret may be stored.

### NO_TRADE

Required:

- same cycle entity;
- normalized NO_TRADE decision;
- raw confidence;
- regime;
- concise rationale;
- supporting factors;
- risk factors;
- feature snapshot hash.

### REJECTED_INFERENCE

Used when model output is valid enough to parse but cannot be published.

Required:

- normalized proposal if available;
- rejection reason code(s);
- feature snapshot hash;
- guardrail config fingerprint.

Examples:

- stale_data;
- schema_invalid;
- cost_too_high;
- active_signal_exists;
- stop_out_of_bounds;
- target_out_of_bounds;
- target_order_invalid;
- arithmetic_invalid.

### SIGNAL

Required:

- direction;
- source bar close UTC;
- signal recorded UTC;
- entry policy;
- ATR used;
- proposed stop_atr;
- proposed tp1_r;
- proposed tp2_r;
- raw confidence;
- deterministic entry timestamp when filled;
- entry price when filled;
- stop price;
- TP1 price;
- TP2 price;
- max hold bars;
- estimated cost inputs;
- feature snapshot hash;
- originating INFERENCE record hash.

If the next eligible H1 open has not yet occurred, implementation may record the approved proposal first and append fill fields in a dedicated deterministic lifecycle event. It must not backdate a fill.

### PARTIAL_EXIT

At most one TP1 partial-exit record per signal entity.

Required:

- exit time;
- TP1 fill price;
- fraction=0.5;
- gross R for the closed fraction;
- cost R allocated to the fraction;
- net R for the fraction;
- trigger reason=TP1.

### EXIT

Closes remaining shadow exposure.

Required:

- exit time;
- exit price;
- remaining fraction;
- reason: TP2 / STOP / TIMEOUT;
- gross R;
- cost R;
- net R;
- total combined signal net R including prior partial exit if any.

### MISSED_INFERENCE

Used when an eligible H1 decision opportunity could not receive a valid inference before the frozen freshness boundary.

Required:

- source bar close UTC;
- detection time;
- reason;
- data age if known.

Do not later insert a live-equivalent inference for that missed cycle.

### ERROR

Operational error not represented by another event.

Required:

- stage;
- error class/code;
- sanitized message;
- source bar close UTC if applicable.

No secret values or raw authorization material may be stored.

## Append ordering

For a normal trade cycle:

`INFERENCE -> SIGNAL -> optional PARTIAL_EXIT -> EXIT`

For abstention:

`INFERENCE -> NO_TRADE`

For rejected proposal:

`INFERENCE -> REJECTED_INFERENCE`

For a provider/data miss:

`MISSED_INFERENCE` or `ERROR` as applicable.

## No mutation / no result deletion

Once appended:

- a losing signal cannot be removed;
- a rationale cannot be edited;
- confidence cannot be changed;
- a model response cannot be replaced;
- outcome correction requires an explicit separately typed correction protocol in a future version, not SQL UPDATE.

AI-v1.0 contains no correction event type. Any implementation defect affecting historical records requires versioned remediation and preservation of the original database.

## Head anchoring

At activation and at material review checkpoints, record each AI-v1 market ledger head SHA-256 in the private GitHub repository, analogous to the existing S02 forward anchors.

This makes local mutation detectable relative to previously committed heads.
