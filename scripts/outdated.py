#!/usr/bin/env python3
"""List outdated apm dependencies across every packages/*.

apm has no workspace mode -- `apm outdated` only ever looks at the apm.yml
in its current directory (see manifest.load's own packages/*/apm.yml scan
for why this repo works around that the same way everywhere else: cd into
each package and run the command there, in a loop, instead of by hand).

This is purely informational: it always exits 0, same as `apm outdated`
itself. Follow up with `apm update [-y]` inside a specific package to
actually upgrade it -- that command isn't looped here since a bump is a
one-package-at-a-time decision, not a blanket action.

Usage:
  python3 scripts/outdated.py [--repo PATH]
"""

import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    args = parser.parse_args()

    repo = os.path.abspath(args.repo)
    entries = manifest.load(repo)
    if not entries:
        sys.stderr.write("no packages/*/apm.yml found\n")
        return 1

    # A wide COLUMNS keeps apm's rich table from truncating when stdout
    # isn't a tty (e.g. captured by `apm run`, piped, or in CI logs).
    env = dict(os.environ, COLUMNS="200")

    for entry in entries:
        package_dir = os.path.join(repo, entry["source"])
        # subprocess writes straight to the inherited fd, bypassing
        # Python's own stdout buffer -- flush around it or these headers
        # print out of order relative to `apm outdated`'s own output.
        print(f"=== {entry['name']} ({entry['source']}) ===", flush=True)
        subprocess.run(["apm", "outdated"], cwd=package_dir, env=env, check=False)
        print(flush=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
