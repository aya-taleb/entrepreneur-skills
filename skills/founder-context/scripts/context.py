#!/usr/bin/env python3
"""Find, list, switch, create and check founder-context business files.

Where files live:
  ~/.founder/businesses/<slug>.md   one per business
  ~/.founder/active                 slug of the business in use
  ./founder/context.md              a project file, overrides both
Set FOUNDER_HOME to use another folder instead of ~/.founder (tests do this).

Usage:
  python3 context.py where                  # which file is in use, and why
  python3 context.py list                   # all businesses, active one marked
  python3 context.py use <slug>             # make <slug> the active business
  python3 context.py new <slug> [--name "Back Street Lunch"] [--project]
                                            # create from the template (won't overwrite)
  python3 context.py new <slug> --from draft.md [--replace]
                                            # put a drafted file in place (keeps a .bak)
  python3 context.py set <field> "<value>" [--file f]   # replace one field, prints before/after
  python3 context.py add <field> "<value>" [--file f]   # add to a list field (comma or bullets)
  python3 context.py check [file]           # list missing or placeholder fields
  python3 context.py get <field> [file]     # print one field, e.g. "Words to avoid"
  python3 context.py slug "Back Street Lunch"   # suggest a slug
  python3 context.py migrate [--dry-run]    # one-time copy from the old folder under ~/.claude

Add --json to where, list and check for machine-readable output.
Standard library only.
"""
import argparse
import datetime
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "..", "references", "template.md")

# label in the file -> required?
FIELDS = [
    ("Name", True),
    ("One-line pitch", True),
    ("Who it serves", True),
    ("Stage", True),
    ("Goals", True),
    ("Topics", True),
    ("Tone words", True),
    ("Words to avoid", False),
    ("Proof I can use", False),
    ("Off-limits", True),
]
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}$")


def home_dir(home=None):
    return home or os.path.expanduser("~")


def founder_dir(home=None):
    """$FOUNDER_HOME if set, else <home>/.founder. ~/.claude is protected, so data lives here."""
    env = os.environ.get("FOUNDER_HOME")
    if env:
        return os.path.expanduser(env)
    return os.path.join(home_dir(home), ".founder")


def old_dir(home=None):
    """Where older versions kept the files (inside ~/.claude)."""
    return os.path.join(home_dir(home), ".claude", "founder")


def migrate_status(home=None):
    """Return (old, new, needed). needed is True when the old folder exists and the new one doesn't."""
    old, new = old_dir(home), founder_dir(home)
    return old, new, os.path.isdir(old) and not os.path.exists(new)


def migrate(home=None):
    """Copy the old folder to the new place. Never deletes or overwrites. Returns the new path."""
    old, new, needed = migrate_status(home)
    if not os.path.isdir(old):
        raise LookupError("nothing to move: %s does not exist" % old)
    if os.path.exists(new):
        raise FileExistsError(new)
    shutil.copytree(old, new)
    return new


def make_slug(name):
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s[:40].strip("-") or "business"


def active_slug(home=None):
    path = os.path.join(founder_dir(home), "active")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as fh:
        slug = fh.read().strip()
    return slug if SLUG_RE.match(slug) else None


def businesses(home=None):
    d = os.path.join(founder_dir(home), "businesses")
    if not os.path.isdir(d):
        return []
    return sorted(f[:-3] for f in os.listdir(d) if f.endswith(".md") and SLUG_RE.match(f[:-3]))


def where(cwd=None, home=None):
    """Return (path or None, reason)."""
    cwd = cwd or os.getcwd()
    local = os.path.join(cwd, "founder", "context.md")
    if os.path.isfile(local):
        return local, "project file founder/context.md (it overrides the active business)"
    slug = active_slug(home)
    if slug:
        path = os.path.join(founder_dir(home), "businesses", slug + ".md")
        if os.path.isfile(path):
            return path, "active business '%s'" % slug
        return None, "active is set to '%s' but %s does not exist" % (slug, path)
    found = businesses(home)
    if len(found) == 1:
        return os.path.join(founder_dir(home), "businesses", found[0] + ".md"), \
            "only business on file '%s' (no active set)" % found[0]
    if found:
        return None, "%d businesses on file and none is active: %s" % (len(found), ", ".join(found))
    return None, "no business file yet"


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def get_field(text, label):
    """Return a field's value: an inline 'Label: value' or the bullets under '## Label'."""
    lines = text.splitlines()
    inline = re.compile(r"^\s*(?:[-*]\s*)?\**\s*" + re.escape(label) + r"\s*\**\s*:\s*\**\s*(.*)$", re.I)
    head = re.compile(r"^\s*#+\s*" + re.escape(label) + r"\s*$", re.I)
    for i, line in enumerate(lines):
        m = inline.match(line)
        if m and m.group(1).strip():
            return m.group(1).strip()
        if head.match(line) or (m and not m.group(1).strip()):
            items = []
            for nxt in lines[i + 1:]:
                if nxt.lstrip().startswith("#"):
                    break
                if re.match(r"^\s*[-*]\s*[A-Za-z][\w -]*:\s", nxt) and not head.match(line):
                    break
                if nxt.strip() and not nxt.strip().startswith("<!--"):
                    items.append(re.sub(r"^\s*[-*]\s*", "", nxt).strip())
            return "\n".join(items).strip()
    return ""


