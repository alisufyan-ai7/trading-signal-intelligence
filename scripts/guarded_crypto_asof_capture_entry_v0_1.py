"""Owner-gated, fail-closed entry for ONE local historical crypto aggregate seal.

DORMANT. --mode import-smoke is the only currently authorized invocation.
Do NOT run --mode capture without separate owner approval and exact SHA checks.

Native Windows asyncio subclasses subprocess.Popen; NEVER replace that class
with a function. Instead use a class-compatible child-process guard.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import socket
import sqlite3
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
SEAL_NAME = "crypto-research-asof-v0.1.json"
OPT_IN = "VOWSIG_CRYPTO_SEAL_CAPTURE_ENABLED"
CONFIRM = "CAPTURE-ONE-CRYPTO-ASOF-RESEARCH-SEAL"
DB_NAMES = (
    "ai_v1_1_xauusd", "ai_v1_1_ustec", "ai_v1_1_us30",
    "ai_v1_2_1_eurusd", "ai_v1_2_1_xagusd", "ai_v1_2_1_usoil",
    "ai_v1_3_btcusdt", "ai_v1_3_ethusdt", "ai_v1_3_solusdt",
)
SCHEDULER_TASK_NAMES = (
    "SignalProof AI-v1 Shadow Scan",
    "SignalProof AI-v1.1 Shadow Scan",
    "VowSig AI-v1.2.1 Expansion Shadow Scan",
    "VowSig AI-v1.3 Crypto Shadow Scan",
)


class CaptureGuardRejected(RuntimeError):
    """A process, network, or SQLite access violated one-shot constraints."""


class CaptureGuard:
    def __init__(self, live_root: Path) -> None:
        self.live = live_root.resolve()
        self.allowed = {
            str((self.live / "data" / (name + ".sqlite")).resolve()).casefold()
            for name in DB_NAMES
        }
        self.opened: set[str] = set()
        if len(self.allowed) != 9:
            raise CaptureGuardRejected("nine allowed SQLite identities required")

    def db_key(self, database: Any) -> str:
        if not isinstance(database, str) or not database.startswith("file:"):
            raise CaptureGuardRejected("SQLite must use file URI")
        address, separator, options = database.partition("?")
        if not separator or options != "mode=ro":
            raise CaptureGuardRejected("SQLite mode must be exactly ro")
        if "%" in address or "#" in address:
            # No URI aliases or fragments. Existing observed DB builder uses
            # plain file:<absolute-path>?mode=ro, which is unambiguous.
            raise CaptureGuardRejected("encoded SQLite URI not accepted")
        key = str(Path(unquote(address[5:])).resolve()).casefold()
        if key not in self.allowed:
            raise CaptureGuardRejected("SQLite outside nine active AI ledgers")
        return key

    def _git_command(self, args: list[str], cwd: Any) -> None:
        if cwd is None or Path(cwd).resolve() != self.live:
            raise CaptureGuardRejected("Git working directory not production root")
        if len(args) < 3:
            raise CaptureGuardRejected("incomplete Git read")
        sub = args[1]
        if sub == "rev-parse":
            ok = len(args) == 3 and args[2] in ("HEAD", "@{u}")
        elif sub == "show":
            ok = (
                len(args) == 3 and ":" in args[2]
                and not args[2].startswith("-")
            )
        elif sub == "status":
            ok = (len(args) == 6 and args[2:5] == [
                "--porcelain", "--untracked-files=no", "--"
            ])
        elif sub == "ls-files":
            ok = len(args) == 4 and args[2] == "--" and args[3] == "web"
        else:
            ok = False
        if not ok:
            raise CaptureGuardRejected("Git command outside read-only allowlist")

    def _powershell_command(self, args: list[str]) -> None:
        if args[1:4] not in (
            ["-NoProfile", "-Command", args[3]] if len(args) == 4 else [],
            ["-NoProfile", "-NonInteractive", "-Command"] if len(args) == 5 else [],
        ):
            raise CaptureGuardRejected("unexpected PowerShell invocation")
        if len(args) not in (4, 5):
            raise CaptureGuardRejected("unexpected PowerShell argument count")
        script = args[-1]
        if not script.startswith("$ErrorActionPreference='Stop';"):
            raise CaptureGuardRejected("PowerShell fail-closed declaration missing")
        if "Get-ScheduledTask -TaskName '" not in script or "Get-ScheduledTaskInfo -TaskName '" not in script or "ConvertTo-Json" not in script:
            raise CaptureGuardRejected("non-observational scheduler command")
        for task in SCHEDULER_TASK_NAMES:
            if f"Get-ScheduledTask -TaskName '{task}'" in script:
                if f"Get-ScheduledTaskInfo -TaskName '{task}'" not in script:
                    raise CaptureGuardRejected("mismatched scheduler task")
                break
        else:
            raise CaptureGuardRejected("unknown scheduled-task name")
        if re.search(
            r"(?i)(Start|Stop|Set|Remove|Register|Unregister|Enable|"
            r"Disable|Invoke|New)-ScheduledTask|Invoke-WebRequest|"
            r"Invoke-RestMethod|Start-Process|Invoke-Expression|"
            r"DownloadString|FromBase64String|EncodedCommand",
            script,
        ):
            raise CaptureGuardRejected("task mutation or network command refused")

    def check_process(self, args: Any, cwd: Any, shell: bool) -> None:
        if shell or not isinstance(args, (tuple, list)) or not args:
            raise CaptureGuardRejected("shell or unrecognized subprocess")
        cmd = [str(x) for x in args]
        binary = Path(cmd[0]).name.casefold()
        if binary in ("git", "git.exe"):
            self._git_command(cmd, cwd)
        elif binary in ("powershell.exe", "powershell", "pwsh.exe", "pwsh"):
            self._powershell_command(cmd)
        else:
            raise CaptureGuardRejected("non-allowlisted child process")

    def install(self) -> None:
        parent = self
        original_popen = subprocess.Popen

        class GuardedPopen(original_popen):
            def __init__(self, args: Any, *items: Any, **kwargs: Any) -> None:
                parent.check_process(
                    args, kwargs.get("cwd"), bool(kwargs.get("shell", False))
                )
                super().__init__(args, *items, **kwargs)

        subprocess.Popen = GuardedPopen
        original_connect = sqlite3.connect

        def guarded_connect(database: Any, *items: Any, **kwargs: Any):
            key = parent.db_key(database)
            if kwargs.get("uri") is not True:
                raise CaptureGuardRejected("SQLite uri=True is required")
            conn = original_connect(database, *items, **kwargs)
            try:
                conn.execute("PRAGMA query_only = ON")
            except BaseException:
                conn.close()
                raise
            parent.opened.add(key)
            return conn

        sqlite3.connect = guarded_connect

        def deny_network(*_args: Any, **_kwargs: Any) -> None:
            raise CaptureGuardRejected("network operation forbidden")

        socket.socket.connect = deny_network
        socket.socket.connect_ex = deny_network
        socket.socket.sendto = deny_network
        socket.create_connection = deny_network
        urllib.request.urlopen = deny_network

        def audit(event: str, _args: tuple[Any, ...]) -> None:
            if event in ("socket.connect", "socket.sendto", "os.system",
                         "os.exec", "os.posix_spawn", "os.startfile"):
                raise CaptureGuardRejected("forbidden audited operation: " + event)

        sys.addaudithook(audit)

    def import_smoke(self) -> None:
        if sys.platform != "win32":
            raise CaptureGuardRejected("native Windows required")
        import asyncio.windows_utils as windows_utils
        import fastapi
        if not isinstance(subprocess.Popen, type):
            raise CaptureGuardRejected("subprocess.Popen no longer a class")
        if not issubclass(windows_utils.Popen, subprocess.Popen):
            raise CaptureGuardRejected("asyncio subclass compatibility failed")
        sys.path.insert(0, str(ROOT / "src"))
        sys.path.insert(0, str(ROOT / "scripts"))
        from capture_crypto_research_asof_v0_1 import produce_one_seal
        if not callable(produce_one_seal):
            raise CaptureGuardRejected("capture import missing")
        if self.opened:
            raise CaptureGuardRejected("import-only attempted SQLite access")
        for attempt in (
            lambda: self.db_key("file:C:/unrelated.sqlite?mode=ro"),
            lambda: self.db_key("file:C:/unrelated.sqlite?mode=rw"),
            lambda: self.check_process(["cmd.exe", "/c", "echo", "x"], None, False),
            lambda: self.check_process(["git", "reset", "--hard"], self.live, False),
        ):
            try:
                attempt()
            except CaptureGuardRejected:
                pass
            else:
                raise CaptureGuardRejected("negative self-check did not refuse")
        print("CAPTURE_GUARD_IMPORT_ONLY=PASS")
        print("WINDOWS_ASYNCIO_FASTAPI_IMPORT=PASS")
        print("SUBPROCESS_POPEN_CLASS_COMPATIBLE=PASS")
        print("FORBIDDEN_PROCESS_SQLITE_DENIAL=PASS")
        print("LIVE_SQLITE_CONNECTIONS=0")
        print("SEAL_CREATED=False")
        print("CLOUD_PUBLICATION=False")


def safe_seal_metadata(path: Path, expected_digest: str) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise CaptureGuardRejected("seal file missing or symlink")
    raw = path.read_bytes()
    if not 0 < len(raw) <= 65536:
        raise CaptureGuardRejected("unexpected local seal bytes")
    if hashlib.sha256(raw).hexdigest() != expected_digest:
        raise CaptureGuardRejected("local seal digest mismatch")
    payload = json.loads(raw)
    if not isinstance(payload, dict) or set(payload) != {
        "seal_schema_version", "source_snapshot_generated_at_utc",
        "crypto_program",
    }:
        raise CaptureGuardRejected("unexpected seal schema")
    crypto = payload["crypto_program"]
    if (not isinstance(crypto, dict)
        or crypto.get("program_id") != "crypto-expansion-1"
        or crypto.get("public_signal_exposure") is not False
        or crypto.get("signal_details_included") is not False
        or crypto.get("health", {}).get("broker_execution_disabled") is not True):
        raise CaptureGuardRejected("safety attributes failed")
    return {"sha256": expected_digest, "bytes": len(raw),
            "observed_at_utc": payload["source_snapshot_generated_at_utc"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("import-smoke", "capture"), required=True)
    parser.add_argument("--live-root", required=True, type=Path)
    parser.add_argument("--confirm", default="")
    args = parser.parse_args()
    live = args.live_root.resolve()
    if args.mode == "capture":
        if args.confirm != CONFIRM or os.environ.get(OPT_IN) != "1":
            raise CaptureGuardRejected("new owner capture approval required")
        if (live / "data" / SEAL_NAME).exists():
            raise CaptureGuardRejected("local seal exists; do not overwrite")
    guard = CaptureGuard(live)
    guard.install()
    guard.import_smoke()
    if args.mode == "import-smoke":
        return
    from capture_crypto_research_asof_v0_1 import produce_one_seal
    digest = produce_one_seal(live)
    if guard.opened != guard.allowed:
        raise CaptureGuardRejected("unexpected SQLite connection count or scope")
    output = safe_seal_metadata(live / "data" / SEAL_NAME, digest)
    print("LOCAL_CRYPTO_SEAL_CREATED=TRUE")
    print("SEAL_SHA256=" + output["sha256"])
    print("SEAL_BYTES=" + str(output["bytes"]))
    print("SEAL_OBSERVED_UTC=" + output["observed_at_utc"])
    print("SQLITE_READ_ONLY_CONNECTIONS=9_OF_9")
    print("CLOUD_UPLOAD=False")
    print("WEBSITE_PUBLICATION=False")


if __name__ == "__main__":
    main()
