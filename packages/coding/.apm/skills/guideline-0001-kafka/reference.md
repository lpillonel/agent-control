# Kafka guidelines

This document describes rules and guidelines regarding the use of Kafka at IMTF. The focus is on the Kafka client.

This document follows the [RFC 2119](https://datatracker.ietf.org/doc/html/rfc2119) about requirements levels.

## Design considerations

When designing a service using Kafka, engineers must carefully consider the following design principles:

- Emit events that represent state changes (e.g. alert created, case completed).
- Ensure publishers remain agnostic of consumers
- Avoid command-like events where possible
- Apply versioning at event level
- Follow deprecation and backward compatibility policies strictly
- Make events self-contained or use versioned lookups
- Respect the `Single Writer Principle` for producers
- Think about idempotency when designing consumers
- Implement robust error-handling strategies per consumer

## Topics

### Naming

The topic name should be chosen wisely and be self-explanatory about its usage and content.

- Each topic name `MUST`come with a default value following the naming convention described below.
- Topic names `MUST` always be configurable via an environment variable.

We apply the following naming convention for **default** topic names:

**Mandatory**

```
imtf.<domain>.<anything-else>
```

**Recommended**

```
imtf.<domain>.<entity>.<event-type>
```

- Use lowercase, hyphens as word separators within a segment, dots between segments
- No version suffix
- Event type in past tense (events describe facts that happened)

Examples:

- `imtf.icos.mdm.entity-created`
- `imtf.sirondetect.namescreening.scoring`
- `imtf.acm.alerts.created`
- `imtf.fm.documents.document.uploaded`

### Retention Policy

Any requirement about the retention policy `MUST` be documented clearly in
the [topic specification](#specification-format). Retention policies (e.g. retention time) may be
challenged by our customer and needs to be carefully designed.

- Define and document retention based on domain and lifecycle needs
- Choose time-based or compacted retention explicitly
- Document appropriate values for segment size

### Partitioning

Partitioning is a key feature in Kafka parallelism and ordering concept. Partitions number for each topic `MUST` be
clearly documented.

### Lifecycle

The creation of Kafka topics `MUST` be delegated to an external component.

## Producer

- Each producer `MUST` follow `Single Writer Principle`, meaning that only **one** producer is allowed per topic
- A client.id `MUST` be configured for observability and tracing. This client.id must be a fully qualified name and be
  attached to each message in the header. (see [Header](###Header))
- Producers `SHOULD` use acks=all to guarantee durability.
- Producers `SHOULD` use snappy compression.

## Consumer

- A consumer group Id (`group.id`) `MUST` be configured for each consumer. The group.id must be a fully qualified name (e.g.
  com.imtf.detect.namescreening.scoring).
- Consumer group Id `MUST` always be configurable via an environment variable.
- Avoid relying on `enable.auto.commit=true`. Instead, implement manual offset management to ensure better control over
  message processing and error handling.

### Error handling

Consumer error handling is critical to ensure the reliability and robustness of the system. The strategy for handling
errors should be designed wisely and take into consideration the use case handled by the consumer.

We identify 2 categories of consumer-side error:

- Poison pill errors
- Processing errors

#### Poison Pill Errors

- Occur when events always fail consumption
- Causes include corrupted events (rare) or deserialisation failures

Handling strategy:

- Skip events when deserialization fails and commit the offset to avoid blocking the consumer
- Log raw event for investigation

#### Processing Errors

- Occur **after** successful deserialisation
- Risk is to block consumers

Retry strategy:

- Implement a retry mechanism with a configurable number of attempts and backoff strategy
- Ensure retries are scoped to the consumer

Dead letter queue strategy:

- Move failed events to Dead Letter Topic (DLQ)
- Ensure DLQ are scoped to the consumer
- Do not use DLQ mechanism when strict ordering is required. In that case, consumers should stop and rely on a retry
  mechanism.

## Security

### Authentication

- Each client application `MUST` implements the following authentication mechanism:
  - SASL/PLAIN
  - SASL/SCRAM
  - SASL/OAUTH

- All mechanism `MUST` be supported and configurable through environment variables.

### Traffic encryption

- Each client application `MUST` implements the following traffic encryption mechanism:
  - SSL

- All mechanism `MUST` be supported and configurable through environment variables.

### Payload encryption

Payload encryption `SHOULD NOT` be implemented by the client application. We delegate this task to a central component
of the platform.

## Messages

Each Kafka message (record) contains:

- Header
- Key
- Value

### Header

- Use UTF-8 string key/value pairs **only**
- Include the following metadata:

| Key            | Mandatory | Notes                                                                       | Example                                                               |
| -------------- | --------- | --------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| encodingFormat | Yes       | The format used for serializing the message. Currently JSON is the default. | `application/json` or `application/avro` or `application/x-protobuf`  |
| recordType     | Yes       | Fully Qualified Name of event type                                          | `com.imtf.detect.namescrening.ScoringCompleted`                       |
| recordVersion  | Yes       | Version of the event schema                                                 | `1.0.3`                                                               |
| traceparent    | No        | Automatically added by OTEL instrumentation                                 | `traceparent:00-1d26d4b43332dd5048ea1023cd324ce6-e2e5d9a98d45faf9-01` |
| correlation-id | No        | For business correlation                                                    | `3e4d28fe-5964-4b8b-bb19-8211b9719a2d`                                |
| producer.id    | Yes       | Message producer identifier                                                 | `com.imtf.detect.namescreening.ScoringCompletedProducer`              |

#### Custom headers

- `MUST` follow all rules of standard headers
- `MUST` be named with the pattern of `X-{header}`, for example `X-my-own-header`
- Message consumers `MUST` ignore unknown headers

### Key

- Design your keys based on the partitioning strategy, not only identity.
- Avoid complex structures for keys, favor IDs or object references.

Examples:

- `"be4cde7e-f653-4298-8d8e-c1539876fc88"`
- `"cases://case/be4cde7e-f653-4298-8d8e-c1539876fc88"`

### Value

- No null value unless it is a tombstone for compacted topics

## Serialization / Deserialization

- Encode messages using JSON only
- Do not use Avro or Protobuf unless there is a strong justification and approval from the architecture board
- Avoid schema registry dependencies for public integrations
- Describe APIs using [AsyncAPI specifications](##Specification format)
- Use information in the header (recordType and recordVersion) for deserialization and consumer-side mapping.

## Versioning and lifecycle management

- Always assume consumers upgrade independently.
- Enforce strict compatibility rules.

### Topic Versioning

- Do not use topic versioning as it can lead to an explosion of the number of topics.
- Design topics with a clear domain and use message versioning.

### Message Versioning

- Create new message version for structural changes.
- New version of a message `MUST` be published to the same topic.
- Use the `recordVersion` header field to indicate the version of the message schema.
- Use the `recordType` header field to allow consumers to route and handle messages without inspecting the payload.
- Use semantic versioning for message versions.
- Use packages packages to define different **major** versions of classes of payloads. In example, the event `com.imtf.detect.namescrening.ScoringCompleted` could be defined in the package `com.imtf.detect.namescrening.v1.ScoringCompleted` for versions 1.x.x, `com.imtf.detect.namescrening.v2.ScoringCompleted` for versions 2.x.x and so on.

### Message schema management

- All message schemas `MUST` be documented using JSON Schema and included in the AsyncAPI specification.
- All AsyncAPI specification and corresponding message schema `MUST`be stored in
  the [siron one api repository](https://github.com/imtf-group/siron-one-api).
- All schema changes `MUST` be reviewed and approved before going to production.

### Breaking Changes

**Breaking changes are NOT allowed and should be avoided at all costs. Any breaking potential changes should be
discussed with the
architecture board and stakeholders**

Example of breaking changes:

- Removing a field
- Renaming a field
- Changing field type
- Altering payload structure
- Changing semantic meaning
- Making a previously optional field required
- Changing the `recordType` identifier

The preferred strategy for handling changes is deprecation:

- Use deprecation instead of breaking changes
- Mark deprecated fields in AsyncAPI schemas

Example:

```yaml
uri:
  type: string
  deprecated: true
```

### Consumer rules

- Consumers `MUST` handle missing optional fields gracefully.
- Consumers `MUST` ignore unknown fields.
- Consumers `MUST NOT` reject messages because of additional fields.

### API lifecycle rules

- Add new fields → No version change required
- Modify fields → Deprecate
- Modify field type or event structure → New event version
- Older events may still be consumed due to retention policies and reprocessing

## Specification format

We use AsyncAPI specifications to document our Kafka APIs. This allows us to have a standardized way to describe our
APIs and topologies such as topics, messages, and operations.

- All services `MUST` be documented using [AsyncAPI specifications](https://www.asyncapi.com/docs/reference) version
  3.0.0 or higher.
- Specifications `MUST` be stored in the [central APIs repository](https://github.com/imtf-group/siron-one-api).
- Specifications `MUST` be reviewed and approved by the architecture board before implementation.

### Info

- All specifications `MUST` use Semantic Versioning for the version field.
- All specification `SHOULD` include a clear and concise description of the specification.

```yaml
asyncapi: 3.0.0
info:
  title: Title of the specification
  version: 1.0.3
  description: |
    A clear and concise description of the specification. It should provide an overview of the purpose and scope of the specification, as well as any relevant context or background information.
```

### Channels

- Channel specification `SHOULD` follow the official AsyncAPI specification format.
- Owner of the channel `MUST` be specified using the `x-owner` field in the channel specification.
- Kafka topic specific configuration `MUST` be included in the channel specification using [kafka channel binding](https://github.com/asyncapi/bindings/blob/master/kafka/README.md#channel).
- Environment variables used for configurable properties (e.g. topic name) `MUST` be clearly documented in the description.

```yaml
x-owner: acm-adapter
```

```yaml
bindings:
  kafka:
    topic: acm.{acmTenantId}.events_in
    topicConfiguration:
      cleanup.policy: [delete]
      retention.ms: 604800000
    partitions: 5
    bindingVersion: "0.5.0"
```

### Operations

- Producers `MUST` be specified under the `publish` section of the channel specification.
- Consumers `MUST` be specified under the `subscribe` section of the channel specification.
- Kafka consumer specific configuration `MUST` be included in the operation specification using [kafka operation bindings](https://github.com/asyncapi/bindings/blob/master/kafka/README.md#operation).
- Environment variables used for configurable properties (e.g. consumer group id) `MUST` be clearly documented in the description. Use the `x-group-id-override` extension.

```yaml
bindings:
  kafka:
    groupId:
      type: string
      default: ACM
    x-group-id-override:
      configurable: true
      env-variable: ACM_CONFIG_MESSAGING_KAFKA_CONSUMER_GROUPID
    bindingVersion: "0.5.0"
```

### Messages

- Messages `MUST` be specified in the `message` section of the operation specification.
- Define message key using [kafka message bindings](https://github.com/asyncapi/bindings/blob/master/kafka/README.md#message).
- Define the message headers using the `headers` field in the message specification.
- Define the header structure by referencing the IMTF common header schema.

```yaml
messages:
  customerCreated:
    name: CustomerCreated
    title: Customer Created event
    summary: Emitted when a user successfully registers.
    contentType: application/json
    bindings:
      kafka:
        key:
          type: string
          description: The customer ID used as the Kafka message key.
        bindingVersion: "0.5.0"

    headers:
      name: headers
      title: IMTF common Kafka header
      $ref: "#/components/schemas/headers"
    payload:
      type: object
      properties:
        customerId:
          type: string
          description: This property describes the id of the customer
        firstName:
          type: string
          description: This property describes the first name of the customer
        lastName:
          type: string
          description: This property describes the last name of the customer
        birthday:
          type: number
          format: date
          pattern: ^\\d{4}-\\d{2}-\\d{2}$
          description: This property describes the birthday of the customer
      required:
        - customerId
        - firstName
        - lastName
```

Header schema:

```yaml
components:
  schemas:
    headers:
      name: headers
      title: IMTF common Kafka headers
      type: object
      properties:
        encoding-format:
          type: string
          description: Serialization format of the message
          enum:
            - AVRO
            - JSON
            - PROTOBUF
        record-type:
          type: string
          description: Fully qualified name of the event type
          example: com.imtf.alert.AlertCreated
        record-version:
          type: string
          description: Version of the event schema (SemVer)
          example: 1.2.5
        producer-id:
          type: string
          description: Message producer identifier
          example: com.imtf.acm.AlertProducer
        traceparent:
          type: string
          description: Automatically added by OTel instrumentation
          example: 00-1d26d4b43332dd5048ea1023cd324ce6-e2e5d9a98d45faf9-01
        correlation-id:
          type: string
          description: Correlation ID for request tracing. Used for business correlation, otherwise use OTel traceparent.
          example: 3e4d28fe-5964-4b8b-bb19-8211b9719a2d
      required:
        - encoding-format
        - record-type
        - record-version
        - producer.id
```
