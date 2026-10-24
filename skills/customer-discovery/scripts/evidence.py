#!/usr/bin/env python3
"""Tally an interview evidence log, and export price answers for a price-sensitivity tool.

The evidence log (founder/discovery/evidence.md) has one block per interview:

    ## Interview: <who, role, company type>  (date: 2026-10-20)
    - Problem: <in their words> | strength: strong
    - Current solution: <what they do today> | pays: $40/month
    - Quote: "<their exact words>"
    - Signal: committed | <what they did: paid, pre-ordered, intro, trial, time>
    - Price: too_cheap=5, cheap=9, expensive=20, too_expensive=35

Strength is one of: strong, medium, weak.
Signal is one of: committed (gave money, time, reputation or an intro), interested
(said nice things, no action), none.

Usage:
  python3 evidence.py summary founder/discovery/evidence.md
  python3 evidence.py summary founder/discovery/evidence.md --json
  python3 evidence.py prices founder/discovery/evidence.md --out founder/discovery/prices.csv

The prices CSV has the columns too_cheap, cheap, expensive, too_expensive (one row per
person who answered all four), which is the format Van Westendorp price tools read,
including Jake Schincariol's van_westendorp.py in founder-pricing.

Standard library only.
"""
import argparse
import csv
import json
import re
import sys
from collections import Counter

PRICE_KEYS = ("too_cheap", "cheap", "expensive", "too_expensive")
STRENGTHS = ("strong", "medium", "weak")
SIGNALS = ("committed", "interested", "none")


def parse(text):
    """Return a list of interview dicts."""
    interviews = []
    cur = None
    for raw in text.splitlines():
        line = raw.strip()
        m = re.match(r"^#{2,3}\s*interview\s*[:\-]?\s*(.*)$", line, re.I)
        if m:
            head = m.group(1).strip()
            date = re.search(r"date:\s*([^)]*)", head, re.I)
            date = date.group(1).strip() if date else ""
            if date.startswith("{{") or date.upper().startswith("YYYY"):
                date = ""
            who = re.sub(r"\(?\s*date:.*$", "", head, flags=re.I).strip(" ()")
            cur = {"who": who, "date": date, "problems": [], "solutions": [],
                   "quotes": [], "signal": "", "signal_note": "", "price": {}, "pays": []}
            interviews.append(cur)
            continue
        if cur is None or not line.startswith(("-", "*")):
            continue
        body = line.lstrip("-* ").strip()
        km = re.match(r"^([A-Za-z ]+?):\s*(.*)$", body)
        if not km:
            continue
        key, val = km.group(1).strip().lower(), km.group(2).strip()
        parts = [p.strip() for p in val.split("|")]
        main = parts[0]
        extras = {}
        for p in parts[1:]:
            em = re.match(r"^([a-z_ ]+):\s*(.*)$", p, re.I)
            if em:
                extras[em.group(1).strip().lower()] = em.group(2).strip()
        if key == "problem":
            strength = extras.get("strength", "").lower()
            cur["problems"].append({"text": main, "strength": strength if strength in STRENGTHS else ""})
        elif key in ("current solution", "solution", "today"):
            cur["solutions"].append(main)
            if extras.get("pays"):
                cur["pays"].append(extras["pays"])
        elif key == "pays":
            cur["pays"].append(main)
        elif key == "quote":
            cur["quotes"].append(main.strip('"“”'))
        elif key == "signal":
            sig = main.lower().split()[0] if main else ""
            cur["signal"] = sig if sig in SIGNALS else ""
            cur["signal_note"] = " | ".join(parts[1:]) if len(parts) > 1 else ""
        elif key == "price":
            for k, v in re.findall(r"(too_cheap|cheap|expensive|too_expensive)\s*=\s*\$?([0-9][0-9,.]*)", val):
                try:
                    cur["price"][k] = float(v.replace(",", ""))
                except ValueError:
                    pass
    return interviews


def norm(text):
    return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()


