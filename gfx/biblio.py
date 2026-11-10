"""Bibliographic fields: offline from the PDF text, optionally completed from Crossref by DOI."""
from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from collections import Counter

DOI_RX = re.compile(r"\b(10\.\d{4,9}/[^\s\"<>,;]+)", re.I)


def _clean_doi(d: str) -> str:
    d = d.rstrip(".)]}")
    return re.sub(r"(?i)(\.pdf|/full|/abstract)$", "", d)


def doi(doc) -> str:
    """The paper's own DOI: printed on page 1 (header/footer/citation box), not one from the reference list."""
    for m in DOI_RX.finditer(doc.front.replace(" ", " ")):
        return _clean_doi(m.group(1))
    head = "\n".join(doc.pages[:2])[:6000]
    m = DOI_RX.search(head)
    return _clean_doi(m.group(1)) if m else ""


def year(doc) -> str:
    fr = doc.front
    for rx in (r"Published(?: online)?:?\s*(?:\d{1,2}\s+)?[A-Za-z]*\.?\s*(?:\d{1,2},?\s+)?((?:19|20)\d{2})",
               r"(?:Accepted|Available online)[^\n]{0,40}?((?:19|20)\d{2})",
               r"©\s*(?:The Author\(s\)\s*)?((?:19|20)\d{2})", r"\(((?:19|20)\d{2})\)\s*\d+[:\s]", r"\b((?:19|20)\d{2});\s*\d+"):
        m = re.search(rx, fr, re.I)
        if m and 1995 <= int(m.group(1)) <= 2030:
            return m.group(1)
    ys = [y for y in re.findall(r"\b((?:19|20)\d{2})\b", fr) if 1995 <= int(y) <= 2030]
    return Counter(ys).most_common(1)[0][0] if ys else ""


def keywords(doc) -> str:
    m = re.search(r"Key ?words?\s*[:.\-—]?\s*(.{5,400}?)(?:\n\s*\n|\n(?:\d\.?\s*)?(?:Introduction|Background|Abbreviations|1\.))",
                  doc.front + "\n" + (doc.pages[1] if len(doc.pages) > 1 else ""), re.I | re.S)
    if not m:
        return "Not Available"
    kw = re.sub(r"\s+", " ", m.group(1)).strip(" .;")
    return kw if 3 <= len(kw) <= 400 else "Not Available"


def _user_agent() -> str:
    """Crossref asks polite clients to give a contact address; set CROSSREF_MAILTO to add one."""
    mail = os.environ.get("CROSSREF_MAILTO", "").strip()
    return "gene-family-extractor/1.0" + (f" (mailto:{mail})" if mail else "")


def crossref(doi_: str, timeout: int = 20) -> dict:
    """Title, authors, year and journal for a DOI from the Crossref REST API."""
    if not doi_:
        return {}
    try:
        url = "https://api.crossref.org/works/" + urllib.parse.quote(doi_)
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": _user_agent()}), timeout=timeout) as r:
            msg = json.load(r)["message"]
    except Exception:
        return {}
    authors = ", ".join(f"{a.get('given', '')} {a.get('family', '')}".strip() for a in msg.get("author", []))
    y = (msg.get("published-print") or msg.get("published-online") or msg.get("issued") or {}).get("date-parts", [[None]])[0][0]
    return {"Title": re.sub(r"<[^>]+>", "", (msg.get("title") or [""])[0]), "Authors": authors, "Year": str(y or ""),
            "Journal": (msg.get("container-title") or [""])[0], "Keywords": "; ".join(msg.get("subject", [])[:0])}


def extract_biblio(doc, online: bool = False) -> dict:
    out = {"Title": doc.title, "Authors": "", "Year": year(doc), "Journal": "", "DOI": doi(doc), "Keywords": keywords(doc)}
    if online:
        cr = crossref(out["DOI"])
        for k, v in cr.items():
            if v:
                out[k] = v if k != "Keywords" else out[k]
    return out
