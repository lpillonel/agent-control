# Logging guideline

This document describes rules and guidelines regarding application logging at IMTF.

This document follows the [RFC 2119](https://datatracker.ietf.org/doc/html/rfc2119) about requirements levels.

## General principles

- All applications `MUST` emit structured logs.
- The log format `MUST` be configurable between `JSON` and `PLAIN-TEXT` output.
- In containerized environments, logs `MUST` be written to `stdout`. File-based appenders `MUST NOT` be used .
- Applications `SHOULD` export logs via the centralized OpenTelemetry Collector in accordance with
  the [observability guidelines](https://github.com/imtf-group/imtf-adrs/blob/main/guidelines/0002-observability.md).
- Sensitive data (PII, secrets, tokens) `MUST NOT` appear in log messages or fields.
- Log levels `SHOULD` be adjustable at runtime without pod restart (see [Configuration](#configuration)).

## Log levels

| Level   | When to use                                                                                                       |
| ------- | ----------------------------------------------------------------------------------------------------------------- |
| `DEBUG` | Diagnostic information useful during development or troubleshooting.                                              |
| `INFO`  | Normal operational lifecycle events (service start, configuration loaded, scheduled job completed).               |
| `WARN`  | Unexpected but recoverable conditions (dependency degraded, retry exhausted, non-critical configuration missing). |
| `ERROR` | Failures that disrupt an operation and require investigation. `MUST` include the full exception or root cause.    |

- Application code `MUST NOT` use `TRACE` level as it is not universally available across all frameworks and languages.
- Kubernetes liveness and readiness probe endpoints `MUST NOT` produce log entries.

## Log timestamp

The timestamp should follow the ISO8601 specification and by default use the local timezone.

```
2019-01-18T01:19:42-03:00
```

The pattern %d{ISO8601_OFFSET_DATE_TIME_HH} allows to display the date with the timezone information suffixed.

If the application components are spread across different timezones, it make sense to use UTC in order to homogenise the
timing information. This can be achieved with the pattern %d{yyyy-MM-dd HH:mm:ss.SSSZ}{GMT+0} (e.g. log4j2).

## PLAIN-TEXT log format

Plain-text log entries `MUST` include the following fields:

```
TIMESTAMP | LEVEL | CORRELATION_ID | CLASS_NAME | MESSAGE
```

We are using a pipe ('|') as a field separator to facilitate the use of parsing tools like awk, sed, grep or logs
aggregators.

**Example:**

```
2025-06-01T12:00:00.123Z | INFO  | 3e4d28fe-5964-4b8b-bb19-8211b9719a2d | com.imtf.acm.AlertCaseService | Alert case created
```

## JSON log format (Draft)

JSON structured log entries `MUST` include the following fields:

| Field            | Required       | Notes                                                                                                                                   |
| ---------------- | -------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `timestamp`      | Yes            | ISO 8601 UTC, millisecond precision, `Z` suffix (e.g. `2025-06-01T12:00:00.123Z`)                                                       |
| `level`          | Yes            | Uppercase: `DEBUG`, `INFO`, `WARN`, `ERROR`                                                                                             |
| `message`        | Yes            | Human-readable description. Structured data `MUST` use dedicated fields, not the message.                                               |
| `service.name`   | Yes            | OTel resource attribute matching the value declared at application startup. Uses OTel dot notation, not snake_case.                     |
| `logger`         | Yes            | Source logger identifier: fully-qualified class name for Java (e.g. `com.imtf.acm.AlertCaseService`), or equivalent for other runtimes. |
| `trace_id`       | When in trace  | Injected automatically by the OTel instrumentation agent. `MUST NOT` be set manually.                                                   |
| `span_id`        | When in trace  | Injected automatically by the OTel instrumentation agent. `MUST NOT` be set manually.                                                   |
| `correlation_id` | When available | Business correlation identifier (see [Correlation and context](#correlation-and-context)).                                              |

Custom additional fields `MAY` be added for domain context. Custom field names `MUST` use `snake_case`. OTel semantic
attributes `MUST` use their standard dot-notation names.

```json
{
  "timestamp": "2025-06-01T12:00:00.123Z",
  "level": "INFO",
  "message": "Alert case created",
  "service.name": "acm-service",
  "logger": "com.imtf.acm.AlertCaseService",
  "trace_id": "1d26d4b43332dd5048ea1023cd324ce6",
  "span_id": "e2e5d9a98d45faf9",
  "correlation_id": "3e4d28fe-5964-4b8b-bb19-8211b9719a2d",
  "case_id": "be4cde7e-f653-4298-8d8e-c1539876fc88"
}
```

## Correlation and context

- The OTel instrumentation agent `SHOULD` inject `trace_id` and `span_id` into the logging context automatically.
- A `correlation_id` `SHOULD` be propagated across service boundaries for business-level correlation (distinct from OTel
  tracing). It `MUST` be forwarded from inbound HTTP headers or Kafka message headers (
  see [Kafka guidelines](https://github.com/imtf-group/imtf-adrs/blob/main/guidelines/0001-kafka.md)).
- Services `MUST NOT` generate a new `correlation_id` if one is already present in the inbound context.
- MDC (Mapped Diagnostic Context) or an equivalent runtime context mechanism `SHOULD` be used to carry correlation
  fields across thread and async boundaries without requiring them as explicit log statement arguments.

## Configuration

- The active log level `MUST` be configurable via an environment variable. Valid values are `DEBUG`, `INFO`, `WARN`,
  `ERROR`.
- Log configuration `MUST NOT` be baked into container images in a way that prevents runtime override via environment
  variables.

## Sensitive data

- Personally identifiable information (names, email addresses, national identifiers, financial account numbers)
  `MUST NOT` appear in log messages or structured fields. When necessary for troubleshooting, including non critical PII
  like person names `MUST`be carefully considered, validated by POs and management.
- Authentication credentials, API keys, secrets, and tokens `MUST NOT` be logged under any circumstance.
- HTTP request and response bodies `MUST NOT` be logged in production. Diagnostic body logging `MUST` be gated behind
  `DEBUG` level and `MUST` apply field-level masking before output.
- Business entity identifiers (case IDs, customer IDs) `MAY` be logged to support incident investigation, provided they
  do not directly expose PII.

## Kubernetes and container deployment

- Applications `MUST` log exclusively to `stdout`. File-based and rolling-file appenders `MUST NOT` be configured in
  container images.
- Log collection and forwarding to the OTel Collector is handled by the platform (OTel Agent or OTel Collector sidecar).
  Applications `MUST NOT` implement their own log forwarding or aggregation.
- Log enrichment with pod metadata (`k8s.pod.name`, `k8s.namespace.name`, node labels) is performed by the collector
  pipeline. Applications `MUST NOT` add Kubernetes metadata fields to log entries.
- Applications `MUST NOT` rely on log persistence beyond the lifetime of a pod. If durability is required `MUST` be
  stored in a dedicated persistent store.

## Java implementation

### Logging facade

- Application code `SHOULD` use [SLF4J](https://www.slf4j.org/) as the logging facade. Logging implementation APIs (
  Logback, Log4j2, JUL) `MUST NOT` be used directly in application code.
- Parameterized log statements `MUST` be used to avoid unnecessary string construction when the log level is disabled:

### Recommended backends

| Framework | Logging backend                        | JSON output                                      |
| --------- | -------------------------------------- | ------------------------------------------------ |
| Quarkus   | JBoss Logging (SLF4J bridge available) | `quarkus-logging-json` extension                 |
| Other JVM | Logback or Log4j2                      | `logstash-logback-encoder` or Log4j2 JSON layout |

- Async appenders `SHOULD` be used in high-throughput services to prevent logging I/O from blocking application threads.
