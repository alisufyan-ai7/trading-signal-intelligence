# S02/XAUUSD Forward Checkpoint — 2026-09-27

This file anchors the first completed forward signal lifecycles observed after the XAUUSD activation.

## Ledger state

- database: `data/forward.sqlite`
- verification: `valid = true`
- records: `6`
- counts:
  - ACTIVATION: 1
  - SIGNAL: 2
  - EXIT: 2
  - SKIPPED_SIGNAL: 1
- unresolved signals: none
- current ledger head SHA-256: `e7b3e4d69292a81865ae62201e5cebb469e1b77d6826e0a9f434c4a677dcd904`

## Forward trade 1

- entity: `S02-v0.1:XAUUSD:PRIMARY:2026-09-22T07:00:00+00:00`
- direction: short
- signal close / entry timestamp: `2026-09-22T08:00:00Z`
- signal recorded: `2026-09-22T08:02:06.549748Z`
- discovery lag: `126.549748 seconds`
- entry: `4301.163`
- stop: `4330.563988105728`
- target: `4227.66052973568`
- signal record hash: `7d2428745115095765ad0aeba0fc551e56d0abdb2e23af7de119a8942fd1852e`
- exit: stop
- exit bar timestamp: `2026-09-22T08:00:00Z`
- gross R: approximately `-1.000000R`
- net R: `-1.007142617086372R`
- exit record hash: `00c0a9f626d1502ab524c87894f9d540627aa5628cd882d7a3bf9ddfefad8326`

## Forward trade 2

- entity: `S02-v0.1:XAUUSD:PRIMARY:2026-09-23T13:00:00+00:00`
- direction: short
- signal close / entry timestamp: `2026-09-23T14:00:00Z`
- signal recorded: `2026-09-23T14:02:09.212223Z`
- discovery lag: `129.212223 seconds`
- entry: `4284.076`
- stop: `4311.80054698403`
- target: `4214.7646325399255`
- signal record hash: `4b9d6292302726259f1dbac173f3e8d52d4b34be7cdb27c31384ae3e6424d0e2`
- exit: stop
- exit bar timestamp: `2026-09-25T11:00:00Z`
- gross R: approximately `-1.000000R`
- net R: `-1.0075745151082596R`
- exit record hash / current ledger head: `e7b3e4d69292a81865ae62201e5cebb469e1b77d6826e0a9f434c4a677dcd904`

## Skipped setup

A further XAUUSD short setup closed at `2026-09-24T09:00:00Z` while forward trade 2 remained open.

It was correctly logged as:

- record type: `SKIPPED_SIGNAL`
- reason: `existing_forward_position_open`
- record hash: `2f460fe2b1f05a89231d1abd947462932bf7cd6469d780bc1debf355eb76b35e`

This is expected under the frozen one-position-per-market rule.

## F1 progress

The predeclared F1 gate is an execution/lifecycle audit after 20 completed forward trades.

Current progress:

`2 / 20 completed forward trades`

The two losses do not trigger strategy rejection, promotion, or tuning.

## Interpretation

Operational lifecycle behavior is consistent with the frozen protocol:

- fresh signals were recorded within the 5-minute allowance;
- entry timestamps matched the next H1 open;
- stop exits were recorded deterministically;
- frozen costs were included;
- the overlapping setup was not retroactively traded;
- ledger verification remains valid.

No strategy/config/scanner/ledger rule changes are authorized from this checkpoint.
