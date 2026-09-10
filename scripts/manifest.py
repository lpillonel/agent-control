"""Local package discovery -- scans packages/*/apm.yml for the scalar
fields publish.py and check.py need. No YAML dependency: apm.yml's
top-level values are plain `key: value` lines, so a line scan is enough
(indented/nested keys, e.g. under `dependencies:`, are skipped).
"""

import os

SCALAR_FIELDS = ("name", "version", "description", "license", "category")


def _read_scalars(path):
    values = {}
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.split("#", 1)[0].rstrip("\n")
            if not line or line[0] in " \t" or ":" not in line:
                continue
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip().strip("'\"")
            if key in SCALAR_FIELDS and value:
                values[key] = value
    return values


def load(repo):
    """One entry per packages/<dir> with an apm.yml, in directory order."""
    packages_root = os.path.join(repo, "packages")
    entries = []
    if not os.path.isdir(packages_root):
        return entries
    for dirname in sorted(os.listdir(packages_root)):
        source = f"packages/{dirname}"
        apm_yml = os.path.join(packages_root, dirname, "apm.yml")
        if not os.path.isfile(apm_yml):
            continue
        values = _read_scalars(apm_yml)
        entries.append(
            {
                "name": values.get("name", dirname),
                "source": source,
                "description": values.get("description", ""),
                "version": values.get("version", "0.0.0"),
                "license": values.get("license", ""),
                "category": values.get("category", ""),
            }
        )
    return entries
