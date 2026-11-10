"""Stage 1: convert full texts (PDF or PubMed Central JATS XML) into labelled text files for extraction.

python scripts/prepare_papers.py --input <folder of PDF/XML files> --workspace <workspace> [--ids ID ...]

Each file <ID>.pdf or <ID>.xml in --input becomes <workspace>/papers/<ID>.txt. When both exist, the XML is used.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from gfx import textprep  # noqa: E402
from gfx.render import render  # noqa: E402


def sources(folder: Path, ids=None) -> dict:
    found = {}
    for p in sorted(folder.iterdir()):
        if p.suffix.lower() in (".pdf", ".xml") and (ids is None or p.stem in ids):
            if p.stem not in found or p.suffix.lower() == ".xml":
                found[p.stem] = p
    return found


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True, type=Path, help="folder with <ID>.pdf / <ID>.xml files")
    ap.add_argument("--workspace", required=True, type=Path)
    ap.add_argument("--ids", nargs="*", help="only these paper IDs (default: all files in --input)")
    a = ap.parse_args()
    out = a.workspace / "papers"
    out.mkdir(parents=True, exist_ok=True)
    (a.workspace / "out").mkdir(exist_ok=True)
    src = sources(a.input, set(a.ids) if a.ids else None)
    if not src:
        sys.exit(f"no PDF or XML files found in {a.input}")
    for pid, path in src.items():
        try:
            (out / f"{pid}.txt").write_text(render(textprep.load(path)), encoding="utf-8")
            print("prepared", pid)
        except Exception as e:  # a damaged file must not stop the batch
            print(f"FAILED {pid}: {e}", file=sys.stderr)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
