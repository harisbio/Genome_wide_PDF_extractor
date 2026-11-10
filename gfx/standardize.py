"""Standard forms for organism, duplication and gene family values.

Organisms: Genus species without authority, one per comma; common names and misspellings fixed; hybrids keep the x sign.
Duplication: types in a fixed order; Fragment = Segmental; values that name no type become "Type not named".
Gene families: synonyms merged with the rules in family_names.py; MANUAL holds reviewed one-off cases.
"""
from .family_names import SYN, key

import re

SP_FIX = {"apple": "Malus domestica", "chickpea": "Cicer arietinum", "hordium vulgare": "Hordeum vulgare", "malus x domestica": "Malus domestica", "malus × domestica": "Malus domestica",
          "fortunella hindisi": "Fortunella hindsii", "gossypium arboretum": "Gossypium arboreum", "pepper": "Capsicum annuum"}
EMPTY = {"", "none", "not available", "not specified", "nan"}
ORDER = ["Segmental", "Tandem", "WGD", "Dispersed", "Proximal", "Transposed"]
UNNAMED = {"duplication", "paralogous", "homoeologous copies"}


def species_one(t):
    t = " ".join(re.sub(r"[\xa0​]", " ", t).split()).strip(" .")
    t = re.sub(r"\s*\([^)]*\)", "", t).strip(" .")
    low = t.lower()
    if low in SP_FIX:
        return SP_FIX[low]
    m = re.match(r"^([A-Z][a-zA-Z\-]+) (?:x |× )([A-Z]?[a-z\-]+)", t)
    if m and m.group(2).islower():            # Genus × species
        name = f"{m.group(1)} × {m.group(2)}"
        return SP_FIX.get(name.lower(), name)
    m = re.match(r"^([A-Z][a-z\-]+ [a-z\-]+) × ([A-Z][a-z\-]+ [a-z\-]+)", t)
    if m:                                     # hybrid of two named species
        return f"{m.group(1)} × {m.group(2)}"
    m = re.match(r"^([A-Z][a-zA-Z\-]+) spp?\.?(?:\s|$)", t)
    if m:
        return f"{m.group(1)} spp."
    m = re.match(r"^([A-Z][a-zA-Z\-]+) ([a-zA-Z][a-z\-]+)", t)
    if m:
        name = f"{m.group(1)} {m.group(2).lower()}"
        return SP_FIX.get(name.lower(), name)
    return t


def species_cell(v):
    parts = [p for p in re.split(r"[,;/]| and ", str(v).replace("\xa0", " ")) if p.strip()]
    out = [species_one(p) for p in parts if p.strip().lower() not in EMPTY]
    return ", ".join(dict.fromkeys(x for x in out if x)) or "Not Available"


def duplication_cell(v):
    found, unnamed = set(), False
    for x in str(v).split(","):
        low = x.strip().lower()
        if low in ("", "not specified"):
            continue
        if low in UNNAMED:
            unnamed = True
            continue
        found.add("Segmental" if low == "fragment" else x.strip())
    extra = sorted(found - set(ORDER))
    if extra:
        raise ValueError(f"unexpected duplication label: {extra}")
    if found:
        return ", ".join(t for t in ORDER if t in found)
    return "Type not named" if unnamed else "Not specified"


MANUAL = {   # reviewed against paper titles: exact cell value -> standard value
    "14-3-3 (GRF)": "14-3-3", "14-3-3 (Mi14-3-3)": "14-3-3",
    "ACO (1-Aminocyclopropane-1-carboxylic acid oxidase)": "ACO (ACC oxidase)", "ACO (Aconitase)": "ACO (aconitase)",
    "ANK (Ankyrin repeats)": "ANK", "ANP (Arabidopsis NPK1-related protein kinase)": "ANP", "FBN (Fibrillin)": "FBN", "GDSL (GELP)": "GDSL",
    "Brassinazole-resistant": "BES1/BZR1", "PERKs": "PERK", "Hsp70": "HSP70", "Hsp90": "HSP90", "HB": "Homeobox", "NRT/NPF": "NPF (NRT1/PTR)",
    "SBP/SPL": "SPL (SBP-box)", "Family-1 UDP-glycosyltransferases (UGTs)": "UGT", "NPR1-like gene family": "NPR1-like",
    "UDP-D-glucuronic acid 4-epimerase (UGlcAE/GAE) gene family": "UGlcAE/GAE", "m6A regulatory gene family": "m6A regulatory genes",
    "Mediator Complex Subunit": "Mediator", "P-type II Ca2+ ATPases": "P-type II Ca2+ ATPase", "RNA helicase (DEAD, DEAH, DExD/H)": "RNA helicase",
    "Potassium transport-related genes (HAK/KUP/KT, HKT, KEA, Shaker, TPK)": "HAK/KUP/KT, HKT, KEA, Shaker, TPK",
}


def split(cell):
    """Split on commas outside brackets."""
    out, depth, cur = [], 0, ""
    for ch in cell:
        depth += ch == "("; depth -= ch == ")"
        if ch == "," and depth == 0:
            out.append(cur); cur = ""
        else:
            cur += ch
    return [x.strip() for x in out + [cur] if x.strip()]


def std_one(name):
    k = key(name)
    if k in SYN:
        return SYN[k]
    return name


def std(cell):
    if cell in MANUAL:
        return MANUAL[cell]
    return ", ".join(dict.fromkeys(std_one(x) for x in split(cell)))
