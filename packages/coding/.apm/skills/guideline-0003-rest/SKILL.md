---
name: imtf-guideline-0003-rest
description: "Apply when working on rest in any repo. IMTF guideline 0003-rest: REST API guidelines."
---

# REST API guidelines

| Revision | Date       | Info                                                                         |
| -------- | ---------- | ---------------------------------------------------------------------------- |
| 1        | 2026-03-27 | Initial document                                                             |
| 2        | 2026-08-14 | Scope the `errors` extension member to field-level `400` validation failures |

This document describes rules and guidelines regarding REST APIs at IMTF.

This document follows the [RFC 2119](https://datatracker.ietf.org/doc/html/rfc2119) about requirements levels.


## Sections in this document (see reference.md for full text)

- ## Scope
- ## Naming
- ## Versioning and Lifecycle Management
- ### Breaking changes
- ### Sunset and Removal
- ## Authentication and authorization
- ### Bearer token
- ### Token validation
- ### OAuth 2.0 flows
- ### OIDC provider configuration
- ### Error responses
- ## Error response
- ## HTTP status codes
- ### 2xx – Success
- ### 4xx – Client errors
- ### 5xx – Server errors
- ## Specification format
- ### Documenting deprecation

Full text: reference.md in this skill folder, or [guidelines/0003-rest.md](https://github.com/imtf-group/imtf-adrs/blob/main/guidelines/0003-rest.md) in the imtf-adrs repository.
