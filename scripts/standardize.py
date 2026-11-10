"""Stage 5: apply the controlled vocabularies to an assembled dataset.

python scripts/standardize.py <extraction.csv> <standardized.csv>

Organism columns become accepted binomials, duplication values a fixed set of categories in a fixed order, and gene
family names one standard spelling. Every change is listed in <standardized>_changes.csv for review.
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from gfx.standardize import duplication_cell, species_cell, std  # noqa: E402

RULES = {"Primary Organism": species_cell, "Secondary Organism": species_cell,
         "Gene Duplication Events (TANDEM/SEGMENTAL)": duplication_cell, "Gene Family": std}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", type=Path)
    ap.add_argument("dst", type=Path)
    a = ap.parse_args()
    d = pd.read_csv(a.src, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    log = []
    for col, fn in RULES.items():
        if col not in d:
            continue
        new = d[col].map(fn)
        for pid, before, after in zip(d["Paper ID"], d[col], new):
            if before != after:
                log.append(dict(pid=pid, field=col, before=before, after=after))
        d[col] = new
    d.to_csv(a.dst, index=False, encoding="utf-8-sig")
    pd.DataFrame(log, columns=["pid", "field", "before", "after"]).to_csv(
        a.dst.with_name(a.dst.stem + "_changes.csv"), index=False, encoding="utf-8-sig")
    print(f"{len(d)} rows -> {a.dst} | {len(log)} values changed")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
