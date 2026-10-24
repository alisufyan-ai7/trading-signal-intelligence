"""EXP042 Windows-VPS-only seven-wheel PyPI acquisition and isolated install.

REQUIRES EXPLICIT OWNER APPROVAL: granted 2026-10-23 for official PyPI
metadata + fixed SHA-pinned wheel downloads, installation in a NEW
disposable venv only AFTER all files and active dependency closure validate.

No AWS/B2 API/credentials, no production venv, no SDK method invocations,
no normal pip index downloads, no runtime scheduled tasks, no live backup.
Never treat SHA verification as proof of code safety.
"""
from __future__ import annotations

import argparse
import email
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
import venv
import zipfile
from pathlib import Path

# One exact, deliberately small reviewed set. Never auto-resolve new packages.
EXPECTED = {
    "boto3": ("1.43.114", "boto3-1.43.114-py3-none-any.whl"),
    "botocore": ("1.43.114", "botocore-1.43.114-py3-none-any.whl"),
    "jmespath": ("1.0.1", "jmespath-1.0.1-py3-none-any.whl"),
    "s3transfer": ("0.19.3", "s3transfer-0.19.3-py3-none-any.whl"),
    "python-dateutil": ("2.9.0.post0", "python_dateutil-2.9.0.post0-py2.py3-none-any.whl"),
    "urllib3": ("2.8.0", "urllib3-2.8.0-py3-none-any.whl"),
    "six": ("1.17.0", "six-1.17.0-py2.py3-none-any.whl"),
}
LOCK_PATTERN = re.compile(r"^([a-z][a-z0-9-]*)==([a-zA-Z0-9.]+) --hash=sha256:([0-9a-f]{64})$")
MAX_WHEEL_BYTES = 20 * 1024 * 1024
MAX_METADATA_BYTES = 2 * 1024 * 1024


