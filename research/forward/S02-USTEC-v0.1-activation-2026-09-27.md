# S02/USTEC Secondary Forward Activation Anchor — 2026-09-27

This file durably records the secondary S02 v0.1 NASDAQ 100 / USTEC forward-test activation before scheduled live scanning begins.

## Activation identity

- strategy: `S02-structure-breakout-v0.1`
- test entity: `S02-v0.1:USTEC:SECONDARY`
- source: `exness_mt5_demo`
- source symbol: `USTEC`
- canonical symbol: `NASDAQ 100`
- database: `data/forward_ustec.sqlite`
- activated at UTC: `2026-09-27T12:42:13.014356+00:00`
- activation record ID: `7d6305cdaca54bcfa2611fe4edc5499b`
- activation sequence: `1`
- repository HEAD pulled before activation: `08cf2282776a4f5f7863f6c16d96b1704dc56bca`

## Frozen fingerprints

- config SHA-256: `6d347330084e34f31a129892b9a43ba96b88c96ac07c93625a601ffc1ad1bd91`
- strategy code SHA-256: `9f5e28817c49e9d206f28961d421d8370ba815b9b5f2d74ae991f68b088e618b`
- scanner code SHA-256: `2f29c7104a0fdd03f7072a677fa2d1656dd549c9f57fbe164696407d75f1da19`
- ledger code SHA-256: `18eb7f052800f37289248c2381fe5af840469140aea68368dbda882bb3d826f8`
- protocol bundle SHA-256: `484b3de25c6ff6c24de30c5a700f211b98be8534c7b0354fcb2d6219587232cf`
- maximum fresh-signal age: `5 minutes`

## Ledger anchor

- activation record hash: `b0bcb4c952c64c3043512905b803697b491841b99b08b256feb9de82f2cd2780`
- ledger head hash immediately after activation: same hash
- previous hash: `null`
- verification immediately after activation: `valid = true`
- record count immediately after activation: `1`
- record types immediately after activation: `ACTIVATION = 1`
- unresolved signals immediately after activation: none

## Pre-activation recency gate

The MT5 sync probe completed before activation and reported current H1/H4 history through `2026-09-25T20:00:00Z`, with all three retrieval methods agreeing and `appears_recent = true`.

## Evidence status

USTEC is a **secondary** launch market. It met the frozen historical transfer-support rule, but its final-test historical expectancy margin was small. This activation does not promote USTEC to the same evidence tier as XAUUSD.

## Integrity rule

Do not recreate this activation, rewrite its database, or silently change the frozen strategy/scanner/ledger/config under this identity. A changed implementation requires a separately versioned activation.
