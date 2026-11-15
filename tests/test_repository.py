"""Repository-structure invariants and end-to-end smoke tests."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from skillkit.engine import ADAPTERS  # noqa: E402

SLUGS = ["document-intake-ledger", "message-to-workbook-sync",
         "scheduled-digest-publisher", "verified-batch-calculation"]


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


class StructureTests(unittest.TestCase):
    def test_only_one_engine_exists(self):
        self.assertTrue((ROOT / "skillkit" / "engine.py").is_file())
        for slug in SLUGS:
            self.assertFalse((ROOT / "skills" / slug / "engine.py").exists(),
                             f"{slug} still carries a duplicated engine")

    def test_all_shims_are_identical(self):
        contents = [(ROOT / "skills" / s / "run.py").read_bytes() for s in SLUGS]
        self.assertTrue(all(c == contents[0] for c in contents))

    def test_profiles_are_valid_and_named_correctly(self):
        for slug in SLUGS:
            data = json.loads((ROOT / "skills" / slug / "profile.json").read_text())
            self.assertEqual(data["slug"], slug)
            self.assertIn("defaults", data)
            self.assertIn("invariants", data)

    def test_config_structures_are_identical(self):
        wizards, engines = [], []
        for slug in SLUGS:
            cfg = json.loads((ROOT / "skills" / slug / "config.example.json").read_text())
            wizards.append(paths(cfg["wizard"]))
            engines.append(paths(cfg["engine"]))
            adapter = cfg["engine"]["output"]["adapter"]
            self.assertIn(adapter, ADAPTERS["output"])
        self.assertTrue(all(x == wizards[0] for x in wizards))
        self.assertTrue(all(x == engines[0] for x in engines))

    def test_version_file_matches_package(self):
        from skillkit import __version__
        self.assertEqual((ROOT / "VERSION").read_text().strip(), __version__)


class EndToEndTests(unittest.TestCase):
    def test_demo_works_in_every_skill(self):
        for slug in SLUGS:
            with self.subTest(slug=slug):
                proc = subprocess.run([sys.executable, "run.py", "demo"],
                                      cwd=ROOT / "skills" / slug,
                                      capture_output=True, text=True, timeout=180)
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                self.assertIn("Run summary", proc.stdout)

    def test_setup_and_doctor_work_from_a_clean_copy(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            cwd = tmp / "skills" / SLUGS[0]
            shutil.copytree(ROOT / "skills" / SLUGS[0], cwd,
                            ignore=shutil.ignore_patterns("__pycache__", "demo-out", "out", "state", "inbox"))
            shutil.copytree(ROOT / "skillkit", tmp / "skillkit",
                            ignore=shutil.ignore_patterns("__pycache__"))
            env = dict(os.environ)
            setup = subprocess.run([sys.executable, "run.py", "setup", "--yes"],
                                   cwd=cwd, capture_output=True, text=True, timeout=120, env=env)
            self.assertEqual(setup.returncode, 0, setup.stdout + setup.stderr)
            self.assertTrue((cwd / "config.json").exists())
            doctor = subprocess.run([sys.executable, "run.py", "doctor"],
                                    cwd=cwd, capture_output=True, text=True, timeout=120, env=env)
            self.assertEqual(doctor.returncode, 0, doctor.stdout + doctor.stderr)
            self.assertIn("result             : OK", doctor.stdout)

    def test_build_produces_standalone_packages(self):
        build = subprocess.run([sys.executable, "build.py"], cwd=ROOT,
                               capture_output=True, text=True, timeout=180)
        self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
        for slug in SLUGS:
            d = ROOT / "dist" / slug
            self.assertTrue((d / "engine.py").is_file())
            self.assertTrue((d / "run.py").is_file())
            info = json.loads((d / "BUILD_INFO.json").read_text())
            self.assertTrue(info["standalone"])
        check = subprocess.run([sys.executable, "build.py", "--check"], cwd=ROOT,
                               capture_output=True, text=True, timeout=300)
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)


if __name__ == "__main__":
    unittest.main()
