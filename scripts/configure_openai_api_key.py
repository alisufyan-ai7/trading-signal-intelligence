from __future__ import annotations

import getpass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
KEY = "OPENAI_API_KEY"


def main() -> None:
    value = getpass.getpass(
        "Enter the OpenAI API key for SignalProof AI-v1 (input hidden): "
    ).strip()
    if not value:
        raise SystemExit("OpenAI API key cannot be empty.")
    if any(ch.isspace() for ch in value):
        raise SystemExit("OpenAI API key must not contain whitespace.")

    existing: list[str] = []
    if ENV_PATH.exists():
        existing = ENV_PATH.read_text(encoding="utf-8-sig").splitlines()

    filtered = [
        line
        for line in existing
        if not line.startswith(f"{KEY}=")
    ]
    filtered.append(f"{KEY}={value}")
    ENV_PATH.write_text("\n".join(filtered) + "\n", encoding="utf-8")

    # Verify without displaying the secret.
    found = False
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{KEY}=") and line.split("=", 1)[1].strip():
            found = True
            break
    if not found:
        raise SystemExit("Failed to verify OPENAI_API_KEY in local .env.")

    print(f"Configured {KEY} in {ENV_PATH}")
    print(f"{KEY}=configured")
    print("Secret value was not displayed.")


if __name__ == "__main__":
    main()
