# Testing

How each skill was tested, what it scored, and the calls made along the way.

**Read this first.** All scores come from our own test runs, graded by a model, not by
people. Each run was a fresh headless Claude that saw only the skill folder, the case
files and the prompt, with an empty throwaway home folder. A separate fresh Claude, with
no tools, graded each run against the case's grader statements and the rubric in
TEST-PROTOCOL.md. So we never graded our own work with full context, but the grader is
still a model and can be wrong. Rerunning the same version moved scores by up to about 5
points, sometimes more (humanize scored 96, 86, 94, 90, 92 and 87 on near-identical
versions). Treat any difference under 5 points as noise. Aya can rerun every case with
`claude plugin eval`. Run outputs are kept outside the repo, in the build's `_work` folder.

| skill | baseline | final | rounds | beats baseline? |
| --- | --- | --- | --- | --- |
| humanize | 79 (Jake's li-human, run 1) and 64 (run 2) | 92 (87 on a confirm run) | 6 | yes |
| founder-context | 51 (no skill) | 95 (93 on a confirm run) | 6 | yes |
| market-research | 45 (no skill) | 94 | 6 | yes |
| customer-discovery | 54 (no skill) | 92 (92 on a confirm run) | 6 | yes |
| validate | 48 (no skill) | 90 (90 on a confirm run) | 6 | yes |

"Final" is the score of the last round. Each skill has 3 cases (an app business, a local
business, an edge case) and 12 trigger prompts in `skills/<name>/evals/`.

### humanize  (ours)
baseline: 79 (Jake Schincariol's li-human SKILL.md and slop.json, run on the same 3 cases;
a second run scored 64). Caveat: his `humanize.py` and `detect.py` were not run, because
the build rules forbid running upstream code. His skill was told the tools were missing
and to do their job by hand. That handicaps it on "show a score", so the gap is probably
smaller than the numbers say. Ours v1 (round 0) scored 86.
final: 92 after 6 rounds. Stopped because two rounds in a row (r5: -4, r6: +2) gained
under 5 points, and r2 to r6 sit inside the noise band.
rounds:
- r1: 90, keep business-file content out of the rewrite (voice only), make long-sentence and avoid-list rules non-optional, end with "you post it".
- r2: 96, new `detect.py --compare` fact check (dropped or added numbers, links, names, new words) and a step to use it.
- r3: 86, asked for "why it matters" lines when nothing loses points, and to delete the in-between clean copy. Mostly noise; tone dipped because replies quoted the removed words.
- r4: 94, "a cut beats a swap" rule and a count-don't-quote rule for removed words.
- r5: 90, sample reply shape added.
- r6: 92, stronger "don't quote removed words" and "don't add traits or enthusiasm" rules.
open issues: replies still sometimes quote the removed words in the change list, and
rewrites sometimes add a small new phrase (a closing question, "does well in"). The
`--compare` new-word list catches these, but the model doesn't always act on it.

### founder-context  (ours)
baseline: 51 (no skill; Claude answered the prompt plainly). Ours v1 (round 0) scored 79.
final: 95 after 6 rounds. Stopped because r3 to r6 each moved under 5 points.
rounds:
- r1: 90, `context.py` gained `new --from`, `set` and `add`, which write the file and print before and after. The skill now writes through the tool, because direct writes under `~/.claude` are blocked in many setups (they were in the test sandbox).
- r2: 96, at most two batches of five questions, no stretching hints into fields.
- r3: 93, no sample numbers in examples.
- r4: 94, "say why when you refuse" line.
- r5: 92, no change worth noting; noise.
- r6: 95, real-proof suggestions describe what to collect, never a sample figure.
open issues: in the "make it up" edge case the reply sometimes still gives an example
count ("12 regular clients") while explaining what real proof looks like.

### market-research  (ours)
baseline: 45 (no skill). Ours v1 (round 0) scored 78.
final: 94 after 6 rounds. Stopped because r5 (+1) and r6 (-1) both gained under 5.
rounds:
- r1: 92, "from memory" counts as made up, trends and competitor names need a source, a call resting on unsourced buyer counts or prices can't be a plain Go, always write `founder/market.md`.
- r2: 91, clarified that reach and win shares are always guesses and don't block Go; a closing checklist.
- r3: 91, description broadened so "TAM slide for my pitch" triggers it.
- r4: 94, a "when asked to make up numbers" section that still writes the file.
- r5: 95, no change to this skill; rerun with the r4 version.
- r6: 94, no change; rerun.
Note: r5 and r6 are reruns without edits, used to confirm the plateau.
open issues: the test runs had no web access, so the web research path (finding and
linking real sources) was not tested. Only the "can't browse, leave placeholders" path
and the "use the founder's notes" path were.

### customer-discovery  (ours)
baseline: 54 (no skill). Ours v1 (round 0) scored 85.
final: 92 after 6 rounds. Stopped because r5 (-6) and r6 (+2) both gained under 5.
rounds:
- r1: 90, a commitment only counts if the person has the problem; asks stay free for the founder; a "make up interviews" section; always write a file.
- r2: 88, the reply's counts must match the log.
- r3: 94, description and triggers cover accelerator-application requests.
- r4: 96, dates copied as written (no guessed year), roles as written; `evidence.py` accepts free-text dates.
- r5: 90, no change; rerun showed a named local group given without a link.
- r6: 92, places described by kind with a search, specific groups only if linked.
open issues: Leo-style cases (an intro from someone with a different problem) are marked
committed with a note, which graders sometimes read as loose. That's a rule choice; see
BUILD-NOTES.md.

### validate  (ours)
baseline: 48 (no skill). Ours v1 (round 0) scored 79.
final: 90 after 6 rounds. Stopped because r6 (-4) gained under 5 and the rule's last
step allows it; r5 had gained exactly 5, so r6 was run.
rounds:
- r1: 79, always write `founder/validate.md`, say why fake social proof is refused, one call not two. The edge-case run did not load the skill at all.
- r2: 90, description now covers "make me a waitlist page" and "I'll decide based on signups", so the skill loads for those.
- r3: 86, page copy goes in validate.md too; name /validate again for the read.
- r4: 89, don't mix a test count with the business goal; pivots get a retest with lines.
- r5: 94, full page copy word for word in validate.md; the retest is added to the plan and relocked.
- r6: 90, no change to this skill; rerun.
open issues: in the read-results case, the pivot retest is not always added and locked in
the plan file. In the design case, humanize is sometimes skipped for the page copy.

## Calls I made

- **Test harness.** Each run used `claude -p` with a fresh empty home folder and only the
  skill folders the case needs (customer-discovery and validate also got founder-context
  and humanize, since they hand off to them). Grading was a separate `claude -p` call with
  no tools. The no-skill baseline got the same cases with no skill installed.
- **Trigger fit.** Checked by a fresh Claude that picked, for each of the 12 prompts, one
  skill (or none) from a list of all five descriptions plus 13 decoy descriptions
  (competitors, pricing, pitch, write-post and others). Jake's li-human was checked with
  our humanize left out of the list, so the two didn't compete. Every final description
  scored 12 of 12. That is a simulation of skill choice, not the real Claude Code loader.
- **Jake's tools not run.** The build rules say never to run upstream code, so the
  baseline used his SKILL.md and lexicon only. Noted above.
- **Writing to `~/.claude`.** In the sandbox, direct file writes under `.claude` count as
  sensitive and are blocked. founder-context now writes only through `context.py`, which
  works everywhere. Real users may still get a permission prompt the first time.
- **Banned words in evals.** The humanize test drafts and graders must contain the banned
  words they test for. Those lines carry an `<!-- allow-words -->` marker so
  `validate.py` passes. The harness strips the marker before a run.
- **Retries.** A few runs and gradings died from rate limits or timeouts. Those cases were
  rerun or regraded with the same version; nothing was cherry-picked.
- **Round 0 humanize fix.** A unit test caught a bug in reading "Words to avoid" (a
  placeholder with a comma split into pieces). It was fixed during round 0. None of the
  eval cases used that placeholder, so the round 0 score is unaffected.

## Independent review (blind)

Spot check by an independent reviewer on 2026-10-23, run blind against the baseline.
Each case ran in a fresh `claude -p` (Sonnet) with its own empty HOME, seeing only that
skill's folder (plus founder-context and humanize where ours uses them), the case prompt
and its input files. The baseline saw only the upstream SKILL.md and non-code files; its
Python tools were left out (never run upstream code), with a note telling it to do their
job by hand. A separate Opus judge saw the request, the expected outcome, the inputs and
both results as A and B in random order (key kept apart), and scored each 0 to 10 on five
lines (did the job, nothing made up, safety, clear and usable, tone), so totals are out
of 50. Close calls were judged a second time with A and B swapped. Outputs, keys and
verdicts: `/home/claude/build/_work/review/spot/`.

Jake's li-human ran text only: SKILL.md and slop.json, no humanize.py or detect.py, with a
note to apply his rules by hand. So his runs give no tool score, which the judge counted
against him on the "shows a score" part of the expected outcome.

| skill | case | winner | ours score | baseline score | fix rounds | one-line reason |
| --- | --- | --- | --- | --- | --- | --- |
| humanize | app-linkedin-post | ours | 44 | 33 | 0 | Kept every fact (212 teams, 3.5 hours, March beta, link), removed dashes and avoid words, showed before and after. Jake's added a June goal, a pitch and 'I read every reply'. Ours added a closing question, flagged. |
| humanize | local-lunch-cold-email | ours | 46 | 35 | 0 | Kept $9, Tue/Thu 11:45, 20-person minimum, address and opt-out; no new claims. Jake's added a sample visit and 'right on our route'. Ours kept 'chef-crafted' and wrote a new subject line. |
