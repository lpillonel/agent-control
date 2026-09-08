"""Tiny marketplace.yml reader -- no YAML dependency, just enough structure
for a flat list of package entries with scalar fields.
"""
import io
import os
import sys


def load(repo):
    path = os.path.join(repo, "marketplace.yml")
    if not os.path.isfile(path):
        sys.stderr.write("no marketplace.yml at %s\n" % path)
        raise SystemExit(1)
    entries = []
    current = None
    for raw in io.open(path, encoding="utf-8"):
        line = raw.split("#", 1)[0].rstrip("\n")
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("- name:"):
            if current:
                entries.append(current)
            current = {"name": stripped.split(":", 1)[1].strip()}
        elif current is not None and ":" in stripped:
            key, _, value = stripped.partition(":")
            current[key.strip()] = value.strip().strip("\"'")
    if current:
        entries.append(current)
    return entries
