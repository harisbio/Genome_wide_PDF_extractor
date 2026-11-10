"""Compare two extractions of the same papers field by field (for example, a new extraction against an earlier one).

python scripts/compare.py <first.csv> <second.csv> [--out differences.csv]

Both files need a "Paper ID" column and the dataset columns. Each differing cell is written with both values and its
agreement score (0-1), and when evidence.csv sits next to the second file, the supporting quote is added so each
disagreement can be resolved against the article.
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from gfx.scoring import score  # noqa: E402

CORE = ["Country of Origin", "Primary Organism", "Secondary Organism", "Gene Family", "Genome Source",
        "HMMER (with Pfam domains ID)", "BLAST (E-value cut-off used)", "SMART", "CDD", "MEGA", "IQ-TREE", "MEME", "MCScanX",
        "TBTools", "Experimental Validation (qPCR)", "Expression Analysis (RNA-seq)", "Number of Genes Identified",
        "Phylogenetic Structure", "Gene Duplication Events (TANDEM/SEGMENTAL)"]
FREE = ["Other (Tools for Domain Analysis)", "Others (Tools for Motif Analysis)", "Other (Tools for Synteny)",
        "Other (Tools for Visualization)", "Other Tools Used In Methodology"]
EV_NAME = {"Gene Duplication Events (TANDEM/SEGMENTAL)": "Gene Duplication Events"}


def read(p):
    return pd.read_csv(p, dtype=str, keep_default_na=False, encoding="utf-8-sig").set_index("Paper ID")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("first", type=Path)
    ap.add_argument("second", type=Path)
    ap.add_argument("--out", type=Path, default=Path("differences.csv"))
    a = ap.parse_args()
    x, y = read(a.first), read(a.second)
    evf = a.second.parent / "evidence.csv"
    ev = {}
    if evf.exists():
        e = pd.read_csv(evf, dtype=str, keep_default_na=False, encoding="utf-8-sig")
        ev = {(r.paper, r.field): r.evidence for r in e.itertuples()}
    ids = [i for i in x.index if i in y.index]
    fields = [f for f in CORE + FREE if f in x.columns and f in y.columns]
    rows = []
    for pid in ids:
        for f in fields:
            va, vb = x.at[pid, f], y.at[pid, f]
            s = score(f, va, vb) if f in CORE else float(va.strip().lower() == vb.strip().lower())
            if s < 1:
                rows.append(dict(pid=pid, field=f, first=va, second=vb, score=round(float(s), 2),
                                 evidence=ev.get((pid, EV_NAME.get(f, f)), "")))
    d = pd.DataFrame(rows, columns=["pid", "field", "first", "second", "score", "evidence"])
    d.to_csv(a.out, index=False, encoding="utf-8-sig")
    total = len(ids) * len(fields)
    print(f"papers compared {len(ids)} | cells {total} | differing {len(d)} ({len(d) / max(total, 1):.1%}) -> {a.out}")
    if len(d):
        print(d.groupby("field", sort=False).size().to_string())


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