def check(text):
    """Return a list of (label, problem) for missing or placeholder fields."""
    problems = []
    for label, required in FIELDS:
        val = get_field(text, label)
        if not val:
            if required:
                problems.append((label, "missing"))
        elif "{{" in val:
            problems.append((label, "still a placeholder" if required else "placeholder (optional)"))
    proof = get_field(text, "Proof I can use")
    for line in proof.splitlines():
        if line and "{{" not in line and "source" not in line.lower() and "(" not in line:
            problems.append(("Proof I can use", "no source noted for: %s" % line[:60]))
    return problems


def target_path(slug, project=False, cwd=None, home=None):
    if project:
        return os.path.join(cwd or os.getcwd(), "founder", "context.md")
    return os.path.join(founder_dir(home), "businesses", slug + ".md")


def new(slug, name=None, project=False, cwd=None, home=None, source=None, replace=False):
    """Create a business file from the template, or from a drafted file (source).

    replace=True lets a drafted file replace an existing one; the old one is kept as .bak.
    """
    if not SLUG_RE.match(slug):
        raise ValueError("slug must be lowercase letters, numbers and hyphens, e.g. back-street-lunch")
    path = target_path(slug, project, cwd, home)
    if os.path.exists(path) and not (replace and source):
        raise FileExistsError(path)
    if source:
        body = read(source)
        if os.path.exists(path):
            shutil.copyfile(path, path + ".bak")
    else:
        body = read(TEMPLATE)
    if name:
        body = body.replace("{{Business name}}", name)
    body = body.replace("{{short-name}}", slug)
    body = body.replace("{{YYYY-MM-DD}}", datetime.date.today().isoformat())
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(body)
    return path


def _field_span(lines, label):
    """Find a field. Return ("inline", index) or ("list", heading_index, first, end) or None."""
    inline = re.compile(r"^(\s*(?:[-*]\s*)?\**\s*" + re.escape(label) + r"\s*\**\s*:\s*\**\s*)(.*)$", re.I)
    head = re.compile(r"^\s*#+\s*" + re.escape(label) + r"\s*$", re.I)
    for i, line in enumerate(lines):
        m = inline.match(line)
        if m:
            return ("inline", i, m.group(1))
        if head.match(line):
            j = i + 1
            while j < len(lines) and not lines[j].lstrip().startswith("#"):
                j += 1
            return ("list", i, i + 1, j)
    return None


def set_field(path, label, value, add=False, today=None):
    """Set (or with add=True, append to) one field. Returns (before, after) text of the field."""
    text = read(path)
    lines = text.split("\n")
    span = _field_span(lines, label)
    before = get_field(text, label)
    if span is None:
        raise LookupError("no field '%s' in %s. Fields: %s" % (label, path, ", ".join(f for f, _ in FIELDS)))
    if span[0] == "inline":
        _, i, prefix = span
        cur = lines[i][len(prefix):].strip()
        if add and cur and "{{" not in cur:
            items = [x.strip() for x in cur.split(",") if x.strip()]
            for v in [x.strip() for x in value.split(",") if x.strip()]:
                if v.lower() not in [x.lower() for x in items]:
                    items.append(v)
            new_val = ", ".join(items)
        else:
            new_val = value.strip()
        lines[i] = prefix + new_val
    else:
        _, h, first, end = span
        body = lines[first:end]
        keep_comments = [l for l in body if l.strip().startswith("<!--")]
        items = [l for l in body if l.strip() and not l.strip().startswith("<!--")]
        items = [l for l in items if "{{" not in l] if add else []
        for v in [x.strip() for x in value.split("\n") if x.strip()]:
            v = re.sub(r"^[-*]\s*", "", v)
            if not any(v.lower() == re.sub(r"^\s*[-*]\s*", "", l).strip().lower() for l in items):
                items.append("- " + v)
        lines[first:end] = keep_comments + items + [""]
    text = "\n".join(lines)
    stamp = today or datetime.date.today().isoformat()
    text = re.sub(r"(?m)^(\s*-\s*Updated:\s*).*$", lambda m: m.group(1) + stamp, text)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return before, get_field(text, label)


