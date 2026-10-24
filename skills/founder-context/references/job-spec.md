# founder-context: job spec

## The job

A founder runs one or more businesses. Every skill that writes, researches or plans for
them needs the same few facts: what the business is, who it's for, where it stands, how
it sounds, what proof is real, and what never to say. Without a shared file, every skill
asks again or, worse, guesses.

## What it does

1. **Set up** a business file by interviewing the founder in two or three batches of
   questions, not twenty single ones.
2. **Draft from material** the founder points to: their website, an about page, a few
   posts they paste. The draft is marked as a draft until they confirm it.
3. **Switch** the active business when they work on a different one.
4. **Update** a field ("we just hit 40 customers", "stop saying cheap").
5. **Show** what's on file and which file is in use.

## Where the files live

- `~/.founder/businesses/<slug>.md`, one per business.
- `~/.founder/active`, the slug of the business in use.
- `founder/context.md` in a project folder overrides both for that project.

## Rules

- Never invent proof. Numbers, customers, quotes and press go in only when the founder
  gives them or a source they point to states them, and each keeps its source.
- Ask once for what's missing. Leave a `{{placeholder}}` for anything they skip.
- Don't overwrite a business file without showing the change.
- Keep the labels stable. Other skills (humanize reads "Words to avoid") parse them.

## Tool

`scripts/context.py`: find the file in use, list businesses, switch, create from the
template, check a file for gaps, read one field. Standard library only.
