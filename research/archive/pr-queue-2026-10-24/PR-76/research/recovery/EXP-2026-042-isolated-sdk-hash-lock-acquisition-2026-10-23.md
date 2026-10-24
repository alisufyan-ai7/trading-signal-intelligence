# EXP042 — owner-approved bounded PyPI SDK wheel acquisition (VPS only)

Date: 2026-10-23. Owner explicitly approved **official PyPI metadata reads, exact SHA-256-locked downloads, then installation after verification in a NEW disposable Windows VPS Python environment ONLY**. No AWS or Backblaze API, no real owner credentials, no production VPS venv/source or task modifications and **no PR merges**.

## Exact frozen context

- GitHub repository: `alisufyan-ai7/trading-signal-intelligence` only. Remote `main=bc00e87cfaafe03127fde3d1ddda5154801e3d92`.
- Draft PR #75 EXP042 head: `73e06ae176da45344316bf0268ebfc8ba04be379`. Previous result immutable: **131 pytest PASSED / 1 SKIPPED**, pinned SDK absent in existing isolated interpreter, standalone fake-SDK proof HOLD; frozen-dependency PASS; live VPS production tree unaffected.
- Goal: enable a *subsequent isolated* offline fake-HTTP proof without installing SDK into the existing EXP042 test interpreter or any production environment.
- Real-provider gate remains `REAL_PROVIDER_REQUESTS_ENABLED=False`; SDK acquisition does not change this flag.

## Fixed, externally cross-checked dependency lock

The seven selected files are the only allowable wheel distribution names; their SHA-256 hashes are frozen in `ops/backup/exp042-sdk-seven-wheel-hash-lock-v0.1.txt`.

| PyPI package | Version | Wheel SHA-256 |
|---|---|---|
| boto3 | 1.43.114 | `d9cac2eb921ce674970cef1c9ad750f85ee3a846aedcf188d18368fb9eb6da23` |
| botocore | 1.43.114 | `d1c441a22e93e158de5b1e026205f5d6d67a4545d10540c5090c62dccb3a9eca` |
| jmespath | 1.0.1 | `02e2e4cc71b5bcab88332eebf907519190dd9e6e82107fa7f83b1003a6252980` |
| s3transfer | 0.19.3 | `24eb7535804306355e31c952a90022bf5b2f9d760f9a11062c7493a217c08553` |
| python-dateutil | 2.9.0.post0 | `a8b2bc7bffae282281c8140a97d3aa9c14da0b136dfe83f850eea9a5f7470427` |
| urllib3 | 2.8.0 | `0cf3cae568d36aa9576b28dfb35f11328f1cb974ca7647d9475ebb86c75ac6e3` |
| six | 1.17.0 | `4721f391ed90541fddacab5acf947aa0d3dc7d27b2e1e8eda2be8970586c3274` |

Official public release records individually reviewed for wheel filenames and digests:
https://pypi.org/project/boto3/1.43.114/
https://pypi.org/project/botocore/1.43.114/
https://pypi.org/project/jmespath/1.0.1/
https://pypi.org/project/s3transfer/0.19.3/
https://pypi.org/project/python-dateutil/2.9.0.post0/
https://pypi.org/project/urllib3/2.8.0/
https://pypi.org/project/six/1.17.0/

Top-level AWS SDK wheels were uploaded without PyPI Trusted Publishing attestations; the urllib3 selected wheel has PyPI provenance. Wheel hashes prove identity relative to PyPI metadata, not that the software is free of malware or defects. Libraries carry Apache-2.0, MIT, or dateutil dual BSD/Apache licenses on their relevant PyPI pages. Lock targets **Python 3.12 Windows**, wheels only; no arbitrary sdists or optional CRT extra. A version conflict in actual downloaded METADATA is a required HOLD, not permission to choose another version.

## Fail-closed acquisition design

`scripts/exp042_isolated_hash_locked_sdk_acquisition.py` is a standalone approved-downloader/installer to be run MANUALLY on existing VPS from a disposable exact-head checkout. Its user-visible arguments are exclusively a known reviewed lockfile and two unique as-yet-NONEXISTENT temp folders. Do not run using production checkout.

1. Check Windows Python 3.12, exact seven lock entries, no symlinks, and wheelhouse/venv are NEW direct children of the current Windows `TEMP` directory, with `vowsig-exp042-` prefix.
2. Fetch each of the seven **exact release JSON documents** from `https://pypi.org/pypi/<name>/<version>/json`. Accept ONLY HTTPS host `pypi.org`, no redirects or proxy, fixed size/time bounds. Require one exact wheel filename and its PyPI JSON SHA matches pre-reviewed SHA.
3. Download only that exact wheel's official `https://files.pythonhosted.org` URL. Byte-budget 20MiB per wheel; SHA-256 of downloaded bytes MUST equal both frozen lock and live official JSON. No alternate mirror/index/fallback/version.
4. BEFORE creating/installing anything, inspect all downloaded wheel `METADATA` via zip read (does NOT execute wheels). Require matching package identity/version, Python 3.12 compatibility, and compare every `Requires-Dist` string against the official JSON metadata. Evaluate active dependency markers in the target VPS environment and require EVERY active dependency to be one of the same seven pinned packages with a satisfying version; no URL requirements, extras or unpinned dependencies. If incompatible → **HOLD, preserve lock and evidence, no install**.
5. Only after all seven pass, build a NEW `venv` with `system_site_packages=False`, from the existing isolated 3.12 interpreter. Install **solely offline** using pip `--isolated install --no-index --no-cache-dir --disable-pip-version-check --only-binary=:all: --require-hashes --no-deps --find-links <verified-temp-wheelhouse> -r <exact-lock>`. Run `pip --isolated check` and validate all installed versions. No registry, global site packages, production task, pip search or external package source is permitted.
6. Print only fixed PASS/HOLD status strings and package names. Do not echo external URL, HTTP response, credentials or pip stderr. On any failure, abort; never auto-fix or retry by relaxing constraints.

**Isolation limitation:** Script-level pathname/source checks, wheel hashes and virtualenv separation do not constitute an OS security sandbox. Downloaded wheels are external code even if hash-matched, so use only disposable context, no privileged data, no keys and no real provider calls. Existing Windows RDP/AV/egress hygiene remain owner responsibilities. HTTP traffic here is ONLY PyPI download/metadata; no AWS/B2 endpoint requests.

## Post-install SDK proof (separate from installation)

The old isolated test venv (used previously for cryptography and pytest) is not modified. For the SDK fake HTTP proof ONLY, run that existing test interpreter with transient `PYTHONPATH` pointing first at the **new venv's** SDK `Lib/site-packages`, then PR #75's disposable `src` and repo. This permits the old interpreter to retain existing pre-approved cryptography/pytest while loading the seven new isolated SDK packages first. Verify import metadata resolves to the exact pins; run `scripts/exp042_pinned_sdk_fake_http_proof.py --offline-only` under its deny-all socket guard/fake HTTP transport. **Do not use real credentials.** Preserve actual PASS/FAIL/HOLD; an SDK runtime error is a STOP/HOLD requiring a new prospective code review, not real-cloud permission.

Do not merge PR #75 or any acquisition draft by running this script. No production VPS sync, new packages in old venv, scheduled tasks, real data cloud rights, or changes to AWS/B2 settings. Real cloud pilot remains separately blocked by $0 spending requirement, separate explicit provider API approval, and effective credential/SDK security review.

**Status at authoring: REPRODUCIBLE LOCK/PREPARED; no VPS wheel downloaded or installed yet and no post-install SDK fake transport proof has run.**
