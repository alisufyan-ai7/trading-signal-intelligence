from __future__ import annotations

import argparse
import getpass
from pathlib import Path

from dotenv import dotenv_values


DEFAULT_URL = (
    "https://tradingtop-early-access-production.up.railway.app"
    "/api/internal/snapshot"
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Configure TradingTop cloud snapshot ingestion in local .env"
    )
    parser.add_argument("--url", default=DEFAULT_URL)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    env_path = repo_root / ".env"

    token = getpass.getpass(
        "Enter the SAME TRADINGTOP_INGEST_TOKEN configured in Railway: "
    ).strip()
    if not token:
        raise SystemExit("Ingestion token cannot be empty.")

    existing = []
    if env_path.exists():
        existing = env_path.read_text(encoding="utf-8-sig").splitlines()

    managed = {"TRADINGTOP_INGEST_URL", "TRADINGTOP_INGEST_TOKEN"}
    kept = []
    for line in existing:
        key = line.split("=", 1)[0].strip() if "=" in line else None
        if key not in managed:
            kept.append(line)

    kept.extend(
        [
            f"TRADINGTOP_INGEST_URL={args.url}",
            f"TRADINGTOP_INGEST_TOKEN={token}",
        ]
    )

    env_path.write_text("\n".join(kept) + "\n", encoding="utf-8")

    loaded = dotenv_values(env_path)
    checks = {
        "TRADINGTOP_INGEST_URL": bool(loaded.get("TRADINGTOP_INGEST_URL")),
        "TRADINGTOP_INGEST_TOKEN": bool(loaded.get("TRADINGTOP_INGEST_TOKEN")),
    }

    if not all(checks.values()):
        raise SystemExit(f"Environment verification failed: {checks}")

    print(f"Cloud ingestion configured: {env_path}")
    print("TRADINGTOP_INGEST_URL=configured")
    print("TRADINGTOP_INGEST_TOKEN=configured")


if __name__ == "__main__":
    main()
