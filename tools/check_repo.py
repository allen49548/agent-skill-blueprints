#!/usr/bin/env python3
"""Repository hygiene gate. Run from the repo root: python3 tools/check_repo.py

Checks: ASCII-only docs/code, no leaked identifiers or machine paths, valid JSON,
identical config structures, a single runtime source, and no generated artifacts
tracked by git. Exits non-zero on the first failing group.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", "dist", "demo-out", "out", "state", "inbox", "__pycache__"}
# These files contain the patterns only as documentation / regex literals.
PRIVACY_EXEMPT = {"PUBLISHING.md", "check_repo.py"}

FORBIDDEN = re.compile(
    r"(oc_[a-f0-9]{16,}|ou_[a-f0-9]{16,}|ghp_[A-Za-z0-9]{20,}|"
    r"/Users/|/home/|\u98de\u4e66|\u4f01\u4e1a\u5fae\u4fe1|"
    r"\u7269\u6d41\u90e8|\u53f8\u673a|\u62a5\u9500|\u7f8e\u7532)")


def tracked_files() -> list[Path]:
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True,
                         text=True, check=True).stdout.splitlines()
    return [ROOT / line for line in out]


def source_files() -> list[Path]:
    return [p for p in ROOT.rglob("*")
            if p.is_file() and not (set(p.relative_to(ROOT).parts) & SKIP_DIRS)]


def check(condition: bool, label: str, detail: str = "") -> bool:
    print(f"  [{'OK' if condition else 'FAIL'}] {label}" + (f"  {detail}" if detail else ""))
    return condition


def paths(obj, prefix=""):
    out = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            q = f"{prefix}.{key}" if prefix else key
            out.add(q)
            out |= paths(value, q)
    elif isinstance(obj, list):
        for item in obj:
            out |= paths(item, prefix + "[]")
    return out


def main() -> int:
    ok = True
    files = source_files()
    tracked = tracked_files()

    print("Encoding and privacy")
    bad_ascii = [(str(p.relative_to(ROOT)), i)
                 for p in files
                 for i, line in enumerate(p.read_text(errors="replace").splitlines(), 1)
                 if any(ord(c) > 127 for c in line)]
    ok &= check(not bad_ascii, "ASCII-only sources", str(bad_ascii[:5]) if bad_ascii else "")
    leaks = [(str(p.relative_to(ROOT)), i)
             for p in files if p.name not in PRIVACY_EXEMPT
             for i, line in enumerate(p.read_text(errors="replace").splitlines(), 1)
             if FORBIDDEN.search(line)]
    ok &= check(not leaks, "no identifiers, machine paths or business terms", str(leaks[:5]) if leaks else "")

    print("JSON and structure")
    bad_json = []
    for p in files:
        if p.suffix == ".json":
            try:
                json.loads(p.read_text())
            except json.JSONDecodeError as exc:
                bad_json.append((p.name, str(exc)))
    ok &= check(not bad_json, "all JSON parses", str(bad_json[:3]) if bad_json else "")

    skills = sorted((ROOT / "skills").iterdir())
    engines = [(ROOT / "skillkit" / "engine.py").read_bytes()]
    duplicated = [d.name for d in skills if (d / "engine.py").exists()]
    ok &= check(not duplicated, "single runtime source", str(duplicated))
    shims = [(d / "run.py").read_bytes() for d in skills]
    ok &= check(len(set(shims)) == 1, "all entry points identical")
    ok &= check(len(engines) == 1 and (ROOT / "skillkit" / "engine.py").is_file(),
                "skillkit/engine.py present")

    wizards, eng_sections = [], []
    for d in skills:
        cfg = json.loads((d / "config.example.json").read_text())
        wizards.append(paths(cfg["wizard"]))
        eng_sections.append(paths(cfg["engine"]))
    ok &= check(all(x == wizards[0] for x in wizards), "wizard structures identical")
    ok &= check(all(x == eng_sections[0] for x in eng_sections), "engine config structures identical")

    from sys import path as sys_path
    sys_path.insert(0, str(ROOT))
    from skillkit import __version__
    ok &= check((ROOT / "VERSION").read_text().strip() == __version__,
                "VERSION matches skillkit.__version__", __version__)

    print("Tracked artifacts")
    generated = [str(p.relative_to(ROOT)) for p in tracked
                 if set(p.relative_to(ROOT).parts) & {"dist", "demo-out", "out", "state", "inbox", "__pycache__"}]
    ok &= check(not generated, "no generated output committed", str(generated[:5]) if generated else "")
    pyc = [str(p.relative_to(ROOT)) for p in tracked if p.suffix in (".pyc", ".xlsx", ".log")]
    ok &= check(not pyc, "no binaries or logs committed", str(pyc[:5]) if pyc else "")

    print(f"\nRESULT: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
