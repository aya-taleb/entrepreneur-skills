"""Tests for skills/humanize/scripts (detect.py, humanize.py, lexicon.json)."""
import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock
from contextlib import redirect_stdout, redirect_stderr

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPTS = os.path.join(ROOT, "skills", "humanize", "scripts")
sys.path.insert(0, SCRIPTS)

import detect  # noqa: E402
import humanize  # noqa: E402

HOUSE_BANNED = [
    "delve", "leverage", "seamless", "streamline", "comprehensive", "journey", "unlock",
    "elevate", "empower", "foster", "thoughtful", "relatable", "humor", "storytelling",
    "simple", "robust", "crucial", "utilize", "synergy", "cutting-edge", "game-changer",
    "revolutionize", "tapestry", "testament", "moreover", "furthermore",
]
HOUSE_PHRASES = ["in today's fast-paced world", "let's dive in"]

HUMAN = (
    "Shipped the export fix today. Took three tries.\n\n"
    "The bug was dumb: we rounded totals before summing, so big invoices drifted by a "
    "cent or two. A customer in Tacoma caught it, not us.\n\n"
    "If you saw a weird total last week, that was it. Sorry. It is fixed now, and I "
    "added a test so it stays fixed.\n"
)
MACHINE = (
    "In today’s fast-paced world, founders need tools that truly work.\n\n"
    "I’m thrilled to announce our new app — a game-changer for small teams. "
    "It’s not just a planner. It’s a movement.\n\n"
    "Our comprehensive platform leverages cutting-edge AI to streamline your workflow "
    "seamlessly. Moreover, it empowers teams to unlock their full potential.\n\n"
    "Thoughts?\n"
)


def checks(result):
    return {c["id"]: c for c in result["checks"]}


class LexiconTests(unittest.TestCase):
    def setUp(self):
        self.lex = detect.load_lexicon()

    def test_every_house_word_is_banned(self):
        words = {e["word"] for e in self.lex["banned"]}
        for w in HOUSE_BANNED:
            self.assertIn(w, words)
        phrases = {e["text"] for e in self.lex["banned_phrases"]}
        for p in HOUSE_PHRASES:
            self.assertIn(p, phrases)

    def test_every_entry_has_a_replacement(self):
        for group in ("banned", "stock"):
            for e in self.lex[group]:
                self.assertTrue(e.get("use"), e)
                self.assertTrue(e.get("forms"), e)
                self.assertIn(e["word"].lower(), [f.lower() for f in e["forms"]] + [e["word"].lower()])
        for group in ("banned_phrases", "phrases"):
            for e in self.lex[group]:
                self.assertTrue(e.get("use"), e)

    def test_no_word_in_two_lists(self):
        banned = {f for e in self.lex["banned"] for f in e["forms"]}
        stock = {f for e in self.lex["stock"] for f in e["forms"]}
        self.assertEqual(banned & stock, set())

    def test_phrases_are_lowercase(self):
        for e in self.lex["phrases"] + self.lex["banned_phrases"]:
            self.assertEqual(e["text"], e["text"].lower())
        for o in self.lex["openers"]:
            self.assertEqual(o, o.lower())


