from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_EVIDENCE = Path("config/evidence_summary.json")


def evidence_summary(path: str | Path = DEFAULT_EVIDENCE) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def market_evidence(source_symbol: str, path: str | Path = DEFAULT_EVIDENCE) -> dict[str, Any] | None:
    payload = evidence_summary(path)
    return payload["markets"].get(source_symbol.upper())
