"""Tests for skills/customer-discovery/scripts/evidence.py."""
import csv
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "skills", "customer-discovery", "scripts"))

import evidence  # noqa: E402

LOG = """# Evidence log

## Interview: Dana, office manager, 60-person law firm (date: 2026-10-20)
- Problem: ordering lunch for the team takes an hour every week | strength: strong
- Current solution: calls three restaurants | pays: about $15 a head
- Quote: "I spend my Tuesday morning on the phone."
- Signal: committed | gave intro to the office manager next door
- Price: too_cheap=5, cheap=9, expensive=16, too_expensive=22

## Interview: Raj, ops lead, 25-person studio (date: 2026-10-21)
- Problem: ordering lunch for the team takes an hour every week | strength: medium
- Problem: dietary needs get missed | strength: strong
- Current solution: DoorDash group order
- Quote: "Someone always gets the wrong thing."
- Signal: interested
- Price: too_cheap=6, cheap=10, expensive=14

## Interview: Kim, founder
- Problem: nothing really
- Signal: none
- Price: too_cheap=20, cheap=10, expensive=8, too_expensive=5
"""


class ParseTests(unittest.TestCase):
    def setUp(self):
        self.iv = evidence.parse(LOG)

    def test_three_interviews(self):
        self.assertEqual(len(self.iv), 3)
        self.assertEqual(self.iv[0]["who"], "Dana, office manager, 60-person law firm")
        self.assertEqual(self.iv[0]["date"], "2026-10-20")

    def test_fields(self):
        d = self.iv[0]
        self.assertEqual(d["problems"][0]["strength"], "strong")
        self.assertEqual(d["pays"], ["about $15 a head"])
        self.assertEqual(d["quotes"], ["I spend my Tuesday morning on the phone."])
        self.assertEqual(d["signal"], "committed")
        self.assertIn("intro", d["signal_note"])
        self.assertEqual(d["price"]["too_expensive"], 22.0)

    def test_free_text_date_kept(self):
        iv = evidence.parse("## Interview: Marco (date: oct 14, year not in notes)\n")
        self.assertEqual(iv[0]["date"], "oct 14, year not in notes")
        iv = evidence.parse("## Interview: Marco (date: YYYY-MM-DD)\n")
        self.assertEqual(iv[0]["date"], "")

    def test_unknown_signal_blank(self):
        iv = evidence.parse("## Interview: X (date: 2026-01-01)\n- Signal: maybe\n")
        self.assertEqual(iv[0]["signal"], "")


class SummaryTests(unittest.TestCase):
    def test_counts_and_gaps(self):
        res = evidence.summary(evidence.parse(LOG))
        self.assertEqual(res["interviews"], 3)
        self.assertEqual(res["signals"]["committed"], 1)
        top, count = res["problems"][0]
        self.assertIn("ordering lunch", top)
        self.assertEqual(count, 2)
        gaps = " ".join(res["gaps"])
        self.assertIn("Kim, founder: no date", gaps)
        self.assertIn("Kim, founder: no direct quote", gaps)
        self.assertIn("Raj, ops lead, 25-person studio: price answers incomplete (3 of 4)", gaps)
        self.assertIn("Too few interviews", res["read"])

    def test_empty(self):
        self.assertEqual(evidence.summary([])["read"], "No interviews logged yet.")

    def test_no_commitment_read(self):
        log = "".join("## Interview: P%d (date: 2026-01-0%d)\n- Signal: interested\n- Quote: \"ok\"\n" % (i, i) for i in range(1, 7))
        self.assertIn("No one has committed", evidence.summary(evidence.parse(log))["read"])


class PriceTests(unittest.TestCase):
    def test_rows_and_drops(self):
        rows, dropped = evidence.price_rows(evidence.parse(LOG))
        self.assertEqual(rows, [[5.0, 9.0, 16.0, 22.0]])
        reasons = dict(dropped)
        self.assertEqual(reasons["Raj, ops lead, 25-person studio"], "missing answers")
        self.assertEqual(reasons["Kim, founder"], "answers out of order")

    def test_csv_matches_van_westendorp_columns(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "e.md")
            out = os.path.join(d, "p.csv")
            with open(src, "w") as fh:
                fh.write(LOG)
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(evidence.main(["prices", src, "--out", out]), 0)
            with open(out, newline="") as fh:
                rows = list(csv.DictReader(fh))
            self.assertEqual(list(rows[0].keys()), ["too_cheap", "cheap", "expensive", "too_expensive"])
            self.assertEqual(rows[0]["expensive"], "16")

    def test_dollar_and_decimal(self):
        iv = evidence.parse("## Interview: A\n- Price: too_cheap=$4.50, cheap=$8, expensive=$1,200, too_expensive=1500\n")
        self.assertEqual(iv[0]["price"]["too_cheap"], 4.5)
        self.assertEqual(iv[0]["price"]["expensive"], 1200.0)


class CliTests(unittest.TestCase):
    def test_summary_cli(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "e.md")
            with open(src, "w") as fh:
                fh.write(LOG)
            buf = io.StringIO()
            with redirect_stdout(buf):
                evidence.main(["summary", src])
            self.assertIn("Interviews: 3", buf.getvalue())
            self.assertIn("(1 strong)", buf.getvalue())

    def test_missing_file(self):
        err = io.StringIO()
        with redirect_stderr(err):
            self.assertEqual(evidence.main(["summary", "/no/such/file.md"]), 1)


if __name__ == "__main__":
    unittest.main()
