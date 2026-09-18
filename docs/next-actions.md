# Current Next Actions

_Last updated: 2026-09-18_

## G3 status

S02 Structure Breakout v0.1 remains:

`RESEARCH — XAU HISTORICAL ROBUSTNESS PASSED; IMMUTABLE FORWARD EVIDENCE NEXT; NOT CANDIDATE`

## EXP-2026-012 transfer result

The predeclared transfer universe was tested unchanged.

| Market | Validation net R/trade | Final net R/trade | Frozen support flag |
|---|---:|---:|---|
| XAG/USD | -0.0839 | +0.1432 | NO |
| USTEC / NASDAQ 100 | +0.1243 | +0.0122 | YES |
| US500 / S&P 500 | +0.0283 | -0.0331 | NO |
| US30 / DOW 30 | +0.0936 | +0.0123 | YES |
| USOIL / WTI | -0.1466 | -0.1493 | NO |

USTEC and US30 meet the descriptive rule (>0 validation and final expectancy with >=50 trades in each split), but their final-test margins are small. They are not promoted to candidate status.

XAGUSD is particularly informative: gross validation expectancy is positive but the MT5 spread-cost proxy is large enough to make net validation negative. The strong recent XAG result therefore does not establish same-metal transfer across the full OOS period.

## Next phase — immutable forward evidence

Historical testing has now done what it can for the XAU lead. The next evidence must be created after a frozen activation timestamp.

The forward ledger is event-sourced, append-only and SHA-256 hash-chained. SQLite triggers reject UPDATE and DELETE operations. Every record commits to:

- record type and entity ID;
- recorded/effective UTC timestamps;
- canonical JSON payload;
- previous ledger hash;
- current record hash.

The initial activation also commits to:

- frozen S02 v0.1 config hash;
- S02 strategy-source SHA-256;
- source/symbol identity;
- activation timestamp;
- maximum accepted signal-recording delay.

This local hash chain is the first integrity layer. External anchoring of ledger heads will be added separately; do not claim the local database alone is independently tamper-proof.

## 1. Pull and test

```powershell
git pull
python -m pytest -q
```

## 2. Activate the primary forward test

Do this **once** after tests pass:

```powershell
python scripts\activate_s02_forward.py
```

Default primary forward test:

- strategy: S02 Structure Breakout v0.1;
- source: Exness MT5 demo (R&D only);
- market: XAU/USD / XAUUSD;
- forward database: `data/forward.sqlite`;
- maximum fresh-signal recording lag: 5 minutes.

The script refuses a second activation for the same test identity.

Paste the complete activation JSON, especially:

- `activated_at_utc`;
- `config_sha256`;
- `strategy_code_sha256`;
- `record_hash`;
- `ledger_head_hash`.

Do **not** start historical backfilling into the forward ledger.

## 3. Verify the chain

```powershell
python scripts\verify_forward_ledger.py
```

Expected:

- `valid: true`;
- one ACTIVATION record;
- zero SIGNAL/EXIT records initially.

## 4. Hourly scanner comes after activation hash is recorded

The scanner implementation is included, but wait until the activation hash has been reported and anchored in the research audit trail before starting hourly scans.

The scan command will be:

```powershell
python scripts\scan_s02_forward.py
```

It never backfills a stale signal as if it were live. Signals discovered more than the frozen age limit after their signal close are logged as `MISSED_SIGNAL`, not as forward signals.

## Research discipline

- Primary forward hypothesis is XAUUSD S02 v0.1 unchanged.
- Do not switch to XAU-long-only.
- Do not select a robustness variant.
- USTEC/US30 remain secondary historical observations, not forward candidates from this result.
- G2 remains open; Exness forward collection is research-only.
