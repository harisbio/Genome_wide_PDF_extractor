"""Field-by-field agreement scores between two extractions of the same paper (used by scripts/compare.py).

score(field, a, b) returns a value in [0, 1]: exact match for Yes/No fields, set overlap (Dice) for lists,
and field-specific keys for organisms, gene families, gene counts, BLAST cut-offs, Pfam IDs and duplication types.
"""
import re

NUMWORDS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen "
                                        "fourteen fifteen sixteen seventeen eighteen nineteen twenty".split())}
NUMWORD_RX = "|".join(sorted(NUMWORDS, key=len, reverse=True))


def to_int(s):
    s = str(s).lower()
    return NUMWORDS[s] if s in NUMWORDS else int(s)


YESNO = ["SMART", "CDD", "MEGA", "IQ-TREE", "MEME", "MCScanX", "TBTools", "Experimental Validation (qPCR)", "Expression Analysis (RNA-seq)"]
SETS = ["Secondary Organism", "Genome Source", "Other (Tools for Domain Analysis)", "Others (Tools for Motif Analysis)",
        "Other (Tools for Synteny)", "Other (Tools for Visualization)", "Other Tools Used In Methodology"]


# ------------------------------------------------------------------ normalisers
def n(s): return re.sub(r"[^a-z0-9]", "", str(s).lower())
def empty(s): return str(s).strip().lower() in {"", "nan", "no", "not available", "not specified", "none", "n/a", "not used"}


def species_key(s):
    s = re.sub(r"\([^)]*\)", "", str(s))
    m = re.match(r"\s*([A-Z][a-z]+)\s+([a-z\-]+)", s.strip())
    return f"{m.group(1)} {m.group(2)}".lower() if m else n(s)


def species_set(s):
    if empty(s): return set()
    return {species_key(x) for x in re.split(r"[,;]| and ", str(s)) if x.strip()}


CANON = {  # tool/database synonyms shared by gold and prediction
    "ensemblplant": "ensemblplants", "ensembl": "ensemblplants", "ensemblplants": "ensemblplants", "phytozomev13": "phytozome",
    "phytozomev12": "phytozome", "phytozomev121": "phytozome", "solgenomicsnetwork": "sgn", "solgenomicsnetworksgn": "sgn", "sgn": "sgn",
    "genestructuredisplayserver": "gsds", "gsdsgenestructuredisplayserver": "gsds", "gsds20": "gsds", "tbtools": "tbtools",
    "plantgenomeduplicationdatabase": "pgdd", "plantgenomicduplicationdatabase": "pgdd", "pgdd": "pgdd", "interproscan": "interproscan",
    "interpro": "interpro", "mapchartsoftware": "mapchart", "mapchart": "mapchart", "graphpadprism": "graphpadprism", "graphpad": "graphpadprism",
    "clustalomega": "clustalomega", "clustalw": "clustalw", "clustalx": "clustalx", "expasy": "expasy", "protparam": "protparam",
    "expasyprotparam": "protparam", "wolfpsort": "wolfpsort", "plantcare": "plantcare", "rgap": "rgap", "msu": "rgap", "rapdb": "rgap",
}


def tok_set(s):
    if empty(s): return set()
    out = set()
    s = re.sub(r"\([^)]*\)", "", str(s))                      # drop parentheticals before splitting
    for x in re.split(r"[,;/]|\band\b", s):
        x = re.sub(r"\b(database|databases|db|software|program|tool|server|web ?server|online|genome|v\d[\d.]*)\b", "", x, flags=re.I)
        k = n(x)
        k = re.sub(r"(v|version)?\d+(\d)*$", "", k) if not k.startswith("mega") else k
        if k:
            out.add(CANON.get(k, k))
    return out


def dup_set(s):
    s = str(s).lower()
    out = set()
    if "segment" in s or "fragment" in s: out.add("segmental")
    if "tandem" in s: out.add("tandem")
    if "wgd" in s or "whole" in s: out.add("wgd")
    return out


def blast_key(s):
    s = str(s)
    if "not used" in s.lower(): return "notused"
    m = re.search(r"1e-?(\d+)", s)
    return f"1e-{m.group(1)}" if m else "unspecified"


def hmmer_key(s):
    s = str(s)
    if s.strip().lower().startswith("no"): return ("no", frozenset())
    return ("yes", frozenset(re.findall(r"PF\d{5}", s)))


def first_int(s):
    """First number in a value, digits or words ("three clades" -> 3)."""
    s = str(s).replace(",", "")
    m = re.search(r"\b(\d+|" + NUMWORD_RX + r")\b", s, re.I)
    return to_int(m.group(1)) if m else None


def fam_match(g, p):
    a, b = n(g), n(p)
    if not a or not b: return a == b
    return a == b or (len(b) >= 2 and (a.startswith(b) or b.startswith(a) or b in a or a in b))


def score(field, g, p):
    """Return a score in [0, 1] for one field."""
    if field in YESNO:
        return float(str(g).strip().lower() == str(p).strip().lower())
    if field == "Country of Origin":
        return float(n(g) == n(p))
    if field == "Primary Organism":
        return float(bool(species_set(g) & species_set(p))) if not empty(g) else float(empty(p))
    if field == "Gene Family":
        return float(fam_match(g, p))
    if field == "Number of Genes Identified":
        return float(first_int(g) is not None and first_int(g) == first_int(p))
    if field == "BLAST (E-value cut-off used)":
        return float(blast_key(g) == blast_key(p))
    if field == "HMMER (with Pfam domains ID)":
        (gy, gp), (py, pp) = hmmer_key(g), hmmer_key(p)
        if gy != py: return 0.0
        if gy == "no" or not gp: return 1.0
        return len(gp & pp) / len(gp | pp)
    if field == "Phylogenetic Structure":
        gi, pi = first_int(g), first_int(p)
        if gi is None: return float(pi is None)
        return float(gi == pi)
    if field == "Gene Duplication Events (TANDEM/SEGMENTAL)":
        return float(dup_set(g) == dup_set(p))
    if field in SETS:
        gs = species_set(g) if field == "Secondary Organism" else tok_set(g)
        ps = species_set(p) if field == "Secondary Organism" else tok_set(p)
        if not gs and not ps: return 1.0
        if not gs or not ps: return 0.0
        return 2 * len(gs & ps) / (len(gs) + len(ps))       # F1 / Dice
    return float(n(g) == n(p))
