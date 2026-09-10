---
name: imtf-adr-0007-oidc-env-vars-convention
description: "Apply when working on guideline in any repo. IMTF adr 0007-oidc-env-vars-convention: OIDC environment variables convention."
---

# ADR-0007: OIDC environment variables convention

| Field  | Value                                                  |
| ------ | ------------------------------------------------------ |
| Date   | 2026-03-18                                             |
| Status | In-Progress \| In-Review \| **Accepted** \| Superseded |
| Tags   | guideline                                              |

## Context

IMTF applications increasingly expose REST endpoints protected by an OIDC provider (e.g. Keycloak). Without a
shared convention, each application has independently named its OIDC-related environment variables, leading to
inconsistency and friction for operational teams managing multi-application deployments.

Additionally, [ADR-0005](https://github.com/imtf-group/imtf-adrs/blob/main/adr/0005-env-variables-convention.md) mandates that all environment variables be prefixed with
an application identifier. OIDC configuration variables, however, are cross-application by nature and therefore
require a specific exception to that rule.

## Decision

OIDC provider configuration supports two modes depending on whether the provider exposes an OIDC discovery
document

- Discovery mode
- Non-discovery mode (is a fallback for providers that do not support it or returns "non-matching" results).

In the context of this ADR, only **Discovery mode** is considered and should be supported.

All `OIDC_*` variables listed below are **global, cross-application** and are explicitly **exempt** from the
application-prefix rule defined in [ADR-0005](https://github.com/imtf-group/imtf-adrs/blob/main/adr/0005-env-variables-convention.md). They must **never** be prefixed
with an application identifier (e.g. `FM_OIDC_ISSUER_URL` is wrong; `OIDC_ISSUER_URL` is correct).

### Discovery mode

This mode follows the [OIDC Discovery specification](https://openid.net/specs/openid-connect-discovery-1_0.html).
Applications configure only the issuer URL; the `/.well-known/openid-configuration` suffix is appended
automatically by the application as mandated by the standard — it must **not** be included in `OIDC_ISSUER_URL`.
The application then fetches all endpoint URLs from that document automatically. Only three variables are required:

- `OIDC_ISSUER_URL` — the issuer URL of the OIDC provider
  (e.g. `https://keycloak.my-domain.com/realm/my-realm`)
- `OIDC_CLIENT_ID` — the client identifier
- `OIDC_CLIENT_SECRET` — the client secret

### Audience

When the application must verify the token audience, the expected value is provided via `OIDC_AUD`:

- `OIDC_AUD` — a single value audience that the application is validating against the token's `aud` claim. If unset, no specific audience validation is required.

### Use cases

#### Protecting your own REST endpoints

Use `OIDC_ISSUER_URL`, `OIDC_CLIENT_ID`, and `OIDC_CLIENT_SECRET` to configure the OIDC provider that
authenticates and authorizes access to the REST endpoints your service exposes. This is the primary use case for
these global variables.

#### Verifying the token audience

Set `OIDC_AUD` when your service must reject tokens not issued for it, e.g. tokens obtained for another resource
server sharing the same OIDC provider, for example.

- We use one Keycloak realm shared across the company services.
- Client A (a frontend) authenticates the user and gets an access token.
- That token is then forwarded to Service B (a backend service) as a bearer token. Service B never talked to the OIDC provider to request it.
- Service B only has OIDC_ISSUER_URL configured, so it has no OIDC_CLIENT_ID of its own tied to that token, or its OIDC_CLIENT_ID differs from the one used to issue the token.

Without an explicit audience check, Service B would accept any valid token from that issuer, including tokens meant for a completely different application on the same Keycloak instance.

### Backward compatibility

If an existing application already defined its own OIDC-related environment variables before this guideline was
adopted, those legacy variables **must be kept until the next major release**. If the standard `OIDC_*` variables
are set, they **must take precedence** over any corresponding legacy variable.

## Consequences

Standardizing OIDC environment variables under a single unprefixed convention reduces configuration inconsistency
across applications and simplifies operational deployments. The explicit exception to ADR-0005 for these variables
keeps the global nature of OIDC configuration visible and intentional. Supporting both discovery and non-discovery
modes ensures compatibility with OIDC providers that do not expose a well-known discovery document. The
backward-compatibility rule ensures existing deployments are not broken during the transition.
