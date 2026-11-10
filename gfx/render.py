"""Render a prepared Doc as the labelled plain-text file that the extractor reads."""
from __future__ import annotations

import re
import textwrap

MAX_LINES, WIDTH = 4000, 180
ORDER = [("abstract", "ABSTRACT"), ("introduction", "INTRODUCTION"), ("methods", "METHODS"), ("results", "RESULTS"),
         ("discussion", "DISCUSSION"), ("conclusion", "CONCLUSION")]
CUT_FIRST = ["introduction", "discussion", "conclusion"]      # shortened (from the end) when a paper is too long
AFFIL = re.compile(r"universit|institut|academy|college|laborator|correspond|e-?mail|@|department|school|centre|center", re.I)


def wrap(s: str) -> list[str]:
    return [line for p in s.split("\n") for line in (textwrap.wrap(" ".join(p.split()), WIDTH) or [])]


def render(doc) -> str:
    """Title, front matter, then the marked sections; the reference list is never included."""
    parts = {k: wrap(doc.sections.get(k, "")) for k, _ in ORDER}
    if not any(parts.get(k) for k in ("methods", "results")):     # unheaded short communication: one BODY block
        parts = {"body": wrap(doc.body)}
    back = [line for line in wrap(doc.sections.get("back", "")) if AFFIL.search(line)][:60]
    head = ["===== TITLE =====", doc.title or "",
            "===== FRONT MATTER (authors, affiliations, correspondence) ====="] + wrap(doc.front)[:80]
    tail = ["===== BACK MATTER (author details / affiliations) ====="] + back if back else []
    budget = MAX_LINES - len(head) - len(tail) - 8
    for k in CUT_FIRST:
        over = sum(len(v) for v in parts.values()) - budget
        if over > 0 and k in parts:
            parts[k] = parts[k][:max(10, len(parts[k]) - over)]
    labels = dict(ORDER, body="BODY")
    out = head[:]
    for k, v in parts.items():
        if v:
            out += [f"===== {labels[k]} ====="] + v
    text = "\n".join(out[:MAX_LINES - len(tail)] + tail) + "\n"
    return re.sub(r"[\x00-\x08\x0b-\x1f\x7f￾￿]", " ", text)