def summary(interviews):
    n = len(interviews)
    signals = Counter(i["signal"] or "unmarked" for i in interviews)
    problems = Counter()
    strong = Counter()
    for i in interviews:
        seen = set()
        for p in i["problems"]:
            k = norm(p["text"])
            if k and k not in seen:
                seen.add(k)
                problems[p["text"]] += 1
                if p["strength"] == "strong":
                    strong[p["text"]] += 1
    gaps = []
    for i in interviews:
        who = i["who"] or "(unnamed)"
        if not i["date"]:
            gaps.append("%s: no date" % who)
        if not i["signal"]:
            gaps.append("%s: no signal marked (committed, interested or none)" % who)
        if not i["quotes"]:
            gaps.append("%s: no direct quote" % who)
        if i["price"] and len(i["price"]) < 4:
            gaps.append("%s: price answers incomplete (%d of 4)" % (who, len(i["price"])))
    committed = signals.get("committed", 0)
    if n == 0:
        read = "No interviews logged yet."
    elif n < 5:
        read = "Too few interviews to call (%d). Aim for at least 5 to 10 in one segment." % n
    elif committed == 0:
        read = "No one has committed anything yet. Interest without action is a weak signal."
    elif committed / float(n) >= 0.3:
        read = "%d of %d committed something. That's a real signal in this segment." % (committed, n)
    else:
        read = "%d of %d committed something. Some signal; look at who they are." % (committed, n)
    return {
        "interviews": n,
        "signals": dict(signals),
        "problems": problems.most_common(),
        "strong_problems": strong.most_common(),
        "price_answers": sum(1 for i in interviews if all(k in i["price"] for k in PRICE_KEYS)),
        "gaps": gaps,
        "read": read,
    }


def price_rows(interviews):
    rows, dropped = [], []
    for i in interviews:
        p = i["price"]
        if not p:
            continue
        if not all(k in p for k in PRICE_KEYS):
            dropped.append((i["who"], "missing answers"))
            continue
        vals = [p[k] for k in PRICE_KEYS]
        if not (vals[0] <= vals[1] <= vals[2] <= vals[3]):
            dropped.append((i["who"], "answers out of order"))
            continue
        rows.append(vals)
    return rows, dropped


def fmt(x):
    return str(int(x)) if x == int(x) else ("%.2f" % x).rstrip("0").rstrip(".")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Evidence log tools")
    sub = ap.add_subparsers(dest="cmd")
    s = sub.add_parser("summary"); s.add_argument("file"); s.add_argument("--json", action="store_true")
    p = sub.add_parser("prices"); p.add_argument("file"); p.add_argument("--out")
    args = ap.parse_args(argv)
    if not args.cmd:
        ap.print_help()
        return 1
    try:
        with open(args.file, encoding="utf-8") as fh:
            interviews = parse(fh.read())
    except OSError as exc:
        print("Could not read %s: %s" % (args.file, exc), file=sys.stderr)
        return 1
    if args.cmd == "summary":
        res = summary(interviews)
        if args.json:
            print(json.dumps(res, indent=2))
            return 0
        print("Interviews: %d" % res["interviews"])
        print("Signals: " + (", ".join("%s %d" % kv for kv in sorted(res["signals"].items())) or "none"))
        print("Problems heard (people who raised each):")
        for text, c in res["problems"][:10]:
            s_ = dict(res["strong_problems"]).get(text, 0)
            print("  - %s: %d%s" % (text, c, " (%d strong)" % s_ if s_ else ""))
        print("Full price answers: %d" % res["price_answers"])
        if res["gaps"]:
            print("Gaps in the log:")
            for g in res["gaps"]:
                print("  - " + g)
        print("Read: " + res["read"])
        return 0
    rows, dropped = price_rows(interviews)
    out = open(args.out, "w", newline="", encoding="utf-8") if args.out else sys.stdout
    w = csv.writer(out)
    w.writerow(PRICE_KEYS)
    for r in rows:
        w.writerow([fmt(x) for x in r])
    if args.out:
        out.close()
        print("wrote %d rows to %s" % (len(rows), args.out))
    for who, why in dropped:
        print("dropped %s: %s" % (who or "(unnamed)", why), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
