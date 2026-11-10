"""Text preparation for genome-wide gene-family PDFs (and PMC XML).

Produces a Doc with:
  pages        per-page text (reading order, ligatures fixed, hyphenation repaired)
  front        first-page text (affiliations, title, abstract)
  body         everything before the reference list, minus back-matter (acknowledgements, funding, contributions…)
  sections     {abstract, introduction, methods, results, discussion, conclusion} best-effort
  references   the reference list (kept only so it can be excluded)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF

LIG = {"ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl", " ": " ", " ": " ",
       " ": " ", " ": " ", " ": " ", "​": "", "­": "", "‐": "-", "‑": "-", "‒": "-",
       "–": "-", "—": "-", "−": "-", "‘": "'", "’": "'", "“": '"', "”": '"', "´": "'"}
# Words that often lose a ligature in PDF text layers ("identi cation", "in uence"). Each broken form maps to the
# real word, so "fi" vs "fl" vs "ff" is never guessed.
_LIG_VOCAB = """identification identifications identified identify identifying classification classifications classified
specific specifically specificity modified modification modifications amplified amplification purified verified verification
significant significantly significance quantification quantified quantify efficient efficiency efficiently efflux profile profiles
profiled profiling confirmed confirm confirms confirmation conflict conflicts influence influenced influences flowering flower
flowers florets fluorescence fluorescent defined define definition reflect reflects reflected benefit benefits different
differences differentially differential differentiation difference sufficient first field fields filter filtered filtering final
finally find finding findings figure figures fitness flanking flag flax flavonoid flavonoids flavonol flexible affinity affected
affect affects effect effects coefficient coefficients offspring workflow fifth fibre fiber fibers fibres beneficial deficiency
deficient magnification magnified certified certificate unified classify diversified diversification specialized fitting fit fits
fixed fixation fluctuation flooding flow flux inflorescence inflorescences""".split()
_LIG_MAP = {}
for _w in _LIG_VOCAB:
    for _lig in ("ffi", "ffl", "fi", "fl", "ff"):
        for _i in [m.start() for m in re.finditer(_lig, _w)]:
            variants = [_w[:_i] + _w[_i + len(_lig):]]
            if _i > 0:                       # "in uence" can be re-joined; "of owering" (lost at word start) cannot
                variants.append(_w[:_i] + " " + _w[_i + len(_lig):])
            for _broken in variants:
                if len(_broken.replace(" ", "")) >= 4 and _broken not in _LIG_VOCAB:
                    _LIG_MAP.setdefault(_broken, _w)
for _k in ("prole", "ower", "owers", "nding", "gure"):   # also real words/fragments: never "fix" these
    _LIG_MAP.pop(_k, None)
LIG_WORDS = re.compile(r"\b(" + "|".join(sorted((re.escape(k) for k in _LIG_MAP), key=len, reverse=True)) + r")\b", re.I)


def _lig_sub(m: re.Match) -> str:
    fixed = _LIG_MAP[m.group(1).lower()]
    return fixed.capitalize() if m.group(1)[0].isupper() else fixed

HEAD = {
    "abstract": r"abstract|summary",
    "introduction": r"introduction|background",
    "methods": r"materials?\s*(?:and|&)\s*methods?|methods?\s*(?:and|&)\s*materials?|methods?|methodology|experimental\s+procedures|"
               r"experimental\s+section|material\s+and\s+method",
    "results": r"results?(?:\s+and\s+discussions?)?",
    "discussion": r"discussions?",
    "conclusion": r"conclusions?|concluding\s+remarks|summary\s+and\s+conclusions?",
    "back": r"acknowledge?ments?|funding(?:\s+information)?|author\s+contributions?|authors'?\s+contributions?|conflicts?\s+of\s+interests?|"
            r"competing\s+interests?|declaration\s+of\s+competing\s+interest|data\s+availability(?:\s+statement)?|availability\s+of\s+data.*|"
            r"supplementary\s+(?:materials?|information|data)|supporting\s+information|abbreviations|ethics\s+approval.*|"
            r"consent\s+for\s+publication|institutional\s+review\s+board\s+statement|informed\s+consent\s+statement|"
            r"publisher'?s?\s+note|additional\s+files?|electronic\s+supplementary\s+material|credit\s+authorship.*",
    "references": r"references?(?:\s+and\s+notes)?|literature\s+cited|bibliography|works\s+cited|reference\s+list",
}
NUM = r"(?:\d{1,2}(?:\.\d{1,2})*\.?|[IVX]{1,4}\.)?\s*"
HEAD_RE = {k: re.compile(rf"^\s*{NUM}(?:{v})\s*[:.]?\s*$", re.I) for k, v in HEAD.items()}
INLINE_ABS = re.compile(r"^\s*(abstract|summary)(?:\s*[:.\-]\s*|\s+(?=[A-Z]))(.{20,})", re.I)


def fix(text: str) -> str:
    for a, b in LIG.items():
        text = text.replace(a, b)
    text = LIG_WORDS.sub(_lig_sub, text)
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)          # re-join hyphenated line breaks
    text = re.sub(r"[ \t]+", " ", text)
    return text


@dataclass
class Doc:
    path: Path
    pages: list[str]
    front: str
    body: str
    references: str
    sections: dict[str, str] = field(default_factory=dict)
    title: str = ""

    @property
    def full(self) -> str:
        return "\n".join(self.pages)

    def sec(self, *names: str) -> str:
        return "\n".join(self.sections.get(n, "") for n in names if self.sections.get(n))


def _page_text(page) -> str:
    # blocks sorted in reading order handle most two-column layouts correctly
    blocks = page.get_text("blocks", sort=True)
    w = page.rect.width
    lines = []
    two_col = sum(1 for b in blocks if (b[2] - b[0]) < w * 0.55) > len(blocks) * 0.5 if blocks else False
    if two_col:
        left = [b for b in blocks if b[0] < w * 0.45]
        right = [b for b in blocks if b[0] >= w * 0.45]
        # full-width blocks (title, abstract) stay in vertical order with the left column
        ordered = sorted(left, key=lambda b: b[1]) + sorted(right, key=lambda b: b[1])
    else:
        ordered = blocks
    for b in ordered:
        if b[6] == 0:
            lines.append(b[4])
    return fix("\n".join(lines))


def pdf_title(d) -> str:
    """Title = the largest-font text on page 1 (skipping short running heads / journal names)."""
    if not len(d):
        return ""
    spans = []
    for b in d[0].get_text("dict")["blocks"]:
        for ln in b.get("lines", []):
            txt = "".join(s["text"] for s in ln["spans"]).strip()
            if txt:
                size = max(s["size"] for s in ln["spans"])
                spans.append((round(size, 1), ln["bbox"][1], txt))
    if not spans:
        return ""
    for size in sorted({s[0] for s in spans}, reverse=True):
        lines = [s for s in spans if abs(s[0] - size) < 0.6]
        text = fix(" ".join(t for _, _, t in sorted(lines, key=lambda x: x[1])))
        words = re.findall(r"[A-Za-z]{2,}", text)
        if len(words) >= 5 and len(text) < 400 and not re.search(r"journal|volume|issn|www\.|http|copyright|open access", text, re.I):
            return re.sub(r"\s+", " ", text).strip()
    return ""


def load_xml(path: Path) -> Doc:
    """PMC / Europe PMC JATS XML: sections, affiliations and the reference list are explicitly tagged."""
    import xml.etree.ElementTree as ET
    root = ET.parse(path).getroot()
    txt = lambda el: fix(re.sub(r"\s+", " ", "".join(el.itertext())).strip()) if el is not None else ""
    title = txt(root.find(".//article-meta//article-title"))
    affs = [txt(a) for a in root.findall(".//article-meta//aff")] or [txt(a) for a in root.findall(".//aff")]
    corresp = " ".join(txt(c) for c in root.findall(".//author-notes//corresp"))
    emails = " ".join(txt(e) for e in root.findall(".//article-meta//email"))
    kwds = "; ".join(txt(k) for k in root.findall(".//kwd"))
    doi_el = root.find(".//article-meta/article-id[@pub-id-type='doi']")
    pub = root.find(".//article-meta/pub-date/year")
    abstract = " ".join(txt(a) for a in root.findall(".//article-meta/abstract"))
    sections: dict[str, list[str]] = {"abstract": [abstract]}
    body = root.find(".//body")
    if body is not None:
        for sec in body.findall("./sec"):
            head = txt(sec.find("title"))
            key = next((k for k, rx in HEAD_RE.items() if rx.match(head)), None)
            if key is None:
                low = head.lower()
                key = ("methods" if "method" in low or "material" in low else "results" if "result" in low else
                       "discussion" if "discussion" in low else "introduction" if "introduction" in low or "background" in low else
                       "conclusion" if "conclusion" in low else "results")
            sections.setdefault(key, []).append(txt(sec))
        caps = " ".join(txt(c) for c in body.findall(".//caption"))
        sections.setdefault("results", []).append(caps)
    back = root.find(".//back")
    refs = txt(back.find(".//ref-list")) if back is not None else ""
    front = "\n".join([title, "\n".join(affs), corresp, emails,
                       f"doi: {doi_el.text}" if doi_el is not None else "", f"Published: {pub.text}" if pub is not None else "",
                       f"Keywords: {kwds}" if kwds else "", abstract])
    sec = {k: "\n".join(v) for k, v in sections.items()}
    body_text = "\n".join(sec.get(k, "") for k in ("abstract", "introduction", "methods", "results", "discussion", "conclusion"))
    doc = Doc(path=path, pages=[front, body_text], front=front, body=front + "\n" + body_text, references=refs, sections=sec)
    doc.title = title
    return doc


def load(path: Path) -> Doc:
    path = Path(path)
    return load_xml(path) if path.suffix.lower() == ".xml" else load_pdf(path)


def load_pdf(path: Path) -> Doc:
    d = fitz.open(path)
    pages = [_page_text(p) for p in d]
    doc = build(path, pages)
    doc.title = pdf_title(d)
    return doc


def build(path: Path, pages: list[str]) -> Doc:
    lines = [ln.strip() for ln in "\n".join(pages).split("\n")]
    sections: dict[str, list[str]] = {}
    cur = "front"
    order = []
    ref_start = None
    n = len(lines)
    for i, ln in enumerate(lines):
        if not ln:
            continue
        m = INLINE_ABS.match(ln)
        if m and "abstract" not in sections and i < n * 0.3:
            cur = "abstract"; sections.setdefault(cur, []).append(m.group(2)); order.append(cur); continue
        hit = None
        if len(ln) < 70:
            for k, rx in HEAD_RE.items():
                if rx.match(ln):
                    hit = k; break
        if hit == "references" and i < n * 0.4:
            hit = None           # an early "References" is a running header/citation style, not the list
        if hit == "back" and i < n * 0.3:
            hit = None           # an early "Abbreviations"/"Funding" box on page 1 must not swallow the body
        if hit:
            if hit == "references" and ref_start is None:
                ref_start = i
            cur = hit; order.append(cur); sections.setdefault(cur, []); continue
        sections.setdefault(cur, []).append(ln)
    sec = {k: "\n".join(v) for k, v in sections.items()}
    references = sec.get("references", "")
    body_parts = [sec.get(k, "") for k in ("front", "abstract", "introduction", "methods", "results", "discussion", "conclusion")]
    body = "\n".join(p for p in body_parts if p)
    if not any(sec.get(k) for k in ("methods", "results", "discussion")):
        # unheaded paper (short communication): keep everything before the reference list
        body = "\n".join(l for l in lines[:ref_start] if l)
    # safety net: if no reference heading was found, drop the tail that looks like a numbered reference list
    if not references:
        m = re.search(r"\n\s*(?:\[?1\]?\.?|1\.)\s+[A-Z][a-z]+,?\s+[A-Z]\.", body[int(len(body) * 0.6):])
        if m:
            cut = int(len(body) * 0.6) + m.start()
            references, body = body[cut:], body[:cut]
    front = pages[0] if pages else ""
    if not sec.get("abstract"):
        # no heading: take the first long paragraph on page 1 that reads like an abstract
        paras = [p.strip() for p in re.split(r"\n\s*\n|(?<=\.)\n(?=[A-Z])", front) if len(p.strip()) > 400]
        cand = [p for p in paras if re.search(r"\b(genes?|family|identified|genome)\b", p, re.I)]
        if cand:
            sec["abstract"] = cand[0]
    return Doc(path=path, pages=pages, front=front, body=body, references=references, sections=sec)
