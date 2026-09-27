from __future__ import annotations

import argparse
import getpass
from pathlib import Path
from urllib.parse import urlparse

from dotenv import dotenv_values, set_key


DEFAULT_URL = (
    "https://tradingtop-early-access-production.up.railway.app"
    "/api/internal/snapshot"
)


def _validate_url(value: str) -> str:
    value = value.strip()
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise SystemExit("Ingest URL must be a valid HTTPS URL.")
    if "TRADINGTOP_" in value or "=" in parsed.path:
        raise SystemExit("Ingest URL appears to contain an environment variable or secret.")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Configure TradingTop cloud snapshot ingestion in local .env"
    )
    parser.add_argument("--url", default=DEFAULT_URL)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    env_path = repo_root / ".env"
    env_path.touch(exist_ok=True)

    url = _validate_url(args.url)
    token = getpass.getpass(
        "Enter the SAME TRADINGTOP_INGEST_TOKEN configured in Railway: "
    ).strip()
    if not token:
        raise SystemExit("Ingestion token cannot be empty.")

    set_key(str(env_path), "TRADINGTOP_INGEST_URL", url, quote_mode="never")
    set_key(
        str(env_path),
        "TRADINGTOP_INGEST_TOKEN",
        token,
        quote_mode="never",
    )

    loaded = dotenv_values(env_path)
    loaded_url = str(loaded.get("TRADINGTOP_INGEST_URL") or "")
    loaded_token = str(loaded.get("TRADINGTOP_INGEST_TOKEN") or "")

    if loaded_url != url:
        raise SystemExit("Environment verification failed for ingest URL.")
    if loaded_token != token:
        raise SystemExit("Environment verification failed for ingest token.")
    _validate_url(loaded_url)

    print(f"Cloud ingestion configured: {env_path}")
    print("TRADINGTOP_INGEST_URL=configured")
    print("TRADINGTOP_INGEST_TOKEN=configured")
    print("Configuration verified.")


if __name__ == "__main__":
    main()