class SDKAcquisitionRejected(RuntimeError):
    """Always redact underlying URLs, files, HTTP exceptions and pip output."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise SDKAcquisitionRejected("unexpected package redirect")


class _NoEchoParser(argparse.ArgumentParser):
    def error(self, message):
        raise SDKAcquisitionRejected("unapproved SDK acquisition arguments")


def _read_lock(path: Path) -> dict[str, tuple[str, str, str]]:
    if not path.is_file() or path.is_symlink():
        raise SDKAcquisitionRejected("reviewed lock missing or symlinked")
    records = {}
    for item in path.read_text(encoding="utf-8").splitlines():
        item = item.strip()
        if not item or item.startswith("#"):
            continue
        match = LOCK_PATTERN.fullmatch(item)
        if match is None:
            raise SDKAcquisitionRejected("unrecognized lock line")
        name, version, sha = match.groups()
        if name in records or name not in EXPECTED or version != EXPECTED[name][0]:
            raise SDKAcquisitionRejected("unapproved package or duplicate lock entry")
        records[name] = (version, sha, EXPECTED[name][1])
    if set(records) != set(EXPECTED):
        raise SDKAcquisitionRejected("wheel lock has missing or added packages")
    return records


def _inside_temp_new_folder(folder: Path) -> Path:
    # Guard accidental use of production paths; only UNIQUE missing folders
    # underneath Windows TEMP can ever become a wheelhouse or virtualenv.
    temporary = Path(tempfile.gettempdir()).resolve(strict=True)
    if (folder.is_symlink() or folder.exists() or folder.parent.is_symlink()
            or folder.parent.resolve(strict=True) != temporary
            or not folder.name.startswith("vowsig-exp042-")):
        raise SDKAcquisitionRejected("new disposable TEMP location required")
    return folder


def _request_exact_https(url: str, host: str, cap: int) -> bytes:
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme != "https" or parsed.hostname != host
            or parsed.port is not None or parsed.username is not None
            or parsed.password is not None or parsed.fragment
            or parsed.query):
        raise SDKAcquisitionRejected("unapproved package source")
    # No credential/ambient proxies or redirects; hostname TLS verified by stdlib.
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}), _NoRedirect())
    try:
        with opener.open(url, timeout=20) as response:
            if response.geturl() != url or response.status != 200:
                raise SDKAcquisitionRejected("package HTTP response rejected")
            payload = response.read(cap + 1)
    except SDKAcquisitionRejected:
        raise
    except Exception:
        raise SDKAcquisitionRejected("official PyPI fetch failed") from None
    if not 0 < len(payload) <= cap:
        raise SDKAcquisitionRejected("package download exceeded byte budget")
    return payload


def _verify_metadata_and_get_wheel_url(name, version, filename, sha):
    # Only pypi.org JSON and a single selected files.pythonhosted.org wheel.
    url = f"https://pypi.org/pypi/{name}/{version}/json"
    try:
        metadata = json.loads(_request_exact_https(url, "pypi.org", MAX_METADATA_BYTES))
    except Exception:
        raise SDKAcquisitionRejected("PyPI release metadata invalid") from None
    if (metadata.get("info", {}).get("name", "").lower().replace("_", "-") != name
            or metadata.get("info", {}).get("version") != version):
        raise SDKAcquisitionRejected("PyPI project metadata unexpected")
    files = [
        obj for obj in metadata.get("urls", [])
        if obj.get("filename") == filename and obj.get("packagetype") == "bdist_wheel"
    ]
    if (len(files) != 1 or files[0].get("digests", {}).get("sha256") != sha
            or files[0].get("yanked") is True):
        raise SDKAcquisitionRejected("published PyPI wheel hash or status mismatch")
    return files[0]["url"], metadata.get("info", {}).get("requires_dist") or []


def _inspect_all_wheel_metadata(wheelhouse: Path, records, published_dependencies):
    # Use only the already-present pip vendored packaging parser on the
    # operator's EXISTING isolated interpreter. It never imports wheel code.
    try:
        from pip._vendor.packaging.requirements import Requirement
        from pip._vendor.packaging.specifiers import SpecifierSet
        from pip._vendor.packaging.utils import canonicalize_name
    except Exception:
        raise SDKAcquisitionRejected("local wheel metadata parser unavailable") from None

    for name, (version, _, filename) in records.items():
        path = wheelhouse / filename
        try:
            with zipfile.ZipFile(path) as archive:
                entries = [entry for entry in archive.namelist()
                           if entry.endswith(".dist-info/METADATA")]
                if len(entries) != 1:
                    raise SDKAcquisitionRejected("ambiguous wheel metadata")
                raw = archive.read(entries[0])
            parsed = email.message_from_bytes(raw)
            package = canonicalize_name(parsed.get("Name", ""))
            if package != name or parsed.get("Version", "") != version:
                raise SDKAcquisitionRejected("wheel metadata identity mismatch")
            python_req = parsed.get("Requires-Python")
            if python_req and ("3.12" not in SpecifierSet(python_req)):
                raise SDKAcquisitionRejected("unsupported wheel Python version")
            requirements = parsed.get_all("Requires-Dist", [])
            # Compare release JSON Requires-Dist with wheel data to prevent
            # silently changing the meaning of the public metadata snapshot.
            normalize = lambda values: sorted(str(Requirement(v)) for v in values)
            if normalize(requirements) != normalize(published_dependencies[name]):
                raise SDKAcquisitionRejected("published and wheel dependencies differ")
            for spec in requirements:
                requirement = Requirement(spec)
                if requirement.marker and not requirement.marker.evaluate({"extra": ""}):
                    continue
                dep = canonicalize_name(requirement.name)
                if (requirement.url is not None or requirement.extras
                        or dep not in records
                        or records[dep][0] not in requirement.specifier):
                    raise SDKAcquisitionRejected("unlocked or incompatible active dependency")
        except SDKAcquisitionRejected:
            raise
        except Exception:
            raise SDKAcquisitionRejected("invalid wheel requirement data") from None


def stage_and_install(*, lock_path: Path, wheelhouse: Path, venv_path: Path):
    if os.name != "nt" or sys.version_info[:2] != (3, 12):
        raise SDKAcquisitionRejected("Python 3.12 Windows VPS required")
    records = _read_lock(lock_path)
    _inside_temp_new_folder(wheelhouse)
    _inside_temp_new_folder(venv_path)
    if wheelhouse == venv_path:
        raise SDKAcquisitionRejected("wheelhouse and venv paths must differ")
    wheelhouse.mkdir(mode=0o700)
    published = {}
    for name, (version, sha, filename) in sorted(records.items()):
        url, deps = _verify_metadata_and_get_wheel_url(name, version, filename, sha)
        content = _request_exact_https(url, "files.pythonhosted.org", MAX_WHEEL_BYTES)
        if hashlib.sha256(content).hexdigest() != sha:
            raise SDKAcquisitionRejected("downloaded wheel SHA256 mismatch")
        (wheelhouse / filename).write_bytes(content)
        published[name] = deps
        print(f"EXP042_WHEEL_HASH=PASS:{name}=={version}")

    if set(p.name for p in wheelhouse.iterdir()) != set(
        item[2] for item in records.values()):
        raise SDKAcquisitionRejected("unexpected wheelhouse contents")
    _inspect_all_wheel_metadata(wheelhouse, records, published)
    print("EXP042_ALL_SEVEN_WHEELS_AND_ACTIVE_DEPENDENCIES=PASS")

    # Absolutely no virtualenv/installation before seven wheel integrity and
    # dependency checks pass. Create a NEW environment; NEVER existing ones.
    try:
        venv.EnvBuilder(with_pip=True, system_site_packages=False).create(venv_path)
    except Exception:
        raise SDKAcquisitionRejected("disposable venv creation failed") from None
    new_python = venv_path / "Scripts" / "python.exe"
    if not new_python.is_file():
        raise SDKAcquisitionRejected("new disposable Python missing")

    command = [
        str(new_python), "-m", "pip", "--isolated", "install",
        "--no-index", "--no-cache-dir", "--disable-pip-version-check",
        "--no-input", "--only-binary=:all:", "--require-hashes",
        "--no-deps", "--find-links", str(wheelhouse), "-r", str(lock_path),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True,
                                timeout=180, check=False)
        if result.returncode != 0:
            raise SDKAcquisitionRejected("offline wheel install rejected")
        result = subprocess.run(
            [str(new_python), "-m", "pip", "--isolated", "check"],
            capture_output=True, text=True, timeout=30, check=False)
        if result.returncode != 0:
            raise SDKAcquisitionRejected("new venv dependency check rejected")
        inspector = (
            "import importlib.metadata as m,json;"
            "print(json.dumps({n:m.version(n) for n in "
            + repr(sorted(records)) + "},sort_keys=True))"
        )
        result = subprocess.run([str(new_python), "-I", "-c", inspector],
                                capture_output=True, text=True,
                                timeout=30, check=False)
        if result.returncode != 0 or json.loads(result.stdout) != {
            name: details[0] for name, details in records.items()
        }:
            raise SDKAcquisitionRejected("installed wheel version mismatch")
    except SDKAcquisitionRejected:
        raise
    except Exception:
        raise SDKAcquisitionRejected("disposable SDK environment verification failed") from None

    print("EXP042_DISPOSABLE_SDK_INSTALL=PASS")
    print("EXP042_PACKAGE_COUNT=7")
    print("EXP042_PYPI_ONLY_REQUESTS=YES")
    print("EXP042_PROVIDER_API_REQUESTS=NONE")
    print("EXP042_REAL_CREDENTIALS=NONE")
    print("EXP042_PRODUCTION_VENV_CHANGED=NO")


def main(argv=None):
    parser = _NoEchoParser(description="EXP042 Windows VPS approved hash-locked SDK install")
    parser.add_argument("--lock", required=True)
    parser.add_argument("--wheelhouse", required=True)
    parser.add_argument("--venv", required=True)
    args = parser.parse_args(argv)
    stage_and_install(
        lock_path=Path(args.lock), wheelhouse=Path(args.wheelhouse),
        venv_path=Path(args.venv),
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SDKAcquisitionRejected:
        # Never log URL, proxy, cookies, secrets, install stdout/stderr.
        print("EXP042_ISOLATED_ACQUISITION=HOLD")
        raise SystemExit(2) from None