class DetectTests(unittest.TestCase):
    def test_human_text_scores_high(self):
        r = detect.analyze(HUMAN)
        self.assertGreaterEqual(r["score"], 90, detect.format_report(r))

    def test_machine_text_scores_low(self):
        r = detect.analyze(MACHINE)
        self.assertLess(r["score"], 55)
        c = checks(r)
        self.assertGreater(c["banned"]["points_lost"], 0)
        self.assertGreater(c["dashes"]["points_lost"], 0)
        self.assertGreater(c["open_close"]["points_lost"], 0)
        self.assertGreater(c["contrast"]["points_lost"], 0)

    def test_score_is_bounded(self):
        r = detect.analyze(MACHINE * 10)
        self.assertGreaterEqual(r["score"], 0)
        self.assertLessEqual(r["score"], 100)

    def test_word_forms_are_caught(self):
        r = detect.analyze("We leveraged it. They are leveraging it. Utilising this is odd.")
        found = " ".join(checks(r)["banned"]["found"])
        self.assertIn("'leverage' x2", found)
        self.assertIn("'utilize' x1", found)

    def test_no_false_hit_inside_other_words(self):
        # "simpleton" should not count as "simple"; "fostering" should count as "foster".
        r = detect.analyze("He is no simpleton. Fosterville is a town.")
        self.assertEqual(checks(r)["banned"]["points_lost"], 0)

    def test_curly_apostrophe_still_matches_phrase(self):
        r = detect.analyze("In today’s fast-paced world we ship.")
        found = " ".join(checks(r)["banned"]["found"])
        self.assertIn("in today's fast-paced world", found)

    def test_links_and_code_are_not_judged(self):
        r = detect.analyze("See https://seamless.example.com/leverage and `robust_mode`.")
        self.assertEqual(checks(r)["banned"]["points_lost"], 0)

    def test_extra_banned_words(self):
        r = detect.analyze("We hustle every day and crush it.", extra_banned=["hustle", "crush it"])
        c = checks(r)["banned"]
        self.assertEqual(c["points_lost"], 12)
        self.assertIn("from your business file", " ".join(c["found"]))

    def test_hidden_characters(self):
        r = detect.analyze("Hello​ world.﻿ Next line.")
        c = checks(r)["hidden"]
        self.assertEqual(c["points_lost"], 10)
        self.assertEqual(len(c["found"]), 3)

    def test_emoji_joiner_is_not_hidden(self):
        family = "\U0001f468‍\U0001f469‍\U0001f467"
        r = detect.analyze("Our team " + family + " grew this year.")
        self.assertEqual(checks(r)["hidden"]["points_lost"], 0)

    def test_rtl_direction_marks_kept(self):
        r = detect.analyze("مرحبا ‏ friends.")
        self.assertEqual(checks(r)["hidden"]["points_lost"], 0)

    def test_long_sentence(self):
        s = " ".join(["word"] * 30) + "."
        r = detect.analyze(s)
        self.assertEqual(checks(r)["long_sentences"]["points_lost"], 3)

    def test_flat_rhythm(self):
        flat = " ".join(["We built the thing for small teams today."] * 8)
        r = detect.analyze(flat)
        self.assertGreater(checks(r)["rhythm"]["points_lost"], 0)

    def test_varied_rhythm_passes(self):
        r = detect.analyze(HUMAN)
        self.assertEqual(checks(r)["rhythm"]["points_lost"], 0)

    def test_fragments(self):
        r = detect.analyze("We tried everything. Fast. Cheap. Done. Then we slept for a week straight.")
        self.assertGreater(checks(r)["fragments"]["points_lost"], 0)

    def test_contrast_two_sentences(self):
        r = detect.analyze("This isn't a tool. It's a movement.")
        self.assertGreater(checks(r)["contrast"]["points_lost"], 0)

    def test_contrast_not_just_but(self):
        r = detect.analyze("It is not just faster, but also cheaper to run.")
        self.assertGreater(checks(r)["contrast"]["points_lost"], 0)

    def test_markdown_flag_and_allow(self):
        text = "**Big news** we shipped.\n# Header\nMore text here."
        self.assertGreater(checks(detect.analyze(text))["markdown"]["points_lost"], 0)
        self.assertEqual(checks(detect.analyze(text, allow_markdown=True))["markdown"]["points_lost"], 0)

    def test_emoji_bullets_and_bangs(self):
        text = "✅ one\n✅ two\n✅ three\nWow! Great! Amazing! Yes!"
        c = checks(detect.analyze(text))["noise"]
        self.assertGreater(c["points_lost"], 0)
        self.assertEqual(len(c["found"]), 2)

    def test_every_check_explains_itself(self):
        r = detect.analyze(MACHINE)
        for c in r["checks"]:
            self.assertTrue(c["why"] and c["fix"] and c["title"], c["id"])
        report = detect.format_report(r)
        self.assertIn("Why it matters:", report)
        self.assertIn("Fix:", report)
        self.assertIn("do not call any AI", report)

    def test_greeting_then_stock_opener(self):
        r = detect.analyze("Hi Sam,\nI hope this email finds you well.\nQuick question about invoices.")
        self.assertGreater(checks(r)["open_close"]["points_lost"], 0)


