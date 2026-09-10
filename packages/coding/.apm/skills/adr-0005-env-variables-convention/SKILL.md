---
name: imtf-adr-0005-env-variables-convention
description: "Apply when working on spec in any repo. IMTF adr 0005-env-variables-convention: Env variables convention."
---

# ADR-0005: Env variables convention

| Field  | Value                                                  |
| ------ | ------------------------------------------------------ |
| Date   | 2023-08-08                                             |
| Status | In-Progress \| In-Review \| **Accepted** \| Superseded |
| Tags   | spec                                                   |

## Context

All IMTF applications come with a large amount of configurable parameters which are likely to vary between deployments. Most of these configurable parameters are editable through environment variables (e.g. [12 factor app](https://12factor.net/config)).
As all applications now start to communicate to each others and share deployments, there is a need to put in place a naming convention for environment variables to improve separation, readability and avoid collisions.

## Decision

All externalized parameters that are editable using an environment variable must be prefixed with and identifier corresponding to the application.

### Digitalize

| Application        | Prefix |
| ------------------ | ------ |
| Folder Manager     | FM\_   |
| HS5 archive system | HS5\_  |
| ZV2                | ZV2\_  |

### Decide products

| Application             | Prefix |
| ----------------------- | ------ |
| Compliance Case Manager | CCM\_  |
| Alert Case Manager      | ACM\_  |
| Siron Decide            | DEC\_  |

### Detect products

| Application   | Prefix |
| ------------- | ------ |
| Siron Detect  | DET\_  |
| IMatch 6      | IM6\_  |
| Siron AML     | AML\_  |
| Siron KYC     | KYC\_  |
| Siron EMB     | EMB\_  |
| Siron TCR     | TCR\_  |
| RAS           | RAS\_  |
| WLL           | WLL\_  |
| ETL Validator | EVL\_  |

### Data lake products

| Application       | Prefix |
| ----------------- | ------ |
| Data Lake Storage | DLK\_  |

### RDBMS Liquibase migrator

| Application              | Prefix |
| ------------------------ | ------ |
| RDBMS Liquibase Migrator | RLM\_  |

### Kafka provisioner

| Application       | Prefix |
| ----------------- | ------ |
| Kafka provisioner | KAP\_  |

### ETL validator

| Application           | Prefix |
| --------------------- | ------ |
| ETL Validator Service | EVL\_  |

### Deletion controller

| Application         | Prefix |
| ------------------- | ------ |
| Deletion Controller | DLC\_  |

### Shared components

| Application        | Prefix |
| ------------------ | ------ |
| DMS core framework | DMS\_  |

### Documentation

Each product `must` maintain a document containing the list of all available variables handled by the application. This list contains at least the following information:

- The name of the variable
- The default value if any
- A description

## Consequences

Following the guideline above will avoid naming collisions and make easy to clearly identify which variables belongs to which applications. A clear and up to date documentation of these variables will make easy to discover configuration and help collaboration between teams and simplify the work of operational teams.
