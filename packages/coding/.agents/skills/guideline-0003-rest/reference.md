# REST API guidelines

| Revision | Date       | Info                                                                         |
| -------- | ---------- | ---------------------------------------------------------------------------- |
| 1        | 2026-03-27 | Initial document                                                             |
| 2        | 2026-08-14 | Scope the `errors` extension member to field-level `400` validation failures |

This document describes rules and guidelines regarding REST APIs at IMTF.

This document follows the [RFC 2119](https://datatracker.ietf.org/doc/html/rfc2119) about requirements levels.

## Scope

We differentiate 2 different scopes for our APIs:

**Private**: Private APIs or internal APIs are used exclusively within IMTF and within the same domain. They are not used by
external parties and are not documented for external use. Typical usages are for communication between microservices of
the same domain, or for communication between a frontend and a backend.

**Public**: External APIs or public APIs are for inter-domain communication, communication with external parties, or
communication between microservices of different teams.

## Naming

All endpoints `MUST` be prefixed with the service domain:

```
/acm/alert-cases/
/fm/documents/
```

Resources `MUST` be identified by nouns, not verbs.

```
OK:  /users, /cases, /documents
NOK: /getCases, /createDocuments
```

You `MUST` use plural for resource names.

```
/users/{id}/cases
```

You `MUST` use kebab-case for URLs.

```
/alert-cases
```

You `MUST` use camelCase for JSON fields.

```
createdAt, alertId
```

You `MUST` use standard HTTP methods or verbs.

```
GET /documents
POST /documents
GET /documents/{id}
PATCH /documents/{id}
DELETE /documents/{id}
```

## Versioning and Lifecycle Management

- APIs `MUST` be versioned.
- The version `MUST` be included in the URL path, prefixed with `v` followed by a positive integer. It `MUST` appears
  after the context path and before the resource path or endpoint:

  ```
  https://api.example.com/v1/cases
  https://api.example.com/v1/documents/123
  https://api.example.com/acm/v1/alerts  ← with context path
  ```

- Query parameter versioning (e.g., `?version=1`) and header versioning (e.g., `Api-Version: 1`) `MUST NOT` be used.

### Breaking changes

**Breaking changes are NOT allowed and should be avoided at all costs. Any potential breaking changes should be
discussed with the architecture board and stakeholders**

Examples of breaking changes:

- Removing an endpoint
- Renaming an endpoint
- Modifying an endpoint HTTP verb
- Modifying returned status code
- Modifying error response format
- Changing semantic meaning of an endpoint
- Change in request and response such as:
  - Renaming a field
  - Removing a field
  - Changing field type
  - Changing a field constraints (e.g.maxLength, enum values, formatting)
  - Altering payload structure
  - Making a previously optional field required

The preferred strategy for handling changes is deprecation:

- Use deprecation instead of breaking changes
- Mark deprecated endpoints and fields in OpenAPI specifications (
  see [Documenting deprecation](#documenting-deprecation))
- Deprecation `MUST` be announced through official channels (e.g., developer portal, changelog, mailing list) at the
  time of deprecation.
- Deprecated versions `MUST` return a `Deprecation` response header (
  see [RFC 9745 format](https://datatracker.ietf.org/doc/rfc9745/)).

```
HTTP/1.1 200 OK
Deprecation: Sun, 01 Jun 2025 00:00:00 GMT
Content-Type: application/json
```

In case a breaking change is decided and accepted, the following rules apply:

- The version number `MUST` only be incremented on breaking changes. Non-breaking additions (new fields, new
  endpoints) `MUST NOT` trigger a version bump.
- At least one previous major version `SHOULD` remain supported after releasing a new one.

### Sunset and Removal

- A minimum deprecation notice period of **1 year** `MUST` be observed before removing any endpoint or field.
- Sunset dates `SHOULD` be announced through official channels (e.g., developer portal, changelog,
  mailing list) at the time of the sunset date is decided, not only at removal.
- Impacted consumers `SHOULD` be identified and directly notified when possible.
- Removal `MUST` be discussed with the architecture board and stakeholders.
- Sunset date `SHOULD` be returned part of the `Deprecation` response header (
  see [RFC 8594 format](https://datatracker.ietf.org/doc/rfc8594/)).

```
HTTP/1.1 200 OK
Deprecation: Sun, 01 Jun 2025 00:00:00 GMT
Sunset: Sun, 01 Jun 2026 00:00:00 GMT
Content-Type: application/json
```

## Authentication and authorization

- All REST APIs `MUST` use [OAuth 2.0](https://datatracker.ietf.org/doc/html/rfc6749)
  with [OIDC](https://openid.net/specs/openid-connect-core-1_0.html) as authentication and authorization mechanism.
  This applies to both internal and external APIs.
- Tokens are issued as [JWT](https://datatracker.ietf.org/doc/html/rfc7519) signed by the OIDC provider.

### Bearer token

- Clients `MUST` pass the access token as a Bearer token in the `Authorization`
  header ([RFC 6750](https://datatracker.ietf.org/doc/html/rfc6750)):
  ```
  Authorization: Bearer <access_token>
  ```
- Tokens `MUST NOT` be passed via query parameters or request body.
- All endpoints `MUST` be served over TLS (HTTPS). Tokens `MUST NOT` be transmitted over unencrypted connections.

### Token validation

- Services `MUST` validate the token signature using the public key retrieved from the JWKS
  endpoint published in the OIDC discovery document.
- Services `MUST` reject any token whose signature cannot be verified.
- Services `MUST` verify that the `exp` claim is in the future and reject expired tokens.
- Services `MUST` verify that the `aud` claim matches the expected resource server or client.
  identifier ([RFC 7519](https://datatracker.ietf.org/doc/html/rfc7519#section-4.1.3)).
- Services `MUST` verify that the token contains the required claims to perform the requested operation if any authorization is required.
- Services `SHOULD` verify that the `azp` claim matches the expected client identifier.

### OAuth 2.0 flows

Use the flow appropriate to the client type:

| Client type                          | Required flow             |
| ------------------------------------ | ------------------------- |
| User-facing frontend (SPA, web app)  | Authorization Code + PKCE |
| Machine-to-machine / service account | Client Credentials        |

- The Implicit flow `MUST NOT` be used.
- For user facing flows, refresh tokens `MUST` be used to obtain new access tokens without re-authentication.
- Access token lifetime `SHOULD` be short (≤ 5 minutes for sensitive endpoints).

### OIDC provider configuration

- Services `MUST` configure the OIDC provider using the standardized environment variables defined
  in [ADR-0007](https://github.com/imtf-group/imtf-adrs/blob/main/adr/0007-oidc-env-vars-convention.md):
  - `OIDC_ISSUER_URL` — the issuer URL (e.g. `https://keycloak.my-domain.com/realm/my-realm`)
  - `OIDC_CLIENT_ID` — the client identifier
  - `OIDC_CLIENT_SECRET` — the client secret (for confidential clients only)
  - `OIDC_AUD` — when your service must reject tokens not issued for it, e.g. tokens obtained for another resource
- Services `MUST` retrieve JWKS keys from the OIDC discovery document (e.g.
  `<OIDC_ISSUER_URL>/.well-known/openid-configuration`).

### Error responses

- A missing or malformed token `MUST` return `401 Unauthorized` with a `WWW-Authenticate: Bearer` header.
- An expired or invalid token `MUST` return `401 Unauthorized`.
- A valid token with insufficient permissions `MUST` return `403 Forbidden`.
- Error responses `MUST` use the `problem+json` format (see [Error response](#error-response)).
- Error details `MUST NOT` reveal why token validation failed (e.g., do not expose `signature invalid` or
  `token expired` in the response body) to avoid information leakage.

## Error response

If an API returns an error, the response body contains
a [problem detail encoded in json](https://www.rfc-editor.org/rfc/rfc9457).

Every REST endpoints:

- MUST use `problem+json` as error response format
- SHOULD use the `errors` extension member when a `400` reports one or more field-level input validation failures
- MUST use absolute URIs for the `type` field in the problem detail object (
  e.g. https://apis.imtf.dev/problems/invalid-params)
- SHOULD register problem types in the [central APIs repository](https://github.com/imtf-group/siron-one-api)
- SHOULD re-use existing problem types

The Problem JSON object is using the media type `application/problem+json` and provide a human and machine-readable
error information. The problem detail object has the following properties:

| property                                                         | type   | required | note                                                                     |
| ---------------------------------------------------------------- | ------ | -------- | ------------------------------------------------------------------------ |
| [type](https://www.rfc-editor.org/rfc/rfc9457#section-3.1.1)     | string | no       | If none is available, use **about:blank** value                          |
| [title](https://www.rfc-editor.org/rfc/rfc9457#section-3.1.3)    | string | no       |                                                                          |
| [status](https://www.rfc-editor.org/rfc/rfc9457#section-3.1.2)   | number | no       | if status is present it **MUST** have the same value as HTTP status code |
| [detail](https://www.rfc-editor.org/rfc/rfc9457#section-3.1.4)   | string | no       |                                                                          |
| [instance](https://www.rfc-editor.org/rfc/rfc9457#section-3.1.5) | string | no       |                                                                          |

Example of a problem detail object:

```json
{
  "type": "about:blank",
  "title": "Forbidden",
  "status": 403,
  "detail": "You are not allowed to view this alert",
  "instance": "/alert/12345/"
}
```

The [Problem detail RFC](https://www.rfc-editor.org/rfc/rfc9457#section-3.2) defines an extension members clause, which
allows
to extend problem detail with an additional object. For example, a validation error may contain additional information
in an `errors` field:

```json
{
  "type": "https://apis.imtf.dev/problems/validation-error",
  "title": "Validation failed",
  "instance": "/customer/1234",
  "status": 400,
  "errors": [
    {
      "type": "invalid_params",
      "title": "Invalid Parameter",
      "instance": "/age",
      "detail": "age must be a positive integer"
    },
    {
      "type": "invalid_params",
      "title": "Invalid Parameter",
      "instance": "/firstname",
      "detail": "firstname is a mandatory field"
    }
  ]
}
```

## HTTP status codes

- APIs `MUST` use only official HTTP status codes as defined in [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110).
- APIs `MUST` use the most specific applicable status code for each outcome.
- APIs `MUST NOT` return a `2xx` status code when the operation failed (e.g. returning `200 OK` with an error body is not acceptable).
- Each endpoint `MUST` document its success and error status codes in the OpenAPI specification.

The following tables list the most commonly used status codes. They are not exhaustive, teams `MUST` use the most specific official code applicable to their use case.

### 2xx – Success

| Code | Name       | When to use                                                                                                       |
| ---- | ---------- | ----------------------------------------------------------------------------------------------------------------- |
| 200  | OK         | Default success for `GET`, `PUT`, `PATCH` with a response body.                                                   |
| 201  | Created    | `POST` that successfully created a resource. `MUST` include a `Location` header pointing to the created resource. |
| 202  | Accepted   | Async operation accepted but not yet completed. `MUST` provide a way to poll or be notified of the outcome.       |
| 204  | No Content | Successful `DELETE` or write operation with no response body.                                                     |

### 4xx – Client errors

| Code | Name                   | When to use                                                                                                                                                                                                |
| ---- | ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 400  | Bad Request            | Malformed request syntax or failed input validation.                                                                                                                                                       |
| 401  | Unauthorized           | Missing, invalid, or expired token (see [Authentication and authorization](#authentication-and-authorization)). When using Bearer token authentication, `MUST` return a `WWW-Authenticate: Bearer` header. |
| 403  | Forbidden              | Valid token with insufficient permissions (see [Authentication and authorization](#authentication-and-authorization)).                                                                                     |
| 404  | Not Found              | Resource identified by the URI does not exist.                                                                                                                                                             |
| 405  | Method Not Allowed     | HTTP verb not supported on this resource.                                                                                                                                                                  |
| 409  | Conflict               | Request conflicts with the current state of the resource (e.g. duplicate, optimistic lock violation).                                                                                                      |
| 415  | Unsupported Media Type | `Content-Type` sent by the client is not accepted.                                                                                                                                                         |
| 422  | Unprocessable Entity   | Request is syntactically valid but semantically incorrect (e.g. business rule violation).                                                                                                                  |

### 5xx – Server errors

| Code | Name                  | When to use                                                                                         |
| ---- | --------------------- | --------------------------------------------------------------------------------------------------- |
| 500  | Internal Server Error | Unexpected server-side failure. `MUST NOT` expose stack traces or internal details in the response. |

> [!IMPORTANT]
> All error responses `MUST` use the `problem+json` format described in [Error response](#error-response).

## Specification format

We use OpenAPI specifications to document our REST APIs. This allows us to have a standardized way to describe our
APIs.

- All services `MUST` be documented using [REST API specifications](https://spec.openapis.org/oas/latest.html) version
  3.0.0 or higher.
- Specifications `MUST` be stored in the [central APIs repository](https://github.com/imtf-group/siron-one-api).
- Specifications `MUST` be reviewed and approved by the architecture board before being released.

### Documenting deprecation

Deprecation `MUST` be documented in the OpenAPI specification using the `deprecated: true` flag. This applies at both,
the endpoint and field level.

**Deprecated endpoint:**

```yaml
paths:
  /v1/alerts/{id}:
    get:
      summary: Get alert by ID
      deprecated: true
      description: >
        **Deprecated.** Use `GET /v2/alerts/{id}` instead.
        This endpoint will be removed after 2026-06-01.
      ...
```

**Deprecated request/response field:**

```yaml
components:
  schemas:
    User:
      type: object
      properties:
        id:
          type: string
        username:
          type: string
        login:
          type: string
          deprecated: true
          description: >
            **Deprecated.** Use `username` instead.
            Will be removed after 2026-06-01.
```
