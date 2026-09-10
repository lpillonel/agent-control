"""Tiny subprocess wrapper shared by check.py and publish.py (git and apm)."""

import subprocess
import sys


def run(cmd, cwd, check=True):
    result = subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, check=False
    )
    if check and result.returncode != 0:
        sys.stderr.write(
            f"{' '.join(cmd)} failed in {cwd}\n{result.stdout}{result.stderr}\n"
        )
        raise SystemExit(1)
    return result.stdout.strip()


def git(args, cwd, check=True):
    return run(["git"] + args, cwd, check=check)
