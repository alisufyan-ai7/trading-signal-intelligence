from __future__ import annotations

import getpass
from pathlib import Path

from dotenv import dotenv_values, set_key


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env_path = repo_root / ".env"
    env_path.touch(exist_ok=True)

    token = getpass.getpass(
        "Enter the SAME SIGNALPROOF_FEEDBACK_OWNER_TOKEN configured in Railway: "
    ).strip()
    if len(token) < 24:
        raise SystemExit("Feedback owner token must be at least 24 characters.")

    set_key(
        str(env_path),
        "SIGNALPROOF_FEEDBACK_OWNER_TOKEN",
        token,
        quote_mode="never",
    )

    loaded = dotenv_values(env_path)
    loaded_token = str(loaded.get("SIGNALPROOF_FEEDBACK_OWNER_TOKEN") or "")
    if loaded_token != token:
        raise SystemExit("Environment verification failed for feedback owner token.")

    print(f"Feedback owner access configured: {env_path}")
    print("SIGNALPROOF_FEEDBACK_OWNER_TOKEN=configured")
    print("Configuration verified.")


if __name__ == "__main__":
    main()
