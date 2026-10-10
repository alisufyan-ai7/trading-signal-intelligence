#!/usr/bin/env python3
"""Fail-closed pre-merge impact detector for active, hash-pinned AI lineages.

Static AST parsing only; never import or execute runtime/activation modules.
All protected paths derive from the trusted base commit, not the PR head.
Never reinterpret activation-era hash mismatches as historically valid.
"""
from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

# Registrations are governed infrastructure. Changes require a distinct
# release/exception protocol, never a free-form in-PR bypass flag.
LINEAGES = (
    ("AI-v1.1", "research/forward/AI-v1.1-activation-2026-09-30T114412Z.json",
     "src/trading_signal_intelligence/ai_v1/activation_v1_1.py",
     (("V11_ARTIFACT_PATHS", "artifact_hashes"),
      ("FROZEN_DECISION_ARTIFACT_PATHS", "frozen_decision_artifact_hashes")),
     None),
    ("AI-v1.2.1", "research/forward/AI-v1.2.1-expansion-activation-2026-10-07T093543Z.json",
     "src/trading_signal_intelligence/ai_v1/activation_v1_2_1.py",
     (("EXPANSION_ARTIFACT_PATHS", "artifact_hashes"),),
     "src/trading_signal_intelligence/ai_v1/expansion_v1_2_1.py"),
    ("AI-v1.3", "research/forward/AI-v1.3-crypto-expansion-activation-2026-10-09T195556Z.json",
     "src/trading_signal_intelligence/ai_v1/crypto_activation_v1_3.py",
     (("ARTIFACT_PATHS", "artifact_hashes"),),
     None),
)
GOVERNANCE_FILES = frozenset((
    "scripts/check_frozen_dependency_impact.py",
    ".github/workflows/frozen-dependency-change-impact.yml",
    ".github/CODEOWNERS",
))
GOVERNANCE_PATTERN = re.compile(
    r"^research/forward/AI-v[^/]*-(?:activation|public-surface-correction)[^/]*\.json$"
)
HEX_SHA = re.compile(r"^[0-9a-f]{64}$")


class GateViolation(RuntimeError):
    pass


