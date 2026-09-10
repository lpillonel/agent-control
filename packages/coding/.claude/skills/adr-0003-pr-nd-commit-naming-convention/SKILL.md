---
name: imtf-adr-0003-pr-nd-commit-naming-convention
description: "Apply when working on process in any repo. IMTF adr 0003-pr-nd-commit-naming-convention: PR naming convention."
---

# ADR-0003: PR naming convention

| Field  | Value                                                  |
| ------ | ------------------------------------------------------ |
| Date   | 2023-07-10                                             |
| Status | In-Progress \| In-Review \| **Accepted** \| Superseded |
| Tags   | process                                                |

| Revision | Date       | Info           |
| -------- | ---------- | -------------- |
| 1        | 2023-07-10 | Initial design |
| 2        | 2025-05-01 | Update         |

## Context

Pull requests names and final commits message are currently disparate between all products and inside a single product as well. It makes PR and commits difficult to understand and to classify.

## Decision

We would like to put in place a common **commits naming convention** for all IMTF git repository. Consistent commit message naming enhances codebase clarity and tool integration. It brings many benefits such as :

- Enables automated release management (e.g., semantic release).
- Enhances automation in CI/CD pipelines.
- Facilitates changelog generation.
- Improves readability and consistency.
- Simplifies creating proper commit messages, especially for newcomers.
- Ensures proper tracking of breaking changes.

### Format

We adhere to the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>)(!): <description>
```

### Components

1. **`<type>`**: The type of change. Refer to the [`config-conventional`](https://github.com/conventional-changelog/commitlint/tree/master/%40commitlint/config-conventional#type-enum) list for accepted types.
2. **`<scope>`**: The optional scope of the change (as defined in the Conventional Commits specification).
3. **`(!)`**: An optional `!` character to indicate a breaking change.
4. **`<description>`**: A concise description of the change.

Additionally, a revert commit can be:
`Revert: "<the previous pattern>"`

## Examples

### Standard Commits

```
chore(deps): Upgrade (DET-2345)
feat(cases): Merge case activation and processes startup into a single EventHandler (DET-6920)
feat(mdm)!: Implement pagination for getAll operation (DET-6870)
feat(inspector/customers): Sort customers alphabetically (DET-1234)
fix(cases): Disabled cases not displayed (DET-1234)
feat(inodes): Support blob cleanup of trashed/deleted inodes (OSI-2345)
chore: Fix formatting issue (OSI-6886) (OSI-6914)
```

### Breaking Changes

```
feat(config)!: Introduce new configuration format
chore!: Drop support for Node.js 10 (OSI-6984)
```

### Including Issue IDs

```
fix(ui): Fix login button styling (OSI-456)
```

> [!NOTE]
> While the Jira ID is not part of the Conventional Commits specification, it is highly recommended to include it in the commit message. Add the Jira ID(s) in parentheses at the end of the description. Teams may decide if this step can be skipped in certain cases.

### Revert Commits

Use `Revert` to undo previous changes:

```
Revert "fix(cases): Disabled cases not displayed (DET-1234)"
Revert "chore(deps): Upgraded deps (DET-2345)"
```

## Consequences

Enforcing pull requests naming convention will standardise names accross all products and make easier to search and classify pull requests, create an explicit PRs history and makes easier to write automated tools on top of.
