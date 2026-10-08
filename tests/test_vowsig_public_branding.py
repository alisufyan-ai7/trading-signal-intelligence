from __future__ import annotations

from pathlib import Path

from scripts.verify_cloud_snapshot_durability import DEFAULT_BASE_URL


ROOT = Path(__file__).resolve().parents[1]


def test_public_html_uses_vowsig_as_canonical_brand() -> None:
    text = (ROOT / "web" / "index.html").read_text(encoding="utf-8")

    assert "<title>VowSig — Research Beta</title>" in text
    assert "VOWSIG • AI RESEARCH BETA" in text
    assert 'rel="canonical" href="https://vowsig.com/"' in text
    assert 'property="og:site_name" content="VowSig"' in text
    assert 'property="og:url" content="https://vowsig.com/"' in text
    assert "Help shape VowSig" in text
    assert "SignalProof AI" not in text


def test_public_javascript_uses_vowsig_customer_copy() -> None:
    text = (ROOT / "web" / "app.js").read_text(encoding="utf-8")

    assert "VowSig AI shadow insights are not available" in text
    assert "No VowSig shadow signal has been issued yet." in text


def test_public_cloud_metadata_uses_vowsig_without_secret_rename() -> None:
    text = (
        ROOT
        / "src"
        / "trading_signal_intelligence"
        / "product"
        / "cloud_app.py"
    ).read_text(encoding="utf-8")

    assert 'title="VowSig Research Beta Cloud"' in text
    assert '"product": "VowSig Research Beta"' in text
    assert '"service": "vowsig"' in text
    assert "filename=vowsig-feedback.csv" in text

    # v0.1 deliberately avoids deployment-secret churn.
    assert 'os.getenv("TRADINGTOP_SNAPSHOT_PATH")' in text
    assert 'os.getenv("TRADINGTOP_INGEST_TOKEN")' in text
    assert 'os.getenv("SIGNALPROOF_FEEDBACK_OWNER_TOKEN")' in text


def test_snapshot_generation_path_uses_vowsig_product_brand() -> None:
    local_app = (
        ROOT
        / "src"
        / "trading_signal_intelligence"
        / "product"
        / "app.py"
    ).read_text(encoding="utf-8")
    launch_config = (
        ROOT / "config" / "launch_universe.json"
    ).read_text(encoding="utf-8")

    assert 'title="VowSig Research Beta"' in local_app
    assert '"product": "VowSig Research Beta"' in local_app
    assert "filename=vowsig-feedback.csv" in local_app
    assert '"launch_target": "VowSig Research Beta"' in launch_config
    assert "SignalProof AI Research Beta" not in local_app
    assert "SignalProof AI Research Beta" not in launch_config

    # Existing secret names remain operational compatibility identifiers.
    assert 'os.getenv("SIGNALPROOF_FEEDBACK_OWNER_TOKEN")' in local_app


def test_cloud_durability_default_is_canonical_vowsig_domain() -> None:
    assert DEFAULT_BASE_URL == "https://vowsig.com"


def test_product_publisher_log_banner_uses_vowsig() -> None:
    text = (
        ROOT / "scripts" / "run_product_publish_task.cmd"
    ).read_text(encoding="utf-8")

    assert "===== VowSig product publish " in text
    assert "===== TradingTop product publish " not in text
