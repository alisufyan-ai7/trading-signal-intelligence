from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from trading_signal_intelligence.product.cloud_app import (
    INDEXABLE_PATHS,
    app,
    robots_txt,
    sitemap_xml,
)


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"

EXPECTED_INDEXABLE_PATHS = (
    "/",
    "/markets/",
    "/markets/xau-usd/",
    "/markets/nasdaq-100/",
    "/markets/dow-30/",
    "/learn/",
    "/learn/buy-sell-no-trade/",
    "/learn/backtests-vs-forward-results/",
    "/learn/immutable-signal-history/",
    "/learn/shadow-validation/",
    "/learn/signal-lifecycle/",
    "/evidence/",
)


def test_phase8a_indexable_route_manifest_is_small_and_explicit() -> None:
    assert INDEXABLE_PATHS == EXPECTED_INDEXABLE_PATHS
    assert len(INDEXABLE_PATHS) == 12
    assert all(path.startswith("/") for path in INDEXABLE_PATHS)
    assert all("/api/" not in path for path in INDEXABLE_PATHS)


def test_root_has_navigation_canonical_and_website_jsonld() -> None:
    text = (WEB / "index.html").read_text(encoding="utf-8")
    assert 'rel="canonical" href="https://vowsig.com/"' in text
    assert 'name="robots" content="index,follow,max-image-preview:large"' in text
    assert 'href="/markets/"' in text
    assert 'href="/learn/"' in text
    assert 'href="/evidence/"' in text
    assert 'type="application/ld+json"' in text
    assert '"@type":"WebSite"' in text


def test_each_phase8a_html_page_has_unique_canonical_and_research_beta() -> None:
    expected = {
        "markets/index.html": "https://vowsig.com/markets/",
        "markets/xau-usd.html": "https://vowsig.com/markets/xau-usd/",
        "markets/nasdaq-100.html": "https://vowsig.com/markets/nasdaq-100/",
        "markets/dow-30.html": "https://vowsig.com/markets/dow-30/",
        "learn/index.html": "https://vowsig.com/learn/",
        "learn/buy-sell-no-trade.html": (
            "https://vowsig.com/learn/buy-sell-no-trade/"
        ),
        "learn/backtests-vs-forward-results.html": (
            "https://vowsig.com/learn/backtests-vs-forward-results/"
        ),
        "learn/immutable-signal-history.html": (
            "https://vowsig.com/learn/immutable-signal-history/"
        ),
        "learn/shadow-validation.html": (
            "https://vowsig.com/learn/shadow-validation/"
        ),
        "learn/signal-lifecycle.html": (
            "https://vowsig.com/learn/signal-lifecycle/"
        ),
        "evidence/index.html": "https://vowsig.com/evidence/",
    }
    titles: set[str] = set()
    for relative, canonical in expected.items():
        text = (WEB / relative).read_text(encoding="utf-8")
        assert f'rel="canonical" href="{canonical}"' in text
        assert 'name="robots" content="index,follow,max-image-preview:large"' in text
        assert "Research beta." in text
        assert "guaranteed return" in text
        assert 'href="/markets/"' in text
        assert 'href="/learn/"' in text
        assert 'href="/evidence/"' in text
        start = text.index("<title>") + len("<title>")
        end = text.index("</title>", start)
        title = text[start:end]
        assert title not in titles
        titles.add(title)


def test_robots_txt_declares_sitemap_and_plumbing_exclusions() -> None:
    body = robots_txt().body.decode("utf-8")
    assert "User-agent: *" in body
    assert "Allow: /" in body
    assert "Disallow: /api/" in body
    assert "Disallow: /healthz" in body
    assert "Disallow: /docs" in body
    assert "Disallow: /redoc" in body
    assert "Disallow: /openapi.json" in body
    assert "Sitemap: https://vowsig.com/sitemap.xml" in body


def test_sitemap_contains_only_canonical_indexable_paths() -> None:
    body = sitemap_xml().body.decode("utf-8")
    for path in EXPECTED_INDEXABLE_PATHS:
        assert f"<loc>https://vowsig.com{path}</loc>" in body
    assert "/api/" not in body
    assert "/healthz" not in body
    assert "/docs" not in body
    assert "/openapi.json" not in body


def test_fastapi_framework_docs_are_disabled() -> None:
    assert app.docs_url is None
    assert app.redoc_url is None
    assert app.openapi_url is None


def test_api_and_health_routes_return_noindex_headers() -> None:
    client = TestClient(app)
    for path in ("/healthz", "/api/health", "/api/markets", "/api/ai/insights"):
        response = client.get(path)
        assert response.headers["X-Robots-Tag"] == (
            "noindex, nofollow, noarchive"
        )


def test_indexable_pages_do_not_receive_x_robots_noindex() -> None:
    client = TestClient(app)
    for path in EXPECTED_INDEXABLE_PATHS:
        response = client.get(path)
        assert response.status_code == 200
        assert "X-Robots-Tag" not in response.headers


def test_market_aliases_redirect_permanently_to_canonical_slugs() -> None:
    client = TestClient(app, follow_redirects=False)
    expected = {
        "/markets/xauusd/": "/markets/xau-usd/",
        "/markets/ustec/": "/markets/nasdaq-100/",
        "/markets/us30/": "/markets/dow-30/",
    }
    for source, target in expected.items():
        response = client.get(source)
        assert response.status_code == 301
        assert response.headers["location"] == target


def test_phase8a_copy_preserves_evidence_boundaries() -> None:
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(WEB.rglob("*.html"))
    )
    assert "SHADOW_ONLY" in combined
    assert "broker execution remains disabled" in combined
    assert "Historical results and live forward results must be evaluated separately." in combined
    assert "AI-v1.1" in combined
    assert "AI-v1.0" in combined
    assert "90% win" not in combined
    assert "guaranteed profit" not in combined.lower()
