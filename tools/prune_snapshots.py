#!/usr/bin/env python3
"""Delete all but the newest raw snapshot folders. Usage: prune_snapshots.py DIR KEEP"""
import shutil
import sys
from pathlib import Path


def prune(folder, keep):
    done = sorted(p.parent for p in Path(folder).glob("*/manifest.json"))
    for old in done[:-keep] if keep else done:
        shutil.rmtree(old)
    return len(done[:-keep]) if keep else len(done)


if __name__ == "__main__":
    print("removed", prune(sys.argv[1], int(sys.argv[2])), "old snapshot folders")
