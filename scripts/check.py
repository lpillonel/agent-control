#!/usr/bin/env python3
"""Pre-merge validation gate for agent-control.

Runs against a plain checkout of this repo -- no marketplace, no APM CLI
required. This is the only gate: everything reaching agent-marketplace has
already passed this, so the marketplace repo carries no validation of its own.

Packages are discovered via manifest.load(): every packages/<dir> with an
apm.yml. For each one, this checks:

  - the package directory has an apm.yml (manifest.load's own discovery
    guarantees this, but a missing directory is reported the same way)
  - the package has at least one of CONTENT_DIRS (.apm/, skills/, commands/,
    agents/) -- i.e. it actually ships something
  - every skill under .apm/skills/ and the legacy top-level skills/ has a
    SKILL.md file
  - every SKILL.md has a --- ... --- YAML frontmatter block, with non-empty
    `name:` and `description:` fields in it

If packages/*/apm.yml matches nothing at all, that alone fails the check
before any per-package validation runs.

Usage:
  python3 scripts/check.py [--repo PATH]   # PATH defaults to "."

Exit codes: 0 clean, 1 problems found.
"""

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import manifest

# apm's producer docs make .apm/ the authoritative primitives source; the
# top-level names are kept too for packages not yet migrated to it.
CONTENT_DIRS = (".apm", "skills", "commands", "agents")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def check_skill_frontmatter(path, problems):
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        problems.append(f"{path}: cannot read file ({e})")
        return
    m = FRONTMATTER_RE.match(text)
    if not m:
        problems.append(f"{path}: missing YAML frontmatter (--- ... ---)")
        return
    body = m.group(1)
    for field in ("name", "description"):
        if not re.search(rf"(?m)^{field}:\s*\S", body):
            problems.append(f"{path}: frontmatter missing `{field}:`")


def check_package(repo, entry, problems):
    name = entry.get("name")
    source = entry.get("source")
    package_dir = os.path.join(repo, source)
    if not os.path.isfile(os.path.join(package_dir, "apm.yml")):
        problems.append(f"{source}: no such directory (package {name!r})")
        return
    if not any(os.path.isdir(os.path.join(package_dir, d)) for d in CONTENT_DIRS):
        problems.append(
            f"{source}: package {name!r} has none of {', '.join(CONTENT_DIRS)}"
        )

    for skills_dir in (
        os.path.join(package_dir, ".apm", "skills"),
        os.path.join(package_dir, "skills"),
    ):
        if not os.path.isdir(skills_dir):
            continue
        rel = os.path.relpath(skills_dir, package_dir)
        for skill in sorted(os.listdir(skills_dir)):
            skill_md = os.path.join(skills_dir, skill, "SKILL.md")
            if os.path.isfile(skill_md):
                check_skill_frontmatter(skill_md, problems)
            else:
                problems.append(f"{source}: {rel}/{skill} has no SKILL.md")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    args = parser.parse_args()

    entries = manifest.load(args.repo)
    if not entries:
        sys.stderr.write("no packages/*/apm.yml found\n")
        return 1

    problems = []
    for entry in entries:
        check_package(args.repo, entry, problems)

    if problems:
        sys.stderr.write("check failed:\n")
        for p in problems:
            sys.stderr.write(f"  - {p}\n")
        return 1

    print(f"check passed: {len(entries)} package(s) OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
