#!/usr/bin/env python3
"""Pack changed packages from agent-control into agent-marketplace, version
them with calver, and commit/tag/push both repos.

Which packages changed is read from git history, not from diffing generated
output: a package is "changed" when it has commits since its own last
`<name>@<version>` tag under its `packages/<dir>` path. A package with no
prior tag at all is always changed (first publish). This mirrors
imtf-group/agent-steering and siegenthalerroger/.llmctl, which use the same
git-log-since-tag approach -- diffing generated output runs into the new
version number always looking like a diff against the old one.

Versioning is calendar-based, not semver: `YYYY.MM.DD`, or `YYYY.MM.DD.N` if
package already published once today. The version lives only in git tags --
nothing is written back into a tracked file in agent-control, so a publish run
needs no pull request against its protected `main`: tags land on the merge
commit directly, since branch protection covers `refs/heads/main`, not
`refs/tags/*`.

agent-marketplace carries no APM configuration of its own. Package metadata
for the manifests (description, category) is read from `marketplace.yml` in
this repo, not from the marketplace repo.

Usage:
  python3 scripts/publish.py --marketplace PATH [--repo PATH]
                             [--dry-run] [--push]

  --repo         agent-control checkout to publish from (default: ".")
  --marketplace  agent-marketplace checkout to publish into
  --dry-run      show what would change; write, commit, tag and push nothing
  --push         push agent-marketplace's main and both repos' new tags.
                 Without it, everything is committed and tagged locally only.

Exit codes: 0 published (or nothing to do), 1 error.
"""

import argparse
import datetime
import glob
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gitutil
import manifest


def last_tag_versions(repo, name):
    """Every `<name>@<calver>` tag for this package, newest first.

    Sorted as plain strings: `YYYY.MM.DD` < `YYYY.MM.DD.N` < `YYYY.MM.DD+1`
    already holds lexicographically for this format, so no date parsing is
    needed to order them.
    """
    out = gitutil.git(["tag", "--list", f"{name}@*"], repo)
    tags = [t for t in out.split("\n") if t]
    versions = [t.split("@", 1)[1] for t in tags]
    return sorted(versions, reverse=True)


def changed(repo, name, source):
    versions = last_tag_versions(repo, name)
    if not versions:
        return True, None
    tag = f"{name}@{versions[0]}"
    commits = gitutil.git(["log", f"{tag}..HEAD", "--oneline", "--", source], repo)
    return bool(commits), tag


def next_version(repo, name, today):
    date_str = today.strftime("%Y.%m.%d")
    versions = last_tag_versions(repo, name)
    todays = [v for v in versions if v == date_str or v.startswith(date_str + ".")]
    if not todays:
        return date_str
    suffixes = [int(v.split(".", 3)[3]) if len(v.split(".")) > 3 else 0 for v in todays]
    return f"{date_str}.{max(suffixes) + 1}"


def existing_bundle_version(marketplace, name):
    """The version already packed for `name`, from its plugins/<name>-<ver> dir.

    Used so an unchanged package still gets listed in the regenerated
    manifests, at whatever version it last published.
    """
    prefix = f"{name}-"
    matches = glob.glob(os.path.join(marketplace, "plugins", f"{prefix}*"))
    versions = [
        os.path.basename(m)[len(prefix) :]
        for m in matches
        if os.path.basename(m).startswith(prefix)
    ]
    return max(versions) if versions else None


def pack_bundle(repo, marketplace, entry, version):
    """Resolve `package_dir`'s own apm.yml dependencies and pack them into
    the marketplace, using the apm CLI itself rather than a hand-rolled
    copy -- this is what lets a package (like `example`) declare and ship
    a real external dependency (e.g. a vendored skill from another repo)
    and have it actually resolved into the bundle, not just its own files.

    apm has no monorepo/workspace mode: every `apm` invocation resolves
    relative to the apm.yml in its current directory, so each package must
    be packed with that package's own directory as cwd (see
    siegenthalerroger/.llmctl's scripts/pack-marketplace.py, which does the
    same). apm.yml's own `version:` field -- not this function's calver
    `version` -- decides the bundle dirname apm writes, so the freshly
    packed dir is renamed into place afterwards.
    """
    name, source = entry["name"], entry["source"]
    package_dir = os.path.join(repo, source)
    plugins_root = os.path.join(marketplace, "plugins")
    bundle_dir = os.path.join(plugins_root, f"{name}-{version}")

    for stale in glob.glob(os.path.join(plugins_root, f"{name}-*")):
        shutil.rmtree(stale)

    gitutil.run(["apm", "install"], package_dir)
    gitutil.run(
        ["apm", "pack", "--format", "agent-plugin", "-o", plugins_root, "--force"],
        package_dir,
    )

    packed = glob.glob(os.path.join(plugins_root, f"{name}-*"))
    if len(packed) != 1:
        sys.stderr.write(f"apm pack produced {packed!r} for {name!r}, expected one\n")
        raise SystemExit(1)
    if packed[0] != bundle_dir:
        os.rename(packed[0], bundle_dir)

    os.remove(os.path.join(bundle_dir, "plugin.json"))
    for extra in ("LICENSE", "LICENSES"):
        src = os.path.join(package_dir, extra)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(bundle_dir, extra))
        elif os.path.isdir(src):
            shutil.copytree(src, os.path.join(bundle_dir, extra))

    description = entry.get("description", "")
    for plugin_dir, extra_fields in (
        (".claude-plugin", {}),
        (".codex-plugin", {"interface": {}}),
    ):
        manifest_dir = os.path.join(bundle_dir, plugin_dir)
        os.makedirs(manifest_dir, exist_ok=True)
        payload = {"name": name, "version": version, "description": description}
        payload.update(extra_fields)
        with open(
            os.path.join(manifest_dir, "plugin.json"), "w", encoding="utf-8"
        ) as f:
            json.dump(payload, f, indent=2, sort_keys=True)
            f.write("\n")

    return bundle_dir


