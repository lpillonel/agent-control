#!/usr/bin/env python3
"""Pre-merge validation gate for agent-control.

Runs against a plain checkout of this repo -- no marketplace, no APM CLI
required. This is the only gate: everything reaching agent-marketplace has
already passed this, so the marketplace repo carries no validation of its own.

Usage:
  python scripts/check.py --repo PATH

Exit codes: 0 clean, 1 problems found.
"""
import argparse
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import manifest  # noqa: E402

CONTENT_DIRS = ("skills", "commands", "agents")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def check_skill_frontmatter(path, problems):
    text = io.open(path, encoding="utf-8").read()
    m = FRONTMATTER_RE.match(text)
    if not m:
        problems.append("%s: missing YAML frontmatter (--- ... ---)" % path)
        return
    body = m.group(1)
    for field in ("name", "description"):
        if not re.search(r"(?m)^%s:\s*\S" % field, body):
            problems.append("%s: frontmatter missing `%s:`" % (path, field))


def check_package(repo, entry, problems):
    name = entry.get("name")
    source = entry.get("source")
    if not name or not source:
        problems.append("marketplace.yml entry missing name/source: %r" % entry)
        return
    package_dir = os.path.join(repo, source)
    if not os.path.isdir(package_dir):
        problems.append("%s: no such directory (package %r)" % (source, name))
        return
    if not any(os.path.isdir(os.path.join(package_dir, d)) for d in CONTENT_DIRS):
        problems.append(
            "%s: package %r has none of %s" % (source, name, ", ".join(CONTENT_DIRS)))

    skills_dir = os.path.join(package_dir, "skills")
    if os.path.isdir(skills_dir):
        for skill in sorted(os.listdir(skills_dir)):
            skill_md = os.path.join(skills_dir, skill, "SKILL.md")
            if os.path.isfile(skill_md):
                check_skill_frontmatter(skill_md, problems)
            else:
                problems.append("%s: skills/%s has no SKILL.md" % (source, skill))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    args = parser.parse_args()

    entries = manifest.load(args.repo)
    if not entries:
        sys.stderr.write("marketplace.yml lists no packages\n")
        return 1

    problems = []
    seen_dirs = set()
    for entry in entries:
        check_package(args.repo, entry, problems)
        seen_dirs.add(entry.get("source"))

    packages_root = os.path.join(args.repo, "packages")
    if os.path.isdir(packages_root):
        for entry in sorted(os.listdir(packages_root)):
            source = "packages/%s" % entry
            if (os.path.isdir(os.path.join(packages_root, entry))
                    and source not in seen_dirs):
                problems.append(
                    "packages/%s exists but has no marketplace.yml entry (orphaned)"
                    % entry)

    if problems:
        sys.stderr.write("check failed:\n")
        for p in problems:
            sys.stderr.write("  - %s\n" % p)
        return 1

    print("check passed: %d package(s) OK" % len(entries))
    return 0


if __name__ == "__main__":
    sys.exit(main())
