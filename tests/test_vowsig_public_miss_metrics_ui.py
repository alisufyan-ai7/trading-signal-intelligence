from __future__ import annotations

from pathlib import Path


APP_JS = Path(__file__).resolve().parents[1] / "web" / "app.js"


def test_public_ai_ui_does_not_label_raw_missed_records_as_opportunities() -> None:
    text = APP_JS.read_text(encoding="utf-8")

    assert '"Missed opportunities"' not in text
    assert "Missed-rate:" not in text
    assert '"Processing misses"' in text
    assert '"No-current-tick cycles"' in text
    assert "Processing-miss rate:" in text
    assert "operational_miss_notice" in text

    # The UI must not fall back to the legacy aggregate if a new snapshot field
    # is absent. Missing separated metrics render as an em dash instead.
    assert "t.missed_inferences" not in text
    assert 't.processing_miss_count == null' in text
    assert 't.no_current_h1_tick_count == null' in text
