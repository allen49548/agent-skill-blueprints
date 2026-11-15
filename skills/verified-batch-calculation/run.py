#!/usr/bin/env python3
"""Entry point. Start with: python3 run.py demo"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
os.environ["SKILLKIT_HOME"] = str(HERE)
sys.path.insert(0, str(REPO_ROOT))

from skillkit.engine import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
