"""Tests for skills/validate/scripts/testplan.py."""
import copy
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "skills", "validate", "scripts"))

import testplan  # noqa: E402

PLAN = {
    "assumption": "Office managers will pre-pay for a second route",
    "tests": [
        {"name": "pre-order page", "type": "pre-order", "metric": "pre-orders",
         "denominator": "unique visitors", "pass_at": 0.05, "fail_below": 0.02,
         "min_sample": 200, "ends": "2026-11-15", "budget": 50},
        {"name": "concierge week", "type": "concierge", "metric": "offices that pay for week two",
         "pass_at": 3, "fail_below": 1, "ends": "2026-11-20"},
    ],
}


class CheckTests(unittest.TestCase):
    def test_good_plan(self):
        self.assertEqual(testplan.check_plan(PLAN), [])

    def test_missing_lines(self):
        p = copy.deepcopy(PLAN)
        del p["tests"][0]["pass_at"]
        self.assertTrue(any("pass_at" in x for x in testplan.check_plan(p)))

    def test_too_many_tests(self):
        p = copy.deepcopy(PLAN)
        p["tests"] = p["tests"] * 2
        probs = " ".join(testplan.check_plan(p))
        self.assertIn("1 to 3 tests", probs)
        self.assertIn("share this name", probs)

    def test_rate_must_be_fraction(self):
        p = copy.deepcopy(PLAN)
        p["tests"][0]["pass_at"] = 5
        p["tests"][0]["fail_below"] = 2
        self.assertTrue(any("rate between 0 and 1" in x for x in testplan.check_plan(p)))

    def test_fail_above_pass(self):
        p = copy.deepcopy(PLAN)
        p["tests"][1]["fail_below"] = 9
        self.assertTrue(any("higher than pass_at" in x for x in testplan.check_plan(p)))

    def test_bad_date_and_type(self):
        p = copy.deepcopy(PLAN)
        p["tests"][0]["ends"] = "next week"
        p["tests"][0]["type"] = "vibes"
        probs = " ".join(testplan.check_plan(p))
        self.assertIn("YYYY-MM-DD", probs)
        self.assertIn("type should be", probs)

    def test_needs_assumption(self):
        p = copy.deepcopy(PLAN)
        p["assumption"] = ""
        self.assertTrue(any("riskiest assumption" in x for x in testplan.check_plan(p)))


    def test_range_without_pick_refuses_lock(self):
        p = copy.deepcopy(PLAN)
        t = p["tests"][1]
        t.update({"pass_range": [10, 30], "fail_range": [3, 8], "pass_at": None, "fail_below": None})
        probs = " ".join(testplan.check_plan(p))
        self.assertIn("founder picks 'pass_at' from 10 to 30", probs)
        self.assertIn("founder picks 'fail_below' from 3 to 8", probs)
        with self.assertRaises(testplan.PlanError):
            testplan.lock(p, today="2026-10-24")

    def test_pick_inside_range_locks(self):
        p = copy.deepcopy(PLAN)
        p["tests"][1].update({"pass_range": [10, 30], "fail_range": [3, 8],
                              "pass_at": 15, "fail_below": 6})
        self.assertEqual(testplan.check_plan(p), [])
        testplan.lock(p, today="2026-10-24")
        self.assertTrue(p["tests"][1]["fingerprint"])

    def test_pick_outside_range_flagged(self):
        p = copy.deepcopy(PLAN)
        p["tests"][1].update({"pass_range": [10, 30], "pass_at": 5, "fail_below": 2})
        self.assertTrue(any("outside the range" in x for x in testplan.check_plan(p)))

    def test_bad_range_shape(self):
        p = copy.deepcopy(PLAN)
        p["tests"][1]["pass_range"] = [30, 10]
        self.assertTrue(any("[low, high]" in x for x in testplan.check_plan(p)))


