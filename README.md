# Genome-Wide PDF Extractor: A python program for structured data extraction from genome-wide gene family study PDFs

Evidence-backed data extraction from genome-wide gene family identification papers in plants.

This program turns the full texts of genome-wide gene family studies into a structured dataset. Every extracted value
is tied to a sentence copied from the paper, and a validation module refuses any value whose supporting quote cannot be
found in the article. It was built for the systematic review and meta-analysis *Twenty-Five Years of Genome-Wide Gene
Family Identification Analysis in Plants: Trends, Tools, and Methodological Shifts* (Haris et al.), where it was used
to extract the data for the 310 included studies.

## How it works

```
 PDF / PMC XML ──► 1. prepare ──► labelled text ──► 2. extract ──► record (JSON) ──► 3. validate ──► saved record
                                                    (Claude Sonnet,           │  problems listed
                                                     codebook rules)          └──────── fix and resend ◄─┘

 saved records ──► 4. assemble ──► extraction.csv + evidence.csv ──► 5. standardize ──► final dataset
                                         │
                                         └──► compare with an earlier extraction (field by field)
```

1. **Prepare** (`scripts/prepare_papers.py`). Each PDF or PubMed Central XML file is converted into a clean text file
   with the title, front matter, abstract, introduction, methods, results and discussion marked as separate sections.
   Two-column PDF layouts are put back in reading order, broken ligatures ("identi cation") and hyphenated line breaks
   are repaired, and the reference list is removed.
2. **Extract**. The prepared text is read by Claude Sonnet (Anthropic), run through
   [Claude Code](https://claude.com/claude-code), which fills 24 fields defined in the
   [codebook](codebook/extraction_codebook.md) and gives a verbatim supporting quote for each value. The instructions
   given to the model are in [docs/extractor_instructions.md](docs/extractor_instructions.md). Claude Sonnet 5.5 was used
   for the published study.
3. **Validate** (`scripts/record_extraction.py`). Each record is checked before it is saved:
   - every field is present;
   - each value has the allowed format (Yes/No fields, Pfam identifiers, BLAST E-value cut-offs, gene counts,
     genes per species, duplication categories, full-text eligibility codes);
   - each value other than "No", "Not specified", "Not Available" or "Not Used" has an evidence quote;
   - each quote is found in the paper text, ignoring spacing, case and punctuation, or matches it at 90% or more
     (rapidfuzz partial ratio).

   A record that fails is returned with a list of problems and is saved only after all of them have been fixed.
4. **Assemble** (`scripts/assemble.py`). Saved records become one table with one row per paper, and an evidence table
   with one row per field and its quote. Free-text tool lists are mapped to standard names with
   [data/tool_checklist.csv](data/tool_checklist.csv) and filed into five tool columns (domain, motif, synteny,
   visualization and other methods).
5. **Standardize** (`scripts/standardize.py`). Controlled vocabularies are applied: organism names become accepted
   binomials, duplication values a fixed set of categories in a fixed order, and gene family names one standard
   spelling. Every change is logged for review.

Two further scripts support the workflow:

- `scripts/add_biblio.py` reads the DOI, year, title and keywords from each article and can complete the
  bibliographic details from the [Crossref REST API](https://api.crossref.org).
- `scripts/compare.py` compares two extractions of the same papers field by field, with field-specific agreement
  scores, and adds the supporting quote for each disagreement so it can be checked against the article.

## Installation

Python 3.10 or later.

```bash
git clone <this repository>
cd gene-family-extractor
python -m pip install -r requirements.txt
```

Step 2 needs [Claude Code](https://claude.com/claude-code) with access to a Claude Sonnet model. All other steps run
offline, except `add_biblio.py --crossref`.

## Quick start

```bash
# 1. prepare the full texts (files named <ID>.pdf or <ID>.xml)
python scripts/prepare_papers.py --input path/to/fulltexts --workspace work

# see which papers still need a record, in batches of 10
python scripts/progress.py work --batch-size 10

# 2-3. in Claude Code, give the model docs/extractor_instructions.md and a batch of IDs;
#      the model saves each record through the validator, for example:
python scripts/record_extraction.py work EX1 < examples/example_record.json

# 4. assemble, with bibliographic details from Crossref
python scripts/add_biblio.py --input path/to/fulltexts --workspace work --crossref
python scripts/assemble.py work --biblio work/biblio.csv

# 5. standardize
python scripts/standardize.py work/extraction.csv work/dataset.csv

# optional: compare with an earlier extraction of the same papers
python scripts/compare.py earlier.csv work/dataset.csv --out work/differences.csv
```

To try the validator without any papers, copy `examples/example_paper.txt` to `work/papers/EX1.txt` and run the
`record_extraction.py` line above. Then change a quote in the JSON and run it again to see a problem reported.

## Workspace layout

```
work/
├── papers/<ID>.txt      prepared texts (step 1)
├── out/<ID>.json        validated records (step 3)
├── biblio.csv           bibliographic details (add_biblio.py)
├── extraction.csv       one row per paper (step 4)
├── evidence.csv         one row per field, with its quote (step 4)
└── dataset.csv          standardized dataset (step 5), with dataset_changes.csv
```

## Repository layout

```
gene-family-extractor/
├── codebook/extraction_codebook.md   field definitions and coding rules (v1.1)
├── docs/extractor_instructions.md    instructions given to the extraction model
├── data/tool_checklist.csv           standard tool names, synonyms and tool columns
├── gfx/                              library code
│   ├── textprep.py                   PDF and PMC XML text preparation
│   ├── render.py                     labelled text output
│   ├── schema.py                     fields, allowed formats and dataset columns
│   ├── validate.py                   record validation and quote matching
│   ├── tools.py                      tool-name keys and column filing
│   ├── biblio.py                     DOI, year, keywords and Crossref look-up
│   ├── scoring.py                    field-by-field agreement scores
│   ├── standardize.py                organism, duplication and gene family vocabularies
│   └── family_names.py               gene family synonym rules
├── scripts/                          command-line steps (see above)
├── examples/                         a synthetic paper and a valid record
└── tests/                            unit and end-to-end tests
```

## Coding rules that matter for reuse

The codebook gives the full rules. The ones that most affect counts are:

- Only tools the paper says it used in its own work count; tools named in the introduction or discussion do not.
- BLAST is recorded only when it was used to identify family members, with that search's E-value cut-off.
- A Pfam or InterPro domain check alone is not an HMM search; HMMER is recorded only for an HMM profile search.
- RNA-seq expression is recorded separately from microarray and EST expression.
- The number of genes is the sum over all study species; genes per species are recorded in their own field.
- A variable the paper does not report is recorded as not stated, never inferred.

## Tests

```bash
python -m unittest discover tests
```

The tests cover validation (missing fields, bad formats, invented quotes, missing evidence, tolerant matching), tool
filing, scoring, standardization, ligature repair and an end-to-end run of steps 3 to 5.

## Notes and limitations

- Full texts are not included. Supply your own PDFs or XML files, and respect publisher licences.
- Quote checking shows that each value is supported by text in the article; it does not show that the model's
  interpretation of that text is correct. Check a sample of records against the articles.
- Model output can vary between runs. Keep the saved records and evidence table as the record of what was extracted.
- Text extraction from PDFs depends on the PDF's text layer. Scanned PDFs without a text layer need OCR first.

## Citation

If you use this program, please cite the article above and this repository (see [CITATION.cff](CITATION.cff)).

## License

MIT. See [LICENSE](LICENSE).
