"""Tool names: one standard key per tool, and filing of free-text tool lists into the five tool columns.

key(name) normalises a tool name (drops "software", "server", version numbers ...) and merges known synonyms.
The checklist (data/tool_checklist.csv) gives each key its standard name and the column it belongs to.
"""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

import pandas as pd

OWN_COLUMN = {"mega", "meme", "smart", "cdd", "tbtools", "mcscanx", "hmmer", "iqtree", "blast", "blastp", "memesuite",
              "megax", "mega7", "mega11", "mega6", "mega5", "megaxi", "mcscan"}
NOT_TOOL = re.compile(r"\bkit\b|master mix|reagent|trizol|sybr|^yes$|^qrt-?pcr$|^rt-?qpcr$|^qpcr$|^pcr$|^rna-?seq$|cdna|"
                      r"^cluster$|^heatmap$|^blast$|thermo|takara|vazyme|tiangen|invitrogen|bio-?rad|applied biosystems|qiagen|"
                      r"roche|illumina|agilent|^ncbi$|^excel$|^microsoft", re.I)
SYN = {  # explicit synonym merges (key -> standard key)
    "genestructuredisplayserver": "gsds", "gsds20": "gsds", "clustal": "clustalw", "clustalo": "clustalomega",
    "plantgenomicduplicationdatabase": "pgdd", "plantgenomeduplicationdatabase": "pgdd", "interproscanprogram": "interproscan",
    "expasyprotparam": "protparam", "expasyscanprosite": "scanprosite", "scanprositeserver": "scanprosite", "motifscan": "motifscan",
    "wolfpsortii": "wolfpsort", "psort": "wolfpsort", "mapgene2chromosome": "mg2c", "mapgene2chrom": "mg2c",
    "multipleemformotifelicitation": "meme", "itoltool": "itol", "interactivetreeoflife": "itol", "stringdatabase": "string",
    "swissmodel": "swissmodel", "phyre": "phyre2", "evolview3": "evolview", "evolviewv3": "evolview", "circosplot": "circos",
    "blast2go": "blast2go", "kakscalculator": "kakscalculator", "kakscalculator20": "kakscalculator", "kaks": "kakscalculator",
    "graphpad": "graphpadprism", "prism": "graphpadprism", "rsoftware": "r", "rstudio": "r", "ggplot2": "r", "pheatmap": "r",
    "tbtool": "tbtools", "plantcaredatabase": "plantcare", "newplace": "place", "placedatabase": "place",
    "mapgene2chromosome": "mg2c", "mapgene2chrome": "mg2c", "mg2cv2": "mg2c", "mapinsect": "mapinspect", "stringdb": "string",
    "primer5": "primerpremier", "primerpremier5": "primerpremier", "primerpremier6": "primerpremier", "geneiousprime": "geneious",
    "ibmspssstatistics": "spss", "ibmspss": "spss", "deseqr": "deseq2", "deseq": "deseq2", "heatmapperonline": "heatmapper",
    "expasycomputepi": "expasy", "computepi": "expasy", "computepimw": "expasy", "expasyportal": "expasy", "eggnog": "eggnogmapper",
    "plantploc": "plantmploc", "plantmploc": "plantmploc", "shinygo": "shinygo", "originpro": "origin", "hemi": "heml",
    "heatmapilluminator": "heml", "ncbigeo": "geo", "geneexpressionomnibus": "geo", "cellpl": "cellploc", "tophat": "tophat2",
    "hisat": "hisat2", "bowtie": "bowtie2", "clustalx2": "clustalx", "clustalw2": "clustalw", "musclev5": "muscle",
    "genestructuredisplay": "gsds", "plantgenomeduplication": "pgdd", "plantgenomicduplication": "pgdd",
    "protparam": "expasy", "expasyprotparam": "expasy", "genestructuredisplaygsds": "gsds",
    "iqtree2": "iqtree", "alphafold": "alphafold", "alphafold2": "alphafold", "alphafold3": "alphafold", "itasser": "itasser",
    "swissmodelworkspace": "swissmodel", "phyre2server": "phyre2", "evolviewv2": "evolview", "dnasp6": "dnasp", "dnaspv6": "dnasp",
}
NOT_TOOL_EXTRA = {"confocalmicroscopy", "floraldipmethod", "floraldip", "nanodrop", "lightcycler480", "lightcycler", "rtpcr", "mw", "psi",
                  "go", "cogs", "geneontology", "__", "bioradcfx96", "cfx96", "trizolreagent", "pcr", "3racepcr", "racepcr", "cluster"}
# sequence/genome repositories: recorded under Genome Source (and RNA-seq), not counted as analysis tools
DATA_SOURCES = {"tair", "phytozome", "ncbi", "ensemblplants", "ensembl", "tigr", "maizegdb", "gramene", "ncbisra", "sra", "genbank",
                "ncbiestdatabase", "ncbiest", "dbest", "ncbigenbank", "rgap", "msu", "ricegenomeannotationproject", "jgi", "uniprot",
                "ncbiprotein", "ncbinr", "sgn", "solgenomicsnetwork", "gdr", "cottonfgd", "ncbigeo", "geo", "arabidopsisinformationresource",
                "brad", "plantgdb", "knowpulse", "peanutbase", "bananagenomehub", "cucurbitgenomics", "cucurbitgenomicsdatabase"}


def key(name: str) -> str:
    k = re.sub(r"\b(software|program|programme|server|web ?server|database|tool|tools|online|web|package|suite|v?\d+(\.\d+)*)\b", "",
               name, flags=re.I)
    k = re.sub(r"[^a-z0-9]", "", k.lower())
    return SYN.get(k, k)


CAT_COL = {"Domain": "Other (Tools for Domain Analysis)", "Motif": "Others (Tools for Motif Analysis)",
           "Synteny": "Other (Tools for Synteny)", "Visualization": "Other (Tools for Visualization)",
           "Methodology": "Other Tools Used In Methodology"}
SKIP = OWN_COLUMN | DATA_SOURCES | NOT_TOOL_EXTRA
CHECKLIST = Path(__file__).resolve().parent.parent / "data" / "tool_checklist.csv"


def load_checklist(path: Path = CHECKLIST) -> dict:
    """key -> (standard name, category)."""
    cl = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
    return {r.key: (r.tool, r.field) for r in cl.itertuples()}


def file_tools(names, checklist: dict) -> dict:
    """File a list of tool names into the five tool columns; unknown names go to 'Other tools (unlisted)'."""
    cols, unlisted = defaultdict(list), []
    for t in names:
        k = key(str(t))
        if not k or k in SKIP:
            continue
        if k in checklist:
            name, cat = checklist[k]
            if name not in cols[CAT_COL[cat]]:
                cols[CAT_COL[cat]].append(name)
        elif str(t).strip() not in unlisted:
            unlisted.append(str(t).strip())
    out = {c: (", ".join(v) if v else "No") for c, v in cols.items()}
    for c in CAT_COL.values():
        out.setdefault(c, "No")
    out["Other tools (unlisted)"] = ", ".join(unlisted) if unlisted else "No"
    return out