def git(root: Path, *args: str) -> bytes:
    try:
        out = subprocess.run(
            ["git", *args], cwd=root, check=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise GateViolation(f"Git operation rejected: {args[0]}") from exc
    return out.stdout


def canonical_path(value: object) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise GateViolation("frozen path must be a nonempty POSIX repository path")
    p = PurePosixPath(value)
    if p.is_absolute() or ".." in p.parts or str(p) != value or value.startswith("."):
        raise GateViolation(f"unsafe frozen path: {value}")
    return value


def _static(node: ast.AST, symbols: dict[str, object]) -> object:
    if isinstance(node, ast.Constant) and isinstance(node.value, (str, int, bool)):
        return node.value
    if isinstance(node, ast.Name) and node.id in symbols:
        return symbols[node.id]
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        a, b = _static(node.left, symbols), _static(node.right, symbols)
        if isinstance(a, str) and isinstance(b, str):
            return a + b
    if isinstance(node, (ast.Tuple, ast.List)):
        return [_static(x, symbols) for x in node.elts]
    if isinstance(node, ast.Dict):
        if any(k is None for k in node.keys):
            raise GateViolation("dict expansion is not admissible in frozen manifests")
        return {_static(k, symbols): _static(v, symbols)
                for k, v in zip(node.keys, node.values)}
    raise GateViolation("unsupported static frozen manifest expression")


def static_symbols(source: bytes, inherited: dict[str, object] | None = None) -> dict[str, object]:
    try:
        tree = ast.parse(source.decode("utf-8"))
    except (UnicodeError, SyntaxError) as exc:
        raise GateViolation("base manifest Python source is invalid") from exc
    symbols = dict(inherited or {})
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if len(targets) != 1 or not isinstance(targets[0], ast.Name):
            continue
        name = targets[0].id
        if name in symbols and name in ("ARTIFACT_PATHS", "V11_ARTIFACT_PATHS",
                                        "FROZEN_DECISION_ARTIFACT_PATHS",
                                        "EXPANSION_ARTIFACT_PATHS"):
            raise GateViolation("frozen manifest map reassigned")
        try:
            symbols[name] = _static(node.value, symbols)
        except GateViolation:
            # Unrelated module constants may be computed dynamically; frozen
            # map objects MUST resolve or the later strict lookup fails.
            symbols.pop(name, None)
    return symbols


def baseline_protected(root: Path, base: str) -> tuple[set[str], dict[str, int]]:
    protected = set(GOVERNANCE_FILES)
    coverage: dict[str, int] = {}
    for lineage, anchor_path, source_path, maps, imported in LINEAGES:
        protected.update((anchor_path, source_path))
        try:
            anchor = json_load(git(root, "show", f"{base}:{anchor_path}"))
        except (ValueError, TypeError) as exc:
            raise GateViolation(f"{lineage}: activation anchor JSON invalid") from exc
        if anchor.get("runtime_version") != lineage:
            raise GateViolation(f"{lineage}: runtime identity mismatch")
        if anchor.get("status") not in ("ACTIVE", "ACTIVE_PARALLEL_SHADOW"):
            raise GateViolation(f"{lineage}: registered anchor no longer active; governance update required")
        symbols: dict[str, object] = {}
        if imported:
            protected.add(imported)
            symbols = static_symbols(git(root, "show", f"{base}:{imported}"))
        symbols = static_symbols(git(root, "show", f"{base}:{source_path}"), symbols)
        total = 0
        for const_name, digest_field in maps:
            paths = symbols.get(const_name)
            expected = anchor.get(digest_field)
            if not isinstance(paths, dict) or not isinstance(expected, dict):
                raise GateViolation(f"{lineage}: unresolved frozen map or anchor hashes: {const_name}")
            if set(paths) != set(expected) or not paths:
                raise GateViolation(f"{lineage}: frozen artifact registry keys do not match anchor")
            for key, filename in paths.items():
                canonical_path(filename)
                if not HEX_SHA.fullmatch(expected[key]):
                    raise GateViolation(f"{lineage}: invalid historical artifact digest: {key}")
                protected.add(filename)
                total += 1
        coverage[lineage] = total
    return protected, coverage


def json_load(data: bytes) -> dict:
    import json
    value = json.loads(data)
    if not isinstance(value, dict):
        raise GateViolation("activation anchor must be a JSON object")
    return value


def changed_paths(root: Path, base: str, head: str) -> set[str]:
    # Three-dot PR semantics, plus every deletion and rename as a changed path.
    fork = git(root, "merge-base", base, head).decode("ascii").strip()
    if not re.fullmatch(r"[0-9a-f]{40}", fork):
        raise GateViolation("unverifiable merge-base")
    out = git(root, "diff", "--no-ext-diff", "--no-renames",
              "--name-only", "-z", fork, head)
    try:
        return {canonical_path(x.decode("utf-8"))
                for x in out.split(b"\x00") if x}
    except UnicodeError as exc:
        raise GateViolation("changed filenames must be UTF-8") from exc


def check(root: Path, base: str, head: str) -> dict:
    for label, ref in (("base", base), ("head", head)):
        if not re.fullmatch(r"[0-9a-f]{40}", ref):
            raise GateViolation(f"{label} must be a full immutable commit SHA")
        git(root, "cat-file", "-e", f"{ref}^{{commit}}")
    protected, coverage = baseline_protected(root, base)
    changed = changed_paths(root, base, head)
    blocked = sorted(p for p in changed
                     if p in protected or GOVERNANCE_PATTERN.fullmatch(p))
    return {"changed": len(changed), "protected": len(protected),
            "coverage": coverage, "blocked": blocked}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", default=".")
    ap.add_argument("--base", required=True)
    ap.add_argument("--head", required=True)
    args = ap.parse_args()
    try:
        result = check(Path(args.repo).resolve(), args.base, args.head)
        print("FROZEN_DEPENDENCY_COVERAGE=" +
              ",".join(f"{name}:{total}" for name, total in result["coverage"].items()))
        print(f"PROTECTED_PATHS={result['protected']}")
        print(f"CHANGED_PATHS={result['changed']}")
        if result["blocked"]:
            print("FROZEN_DEPENDENCY_CHANGE_IMPACT=BLOCKED")
            for path in result["blocked"]:
                print("BLOCKED_PATH=" + path)
            print("REASON=Historical active-lineage frozen dependency or guard policy touched")
            print("RESOLUTION=Separate approved prospective compatibility and controlled release")
            return 1
        print("FROZEN_DEPENDENCY_CHANGE_IMPACT=PASS")
        return 0
    except GateViolation as exc:
        print("FROZEN_DEPENDENCY_CHANGE_IMPACT=ERROR_FAIL_CLOSED")
        print("REASON=" + str(exc))
        return 2


if __name__ == "__main__":
    sys.exit(main())
