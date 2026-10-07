from __future__ import annotations

import re
import struct
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"

HTML_FILES = (
    WEB / "index.html",
    WEB / "markets" / "index.html",
    WEB / "markets" / "xau-usd.html",
    WEB / "markets" / "nasdaq-100.html",
    WEB / "markets" / "dow-30.html",
    WEB / "learn" / "index.html",
    WEB / "learn" / "buy-sell-no-trade.html",
    WEB / "learn" / "backtests-vs-forward-results.html",
    WEB / "learn" / "immutable-signal-history.html",
    WEB / "learn" / "shadow-validation.html",
    WEB / "learn" / "signal-lifecycle.html",
    WEB / "evidence" / "index.html",
)

FAVICON_SVG = WEB / "vowsig-favicon.svg"
FAVICON_PNG = WEB / "vowsig-favicon-96.png"
APPLE_TOUCH = WEB / "vowsig-apple-touch-icon.png"


class _AuditParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.h1_count = 0
        self.main_ids: list[str | None] = []
        self.main_tabindexes: list[str | None] = []
        self.skip_links: list[str | None] = []
        self.icon_hrefs: list[str] = []
        self.apple_hrefs: list[str] = []
        self.viewport = False
        self.theme_color = False
        self.primary_nav = False
        self.images_missing_alt = 0
        self.external_assets: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        values = dict(attrs)
        if tag == "h1":
            self.h1_count += 1
        if tag == "main":
            self.main_ids.append(values.get("id"))
            self.main_tabindexes.append(values.get("tabindex"))
        if tag == "a" and "skip-link" in (values.get("class") or "").split():
            self.skip_links.append(values.get("href"))
        if tag == "meta" and values.get("name") == "viewport":
            self.viewport = True
        if tag == "meta" and values.get("name") == "theme-color":
            self.theme_color = values.get("content") == "#09111f"
        if tag == "nav" and values.get("aria-label") == "Primary":
            self.primary_nav = True
        if tag == "img" and "alt" not in values:
            self.images_missing_alt += 1
        if tag == "link":
            rel = (values.get("rel") or "").split()
            href = values.get("href") or ""
            if "icon" in rel:
                self.icon_hrefs.append(href)
            if "apple-touch-icon" in rel:
                self.apple_hrefs.append(href)
            if "stylesheet" in rel and href.startswith(("http://", "https://")):
                self.external_assets.append(href)
        if tag == "script":
            src = values.get("src") or ""
            if src.startswith(("http://", "https://")):
                self.external_assets.append(src)


def _parsed(path: Path) -> tuple[str, _AuditParser]:
    text = path.read_text(encoding="utf-8")
    parser = _AuditParser()
    parser.feed(text)
    return text, parser


def _png_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert data[12:16] == b"IHDR"
    return struct.unpack(">II", data[16:24])


def _srgb_luminance(hex_color: str) -> float:
    rgb = [int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5)]

    def linear(value: float) -> float:
        if value <= 0.04045:
            return value / 12.92
        return ((value + 0.055) / 1.055) ** 2.4

    red, green, blue = (linear(value) for value in rgb)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def _contrast(a: str, b: str) -> float:
    first, second = sorted(
        (_srgb_luminance(a), _srgb_luminance(b)),
        reverse=True,
    )
    return (first + 0.05) / (second + 0.05)


def test_all_indexable_pages_have_search_branding_and_accessibility_foundation() -> None:
    assert len(HTML_FILES) == 12
    for path in HTML_FILES:
        text, parser = _parsed(path)
        assert parser.viewport, path
        assert parser.theme_color, path
        assert parser.h1_count == 1, path
        assert parser.main_ids == ["main-content"], path
        assert parser.main_tabindexes == ["-1"], path
        assert parser.skip_links == ["#main-content"], path
        assert parser.primary_nav, path
        assert parser.images_missing_alt == 0, path
        assert parser.external_assets == [], path
        assert "/static/vowsig-favicon.svg" in parser.icon_hrefs, path
        assert "/static/vowsig-favicon-96.png" in parser.icon_hrefs, path
        assert parser.apple_hrefs == ["/static/vowsig-apple-touch-icon.png"], path
        assert 'name="robots" content="index,follow,max-image-preview:large"' in text


def test_content_pages_use_semantic_breadcrumb_navigation() -> None:
    for path in HTML_FILES[1:]:
        text = path.read_text(encoding="utf-8")
        assert '<nav class="breadcrumbs" aria-label="Breadcrumb">' in text


def test_dashboard_javascript_is_deferred() -> None:
    text = (WEB / "index.html").read_text(encoding="utf-8")
    assert '<script defer src="/static/app.js?v=20261008-consistency-1"></script>' in text


def test_favicon_assets_are_square_and_expected_sizes() -> None:
    tree = ET.parse(FAVICON_SVG)
    root = tree.getroot()
    assert root.attrib["viewBox"] == "0 0 96 96"
    assert _png_dimensions(FAVICON_PNG) == (96, 96)
    assert _png_dimensions(APPLE_TOUCH) == (180, 180)
    assert FAVICON_PNG.stat().st_size < 4096
    assert APPLE_TOUCH.stat().st_size < 8192


def test_frontend_payloads_remain_small_and_local() -> None:
    assert (WEB / "index.html").stat().st_size < 20_000
    assert (WEB / "styles.css").stat().st_size < 20_000
    assert (WEB / "app.js").stat().st_size < 25_000
    for path in HTML_FILES[1:]:
        assert path.stat().st_size < 8_000, path


def test_styles_include_keyboard_touch_mobile_and_reduced_motion_guards() -> None:
    css = (WEB / "styles.css").read_text(encoding="utf-8")
    required = (
        ".skip-link",
        ":focus-visible",
        "min-height: 44px",
        "@media (max-width: 520px)",
        "@media (prefers-reduced-motion: reduce)",
        "font-size: 16px",
    )
    for token in required:
        assert token in css


def test_core_palette_meets_wcag_aa_normal_text_contrast() -> None:
    foregrounds = ("#f5f7fb", "#9eacc0", "#78e0b1", "#ffd479", "#ff9f9f")
    backgrounds = ("#09111f", "#111b2d", "#17243a")
    for foreground in foregrounds:
        for background in backgrounds:
            assert _contrast(foreground, background) >= 4.5


def test_no_duplicate_ids_in_static_html() -> None:
    for path in HTML_FILES:
        text = path.read_text(encoding="utf-8")
        ids = re.findall(r'\bid="([^"]+)"', text)
        assert len(ids) == len(set(ids)), path
