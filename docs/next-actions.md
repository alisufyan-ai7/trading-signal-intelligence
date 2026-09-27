# Current Next Actions

_Last updated: 2026-09-27_

## Launch status

The local TradingTop Early Access launch path is operational and ready for public hosting.

Public Railway deployment was explicitly approved and attempted, but Railway blocked new resource creation with:

`Free plan resource provision limit exceeded. Please upgrade to provision more resources!`

No TradingTop Railway resource was created.

Existing unrelated Railway projects were deliberately not reused.

## Immediate external action

Create Railway capacity by either:

1. upgrading the Railway account/plan; or
2. deleting/stopping an unused Railway resource so a new project/service can be provisioned.

Do not delete any existing Railway resource solely for this project unless its owner confirms it is safe to remove.

## Resume point

As soon as Railway capacity is available, resume with:

1. create isolated private project `tradingtop-early-access`;
2. deploy `alisufyan-ai7/trading-signal-intelligence` from `main`;
3. use root `Dockerfile`;
4. healthcheck: `/healthz`;
5. mount persistent volume at `/data`;
6. set `TRADINGTOP_SNAPSHOT_PATH=/data/public_snapshot.json`;
7. configure invite + ingest secrets;
8. generate the public Railway domain;
9. configure Windows ingest URL/token;
10. push and verify the first derived snapshot.

See:

`docs/public-beta-deployment-railway.md`

## Local system

No action is needed on the scanners while hosting capacity is resolved.

XAUUSD, USTEC and US30 collectors continue running.

S02 remains NOT CANDIDATE.

XAU F1 progress remains `2/20`.
