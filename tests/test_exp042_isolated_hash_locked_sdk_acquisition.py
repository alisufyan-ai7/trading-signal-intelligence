"""EXP042 SDK wheel acquisition negative tests; never download, install or call cloud."""
from __future__ import annotations

import io
from pathlib import Path
import tempfile
import zipfile

import pytest

from scripts import exp042_isolated_hash_locked_sdk_acquisition as acq


def _lock_text():
    items = []
    for name, (version, _) in acq.EXPECTED.items():
        items.append(f"{name}=={version} --hash=sha256:" + ("a" * 64))
    return "\n".join(items) + "\n"


def _fake_wheel(path: Path, name: str, version: str, requires=()):
    wheel_name = acq.EXPECTED[name][1]
    metadata = "\n".join([
        "Metadata-Version: 2.1",
        f"Name: {name}",
        f"Version: {version}",
        "Requires-Python: >=3.10",
        *(f"Requires-Dist: {r}" for r in requires),
        "", "",
    ])
    with zipfile.ZipFile(path / wheel_name, "w") as z:
        z.writestr(f"{name.replace('-', '_')}-{version}.dist-info/METADATA", metadata)


def test_exact_seven_lock_parses(tmp_path):
    f = tmp_path / "sdk-lock.txt"
    f.write_text(_lock_text(), encoding="utf-8")
    result = acq._read_lock(f)
    assert len(result) == 7
    assert result["boto3"][0] == "1.43.114"
    assert result["botocore"][0] == "1.43.114"


@pytest.mark.parametrize("bad", [
    "unknown-sdk==1.0 --hash=sha256:" + "a"*64,
    "boto3==1.43.115 --hash=sha256:" + "a"*64,
    "boto3==1.43.114 --hash=sha256:" + "b"*64,
    "--extra-index-url https://unknown.example",
])
def test_extra_or_unapproved_lock_line_denied(tmp_path, bad):
    f = tmp_path / "sdk-lock.txt"
    f.write_text(_lock_text() + bad + "\n", encoding="utf-8")
    with pytest.raises(acq.SDKAcquisitionRejected):
        acq._read_lock(f)


def test_missing_wheel_lock_rejected(tmp_path):
    f = tmp_path / "sdk-lock.txt"
    f.write_text(_lock_text().splitlines()[0] + "\n", encoding="utf-8")
    with pytest.raises(acq.SDKAcquisitionRejected):
        acq._read_lock(f)


@pytest.mark.parametrize("url,host", [
    ("http://pypi.org/pypi/boto3/json", "pypi.org"),
    ("https://evil.example/pypi/boto3/json", "pypi.org"),
    ("https://pypi.org:444/pypi/boto3/json", "pypi.org"),
    ("https://pypi.org/pypi/boto3/json?extra=1", "pypi.org"),
    ("https://someone@pypi.org/pypi/boto3/json", "pypi.org"),
])
def test_url_approval_is_strict_and_never_fetches(url, host):
    with pytest.raises(acq.SDKAcquisitionRejected):
        acq._request_exact_https(url, host, 100)


def test_pub_metadata_version_or_hash_mismatch_blocks_download(monkeypatch):
    def fake_get(url, host, cap):
        return (
            '{"info":{"name":"boto3","version":"1.43.114"},'
            '"urls":[{"packagetype":"bdist_wheel",'
            '"filename":"boto3-1.43.114-py3-none-any.whl",'
            '"digests":{"sha256":"' + "b"*64 + '"},"url":'
            '"https://files.pythonhosted.org/fake.whl"}]}'
        ).encode()
    monkeypatch.setattr(acq, "_request_exact_https", fake_get)
    with pytest.raises(acq.SDKAcquisitionRejected, match="published PyPI wheel"):
        acq._verify_metadata_and_get_wheel_url(
            "boto3", "1.43.114", "boto3-1.43.114-py3-none-any.whl", "a"*64)


def test_dependency_metadata_exact_closure_accepts(tmp_path):
    records = {
        name: (v, "a"*64, wheel) for name, (v, wheel) in acq.EXPECTED.items()
    }
    requirements = {
        "boto3": ["botocore>=1.43.114,<1.44.0",
                  "s3transfer>=0.19.0,<0.20.0",
                  "jmespath>=0.7.1,<2.0.0"],
        "botocore": ["jmespath>=0.7.1,<2.0.0",
                    "python-dateutil>=2.1,<3.0.0", "urllib3>=1.25.4,<3"],
        "s3transfer": ["botocore>=1.41.0,<2.0a.0"],
        "python-dateutil": ["six>=1.5"],
        "jmespath": [], "urllib3": [], "six": [],
    }
    for name, (v, _) in acq.EXPECTED.items():
        _fake_wheel(tmp_path, name, v, requirements[name])
    acq._inspect_all_wheel_metadata(tmp_path, records, requirements)


def test_malformed_unlocked_dependency_denied(tmp_path):
    records = {
        name: (v, "a"*64, wheel) for name, (v, wheel) in acq.EXPECTED.items()
    }
    pub = {name: [] for name in records}
    for name, (v, _) in acq.EXPECTED.items():
        reqs = ["malicious-unlisted-package>=1"] if name == "boto3" else []
        pub[name] = reqs
        _fake_wheel(tmp_path, name, v, reqs)
    with pytest.raises(acq.SDKAcquisitionRejected, match="unlocked"):
        acq._inspect_all_wheel_metadata(tmp_path, records, pub)


def test_metadata_source_does_not_match_wheel_denied(tmp_path):
    records = {name: (v, "a"*64, wheel)
               for name, (v, wheel) in acq.EXPECTED.items()}
    for name, (v, _) in acq.EXPECTED.items():
        _fake_wheel(tmp_path, name, v)
    pub = {name: [] for name in records}
    pub["boto3"] = ["botocore>=1"]
    with pytest.raises(acq.SDKAcquisitionRejected, match="dependencies differ"):
        acq._inspect_all_wheel_metadata(tmp_path, records, pub)


def test_new_disposable_folder_required_not_existing_or_outside_temp(tmp_path):
    with pytest.raises(acq.SDKAcquisitionRejected):
        acq._inside_temp_new_folder(tmp_path)
    with pytest.raises(acq.SDKAcquisitionRejected):
        acq._inside_temp_new_folder(Path("C:/Windows/System32"))


def test_source_does_not_enable_sdk_cloud_or_unhashed_pip():
    import inspect
    text = inspect.getsource(acq)
    assert "pypi.org/pypi/" in text
    assert '"files.pythonhosted.org"' in text
    assert '"--no-index"' in text
    assert '"--require-hashes"' in text
    assert '"--no-deps"' in text
    assert "getpass" not in text
    assert "import boto3" not in text
    assert "aws_access_key_id" not in text
    assert "subprocess.run(command" in text
    assert "with_pip=True, system_site_packages=False" in text
