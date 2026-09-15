# G1 Data Reliability Runbook

1. Complete `docs/windows-setup.md`.
2. Run `scripts/mt5_probe.py` on the Windows MT5/Exness demo machine.
3. Record non-sensitive findings in `EXP-2026-001`.
4. Run `scripts/binance_probe.py`; update `EXP-2026-002`.
5. Confirm exact Exness source symbols and update the universe mapping.
6. Measure historical depth by market/timeframe.
7. Run/expand quality diagnostics (`EXP-2026-006`).
8. Mark G1 complete only after both connectors produce reproducible normalized data with understood limitations.
