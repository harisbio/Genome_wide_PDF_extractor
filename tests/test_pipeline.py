"""Tests for validation, tool filing, scoring and standardization. Run with: python -m unittest discover tests"""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from gfx.scoring import score  # noqa: E402
from gfx.standardize import duplication_cell, species_cell, std  # noqa: E402
from gfx.textprep import fix  # noqa: E402
from gfx.tools import file_tools, key, load_checklist  # noqa: E402
from gfx.validate import validate  # noqa: E402

PAPER = (ROOT / "examples" / "example_paper.txt").read_text(encoding="utf-8")
RECORD = json.loads((ROOT / "examples" / "example_record.json").read_text(encoding="utf-8"))


class PipelineTests(unittest.TestCase):
    def test_example_record_is_valid(self):
        assert validate(RECORD, PAPER) == []

    def test_missing_field_is_reported(self):
        rec = copy.deepcopy(RECORD)
        del rec["values"]["MEGA"]
        assert "missing field: MEGA" in validate(rec, PAPER)

    def test_bad_format_is_reported(self):
        rec = copy.deepcopy(RECORD)
        rec["values"]["BLAST (E-value cut-off used)"] = "1e-5"
        assert any("bad format" in p for p in validate(rec, PAPER))

    def test_invented_quote_is_rejected(self):
        rec = copy.deepcopy(RECORD)
        rec["evidence"]["MEGA"] = "Maximum likelihood trees were inferred with RAxML under the GTR model"
        assert any("NOT FOUND" in p for p in validate(rec, PAPER))

    def test_value_without_evidence_is_rejected(self):
        rec = copy.deepcopy(RECORD)
        del rec["evidence"]["SMART"]
        assert any("evidence required" in p for p in validate(rec, PAPER))

    def test_quote_matches_despite_spacing_and_case(self):
        rec = copy.deepcopy(RECORD)
        rec["evidence"]["MEME"] = "THE CONSERVED   motifs were identified with MEME"
        assert validate(rec, PAPER) == []

    def test_tool_keys_and_filing(self):
        assert key("MEGA X software") == "megax"
        assert key("GSDS 2.0") == "gsds"
        cols = file_tools(["GSDS", "PlantCARE", "ClustalW", "NotARealTool"], load_checklist())
        assert "GSDS" in cols["Other (Tools for Visualization)"]
        assert cols["Other tools (unlisted)"] == "NotARealTool"

    def test_scoring(self):
        for field, a, b, expected in [("Gene Family", "WRKY", "WRKY", 1.0),
                                      ("Number of Genes Identified", "136", "136 genes", 1.0),
                                      ("BLAST (E-value cut-off used)", "BLAST (1e-5)", "BLAST (1e-10)", 0.0),
                                      ("MEGA", "Yes", "No", 0.0)]:
            assert score(field, a, b) == expected, field

    def test_standardization(self):
        assert species_cell("Malus x domestica, chickpea") == "Malus domestica, Cicer arietinum"
        assert duplication_cell("Tandem, Fragment") == "Segmental, Tandem"
        assert duplication_cell("duplication") == "Type not named"
        assert std("SBP/SPL") == "SPL (SBP-box)"

    def test_ligature_repair(self):
        assert fix("identi cation of the WRKY family") == "identification of the WRKY family"

    def test_end_to_end(self):
        ws = Path(tempfile.mkdtemp()) / "ws"
        (ws / "papers").mkdir(parents=True)
        (ws / "papers" / "EX1.txt").write_text(PAPER, encoding="utf-8")
        run = lambda *a, **k: subprocess.run([sys.executable, *a], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", **k)
        r = run("scripts/record_extraction.py", str(ws), "EX1", input=json.dumps(RECORD))
        assert r.returncode == 0 and "SAVED EX1" in r.stdout
        r = run("scripts/assemble.py", str(ws))
        assert r.returncode == 0 and (ws / "extraction.csv").exists() and (ws / "evidence.csv").exists()
        r = run("scripts/standardize.py", str(ws / "extraction.csv"), str(ws / "standardized.csv"))
        assert r.returncode == 0
        r = run("scripts/compare.py", str(ws / "extraction.csv"), str(ws / "standardized.csv"), "--out", str(ws / "diff.csv"))
        assert r.returncode == 0 and "papers compared 1" in r.stdout


if __name__ == "__main__":
    unittest.main()
