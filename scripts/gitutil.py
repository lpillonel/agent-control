"""Tiny git subprocess wrapper shared by check.py and publish.py."""
import subprocess
import sys


def git(args, cwd, check=True):
    result = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True)
    if check and result.returncode != 0:
        sys.stderr.write("git %s failed in %s\n%s\n"
                          % (" ".join(args), cwd, result.stderr.strip()))
        raise SystemExit(1)
    return result.stdout.strip()
