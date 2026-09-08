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

Versioning is calendar-based, not semver: `YYYY.MM.DD`, or `YYYY.MM.DD.N` if a
package already published once today. The version lives only in git tags --
nothing is written back into a tracked file in agent-control, so a publish run
needs no pull request against its protected `main`: tags land on the merge
commit directly, since branch protection covers `refs/heads/main`, not
`refs/tags/*`.

agent-marketplace carries no APM configuration of its own. Package metadata
for the manifests (description, category) is read from `marketplace.yml` in
this repo, not from the marketplace repo.

Usage:
  python scripts/publish.py --repo PATH --marketplace PATH
                            [--dry-run] [--push]

  --repo         agent-control checkout to publish from
  --marketplace  agent-marketplace checkout to publish into
  --dry-run      show what would change; write, commit, tag and push nothing
  --push         push agent-marketplace's main and both repos' new tags.
                 Without it, everything is committed and tagged locally only.

Exit codes: 0 published (or nothing to do), 1 error.
"""
import argparse
import datetime
import glob
import io
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gitutil  # noqa: E402
import manifest  # noqa: E402

CONTENT_DIRS = ("skills", "commands", "agents")


def last_tag_versions(repo, name):
    """Every `<name>@<calver>` tag for this package, newest first.

    Sorted as plain strings: `YYYY.MM.DD` < `YYYY.MM.DD.N` < `YYYY.MM.DD+1`
    already holds lexicographically for this format, so no date parsing is
    needed to order them.
    """
    out = gitutil.git(["tag", "--list", "%s@*" % name], repo)
    tags = [t for t in out.split("\n") if t]
    versions = [t.split("@", 1)[1] for t in tags]
    return sorted(versions, reverse=True)


def changed(repo, name, source):
    versions = last_tag_versions(repo, name)
    if not versions:
        return True, None
    tag = "%s@%s" % (name, versions[0])
    commits = gitutil.git(["log", "%s..HEAD" % tag, "--oneline", "--", source], repo)
    return bool(commits), tag


def next_version(repo, name, today):
    date_str = today.strftime("%Y.%m.%d")
    versions = last_tag_versions(repo, name)
    todays = [v for v in versions if v == date_str or v.startswith(date_str + ".")]
    if not todays:
        return date_str
    suffixes = [int(v.split(".", 3)[3]) if len(v.split(".")) > 3 else 0
                for v in todays]
    return "%s.%d" % (date_str, max(suffixes) + 1)


def existing_bundle_version(marketplace, name):
    """The version already packed for `name`, from its plugins/<name>-<ver> dir.

    Used so an unchanged package still gets listed in the regenerated
    manifests, at whatever version it last published.
    """
    prefix = "%s-" % name
    matches = glob.glob(os.path.join(marketplace, "plugins", "%s*" % prefix))
    versions = [os.path.basename(m)[len(prefix):] for m in matches
                if os.path.basename(m).startswith(prefix)]
    return sorted(versions, reverse=True)[0] if versions else None


def pack_bundle(repo, marketplace, entry, version):
    name, source = entry["name"], entry["source"]
    package_dir = os.path.join(repo, source)
    bundle_dir = os.path.join(marketplace, "plugins", "%s-%s" % (name, version))

    for stale in glob.glob(os.path.join(marketplace, "plugins", "%s-*" % name)):
        shutil.rmtree(stale)

    os.makedirs(bundle_dir, exist_ok=True)
    for content_dir in CONTENT_DIRS:
        src = os.path.join(package_dir, content_dir)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(bundle_dir, content_dir))
    for extra in ("LICENSE", "LICENSES"):
        src = os.path.join(package_dir, extra)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(bundle_dir, extra))
        elif os.path.isdir(src):
            shutil.copytree(src, os.path.join(bundle_dir, extra))

    description = entry.get("description", "")
    for plugin_dir, extra_fields in ((".claude-plugin", {}),
                                      (".codex-plugin", {"interface": {}})):
        manifest_dir = os.path.join(bundle_dir, plugin_dir)
        os.makedirs(manifest_dir, exist_ok=True)
        payload = {"name": name, "version": version, "description": description}
        payload.update(extra_fields)
        with io.open(os.path.join(manifest_dir, "plugin.json"), "w",
                     encoding="utf-8") as f:
            json.dump(payload, f, indent=2, sort_keys=True)
            f.write("\n")

    return bundle_dir


def write_marketplace_manifests(marketplace, entries, new_versions):
    plugins = []
    for entry in entries:
        name = entry["name"]
        version = new_versions.get(name) or existing_bundle_version(marketplace, name)
        if not version:
            continue  # never packed, and not changed this run -- nothing to list
        plugins.append({
            "name": name,
            "source": "./plugins/%s-%s" % (name, version),
            "version": version,
            "description": entry.get("description", ""),
            "category": entry.get("category", ""),
        })
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
    with io.open(os.path.join(claude_dir, "marketplace.json"), "w",
                 encoding="utf-8") as f:
        json.dump(base, f, indent=2, sort_keys=True)
        f.write("\n")

    # Best-effort mirror for Codex/ChatGPT Desktop. Unlike the Claude manifest
    # above, this shape has not been validated against a real host -- check it
    # against Codex/ChatGPT's current marketplace schema before relying on it.
    agents_dir = os.path.join(marketplace, ".agents", "plugins")
    os.makedirs(agents_dir, exist_ok=True)
    with io.open(os.path.join(agents_dir, "marketplace.json"), "w",
                 encoding="utf-8") as f:
        json.dump(base, f, indent=2, sort_keys=True)
        f.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
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
            print("[bump] %-20s -> %s (since %s)" % (name, version, since or "the start"))
            to_publish.append((entry, version))
        else:
            print("[skip] %-20s no commits since %s" % (name, since))

    if not to_publish:
        print("\nnothing to publish")
        return 0

    if args.dry_run:
        print("\n[dry-run] no files written")
        return 0

    for entry, version in to_publish:
        pack_bundle(repo, marketplace, entry, version)

    write_marketplace_manifests(
        marketplace, entries, dict((e["name"], v) for e, v in to_publish))

    gitutil.git(["add", "-A"], marketplace)
    if not gitutil.git(["status", "--porcelain"], marketplace):
        print("\nnothing changed in the marketplace tree")
        return 0

    summary = ", ".join("%s %s" % (e["name"], v) for e, v in to_publish)
    message = "publish: %s" % summary
    gitutil.git(["commit", "-m", message], marketplace)
    print("[git ] committed in the marketplace")

    for entry, version in to_publish:
        tag = "%s@%s" % (entry["name"], version)
        gitutil.git(["tag", "-a", tag, "-m", tag], marketplace)
        gitutil.git(["tag", "-a", tag, "-m", tag], repo)
        print("[tag ] %s" % tag)

    if not args.push:
        print("\nCommitted and tagged locally. Push both repos to publish:")
        print("  git -C %s push --follow-tags" % marketplace)
        print("  git -C %s push --tags" % repo)
        return 0

    gitutil.git(["push", "--follow-tags", "origin", "HEAD"], marketplace)
    print("[push] marketplace")
    gitutil.git(["push", "--tags", "origin"], repo)
    print("[push] agent-control tags")

    print("\nPublished %d package(s)." % len(to_publish))
    return 0


if __name__ == "__main__":
    sys.exit(main())
