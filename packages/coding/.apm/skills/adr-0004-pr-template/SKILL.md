---
name: imtf-adr-0004-pr-template
description: "Apply when working on process, guideline in any repo. IMTF adr 0004-pr-template: Pull Request Template."
---

# ADR-0004: Pull Request Template

| Field  | Value                                                  |
| ------ | ------------------------------------------------------ |
| Date   | 2023-09-01                                             |
| Status | In-Progress \| In-Review \| **Accepted** \| Superseded |
| Tags   | process, guideline                                     |

## Context

Pull requests are currently disparate between all products and inside a single product as well. It makes PR sometimes difficult to understand and to classify.

## Decision

Idea is to establish a common **Pull Requests template** for all IMTF products and tools.
This will help to have a common structure for all PRs and to have a better understanding of the changes.
It will also help developers to think about the changes they are doing and to have a better understanding of the impact of their changes.

The template has to be stored in the `.github` folder of each repositories and named `pull_request_template.md`.

It might be adapted per project but the following template is a good starting point:

```
# Description

Resolves [XXX-0000](https://imtf.atlassian.net/browse/XXX-0000)

Please include a summary of the changes and the related issue. Please also include relevant motivation and context. Provide screenshots, screen-records, logs, etc. if it helps understanding this pull request.

## Checklist:

- [ ] My code follows the style guidelines of this project
- [ ] I have performed a self-review of my code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] Log messages follow IMTF's [logging guidelines](https://github.com/imtf-group/imtf-adrs/blob/main/guidelines/01_logging.md)
- [ ] Public APIs are properly documented and have examples
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing tests pass locally with my changes
```

## Consequences

- Reviewing PRs will be easier and faster.
- Developpers will have a better understanding of the changes they are doing.
- Checklist will help to not miss important steps.
