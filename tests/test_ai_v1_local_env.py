from __future__ import annotations

import os

from trading_signal_intelligence.ai_v1.local_env import load_project_env


def test_project_env_overrides_inherited_openai_key(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "inherited-other-project-key")
    env_path = tmp_path / ".env"
    env_path.write_text(
        "OPENAI_API_KEY=project-local-key\n",
        encoding="utf-8",
    )

    load_project_env(env_path)

    assert os.environ["OPENAI_API_KEY"] == "project-local-key"
