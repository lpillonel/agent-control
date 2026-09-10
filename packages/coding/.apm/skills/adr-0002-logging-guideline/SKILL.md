---
name: imtf-adr-0002-logging-guideline
description: "Apply when working on spec, guideline in any repo. IMTF adr 0002-logging-guideline: Logging guideline."
---

# ADR-0002: Logging guideline

| Field  | Value                                                  |
| ------ | ------------------------------------------------------ |
| Date   | 2023-07-07                                             |
| Status | In-Progress \| In-Review \| **Accepted** \| Superseded |
| Tags   | spec, guideline                                        |

## Context

All IMTF applications are currently handling logging in their own way. The consequence of this situation is that the logs are difficult for the operational and support teams to understand, building common tools for log analysis and aggregation is very tedious and, obviously, our response time to production issue is impacted.

## Decision

Establish a common logging guideline for all IMTF applications. The guideline is maintained as a living document in the guidelines directory.

See [guidelines/0005-logging-guideline.md](https://github.com/imtf-group/imtf-adrs/blob/main/guidelines/0005-logging-guideline.md).

## Consequences

A common logging guideline improves log quality, enables shared tooling for analysis and aggregation, and reduces response time to production incidents. The guideline will be updated as experience is gained and feedback is received from product development, software operations, and support teams.
