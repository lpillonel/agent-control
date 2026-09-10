---
name: imtf-guideline-0002-observability
description: "Apply when working on observability in any repo. IMTF guideline 0002-observability: Observability guidelines."
---

# Observability guidelines

This document describes rules and guidelines regarding applications observability at IMTF.

This document follows the [RFC 2119](https://datatracker.ietf.org/doc/html/rfc2119) about requirements levels.

## General principles

- All applications `MUST` be instrumented to expose metrics, logs and traces.
- Instrumentation `MUST` use the [OpenTelemetry](https://opentelemetry.io/) (OTel) SDK and API.
- Application `SHOULD` use auto-instrumentation when available for their language and framework.
- Applications `SHOULD` export telemetry to a centralized collector (OpenTelemetry Collector) rather than directly to a
  backend.

## Metrics

- All applications `MUST` expose basic system metrics (CPU, memory, disk, network) and application metrics (request
  count, latency, error count)
  using [OTel semantic conventions](https://opentelemetry.io/docs/concepts/semantic-conventions/).
- Metric names `MUST` follow the [OTel naming convention](https://opentelemetry.io/docs/concepts/semantic-conventions/):
  `<namespace>.<unit>` in snake_case (e.g.,
  `http.server.request.duration`).
- Cardinality `SHOULD` be considered with care. Dynamic values (user IDs, URLs with path params) `MUST NOT` be used as
  metric attributes.
- Custom business metrics `SHOULD` be defined for domain related information (e.g., document ingested rate, alert
  created, ... ).
- Custom technical metrics `SHOULD` be defined for technical information (e.g., consumer lag, cache hit rate, db
  connection pools, ... ).

## Logs

- Logs `MUST` follow IMTF internal [logging guidelines](https://portal.imtf.dev/docs/policies/logging).
- All logs `MUST` be structured (JSON format) when exposed via OTel signals.
- Logs `SHOULD` include the OTel correlation fields `trace_id` and `span_id` when emitted within a traced context. The
  part is usually handle by the instrumenting agent.
- Sensitive data (PII, secrets, tokens) **MUST NOT** appear in log messages or fields.

## Traces

(WIP - to be completed in a future version of this document)

- Spans `MUST` follow the [OTel semantic conventions](https://opentelemetry.io/docs/concepts/semantic-conventions/) for
  naming and
  attributes.

## Resource attributes

- All application `MUST` set a default `service.name`
- Additional attributes (`service.namespace`, `host.name`, `k8s.pod.name`, ...) `MUST NOT` be added by the application.
  We use collector's processing stage for that purpose.
