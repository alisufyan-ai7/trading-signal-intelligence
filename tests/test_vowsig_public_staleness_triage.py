from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "ops/handoffs/vowsig_public_staleness_readonly_v0_1.ps1"

def test_stale_operator_checks_all_four_real_tasks():
    body = SOURCE.read_text(encoding="utf-8")
    for name in ("SignalProof AI-v1.1 Shadow Scan",
                 "VowSig AI-v1.2.1 Expansion Shadow Scan",
                 "VowSig AI-v1.3 Crypto Shadow Scan",
                 "TradingTop Product Publish"):
        assert body.count(name) == 1
    assert "Get-ScheduledTaskInfo" in body
    assert "Get-ScheduledTask -TaskName" in body
    assert "data\\public_snapshot.json" in body
    assert "LOCAL_SNAPSHOT_STALE_150MIN" in body
    assert "LAST_RUN_OLDER_THAN_3H" in body

def test_operator_never_exposes_keys_or_mutates_production():
    body = SOURCE.read_text(encoding="utf-8").lower()
    forbidden = ("start-scheduledtask", "set-scheduledtask", "register-scheduledtask",
                 "invoke-webrequest", "invoke-restmethod", "start-process",
                 "git pull", "git checkout", "git reset", "set-content",
                 "new-item", "remove-item", "start-transcript",
                 "tradingtop_ingest_token", "openai_api_key", "write-host $tail")
    for keyword in forbidden:
        assert keyword not in body
    assert "get-content -literalpath $log -tail 160" in body
    assert "raw_logs_or_secrets_exported=$false" in body
    assert "network_calls=0" in body and "task_changes=0" in body
