from __future__ import annotations

from pathlib import Path

import pytest

from trading_signal_intelligence.ai_v1.active_observability import (
    detect_active_runtime,
    v1_1_state,
)
from trading_signal_intelligence.ai_v1.observability import ObservabilityError
from trading_signal_intelligence.ai_v1.shadow_runtime_v1_1 import (
    DATABASE_PATHS as V11_DATABASE_PATHS,
)


def test_no_v1_1_state_keeps_v1_0_active(tmp_path: Path) -> None:
    assert detect_active_runtime(tmp_path) == "AI-v1.0"
    state = v1_1_state(tmp_path)
    assert state["any_state"] is False
    assert state["complete_shape"] is False


def test_partial_v1_1_ledger_state_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / V11_DATABASE_PATHS["USTEC"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"partial")

    with pytest.raises(ObservabilityError, match="partial AI-v1.1 state"):
        detect_active_runtime(tmp_path)


def test_partial_v1_1_anchor_state_fails_closed(tmp_path: Path) -> None:
    forward = tmp_path / "research" / "forward"
    forward.mkdir(parents=True, exist_ok=True)
    (forward / "AI-v1.1-activation-test.json").write_text(
        "{}\n",
        encoding="utf-8",
    )

    with pytest.raises(ObservabilityError, match="partial AI-v1.1 state"):
        detect_active_runtime(tmp_path)
