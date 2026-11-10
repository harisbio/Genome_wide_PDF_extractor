"""Stage 3: validate one extraction record and save it only if it passes every check.

python scripts/record_extraction.py <workspace> <paper_id> < record.json

Checks: all fields present, each value in its allowed format, and every evidence quote found in the paper text
(ignoring spacing, case and punctuation, or a close match of at least 90%). Prints the problems to fix, or SAVED <ID>.
Exit code 0 = saved, 1 = problems, 2 = usage error.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from gfx.validate import validate  # noqa: E402


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    ws, pid = Path(sys.argv[1]), sys.argv[2]
    paper = ws / "papers" / f"{pid}.txt"
    if not paper.exists():
        print(f"no prepared text for {pid}: {paper}")
        return 2
    try:
        rec = json.loads(sys.stdin.read())
    except json.JSONDecodeError as e:
        print("PROBLEMS (fix and resend the whole JSON):\n  - invalid JSON:", e)
        return 1
    probs = validate(rec, paper.read_text(encoding="utf-8"))
    if probs:
        print("PROBLEMS (fix and resend the whole JSON):")
        for p in probs:
            print("  -", p)
        return 1
    (ws / "out").mkdir(exist_ok=True)
    (ws / "out" / f"{pid}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"SAVED {pid}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")
    sys.exit(main())
