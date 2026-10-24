"""Tests for skills/market-research/scripts/size.py."""
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "skills", "market-research", "scripts"))

import size  # noqa: E402

SPEC = {
    "unit": "offices",
    "inputs": {
        "buyers": {"value": 1000, "source": "https://example.gov/cbp"},
        "per_year": {"value": [2000, 3000], "assumption": "20 people x 2 lunches x 50 to 75 weeks"},
        "price": {"value": 9, "source": "founder"},
        "reachable": {"value": 0.3, "assumption": "inside delivery zone"},
        "win": {"value": 0.05, "assumption": "3-year share"},
    },
    "formula": {
        "TAM": "buyers * per_year * price",
        "SAM": "TAM * reachable",
        "SOM": "SAM * win",
    },
}


class ComputeTests(unittest.TestCase):
    def test_ranges_flow_through(self):
        res = size.compute(SPEC)
        r = {x["name"]: x for x in res["results"]}
        self.assertEqual(r["TAM"]["value"], (18000000.0, 27000000.0))
        self.assertAlmostEqual(r["SAM"]["value"][0], 5400000.0)
        self.assertAlmostEqual(r["SOM"]["value"][1], 405000.0)

    def test_assumptions_traced_through_results(self):
        res = size.compute(SPEC)
        r = {x["name"]: x for x in res["results"]}
        self.assertEqual(r["TAM"]["assumptions_used"], ["per_year"])
        self.assertEqual(r["SOM"]["assumptions_used"], ["per_year", "reachable", "win"])

    def test_unsourced_input_rejected(self):
        bad = json.loads(json.dumps(SPEC))
        bad["inputs"]["buyers"] = {"value": 1000}
        with self.assertRaises(size.SizeError) as cm:
            size.compute(bad)
        self.assertIn("no source", str(cm.exception))

    def test_unknown_name_rejected(self):
        bad = json.loads(json.dumps(SPEC))
        bad["formula"] = {"TAM": "buyers * cost"}
        with self.assertRaises(size.SizeError):
            size.compute(bad)

    def test_no_code_execution(self):
        bad = json.loads(json.dumps(SPEC))
        bad["formula"] = {"TAM": "__import__('os').system('echo hi')"}
        with self.assertRaises(size.SizeError):
            size.compute(bad)

    def test_divide_by_zero_range(self):
        bad = {"inputs": {"a": {"value": 1, "source": "x"}, "b": {"value": [0, 2], "source": "x"}},
               "formula": {"r": "a / b"}}
        with self.assertRaises(size.SizeError):
            size.compute(bad)

    def test_reversed_range_is_sorted(self):
        self.assertEqual(size.as_range([5, 2]), (2.0, 5.0))

    def test_constants_allowed(self):
        spec = {"inputs": {"people": {"value": 20, "source": "x"}}, "formula": {"lunches": "people * 2 * 50"}}
        self.assertEqual(size.compute(spec)["results"][0]["value"], (2000.0, 2000.0))


class FormatTests(unittest.TestCase):
    def test_money(self):
        self.assertEqual(size.money(18000000), "$18.0M")
        self.assertEqual(size.money(2.5e9), "$2.5B")
        self.assertEqual(size.money(950), "$950")
        self.assertEqual(size.money(1500, "EUR"), "€1.5K")

    def test_markdown_labels_guesses(self):
        md = size.to_markdown(size.compute(SPEC))
        self.assertIn("ASSUMPTION: inside delivery zone", md)
        self.assertIn("https://example.gov/cbp", md)
        self.assertIn("$18.0M to $27.0M", md)
        self.assertIn("Assumptions to test", md)
        self.assertIn("30%", md)

    def test_top_down_without_value(self):
        spec = dict(SPEC, top_down=[{"label": "Industry report", "source": ""}])
        md = size.to_markdown(size.compute(spec))
        self.assertIn("{{source needed}}", md)


class CliTests(unittest.TestCase):
    def test_cli_out(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "in.json")
            out = os.path.join(d, "out.md")
            with open(src, "w") as fh:
                json.dump(SPEC, fh)
            with redirect_stdout(io.StringIO()):
                self.assertEqual(size.main([src, "--out", out]), 0)
            with open(out) as fh:
                self.assertIn("Bottom-up sizing", fh.read())

    def test_cli_error(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "in.json")
            with open(src, "w") as fh:
                fh.write("{not json")
            err = io.StringIO()
            with redirect_stderr(err):
                self.assertEqual(size.main([src]), 1)


if __name__ == "__main__":
    unittest.main()
