from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"


def test_homepage_scopes_s02_and_ai_lineages_explicitly() -> None:
    html = (WEB / "index.html").read_text(encoding="utf-8")

    required = (
        "Core AI-v1.1 shadow evidence",
        "S02 BENCHMARK • FORWARD",
        "S02 benchmark markets",
        "S02 BENCHMARK • HISTORICAL EVIDENCE",
        "Recent S02 benchmark signals",
        "S02 BENCHMARK • TRANSFER RESEARCH",
        "EUR/USD, XAG/USD and WTI also appear separately in AI-v1.2.1",
    )
    for token in required:
        assert token in html

    assert "Markets we scan" not in html
    assert "Recent issued signals" not in html


def test_homepage_status_is_snapshot_freshness_aware_and_s02_scoped() -> None:
    app = (WEB / "app.js").read_text(encoding="utf-8")

    assert 'health.snapshot_freshness === "stale"' in app
    assert 'health.snapshot_freshness === "delayed"' in app
    assert 'health.snapshot_freshness !== "fresh"' in app
    assert "S02 benchmark collectors operational" in app
    assert "Public data stale" in app
    assert "Public data delayed" in app
    assert "Systems operational" not in app


def test_homepage_validation_copy_is_customer_facing() -> None:
    html = (WEB / "index.html").read_text(encoding="utf-8")
    app = (WEB / "app.js").read_text(encoding="utf-8")

    assert "PUBLIC SHADOW FEED" in app
    assert "VALIDATION PROGRESS ONLY" in app
    assert "Active shadow records" in app
    assert "Recorded errors" in app
    assert "not hard-coded in the website" not in app
    assert "hard-coding new gate names" not in html


def test_homepage_reduces_initial_density_without_dropping_records() -> None:
    app = (WEB / "app.js").read_text(encoding="utf-8")
    css = (WEB / "styles.css").read_text(encoding="utf-8")

    assert "function renderExpandableRows" in app
    assert "renderExpandableRows(" in app
    assert "5," in app
    assert "evidence-more" in app
    assert ".evidence-more" in css


def test_homepage_hero_matches_research_beta_posture() -> None:
    html = (WEB / "index.html").read_text(encoding="utf-8")

    assert "See the setup. See the risk. Verify the record." in html
    assert "Find the trade. See the risk. Verify the record." not in html
    assert 'href="#ai-intelligence">See AI evidence</a>' in html
    assert 'href="/evidence/">How the evidence works</a>' in html
