"""Tests for skills/founder-context/scripts/context.py."""
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "skills", "founder-context", "scripts"))

import context  # noqa: E402

FULL = """# Tally

- Name: Tally
- One-line pitch: Shared to-do lists for small agencies.
- Who it serves: agency owners with 3 to 15 people
- Stage: beta, 212 teams

## Goals
- 50 paying teams by June

## Topics
- async work

## Tone
- Tone words: direct, warm, dry
- Words to avoid: hustle, crush it

## Proof I can use
- 212 beta teams (source: our dashboard, March 2026)

## Off-limits
- client names
"""


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = os.path.join(self.tmp.name, "home")
        self.proj = os.path.join(self.tmp.name, "proj")
        os.makedirs(self.home)
        os.makedirs(self.proj)
        # Every test uses a temp FOUNDER_HOME, so nothing touches the real ~/.founder.
        self.fh = os.path.join(self.tmp.name, "founder-home")
        self._old_env = os.environ.get("FOUNDER_HOME")
        os.environ["FOUNDER_HOME"] = self.fh

    def tearDown(self):
        if self._old_env is None:
            os.environ.pop("FOUNDER_HOME", None)
        else:
            os.environ["FOUNDER_HOME"] = self._old_env
        self.tmp.cleanup()

    def put(self, rel, text, root=None):
        if rel.startswith("FH/"):
            rel, root = rel[3:], self.fh
        p = os.path.join(root or self.home, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
        return p


class WhereTests(Base):
    def test_nothing(self):
        path, why = context.where(self.proj, self.home)
        self.assertIsNone(path)
        self.assertIn("no business file", why)

    def test_active(self):
        p = self.put("FH/businesses/tally.md", FULL)
        self.put("FH/active", "tally\n")
        self.assertEqual(context.where(self.proj, self.home)[0], p)

    def test_project_overrides(self):
        self.put("FH/businesses/tally.md", FULL)
        self.put("FH/active", "tally\n")
        local = self.put("founder/context.md", FULL, root=self.proj)
        self.assertEqual(context.where(self.proj, self.home)[0], local)

    def test_single_business_without_active(self):
        p = self.put("FH/businesses/tally.md", FULL)
        path, why = context.where(self.proj, self.home)
        self.assertEqual(path, p)
        self.assertIn("no active", why)

    def test_several_without_active(self):
        self.put("FH/businesses/a.md", FULL)
        self.put("FH/businesses/b.md", FULL)
        path, why = context.where(self.proj, self.home)
        self.assertIsNone(path)
        self.assertIn("none is active", why)

    def test_active_points_nowhere(self):
        self.put("FH/active", "ghost\n")
        path, why = context.where(self.proj, self.home)
        self.assertIsNone(path)
        self.assertIn("does not exist", why)

    def test_unsafe_slug_rejected(self):
        self.put("FH/active", "../../etc\n")
        self.assertIsNone(context.active_slug(self.home))


class FounderHomeTests(Base):
    def test_env_wins(self):
        self.assertEqual(context.founder_dir(self.home), self.fh)
        p = context.new("tally", home=self.home)
        self.assertTrue(p.startswith(self.fh + os.sep))

    def test_default_is_dot_founder_not_claude(self):
        os.environ.pop("FOUNDER_HOME")
        self.assertEqual(context.founder_dir(self.home), os.path.join(self.home, ".founder"))
        self.assertNotIn(".claude", context.founder_dir(self.home))


class MigrateTests(Base):
    def setUp(self):
        super().setUp()
        os.environ.pop("FOUNDER_HOME")
        self.old = os.path.join(self.home, ".claude", "founder")
        self.new = os.path.join(self.home, ".founder")

    def test_nothing_to_move(self):
        self.assertFalse(context.migrate_status(self.home)[2])
        with self.assertRaises(LookupError):
            context.migrate(self.home)

    def test_copies_and_keeps_old(self):
        self.put(os.path.join(self.old, "businesses", "tally.md"), FULL)
        self.put(os.path.join(self.old, "active"), "tally\n")
        self.assertTrue(context.migrate_status(self.home)[2])
        buf = io.StringIO()
        with redirect_stdout(buf):
            context.main(["where"], cwd=self.proj, home=self.home)
        self.assertIn("older version", buf.getvalue())
        with redirect_stdout(io.StringIO()):
            self.assertEqual(context.main(["migrate"], home=self.home), 0)
        self.assertTrue(os.path.isfile(os.path.join(self.new, "businesses", "tally.md")))
        self.assertTrue(os.path.isfile(os.path.join(self.old, "active")))
        self.assertEqual(context.where(self.proj, self.home)[0],
                         os.path.join(self.new, "businesses", "tally.md"))

    def test_never_overwrites_new(self):
        self.put(os.path.join(self.old, "active"), "tally\n")
        self.put(os.path.join(self.new, "active"), "other\n")
        self.assertFalse(context.migrate_status(self.home)[2])
        with self.assertRaises(FileExistsError):
            context.migrate(self.home)

    def test_dry_run_writes_nothing(self):
        self.put(os.path.join(self.old, "active"), "tally\n")
        with redirect_stdout(io.StringIO()):
            context.main(["migrate", "--dry-run"], home=self.home)
        self.assertFalse(os.path.exists(self.new))


class NewUseTests(Base):
    def test_new_then_use(self):
        p = context.new("back-street-lunch", "Back Street Lunch", home=self.home)
        with open(p) as fh:
            text = fh.read()
        self.assertIn("# Back Street Lunch", text)
        self.assertIn("Slug: back-street-lunch", text)
        context.use("back-street-lunch", home=self.home)
        self.assertEqual(context.active_slug(self.home), "back-street-lunch")

    def test_new_will_not_overwrite(self):
        context.new("tally", home=self.home)
        with self.assertRaises(FileExistsError):
            context.new("tally", home=self.home)

    def test_new_project_file(self):
        p = context.new("tally", "Tally", project=True, cwd=self.proj, home=self.home)
        self.assertEqual(p, os.path.join(self.proj, "founder", "context.md"))

    def test_bad_slug(self):
        with self.assertRaises(ValueError):
            context.new("Bad Slug!", home=self.home)

    def test_use_unknown(self):
        with self.assertRaises(LookupError):
            context.use("nope", home=self.home)

    def test_list_marks_active(self):
        context.new("a", home=self.home)
        context.new("b", home=self.home)
        context.use("b", home=self.home)
        buf = io.StringIO()
        with redirect_stdout(buf):
            context.main(["list"], home=self.home)
        self.assertIn("* b", buf.getvalue())
        self.assertIn("  a", buf.getvalue())

    def test_make_slug(self):
        self.assertEqual(context.make_slug("Back Street Lunch!"), "back-street-lunch")
        self.assertEqual(context.make_slug("   "), "business")


class FieldTests(unittest.TestCase):
    def test_inline_and_heading_fields(self):
        self.assertEqual(context.get_field(FULL, "Name"), "Tally")
        self.assertEqual(context.get_field(FULL, "Goals"), "50 paying teams by June")
        self.assertEqual(context.get_field(FULL, "Words to avoid"), "hustle, crush it")
        self.assertEqual(context.get_field(FULL, "Off-limits"), "client names")

    def test_complete_file_has_no_gaps(self):
        self.assertEqual(context.check(FULL), [])

    def test_template_is_all_gaps(self):
        with open(context.TEMPLATE) as fh:
            text = fh.read()
        labels = {f for f, _ in context.check(text)}
        for label, required in context.FIELDS:
            if required:
                self.assertIn(label, labels)

    def test_proof_without_source_flagged(self):
        text = FULL.replace("212 beta teams (source: our dashboard, March 2026)", "212 beta teams")
        self.assertIn(("Proof I can use", "no source noted for: 212 beta teams"), context.check(text))

    def test_humanize_reads_same_words(self):
        sys.path.insert(0, os.path.join(ROOT, "skills", "humanize", "scripts"))
        import detect
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "t.md")
            with open(p, "w") as fh:
                fh.write(FULL)
            self.assertEqual(detect.read_avoid_words(p), ["hustle", "crush it"])

    def test_template_works_with_humanize(self):
        sys.path.insert(0, os.path.join(ROOT, "skills", "humanize", "scripts"))
        import detect
        self.assertEqual(detect.read_avoid_words(context.TEMPLATE), [])