class ContextTests(unittest.TestCase):
    def write(self, folder, rel, text):
        path = os.path.join(folder, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path

    def test_inline_words_to_avoid(self):
        with tempfile.TemporaryDirectory() as d:
            p = self.write(d, "b.md", "# Biz\n\n- Words to avoid: hustle, guru, \"crush it\"\n")
            self.assertEqual(detect.read_avoid_words(p), ["hustle", "guru", "crush it"])

    def test_bold_label(self):
        with tempfile.TemporaryDirectory() as d:
            p = self.write(d, "b.md", "**Words to avoid:** cheap; deal\n")
            self.assertEqual(detect.read_avoid_words(p), ["cheap", "deal"])

    def test_heading_list(self):
        with tempfile.TemporaryDirectory() as d:
            p = self.write(d, "b.md", "## Words to avoid\n- foodie\n- yummy\n\n## Proof\n- 40 subscribers\n")
            self.assertEqual(detect.read_avoid_words(p), ["foodie", "yummy"])

    def test_placeholder_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            p = self.write(d, "b.md", "Words to avoid: {{your words}}\n")
            self.assertEqual(detect.read_avoid_words(p), [])

    def test_find_context_prefers_project_file(self):
        with tempfile.TemporaryDirectory() as proj, tempfile.TemporaryDirectory() as fh, \
                mock.patch.dict(os.environ, {"FOUNDER_HOME": fh}):
            self.write(fh, "active", "lunchbox\n")
            biz = self.write(fh, "businesses/lunchbox.md", "Words to avoid: yum\n")
            self.assertEqual(detect.find_context_file(proj), biz)
            local = self.write(proj, "founder/context.md", "Words to avoid: zap\n")
            self.assertEqual(detect.find_context_file(proj), local)

    def test_default_home_is_dot_founder(self):
        with tempfile.TemporaryDirectory() as proj, tempfile.TemporaryDirectory() as home, \
                mock.patch.dict(os.environ):
            os.environ.pop("FOUNDER_HOME", None)
            self.write(home, ".founder/active", "lunchbox\n")
            biz = self.write(home, ".founder/businesses/lunchbox.md", "Words to avoid: yum\n")
            self.assertEqual(detect.find_context_file(proj, home), biz)

    def test_bad_slug_is_ignored(self):
        with tempfile.TemporaryDirectory() as proj, tempfile.TemporaryDirectory() as fh, \
                mock.patch.dict(os.environ, {"FOUNDER_HOME": fh}):
            self.write(fh, "active", "../../etc/passwd\n")
            self.assertIsNone(detect.find_context_file(proj))

    def test_cli_reads_context(self):
        with tempfile.TemporaryDirectory() as d:
            ctx = self.write(d, "ctx.md", "Words to avoid: hustle\n")
            draft = self.write(d, "draft.txt", "We hustle hard.\n")
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = detect.main([draft, "--context", ctx, "--json"])
            self.assertEqual(code, 0)
            data = json.loads(buf.getvalue())
            self.assertEqual(data["extra_banned"], ["hustle"])
            self.assertLess(data["score"], 100)


class CleanTests(unittest.TestCase):
    def test_removes_hidden_and_odd_spaces(self):
        out, counts = humanize.clean("Hi​ there friend.﻿")
        self.assertEqual(out, "Hi there friend.")
        self.assertIn("hidden characters removed", counts)

    def test_dash_mid_sentence_becomes_comma(self):
        out, _ = humanize.clean("We shipped it — finally.")
        self.assertEqual(out, "We shipped it, finally.")

    def test_dash_without_spaces(self):
        out, _ = humanize.clean("Fast—and cheap.")
        self.assertEqual(out, "Fast, and cheap.")

    def test_dash_range_becomes_hyphen(self):
        out, _ = humanize.clean("From 2019—2021 we grew.")
        self.assertEqual(out, "From 2019-2021 we grew.")

    def test_dash_before_list_becomes_colon(self):
        out, _ = humanize.clean("Three things —\n- one\n- two")
        self.assertEqual(out, "Three things:\n- one\n- two")

    def test_dash_bullet(self):
        out, _ = humanize.clean("— first point\n— second point")
        self.assertEqual(out, "- first point\n- second point")

    def test_double_hyphen(self):
        out, _ = humanize.clean("It works -- mostly.")
        self.assertEqual(out, "It works, mostly.")

    def test_dash_before_period_does_not_leave_comma(self):
        out, _ = humanize.clean("We did it —.")
        self.assertEqual(out, "We did it.")

    def test_quotes_and_ellipsis(self):
        out, _ = humanize.clean("“It’s fine…” she said.")
        self.assertEqual(out, "\"It's fine...\" she said.")

    def test_code_and_links_untouched(self):
        src = "Run `a—b` and see https://x.com/a—b — done."
        out, _ = humanize.clean(src)
        self.assertIn("`a—b`", out)
        self.assertIn("https://x.com/a—b", out)
        self.assertTrue(out.endswith(", done."))

    def test_handles_and_hashtags_untouched(self):
        out, _ = humanize.clean("Thanks @aya— and #buildinpublic")
        self.assertIn("@aya", out)
        self.assertIn("#buildinpublic", out)

    def test_swap_words_keeps_case(self):
        out, _ = humanize.clean("Utilize it. We utilized it in order to win.", swap=True)
        self.assertEqual(out, "Use it. We used it to win.")

    def test_no_swap_by_default(self):
        out, _ = humanize.clean("We utilize it.")
        self.assertEqual(out, "We utilize it.")

    def test_strip_markdown(self):
        out, _ = humanize.clean("**Big** news\n## Title\ntext", markdown=True)
        self.assertEqual(out, "Big news\nTitle\ntext")

    def test_keeps_line_breaks_and_indent(self):
        src = "Line one.\n\n  - indented item\nLine  two."
        out, _ = humanize.clean(src)
        self.assertEqual(out, "Line one.\n\n  - indented item\nLine two.")

    def test_rtl_text_kept(self):
        src = "مرحبا‏ friends"
        out, _ = humanize.clean(src)
        self.assertEqual(out, src)

    def test_emoji_sequence_kept(self):
        fam = "\U0001f468‍\U0001f469‍\U0001f467"
        out, _ = humanize.clean("Team " + fam)
        self.assertEqual(out, "Team " + fam)

    def test_clean_is_idempotent(self):
        once, _ = humanize.clean(MACHINE, swap=True)
        twice, counts = humanize.clean(once, swap=True)
        self.assertEqual(once, twice)
        self.assertEqual(counts, {})

    def test_cleaning_raises_score(self):
        before = detect.analyze(MACHINE)["score"]
        after = detect.analyze(humanize.clean(MACHINE)[0])["score"]
        self.assertGreater(after, before)

    def test_meaning_words_kept(self):
        out, _ = humanize.clean(MACHINE)
        for word in ("founders", "planner", "movement", "teams", "Thoughts?"):
            self.assertIn(word, out)


class CliTests(unittest.TestCase):
    def test_out_file_and_report(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "draft.txt")
            dst = os.path.join(d, "clean.txt")
            with open(src, "w", encoding="utf-8") as fh:
                fh.write(MACHINE)
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = humanize.main([src, "--out", dst, "--no-context"])
            self.assertEqual(code, 0)
            with open(dst, encoding="utf-8") as fh:
                self.assertNotIn("—", fh.read())
            self.assertIn("Before:", buf.getvalue())

    def test_in_place_keeps_backup(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "draft.txt")
            with open(src, "w", encoding="utf-8") as fh:
                fh.write("A — B")
            with redirect_stdout(io.StringIO()):
                humanize.main([src, "--in-place", "--no-context"])
            self.assertTrue(os.path.exists(src + ".bak"))
            with open(src, encoding="utf-8") as fh:
                self.assertEqual(fh.read(), "A, B")

    def test_empty_input_fails_kindly(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "empty.txt")
            open(src, "w").close()
            err = io.StringIO()
            with redirect_stderr(err):
                code = detect.main([src, "--no-context"])
            self.assertEqual(code, 1)
            self.assertIn("empty", err.getvalue())

    def test_min_score_exit_code(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "draft.txt")
            with open(src, "w", encoding="utf-8") as fh:
                fh.write(MACHINE)
            with redirect_stdout(io.StringIO()):
                code = detect.main([src, "--no-context", "--min-score", "90"])
            self.assertEqual(code, 2)


class CompareTests(unittest.TestCase):
    def test_same_facts(self):
        a = "We hit 212 teams in March. See https://tallyapp.io for more."
        b = "212 teams signed up in March. More at https://tallyapp.io"
        c = detect.compare(a, b)
        self.assertEqual(c["dropped_numbers"], [])
        self.assertEqual(c["added_numbers"], [])
        self.assertEqual(c["dropped_links"], [])
        self.assertEqual(c["dropped_names"], [])

    def test_added_number_and_name(self):
        c = detect.compare("We saved teams time.", "We saved 40 teams at Acme about 3.5 hours.")
        self.assertIn("40", c["added_numbers"])
        self.assertIn("3.5", c["added_numbers"])
        self.assertIn("Acme", c["added_names"])

    def test_dropped_link(self):
        c = detect.compare("Try it at https://x.io today.", "Try it today.")
        self.assertEqual(c["dropped_links"], ["https://x.io"])

    def test_name_moved_to_sentence_start_not_dropped(self):
        c = detect.compare("Today we launch Tally for teams.", "Tally launches today.")
        self.assertEqual(c["dropped_names"], [])

    def test_new_words_listed(self):
        c = detect.compare("We ship fast.", "We ship fast and guarantee results.")
        self.assertIn("guarantee", c["new_words"])

    def test_placeholders_ignored(self):
        c = detect.compare("Join us.", "Join us as {{Role Title}} in {{City}}.")
        self.assertEqual(c["added_names"], [])

    def test_cli_compare(self):
        with tempfile.TemporaryDirectory() as d:
            a = os.path.join(d, "a.txt")
            b = os.path.join(d, "b.txt")
            with open(a, "w") as fh:
                fh.write("We have 6 offices.")
            with open(b, "w") as fh:
                fh.write("We have 9 offices.")
            buf = io.StringIO()
            with redirect_stdout(buf):
                detect.main([b, "--compare", a, "--no-context"])
            out = buf.getvalue()
            self.assertIn("Dropped numbers: 6", out)
            self.assertIn("Added numbers: 9", out)


if __name__ == "__main__":
    unittest.main()
