from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"


def test_homepage_is_ai_first_with_s02_as_supporting_benchmark() -> None:
    html = (WEB / "index.html").read_text(encoding="utf-8")

    required = (
        "VOWSIG • AI RESEARCH BETA",
        "AI market intelligence, validated in the open.",
        "VowSig is an AI-first research beta.",
        "Core AI-v1.1 shadow evidence",
        "INDEPENDENT CONTROL • S02",
        "A fixed benchmark for testing whether AI adds value",
        "It does not drive, train or inform AI decisions",
        "The customer product is VowSig AI.",
        "Explore the S02 benchmark evidence",
    )
    for token in required:
        assert token in html

    assert html.index('id="ai-intelligence"') < html.index(
        'id="validation-programs-section"'
    )
    assert html.index('id="validation-programs-section"') < html.index(
        'id="s02-benchmark"'
    )

    # The complete benchmark evidence surface remains available.
    for element_id in (
        'id="live-grid"',
        'id="evidence-grid"',
        'id="signal-history"',
        'id="research-grid"',
    ):
        assert element_id in html

    assert '<details class="benchmark-details">' in html
    assert "S02 BENCHMARK • FORWARD" not in html
    assert "Recent S02 benchmark signals" not in html
    assert "Markets we scan" not in html
    assert "Recent issued signals" not in html


def test_homepage_status_is_snapshot_freshness_aware_and_ai_first() -> None:
    app = (WEB / "app.js").read_text(encoding="utf-8")

    assert 'health.snapshot_freshness === "stale"' in app
    assert 'health.snapshot_freshness === "delayed"' in app
    assert 'health.snapshot_freshness !== "fresh"' in app
    assert "AI shadow validation operational" in app
    assert "AI shadow validation attention required" in app
    assert "Public AI data stale" in app
    assert "Public AI data delayed" in app
    assert "benchmark evidence needs attention" in app
    assert "S02 benchmark collectors operational" not in app
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

    assert ".benchmark-principles" in css
    assert ".benchmark-details" in css
    assert ".benchmark-details-body" in css


def test_homepage_hero_matches_ai_first_research_beta_posture() -> None:
    html = (WEB / "index.html").read_text(encoding="utf-8")

    assert "AI market intelligence, validated in the open." in html
    assert "See the setup. See the risk. Verify the record." not in html
    assert 'href="#ai-intelligence">See AI intelligence</a>' in html
    assert (
        'href="#validation-programs-section">How validation works</a>'
        in html
    )
    assert (
        'property="og:description" '
        'content="AI market intelligence, validated in the open."'
        in html
    )
