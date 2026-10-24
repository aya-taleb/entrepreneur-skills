# Build notes

## Unfinished

- **competitors** is listed in `skills.json` as synced from biz-launch-skills, but that
  repo isn't built yet, so the folder isn't here. The README goal table already points
  to `/competitors`. Run the sync once biz-launch-skills exists:
  `python3 entrepreneur-skills/scripts/sync_shared.py --root <folder with all repos>`.
  A dry run shows every synced entry across the repos resolving to a home.
- **Web research was not tested.** Test runs had no web access, so market-research's
  "find and link real sources" path, and any trend research, ran only in its "can't
  browse, leave placeholders" form. Worth one manual run with search on.
- **Not tested end to end:** the full chain founder-context, market-research,
  customer-discovery, validate in one project. Each skill was tested alone with prepared
  input files.

## Needs Aya

- **Decide:** an intro from someone who has a *different* problem is logged as
  "committed" with a "different problem" note, and doesn't count toward the guess being
  tested. Graders sometimes called that loose. The other option is a fourth signal
  ("lead") in `evidence.py`. I kept three signals to stay close to the usual practice.
- **Decide:** `sync_shared.py` defaults `--root` to the folder the script is in. Run from
  `entrepreneur-skills/scripts/`, that's the wrong folder, so `--root` must always be
  given. CONTRIBUTING says so. You may want to change the default in the build-root copy.
- **Check:** the founder-context file lives under `~/.founder/`. It moved out of
  `~/.claude` in the fix round, because Claude Code protects that folder. The skill writes
  through `context.py`, which honors `FOUNDER_HOME`.
- **Check:** the humanize baseline is Jake's li-human without his scripts (we may not run
  upstream code). Ours beat it in both baseline runs (92 vs 79 and 64), but if you want a
  fair tool-for-tool comparison, run his `detect.py` on our test drafts yourself.

## Calls to review

- humanize's score is our own 15-check rubric (hidden characters, dashes, banned words,
  stock words and phrases, openers and sign-offs, the "not X, it's Y" move, sentence
  length and rhythm, fragments, triples, emoji and hashtag noise, Markdown, paragraphs).
  The weights are judgment calls. They're all in `detect.py`, easy to tune.
- humanize adds `--compare` (dropped or added facts between the draft and the rewrite).
  It wasn't in the spec. It was the biggest single improvement in testing.
- Each skill writes a JSON file the tool reads (`market-inputs.json`,
  `validate-plan.json`) next to its Markdown file. The Markdown is for people; the JSON
  keeps the math and the locked lines checkable.
- validate locks pass and fail lines with a fingerprint, so a moved line shows up in the
  read. It is a tripwire, not security: anyone can edit the file.
- Python tools need Python 3.8+; tests were run on 3.13.

## Fix round after review

- User data moved out of `~/.claude` (protected by Claude Code) to `~/.founder`: business files, social folders and the media ledger. Tools honor `FOUNDER_HOME`; tests use a temp one.
- founder-context: `context.py migrate` copies the old folder from inside `~/.claude` to `~/.founder` once, after the user's yes; never deletes or overwrites. `where` mentions it when the old folder is found. Tests added.
- humanize `detect.py` reads the business file from `FOUNDER_HOME` or `~/.founder`.
- Eval fixtures moved from the old folder under `files/home/.claude` to `files/home/.founder`; two grader files renamed.
