# S02/XAUUSD Forward Activation Anchor — 2026-09-18

This file durably records the primary S02 v0.1 XAU/USD forward-test activation before live signal scanning begins.

## Activation identity

- strategy: `S02-structure-breakout-v0.1`
- test entity: `S02-v0.1:XAUUSD:PRIMARY`
- source: `exness_mt5_demo` — R&D only
- source symbol: `XAUUSD`
- canonical symbol: `XAU/USD`
- activated at UTC: `2026-09-18T13:58:54.786419+00:00`
- activation record ID: `16a936e5658b4762a04dbbd177c79517`
- activation sequence: `1`
- repository HEAD pulled before activation: `b309cff26974728ef1f359d443d5927ee16010db`

## Frozen fingerprints

- config SHA-256: `6d347330084e34f31a129892b9a43ba96b88c96ac07c93625a601ffc1ad1bd91`
- strategy code SHA-256: `9f5e28817c49e9d206f28961d421d8370ba815b9b5f2d74ae991f68b088e618b`
- scanner code SHA-256: `2f29c7104a0fdd03f7072a677fa2d1656dd549c9f57fbe164696407d75f1da19`
- ledger code SHA-256: `18eb7f052800f37289248c2381fe5af840469140aea68368dbda882bb3d826f8`
- protocol bundle SHA-256: `484b3de25c6ff6c24de30c5a700f211b98be8534c7b0354fcb2d6219587232cf`
- maximum fresh-signal age: `5 minutes`

## Ledger anchor

- activation record hash: `c901167c0aa2f8d0aff8feb4411664063488b6e67da894279c63bd4fca284115`
- ledger head hash immediately after activation: `c901167c0aa2f8d0aff8feb4411664063488b6e67da894279c63bd4fca284115`
- previous hash: `null`
- verification immediately after activation: `valid = true`
- record count immediately after activation: `1`
- record types immediately after activation: `ACTIVATION = 1`
- unresolved signals immediately after activation: none

## Test evidence

Before activation:

- `python -m pytest -q`
- result: `7 passed`
- reported runtime: `7883.23s`

The unusually long runtime should be investigated as an engineering-performance issue if it recurs, but there were no test failures.

## Research-integrity rule from this point

No historical signal may be inserted as a live forward signal. Signals discovered more than five minutes after their signal close must be logged as `MISSED_SIGNAL`.

The frozen activation fingerprints must match before the scanner runs. If any fingerprint changes, this activation is no longer valid for that changed implementation; create a separately versioned forward protocol rather than silently altering this one.

## Anchor limitation

This GitHub record is a durable external operational anchor for the activation hash. It is not a cryptographic timestamp-authority service and should not be marketed as independently immutable proof. Periodic external ledger-head anchoring remains a follow-up requirement.
