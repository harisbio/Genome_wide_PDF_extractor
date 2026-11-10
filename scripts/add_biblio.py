"""Bibliographic details for each paper: title, year, DOI and keywords from the full text, completed from Crossref.

python scripts/add_biblio.py --input <folder of PDF/XML files> --workspace <workspace> [--crossref]

Writes <workspace>/biblio.csv, which scripts/assemble.py --biblio merges into the dataset.
With --crossref, the DOI found on the first page is looked up in the Crossref REST API, and Crossref's title, authors,
year and journal replace the values read from the PDF. Set the environment variable CROSSREF_MAILTO to your contact
address to identify your requests to Crossref (recommended by Crossref; never stored in the output).
"""
import argparse
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from gfx import biblio, textprep  # noqa: E402
from scripts.prepare_papers import sources  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--workspace", required=True, type=Path)
    ap.add_argument("--crossref", action="store_true", help="complete the details from Crossref by DOI")
    a = ap.parse_args()
    rows = []
    for pid, path in sources(a.input).items():
        try:
            doc = textprep.load(path)
        except Exception as e:
            print(f"FAILED {pid}: {e}", file=sys.stderr)
            continue
        b = biblio.extract_biblio(doc, online=a.crossref)
        rows.append({"Paper ID": pid, **b})
        print(pid, b.get("DOI", ""), "|", (b.get("Title") or "")[:70])
        if a.crossref:
            time.sleep(0.2)                       # stay well inside Crossref's public rate limit
    a.workspace.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(a.workspace / "biblio.csv", index=False, encoding="utf-8-sig")
    print(f"{len(rows)} papers -> {a.workspace / 'biblio.csv'}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
