"""Validation of one extraction record against the codebook formats and the paper text."""
from __future__ import annotations

import re

from rapidfuzz import fuzz

from .schema import EMPTY_VALUES, FIELDS, FORMAT, FUZZY_THRESHOLD, MIN_QUOTE_CHARS, NO_EVIDENCE, YESNO


def norm(s: str) -> str:
    """Lower case, letters and digits only: quotes match regardless of spacing, case and punctuation."""
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def quote_found(quote: str, paper_norm: str) -> bool:
    nq = norm(quote)
    return nq in paper_norm or fuzz.partial_ratio(nq, paper_norm) >= FUZZY_THRESHOLD


def validate(record: dict, paper_text: str) -> list[str]:
    """Return a list of problems; an empty list means the record can be saved."""
    probs = []
    if not isinstance(record, dict):
        return ["record must be a JSON object with 'values' and 'evidence'"]
    vals, ev = record.get("values", {}), record.get("evidence", {})
    if not isinstance(vals, dict) or not isinstance(ev, dict):
        return ["'values' and 'evidence' must both be JSON objects"]
    paper_norm = norm(paper_text)
    for f in FIELDS:
        if f not in vals:
            probs.append(f"missing field: {f}")
            continue
        v = vals[f]
        if f == "tools":
            if not isinstance(v, list):
                probs.append("tools must be a JSON list of names")
            continue
        v = str(v).strip()
        if f in YESNO and v not in ("Yes", "No"):
            probs.append(f"{f}: must be Yes or No")
        if f in FORMAT and not re.fullmatch(FORMAT[f], v):
            probs.append(f"{f}: bad format {v!r}")
        q = str(ev.get(f, "")).strip()
        if q:
            if len(norm(q)) < MIN_QUOTE_CHARS:
                probs.append(f"{f}: evidence too short")
            elif not quote_found(q, paper_norm):
                probs.append(f"{f}: evidence quote NOT FOUND in paper text: {q[:90]!r}")
        elif v not in EMPTY_VALUES and f not in NO_EVIDENCE:
            probs.append(f"{f}: evidence required for value {v!r}")
    return probs
