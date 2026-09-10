# ADR-0009: Use of presigned URLs

| Field  | Value                                                  |
| ------ | ------------------------------------------------------ |
| Date   | 2026-07-23                                             |
| Status | In-Progress \| **In-Review** \| Accepted \| Superseded |
| Tags   | guideline, platform                                    |

## Context

The PDF generator service produces PDF files from pre-defined templates. It uses an S3 bucket to store and expose the generated files, and the default mechanism for exposing them is a S3 presigned URL. Several operational constraints can, however, make presigned URLs unavailable:

- The S3 implementation does not support presigned URLs (e.g. Finanz Informatik).
- The S3 storage is not exposed to the browser (UI), which has no access to it for security reasons.
- The system sits behind a WAF that enforces authentication and SSO.

This ADR proposes a fallback mechanism for serving PDF files to the browser (UI) without relying on S3 presigned URLs. It is a company-wide architecture decision, as other services may be affected by similar restrictions.

## Decision

We propose to support two delivery modes, depending on network and security constraints:

- **Default mode**: the browser downloads directly from S3 using an S3-generated presigned URL.
- **Fallback mode**: the browser downloads via our service, using a **service-signed URL** that we issue when S3 cannot be exposed directly to the browser.

### Default mode - S3 presigned URLs

- Browser calls the service API to request an S3 presigned URL.
- Backend obtains a presigned URL scoped to the S3 object.
- Backend returns the URL to the browser.
- Browser downloads directly from S3, bypassing our service entirely for the file transfer itself.

### Fallback mode - service-signed URLs

- Browser calls the service API to request a presigned URL.
- Backend issues a service-signed URL.
- Backend returns the URL to the browser.
- Browser downloads from our service domain (`/download/*` or similar).
- Backend validates the URL, then fetches the file from S3 server-side and streams it back to the browser.

### Service-signed URL specification

The URL structure for service-signed URLs is the following:

```
GET|HEAD https://host:port/path/to/file.pdf?X-Key-Id=...&X-Algorithm=...&X-Expires=...&X-UserId=...&X-MaxDownloads=...&X-Signature=...
```

The request's HTTP method, the path and the query parameters are signed. The HTTP method is taken from the request itself and is not carried in the URL. The scheme and host are excluded, so that the same signature is valid whether the service is exposed behind `localhost:3000`, a CDN, or a load balancer with a different hostname.

**Reserved query parameters:**

| Parameter      | Value          | Required | Description                                                             |
| -------------- | -------------- | -------- | ----------------------------------------------------------------------- |
| X-Key-Id       | key1           | Yes      | Which secret key was used to sign the URL. Necessary for rotation.      |
| X-Algorithm    | HMAC-SHA256    | No       | Which signing algorithm was used. Allows the scheme to evolve.          |
| X-Expires      | Unix timestamp | Yes      | When the URL expires and is no longer valid.                            |
| X-Signature    | 64 hex chars   | Yes      | The HMAC-SHA256 output, the digital signature.                          |
| X-UserId       | user_1234      | No       | The user ID of the requester, obtained from the request token.          |
| X-MaxDownloads | 1              | No       | The maximum number of times the URL can be downloaded (see note below). |
| X-ClientIp │   | ip address     | No       | client's IP address                                                     |

> **Note:** unlike the other parameters, `X-MaxDownloads` cannot be enforced by the signature alone. It requires **server-side state** — a per-URL download counter that the backend increments and checks on each request.

> **Note:** the optional `X-ClientIp` parameter binds the URL to the client's IP address. It reduces the risk of leaked URL but add risks of false rejections (e.g. behind NAT or proxies).

**Full URL example:**

```
https://host:port/path/to/file.pdf
   ?X-Key-Id=key1
   &X-Algorithm=HMAC-SHA256
   &X-Expires=1784789777
   &X-UserId=u_1234
   &X-MaxDownloads=1
   &X-Signature=feafffb03c022d1c568e5718a25c0409d751d80abc4e83c758ef9c056c773d5c
```

