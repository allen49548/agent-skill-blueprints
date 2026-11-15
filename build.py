#!/usr/bin/env python3
"""Build self-contained, individually distributable skill packages into dist/.

The repository keeps exactly one copy of the runtime (skillkit/engine.py).
The four skills in skills/ are thin shims that import it. This script produces
standalone copies for people who want to install a single skill elsewhere.

    python3 build.py            # writes dist/<slug>/ for all four skills
    python3 build.py --check    # verify the built packages are runnable

dist/ is generated output and is not committed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
sys.path.insert(0, str(ROOT))
from skillkit import __version__  # noqa: E402
from skillkit.engine import THIN_RUNPY  # noqa: E402

FILES = ["SKILL.md", "README.md", "DESIGN.md", "config.example.json",
         "config.schema.md", "profile.json"]


def build_one(skill_dir: Path) -> Path:
    slug = skill_dir.name
    target = DIST / slug
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    for name in FILES:
        src = skill_dir / name
        if src.exists():
            shutil.copy2(src, target / name)
    examples = skill_dir / "examples"
    if examples.exists():
        shutil.copytree(examples, target / "examples")
    engine = ROOT / "skillkit" / "engine.py"
    shutil.copy2(engine, target / "engine.py")
    (target / "run.py").write_text(THIN_RUNPY, encoding="utf-8")
    digest = hashlib.sha256(engine.read_bytes()).hexdigest()
    (target / "BUILD_INFO.json").write_text(json.dumps({
        "slug": slug,
        "version": __version__,
        "engine_sha256": digest,
        "standalone": True,
    }, indent=2) + "\n", encoding="utf-8")
    return target


def check_one(target: Path) -> bool:
    proc = subprocess.run([sys.executable, "run.py", "demo"],
                          cwd=target, capture_output=True, text=True, timeout=120)
    ok = proc.returncode == 0 and "Run summary" in proc.stdout
    print(f"  {target.name:32} {'OK' if ok else 'FAILED'}")
    if not ok:
        print((proc.stdout + proc.stderr)[-1200:])
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="run demo in every built package")
    args = ap.parse_args()
    if args.check and not DIST.exists():
        print("ERROR: run python3 build.py first", file=sys.stderr)
        return 2
    if not args.check:
        print(f"Building standalone packages, version {__version__}")
        for d in sorted((ROOT / "skills").iterdir()):
            if d.is_dir():
                t = build_one(d)
                print(f"  {t.relative_to(ROOT)}")
        print(f"\nDone. {len(list(DIST.iterdir()))} packages in dist/ (gitignored).")
    if args.check:
        print("Verifying built packages:")
        results = [check_one(d) for d in sorted(DIST.iterdir()) if d.is_dir()]
        print("all packages runnable:", all(results))
        return 0 if all(results) else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
