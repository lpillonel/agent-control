---
name: imtf-adr-0006-rustfs-for-development
description: "Apply when working on guideline in any repo. IMTF adr 0006-rustfs-for-development: Adopt RustFS as a MinIO Replacement for Local Development and CI/CD."
---

# ADR-0006: Adopt RustFS as a MinIO Replacement for Local Development and CI/CD

| Field  | Value                                                  |
| ------ | ------------------------------------------------------ |
| Date   | 2026-03-10                                             |
| Status | In-Progress \| In-Review \| **Accepted** \| Superseded |
| Tags   | guideline                                              |

## Context

Most of our teams currently depend on MinIO to provide S3-compatible object storage service to their local development and CI/CD pipeline.
MinIO recent change of license (from Apache 2.0 to AGPL-3.0) and distribution mode make it unusable for IMTF.

Different alternative to MinIO have been evaluated such as RustFS, SeaweedFS and Garage.

## Decision

We recommend replacing MinIO with RustFS for all **local development** environments and **CI/CD pipeline** stages that require S3-compatible object storage. RustFS exposes a fully S3-compatible API, meaning no changes are required to application code or SDK configuration beyond updating the endpoint URL and credentials in configuration files.
The low memory overhead and fast startup make it well suited to ephemeral Docker-based CI runners. RustFS is available as a Docker image and can be used for Docker compose, test containers and CI pipeline service definitions.

Here is an example of RustFS usage in a docker compose file:

```yaml
rustfs:
  container_name: rustfs
  image: rustfs/rustfs:latest
  command: ["--console-address", ":9001"]
  ports:
    - "9000:9000" # S3 API
    - "9001:9001" # Console UI
  environment:
    RUSTFS_ACCESS_KEY: ${S3_ACCESS_KEY:-s3admin}
    RUSTFS_SECRET_KEY: ${S3_SECRET_KEY:-s3admin}
  volumes:
    - rustfs_data:/data
  healthcheck:
    test:
      [
        "CMD-SHELL",
        "curl -f http://localhost:9000/health && curl -f http://localhost:9001/rustfs/console/health || exit 1",
      ]
    interval: 10s
    timeout: 5s
    retries: 5
```

## Consequences

Application code and S3 SDK usage remain unchanged. This decision **does not cover the production use cases**. The production object storage strategy is unaffected by this decision and is covered by a separate decision.
Development teams and CI pipeline maintainers are responsible for updating the RustFS image version. A brief migration task is required to replace the MinIO service definition in `docker-compose.yml` and update CI service container references. No data migration is necessary as these environments are ephemeral.