The examples above are line-wrapped for readability only; an actual URL contains no whitespace.

Everything after `?` except `X-Signature` is sorted and canonicalised. The signature is then applied to the request's HTTP method, the path and the sorted, canonicalised query string.

**Signature calculation:**

The signature is calculated on the canonicalised string:

```
canonicalised = http_method + "\n" + path + "?" + sorted_query_string
```

`sorted_query_string` contains every query parameter except `X-Signature`. The reserved parameters `X-Algorithm`, `X-Expires`, `X-UserId` and `X-Key-Id` are all part of the signed payload and therefore cannot be tampered.

`http_method` is the request's HTTP verb in upper case. `HEAD` is normalised to `GET` before creating the signature, so a single pre signed URL can be used for both, the `GET` download and the `HEAD` pre-flight. Other verbs produce a different canonical string and therefore cannot be used for issuing`PUT`, `POST` or `DELETE` queries.

The canonicalised string is then signed with the secret key using the HMAC-SHA256 algorithm, the same as that used for the standard AWS S3 signature. HMAC-SHA256 is a symmetric key algorithm, so the same key is used for signing and verifying. It fits our use case well, as the client (the browser) does not need to validate the signature.

### Validation

When a service-signed URL is requested, the backend performs the following checks before serving the file:

- Reject the request if any required parameter (`X-Key-Id`, `X-Expires`, `X-Signature`) is missing. A URL without `X-Expires` in particular is not treated as non-expiring, it is rejected.
- Recompute the HMAC-SHA256 signature over the canonicalised string, using the secret key identified by `X-Key-Id`, and compare it against `X-Signature`. Because the request's HTTP method is part of that string (with `HEAD` normalised to `GET`), a download URL cannot be replayed with another verb.
- Reject the request if `X-Expires` is in the past. Because `X-Expires` is covered by the signature, this check is meaningful: the timestamp cannot have been altered without invalidating `X-Signature`.
- If `X-MaxDownloads` is present and implemented check and increment the server-side download counter and reject the request once the limit is reached.

If all checks pass, the backend loads the object from S3 and streams it back to the browser.

### Key rotation

Key storage and rotation are delegated to a Vault or another secret-management mechanism, which provides the `X-Key-Id` to secret map consumed by the library (see _Implementation_). During rotation, several keys can be active at once: `X-Key-Id` tells the verifier which key signed a given URL, so URLs issued with an older key stay valid until they expire.

### Implementation

We propose to provide this functionality as a shared Java library so that every service signs and verifies URLs the same way. The library should be framework-free (canonicalisation, signing, verification). Two aspects of the implementation remains the responsability of the user of the library:

- **Secret sourcing.** Signing secrets are not embedded in the library, they are supplied through configuration or aVault as a map of `X-Key-Id` to secret, which also enables rotation (see _Key rotation_).
- **`X-MaxDownloads` counter.** The stateful download counter is not owned by the library. The library exposes an SPI that each service implements against its own store, the library enforces the signed limit, the service provides the state.

## Consequences

- **Memory and load management** In fallback mode the file transfer passes through our service instead of going directly from the browser to S3, so the service carries the full download traffic. Responses must be streamed rather than buffered in memory, to avoid excessive memory usage for large PDF files.
- **Introduced server-side state.** `X-MaxDownloads` requires a per-URL download counter whichrequires a storage mechanism.
- **Key management.** The implementation must securely provide or store the signing secrets, identify them via `X-Key-Id`, and support rotation.
- **Portability.** Because the scheme and host are excluded from the signature, the same URL remains valid across environments (local, CDN, load balancer). This simplifies deployment, but means the signature does not bind the URL to a specific host.
- **Shared library** The signing and canonicalisation format is a contract. It must stay stable across library releases.
- **Company-wide adoption.** Other services subject to the same S3 restrictions can reuse this scheme. The default mode remains available where S3 presigned URLs are supported, so existing integrations are unaffected.