class LockReadTests(unittest.TestCase):
    def locked(self):
        return testplan.lock(copy.deepcopy(PLAN), today="2026-10-23")

    def test_lock_stamps(self):
        p = self.locked()
        self.assertEqual(p["tests"][0]["locked_on"], "2026-10-23")
        self.assertEqual(len(p["tests"][0]["fingerprint"]), 12)

    def test_lock_refuses_bad_plan(self):
        p = copy.deepcopy(PLAN)
        del p["tests"][0]["fail_below"]
        with self.assertRaises(testplan.PlanError):
            testplan.lock(p)

    def test_pass_and_fail(self):
        res = testplan.read(self.locked(), {
            "pre-order page": {"count": 15, "denominator": 250},
            "concierge week": {"count": 0},
        })
        v = {t["name"]: t["verdict"] for t in res["tests"]}
        self.assertEqual(v["pre-order page"], "pass")
        self.assertEqual(v["concierge week"], "fail")
        self.assertIn("Mixed", res["overall"])

    def test_unclear_band(self):
        res = testplan.read(self.locked(), {"pre-order page": {"count": 7, "denominator": 250},
                                            "concierge week": {"count": 2}})
        self.assertEqual([t["verdict"] for t in res["tests"]], ["unclear", "unclear"])

    def test_too_early(self):
        res = testplan.read(self.locked(), {"pre-order page": {"count": 9, "denominator": 40},
                                            "concierge week": {"count": 3}})
        self.assertEqual(res["tests"][0]["verdict"], "too early")
        self.assertIn("Not every test", res["overall"])

    def test_no_data(self):
        res = testplan.read(self.locked(), {})
        self.assertEqual({t["verdict"] for t in res["tests"]}, {"no data"})

    def test_moved_lines_detected(self):
        p = self.locked()
        p["tests"][0]["pass_at"] = 0.01
        res = testplan.read(p, {"pre-order page": {"count": 3, "denominator": 250},
                                "concierge week": {"count": 3}})
        self.assertTrue(res["tests"][0]["lines_moved"])
        self.assertIn("changed after the plan was locked", res["overall"])

    def test_unlocked_plan_is_soft(self):
        res = testplan.read(copy.deepcopy(PLAN), {"pre-order page": {"count": 15, "denominator": 250},
                                                  "concierge week": {"count": 4}})
        self.assertIn("never locked", res["overall"])

    def test_all_pass(self):
        res = testplan.read(self.locked(), {"pre-order page": {"count": 15, "denominator": 250},
                                            "concierge week": {"count": 4}})
        self.assertIn("go", res["overall"])

    def test_extra_fields_do_not_change_fingerprint(self):
        p = self.locked()
        fp = p["tests"][0]["fingerprint"]
        p["tests"][0]["budget"] = 500
        p["tests"][0]["ends"] = "2026-12-01"
        self.assertEqual(testplan.fingerprint(p["tests"][0]), fp)


class CliTests(unittest.TestCase):
    def test_lock_then_read(self):
        with tempfile.TemporaryDirectory() as d:
            plan = os.path.join(d, "plan.json")
            results = os.path.join(d, "r.json")
            with open(plan, "w") as fh:
                json.dump(PLAN, fh)
            with open(results, "w") as fh:
                json.dump({"pre-order page": {"count": 15, "denominator": 250}, "concierge week": {"count": 0}}, fh)
            with redirect_stdout(io.StringIO()):
                self.assertEqual(testplan.main(["lock", plan]), 0)
            buf = io.StringIO()
            with redirect_stdout(buf):
                testplan.main(["read", plan, results])
            self.assertIn("pre-order page: PASS", buf.getvalue())
            self.assertIn("concierge week: FAIL", buf.getvalue())

    def test_lock_bad_plan_exit_2(self):
        with tempfile.TemporaryDirectory() as d:
            plan = os.path.join(d, "plan.json")
            with open(plan, "w") as fh:
                json.dump({"tests": []}, fh)
            with redirect_stderr(io.StringIO()):
                self.assertEqual(testplan.main(["lock", plan]), 2)


if __name__ == "__main__":
    unittest.main()