def use(slug, home=None):
    if slug not in businesses(home):
        raise LookupError("no business file for '%s'. On file: %s" % (slug, ", ".join(businesses(home)) or "none"))
    d = founder_dir(home)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "active"), "w", encoding="utf-8") as fh:
        fh.write(slug + "\n")
    return os.path.join(d, "businesses", slug + ".md")


def main(argv=None, cwd=None, home=None):
    ap = argparse.ArgumentParser(description="founder-context files")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("where"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("list"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("use"); p.add_argument("slug")
    p = sub.add_parser("new"); p.add_argument("slug"); p.add_argument("--name"); p.add_argument("--project", action="store_true")
    p.add_argument("--from", dest="source", help="copy a drafted file into place instead of the blank template")
    p.add_argument("--replace", action="store_true", help="with --from, replace an existing file (keeps a .bak)")
    for cmd in ("set", "add"):
        p = sub.add_parser(cmd); p.add_argument("field"); p.add_argument("value"); p.add_argument("--file")
    p = sub.add_parser("check"); p.add_argument("file", nargs="?"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("get"); p.add_argument("field"); p.add_argument("file", nargs="?")
    p = sub.add_parser("slug"); p.add_argument("name")
    p = sub.add_parser("migrate"); p.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    if args.cmd == "where":
        path, why = where(cwd, home)
        old, dest, needed = migrate_status(home)
        if args.json:
            print(json.dumps({"path": path, "reason": why, "old_folder": old if needed else None}))
        else:
            print(path or "none")
            print("(%s)" % why)
            if needed:
                print("Found files from an older version at %s. Ask the user, then run: "
                      "context.py migrate" % old)
        return 0 if path else 3
    if args.cmd == "list":
        act = active_slug(home)
        items = businesses(home)
        if args.json:
            print(json.dumps({"active": act, "businesses": items}))
        elif not items:
            print("No businesses on file yet.")
        else:
            for s in items:
                print(("* " if s == act else "  ") + s)
        return 0
    if args.cmd == "use":
        try:
            print("Active business is now %s (%s)" % (args.slug, use(args.slug, home)))
        except LookupError as exc:
            print(exc, file=sys.stderr)
            return 1
        return 0
    if args.cmd == "new":
        try:
            path = new(args.slug, args.name, args.project, cwd, home, args.source, args.replace)
        except FileExistsError as exc:
            print("Already exists, not overwriting: %s" % exc, file=sys.stderr)
            return 1
        except ValueError as exc:
            print(exc, file=sys.stderr)
            return 1
        print(path)
        return 0
    if args.cmd in ("check", "get"):
        path = args.file
        if not path:
            path, why = where(cwd, home)
            if not path:
                print("No business file found (%s)." % why, file=sys.stderr)
                return 3
        text = read(path)
        if args.cmd == "get":
            print(get_field(text, args.field))
            return 0
        problems = check(text)
        if args.json:
            print(json.dumps({"file": path, "problems": [{"field": f, "problem": p} for f, p in problems]}))
        elif problems:
            print("%s has %d gap(s):" % (path, len(problems)))
            for f, p in problems:
                print("  - %s: %s" % (f, p))
        else:
            print("%s looks complete." % path)
        return 0
    if args.cmd in ("set", "add"):
        path = args.file
        if not path:
            path, why = where(cwd, home)
            if not path:
                print("No business file found (%s)." % why, file=sys.stderr)
                return 3
        try:
            before, after = set_field(path, args.field, args.value, add=(args.cmd == "add"))
        except LookupError as exc:
            print(exc, file=sys.stderr)
            return 1
        print("File: %s" % path)
        print("%s before: %s" % (args.field, before.replace("\n", " / ") or "(empty)"))
        print("%s after:  %s" % (args.field, after.replace("\n", " / ")))
        return 0
    if args.cmd == "slug":
        print(make_slug(args.name))
        return 0
    if args.cmd == "migrate":
        old, dest, needed = migrate_status(home)
        if not needed:
            print("Nothing to move. Old folder %s: %s. New folder %s: %s." % (
                old, "found" if os.path.isdir(old) else "not found",
                dest, "already exists" if os.path.exists(dest) else "not found"))
            return 0
        if args.dry_run:
            print("Would copy %s to %s (the old folder stays as it is)." % (old, dest))
            return 0
        print("Copied %s to %s. The old folder is untouched; delete it yourself when ready." % (old, migrate(home)))
        return 0
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
