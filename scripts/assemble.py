"""Stage 4: turn the saved records into the dataset table and an evidence table.

python scripts/assemble.py <workspace> [--biblio <biblio.csv>]

Writes <workspace>/extraction.csv (one row per paper) and <workspace>/evidence.csv (one row per field with its quote).
Free-text tool lists are filed into the five tool columns with data/tool_checklist.csv.
With --biblio (from scripts/add_biblio.py), Title, Authors, Year, Journal, DOI and Keywords are filled in.
"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from gfx.schema import DATA_COLS, EXTRA_COLS  # noqa: E402
from gfx.tools import file_tools, load_checklist  # noqa: E402

DIRECT = ["Country of Origin", "Primary Organism", "Secondary Organism", "Gene Family", "Genome Source",
          "HMMER (with Pfam domains ID)", "BLAST (E-value cut-off used)", "SMART", "CDD", "MEGA", "IQ-TREE", "MEME", "MCScanX",
          "TBTools", "Experimental Validation (qPCR)", "Expression Analysis (RNA-seq)", "Number of Genes Identified",
          "Phylogenetic Structure", "Expression (microarray/EST)", "Genes per species"]


def to_row(pid, rec, checklist):
    v = rec["values"]
    row = {"Paper ID": pid, "Keywords": v.get("Keywords", "Not Available")}
    row.update({f: v.get(f, "") for f in DIRECT})
    row["Gene Duplication Events (TANDEM/SEGMENTAL)"] = v.get("Gene Duplication Events", "")
    row["Full-text eligibility"] = v.get("eligibility", "")
    row.update(file_tools(v.get("tools", []), checklist))
    return row


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("workspace", type=Path)
    ap.add_argument("--biblio", type=Path, help="CSV from scripts/add_biblio.py")
    a = ap.parse_args()
    checklist = load_checklist()
    recs = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted((a.workspace / "out").glob("*.json"))}
    if not recs:
        sys.exit(f"no saved records in {a.workspace / 'out'}")
    df = pd.DataFrame([to_row(pid, r, checklist) for pid, r in recs.items()]).set_index("Paper ID")
    if a.biblio:
        b = pd.read_csv(a.biblio, dtype=str, keep_default_na=False).set_index("Paper ID")
        for c in ["Title", "Authors", "Year", "Journal", "DOI", "Keywords"]:
            if c in b:
                filled = b[c].reindex(df.index).fillna("")
                df[c] = filled.where(filled != "", df[c] if c in df else "")
    df = df.reset_index().reindex(columns=DATA_COLS + EXTRA_COLS)
    df.to_csv(a.workspace / "extraction.csv", index=False, encoding="utf-8-sig")
    ev = [dict(paper=pid, field=f, value=r["values"].get(f, ""), evidence=q)
          for pid, r in recs.items() for f, q in r.get("evidence", {}).items()]
    pd.DataFrame(ev).to_csv(a.workspace / "evidence.csv", index=False, encoding="utf-8-sig")
    print(f"{len(df)} papers -> {a.workspace / 'extraction.csv'} and evidence.csv")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
