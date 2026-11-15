#!/usr/bin/env python3
"""Entry point for this skill. Start with: python3 run.py demo"""
import sys

from engine import main

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
