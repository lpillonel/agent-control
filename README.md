# agent-control

Source of truth for IMTF-managed agent skills. Authored and validated here,
published to [imtf-group/agent-marketplace](https://github.com/imtf-group/agent-marketplace)
for consumption in Claude Desktop, Claude Code and ChatGPT.

## Layout

| Path | What it is |
|---|---|
| `packages/<name>/` | A package: `skills/`, `commands/`, `agents/`, its own `apm.yml` |
| `marketplace.yml` | Marketplace-only metadata per package (description, category) |
| `scripts/check.py` | The pre-merge gate -- run on every pull request |
| `scripts/publish.py` | Packs changed packages, versions them, publishes to `agent-marketplace` |

## Architecture

- All validation (`scripts/check.py`) runs **pre-merge**, on every pull
  request. Nothing else gates a release.
- On merge to `main`, `.github/workflows/publish.yml` packs whatever packages
  changed and pushes the result directly to `agent-marketplace`'s `main`. That
  repo has no branch protection and no gate of its own -- everything reaching
  it has already passed the check above.
- A package is considered "changed" when it has commits since its own last
  `<name>@<version>` tag, not by diffing generated output. See the module
  docstring in `scripts/publish.py`.
- Versioning is calendar-based per package (`YYYY.MM.DD`, `YYYY.MM.DD.N` for a
  same-day republish) and lives only in git tags -- nothing is written back
  into a tracked file here, so a publish needs no release pull request.

## Adding a package

1. Create `packages/<name>/apm.yml` (name, version for APM's own use,
   description, license) and its content under `skills/`, `commands/` or
   `agents/`.
2. Add an entry to `marketplace.yml` with the same `name`, its `source` path,
   and the marketplace-facing `description` and `category`.
3. Open a pull request. `scripts/check.py` validates the package structure and
   every `SKILL.md`'s frontmatter.
4. On merge, the package publishes automatically at its first calendar
   version.

## Running the gate and a publish locally

```bash
python scripts/check.py --repo .
python scripts/publish.py --repo . --marketplace ../agent-marketplace --dry-run
python scripts/publish.py --repo . --marketplace ../agent-marketplace   # commits + tags locally, does not push
```

## CI

- `.github/workflows/checks.yml` -- runs the gate on every pull request.
- `.github/workflows/publish.yml` -- runs on every merge to `main`, needs a
  `MARKETPLACE_TOKEN` secret (a PAT with `contents:write` on
  `imtf-group/agent-marketplace`).
