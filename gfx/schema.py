"""Fields of an extraction record, their allowed formats, and the columns of the output dataset."""

# Fields every record must contain (see codebook/extraction_codebook.md for definitions).
FIELDS = [
    "eligibility", "Country of Origin", "Primary Organism", "Secondary Organism", "Gene Family", "Genome Source",
    "HMMER (with Pfam domains ID)", "BLAST (E-value cut-off used)", "SMART", "CDD", "MEGA", "IQ-TREE", "MEME", "MCScanX",
    "TBTools", "Experimental Validation (qPCR)", "Expression Analysis (RNA-seq)", "Expression (microarray/EST)",
    "Number of Genes Identified", "Genes per species", "Phylogenetic Structure", "Gene Duplication Events", "tools", "Keywords",
]

YESNO = [
    "SMART", "CDD", "MEGA", "IQ-TREE", "MEME", "MCScanX", "TBTools", "Experimental Validation (qPCR)",
    "Expression Analysis (RNA-seq)", "Expression (microarray/EST)",
]

# Full-match regular expressions for fields with a fixed format.
FORMAT = {
    "eligibility": r"INCLUDE|EXCLUDE: E\d+_[A-Z_]+",
    "HMMER (with Pfam domains ID)": r"No|Yes \(Pfam domain ID not mentioned\)|Yes \(Pfam PF\d{5}(, PF\d{5})*\)",
    "BLAST (E-value cut-off used)": r"Not Used|BLAST \(not specified\)|BLAST \(\d?e-\d{1,3}\)|BLAST \(1\.0\)",
    "Number of Genes Identified": r"\d{1,5}|Not specified",
    "Genes per species": r"Not specified|[A-Z][a-z]+ [a-z.-]+(?: [a-z.-]+)*: \d{1,5}(; [A-Z][a-z]+ [a-z.-]+(?: [a-z.-]+)*: \d{1,5})*",
    "Gene Duplication Events": r"Not specified|(Segmental|Tandem|WGD|Dispersed|Proximal|Transposed)"
                               r"(, (Segmental|Tandem|WGD|Dispersed|Proximal|Transposed))*",
}

# Values that mean "nothing stated": no evidence quote is required for them.
EMPTY_VALUES = {"No", "Not specified", "Not Available", "Not Used", ""}
# Fields that never need an evidence quote.
NO_EVIDENCE = {"tools", "Keywords", "eligibility"}
# Minimum quote length after removing everything except letters and digits.
MIN_QUOTE_CHARS = 12
# Minimum rapidfuzz partial_ratio for a quote that is not found exactly.
FUZZY_THRESHOLD = 90

# Columns of the assembled dataset.
DATA_COLS = [
    "Paper ID", "Country of Origin", "Title", "Authors", "Year", "Journal", "DOI", "Keywords", "Primary Organism",
    "Secondary Organism", "Gene Family", "Genome Source", "HMMER (with Pfam domains ID)", "BLAST (E-value cut-off used)",
    "SMART", "Other (Tools for Domain Analysis)", "CDD", "MEGA", "IQ-TREE", "MEME", "Others (Tools for Motif Analysis)",
    "MCScanX", "Other (Tools for Synteny)", "TBTools", "Other (Tools for Visualization)", "Experimental Validation (qPCR)",
    "Other Tools Used In Methodology", "Number of Genes Identified", "Phylogenetic Structure",
    "Gene Duplication Events (TANDEM/SEGMENTAL)", "Expression Analysis (RNA-seq)",
]
EXTRA_COLS = ["Expression (microarray/EST)", "Genes per species", "Other tools (unlisted)", "Full-text eligibility"]
