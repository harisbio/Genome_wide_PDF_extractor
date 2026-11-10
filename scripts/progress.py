"""Show which prepared papers still have no saved record, optionally split into batches for extraction.

python scripts/progress.py <workspace> [--batch-size 10]
"""
import argparse
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("workspace", type=Path)
    ap.add_argument("--batch-size", type=int, default=0, help="print the remaining IDs in batches of this size")
    a = ap.parse_args()
    prepared = sorted(p.stem for p in (a.workspace / "papers").glob("*.txt"))
    saved = {p.stem for p in (a.workspace / "out").glob("*.json")}
    left = [p for p in prepared if p not in saved]
    print(f"prepared {len(prepared)} | saved {len(saved & set(prepared))} | remaining {len(left)}")
    if a.batch_size and left:
        for i in range(0, len(left), a.batch_size):
            print(f"batch {i // a.batch_size + 1}: " + " ".join(left[i:i + a.batch_size]))
    elif left:
        print(" ".join(left))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