class CliTests(Base):
    def test_where_exit_code(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(context.main(["where"], cwd=self.proj, home=self.home), 3)

    def test_check_cli(self):
        p = self.put("x.md", FULL)
        buf = io.StringIO()
        with redirect_stdout(buf):
            context.main(["check", p], home=self.home)
        self.assertIn("looks complete", buf.getvalue())

    def test_new_cli_refuses_overwrite(self):
        with redirect_stdout(io.StringIO()):
            context.main(["new", "tally"], home=self.home)
        err = io.StringIO()
        with redirect_stderr(err):
            self.assertEqual(context.main(["new", "tally"], home=self.home), 1)
        self.assertIn("not overwriting", err.getvalue())


class SetFieldTests(Base):
    def test_set_inline(self):
        p = self.put("b.md", FULL + "\n## Notes\n- Updated: 2026-01-01\n")
        before, after = context.set_field(p, "Stage", "launched, 260 teams", today="2026-10-23")
        self.assertEqual(before, "beta, 212 teams")
        self.assertEqual(after, "launched, 260 teams")
        with open(p) as fh:
            text = fh.read()
        self.assertIn("Updated: 2026-10-23", text)
        self.assertIn("## Goals", text)

    def test_add_inline_list_keeps_old(self):
        p = self.put("b.md", FULL)
        _, after = context.set_field(p, "Words to avoid", "foodie, hustle", add=True)
        self.assertEqual(after, "hustle, crush it, foodie")

    def test_add_to_heading_list(self):
        p = self.put("b.md", FULL)
        _, after = context.set_field(p, "Proof I can use", "7 offices (source: founder, 2026-10-23)", add=True)
        self.assertIn("212 beta teams", after)
        self.assertIn("7 offices", after)
        with open(p) as fh:
            self.assertIn("## Off-limits\n- client names", fh.read())

    def test_set_heading_list_replaces(self):
        p = self.put("b.md", FULL)
        _, after = context.set_field(p, "Goals", "60 paying teams by July")
        self.assertEqual(after, "60 paying teams by July")

    def test_add_replaces_placeholder(self):
        p = self.put("b.md", "- Words to avoid: {{your words}}\n")
        _, after = context.set_field(p, "Words to avoid", "foodie", add=True)
        self.assertEqual(after, "foodie")

    def test_unknown_field(self):
        p = self.put("b.md", FULL)
        with self.assertRaises(LookupError):
            context.set_field(p, "Favourite colour", "blue")

    def test_cli_add_prints_before_after(self):
        p = self.put("b.md", FULL)
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(context.main(["add", "Words to avoid", "foodie", "--file", p], home=self.home), 0)
        self.assertIn("before: hustle, crush it", buf.getvalue())
        self.assertIn("after:  hustle, crush it, foodie", buf.getvalue())

    def test_humanize_sees_added_word(self):
        sys.path.insert(0, os.path.join(ROOT, "skills", "humanize", "scripts"))
        import detect
        p = self.put("b.md", FULL)
        context.set_field(p, "Words to avoid", "foodie", add=True)
        self.assertIn("foodie", detect.read_avoid_words(p))


class FromDraftTests(Base):
    def test_new_from_draft(self):
        draft = self.put("draft.md", FULL)
        path = context.new("tally", source=draft, home=self.home)
        with open(path) as fh:
            self.assertIn("212 beta teams", fh.read())

    def test_replace_keeps_backup(self):
        context.new("tally", home=self.home)
        draft = self.put("draft.md", FULL)
        path = context.new("tally", source=draft, replace=True, home=self.home)
        self.assertTrue(os.path.exists(path + ".bak"))

    def test_replace_needs_source(self):
        context.new("tally", home=self.home)
        with self.assertRaises(FileExistsError):
            context.new("tally", replace=True, home=self.home)


if __name__ == "__main__":
    unittest.main()
