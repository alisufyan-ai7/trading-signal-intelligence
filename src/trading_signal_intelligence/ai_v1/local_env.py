from __future__ import annotations

import os
from pathlib import Path


def load_local_env(path: str | Path, *, override: bool = False) -> None:
    """Load simple KEY=VALUE entries without adding a runtime dependency.

    This intentionally supports the repository's local secret file format, not
    the full dotenv specification.
    """

    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if override or key not in os.environ:
            os.environ[key] = value


def load_project_env(path: str | Path) -> None:
    """Load project-local secrets with precedence over inherited process env.

    The SignalProof AI-v1 runtime intentionally prefers the repository-local
    .env for project-scoped credentials (for example OPENAI_API_KEY). This
    prevents unrelated machine/user environment variables from silently
    selecting credentials for another OpenAI project.
    """
    load_local_env(path, override=True)
