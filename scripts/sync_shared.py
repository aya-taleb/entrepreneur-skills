#!/usr/bin/env python3
"""Copy shared skills from their home repo into every repo that ships them.

Reads each repo's skills.json. For every entry with status "synced" and a "home",
copies <root>/<home>/skills/<name>/ into <root>/<repo>/skills/<name>/, replacing what
was there, and writes a .synced-from file with the home repo and version.

Usage: python3 sync_shared.py [--root /path/to/folder/with/all/repos] [--dry-run]
Standard library only.
"""
import argparse
import json
import os
import shutil
import sys


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def main():
    parser = argparse.ArgumentParser()
    # Default: the folder that holds this repo and its sibling *-skills repos.
    here = os.path.dirname(os.path.abspath(__file__))
    parser.add_argument("--root", default=os.path.dirname(os.path.dirname(here)))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    root = args.root
    repos = [d for d in sorted(os.listdir(root))
             if d.endswith("-skills") and os.path.exists(os.path.join(root, d, "skills.json"))]
    homes = {}
    for repo in repos:
        for s in load(os.path.join(root, repo, "skills.json")).get("skills", []):
            if s.get("status") not in ("synced", "linked"):
                homes[s["name"]] = (repo, s.get("version", "0.1.0"))
    problems = 0
    for repo in repos:
        for s in load(os.path.join(root, repo, "skills.json")).get("skills", []):
            if s.get("status") != "synced":
                continue
            name = s["name"]
            home = s.get("home")
            if not home or name not in homes or homes[name][0] != home:
                print("! %s/%s: home %r has no such skill" % (repo, name, home))
                problems += 1
                continue
            src = os.path.join(root, home, "skills", name)
            dst = os.path.join(root, repo, "skills", name)
            if not os.path.isdir(src):
                print("! %s/%s: source folder missing at %s" % (repo, name, src))
                problems += 1
                continue
            print("%s/%s <- %s (v%s)" % (repo, name, home, homes[name][1]))
            if args.dry_run:
                continue
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__"))
            with open(os.path.join(dst, ".synced-from"), "w", encoding="utf-8") as fh:
                fh.write("home: aya-taleb/%s\nversion: %s\nEdit this skill in its home repo, not here.\n"
                         % (home, homes[name][1]))
            s["version"] = homes[name][1]
        if not args.dry_run:
            path = os.path.join(root, repo, "skills.json")
            manifest = load(path)
            for s in manifest.get("skills", []):
                if s.get("status") == "synced" and s["name"] in homes:
                    s["version"] = homes[s["name"]][1]
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(manifest, fh, indent=2)
                fh.write("\n")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