def write_marketplace_manifests(marketplace, entries, new_versions):
    plugins = []
    for entry in entries:
        name = entry["name"]
        version = new_versions.get(name) or existing_bundle_version(marketplace, name)
        if not version:
            continue
        plugins.append(
            {
                "name": name,
                "source": f"./plugins/{name}-{version}",
                "version": version,
                "description": entry.get("description", ""),
                "category": entry.get("category", ""),
            }
        )
    plugins.sort(key=lambda p: p["name"])

    owner = {"name": "imtf-group", "url": "https://github.com/imtf-group"}
    base = {
        "name": "agent-marketplace",
        "owner": owner,
        "metadata": {"description": "IMTF agent skills, packaged for plugin hosts."},
        "plugins": plugins,
    }

    claude_dir = os.path.join(marketplace, ".claude-plugin")
    os.makedirs(claude_dir, exist_ok=True)
    with open(os.path.join(claude_dir, "marketplace.json"), "w", encoding="utf-8") as f:
        json.dump(base, f, indent=2, sort_keys=True)
        f.write("\n")

    agents_dir = os.path.join(marketplace, ".agents", "plugins")
    os.makedirs(agents_dir, exist_ok=True)
    with open(os.path.join(agents_dir, "marketplace.json"), "w", encoding="utf-8") as f:
        json.dump(base, f, indent=2, sort_keys=True)
        f.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--marketplace", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--push", action="store_true")
    args = parser.parse_args()

    repo = os.path.abspath(args.repo)
    marketplace = os.path.abspath(args.marketplace)
    entries = manifest.load(repo)
    today = datetime.datetime.now(datetime.timezone.utc).date()

    to_publish = []
    for entry in entries:
        name, source = entry["name"], entry["source"]
        is_changed, since = changed(repo, name, source)
        if is_changed:
            version = next_version(repo, name, today)
            print(f"[bump] {name:<20} -> {version} (since {since or 'the start'})")
            to_publish.append((entry, version))
        else:
            print(f"[skip] {name:<20} no commits since {since}")

    if not to_publish:
        print("\nnothing to publish")
        return 0

    if args.dry_run:
        print("\n[dry-run] no files written")
        return 0

    for entry, version in to_publish:
        pack_bundle(repo, marketplace, entry, version)

    write_marketplace_manifests(
        marketplace, entries, {e["name"]: v for e, v in to_publish}
    )

    gitutil.git(["add", "-A"], marketplace)
    if not gitutil.git(["status", "--porcelain"], marketplace):
        print("\nnothing changed in the marketplace tree")
        return 0

    summary = ", ".join(f"{e['name']} {v}" for e, v in to_publish)
    message = f"publish: {summary}"
    gitutil.git(["commit", "-m", message], marketplace)
    print("[git ] committed in the marketplace")

    for entry, version in to_publish:
        tag = f"{entry['name']}@{version}"
        gitutil.git(["tag", "-a", tag, "-m", tag], marketplace)
        gitutil.git(["tag", "-a", tag, "-m", tag], repo)
        print(f"[tag ] {tag}")

    if not args.push:
        print("\nCommitted and tagged locally. Push both repos to publish:")
        print(f"  git -C {marketplace} push --follow-tags")
        print(f"  git -C {repo} push --tags")
        return 0

    gitutil.git(["push", "--follow-tags", "origin", "HEAD"], marketplace)
    print("[push] marketplace")
    gitutil.git(["push", "--tags", "origin"], repo)
    print("[push] agent-control tags")

    print(f"\nPublished {len(to_publish)} package(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
