# AI and ML guidelines

This document describes rules and guidelines regarding the development, deployment, and operation of AI and ML components at IMTF. The scope covers all AI and ML components without exception, including predictive models, scoring engines, analytics pipelines, simulation models, and agent-based systems. Simulation and analytics components must additionally demonstrate with quantitative metrics that their outputs reliably match actual observed outcomes.

This document follows the [RFC 2119](https://datatracker.ietf.org/doc/html/rfc2119) about requirements levels.

## Scope

These guidelines apply to every AI and ML component developed or operated at IMTF, including:

- Supervised and unsupervised predictive models
- Rule-based scoring engines with learned parameters
- Simulation models and Monte Carlo engines
- Analytics and reporting pipelines producing derived metrics
- LLM-backed and agent-based AI components
- Any third-party AI component integrated into a SironOne or IMTF product

**Any AI or ML component at IMTF that is not registered in the IMTF AI Core MLFlow model registry, or for which versioned test data, performance metrics, a model card, and DQ rules for training and inference do not exist, is non-compliant and `MUST NOT` be deployed to any environment.**

For simplicity the document will use AI & ML or AI when referencing to the entire scope above.

## Regulatory compliance

Model engineers are responsible for building compliant models and handling data appropriately. The following `MAY` be usefule to unserstand before designing or modifying any model:

- The [European Union AI Act](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689) — IMTF models are treated as high-risk AI systems under Annex III if the scope goes beyond fraud and financial crime detection. This may trigger more stringent bias evaluation and wider public safety requirements under Union law.
- [GDPR](https://gdpr-info.eu/) — the profiling restriction exception applies for money-laundering detection when complying with sectoral Union law. Sensitive trait inference (gender, sexual orientation, nationality) is prohibited.
- [ISO 27001](https://www.iso.org/standard/27001) — information security guidelines apply as relevant to each model and its data assets.
- [OWASP LLM Top-10](https://genai.owasp.org/llm-top-10/) - LLM security risks are expected to be covered with test and validation data or mitigation measures as part of the devops pipeline.

Any AI system developed or operated by IMTF is **strictly** and only for the functional purpose of the detection of fraud, money laundering, or sanction evasion.

## Platform reuse

The **SironOne AI Core** and the **IMTF AI Core** are two functionally equivalent platforms differing only in their runtime environments. Both provide:

- Versioned data storage in a Delta Lake (S3A protocol)
- A Spark Connect Server (`spark-connect-service:15002`) as the entry-point for distributed compute
- An MLFlow model registry (`mlflow-server-tracking:80`) for storage of model artifacts (e.g., ONNX), DQ results, model cards, and performance metrics

All AI & ML initiatives `MUST` use the SironOne AI Core platform for any new initiative and **migrate** to the platform with in **24 months**. An exception or extension may be requested to the Architecture Board. the SironOne AI Core is designed for customer facing product features.

Model experiments `MUST` use the IMTF AI Core for model training **effective immediately**. The IMTF AI Core is designed for in-house model training and inference.

For each model there will be one AI Service Manager to provide an interaction interface to the model. The AI Service Manager exposes all external interfaces at TCP 8000 (REST) with co-located Kafka, gRPC, and streaming socket interfaces. All AI model repositories `MUST` derive from the [ai-core-template](https://github.com/imtf-group/ai-core-template).

Using the AI Core compnents ensures in large part adherance to the AI & ML guidelines.

## Model execution controls

Many models must have an element of control to allow adjusting the model behavior to individual risk and business charactersitics. If the model has such controls, either through reward function weights, feature importance or post-training mechanisms the model `MUST` be evaluated against a baseline set of parameters and further:

- Baseline configuration setting and all options `MUST`be included as part of
  [Configuration and environment variables](Configuration-and-environment-variables)
- The actual setting used for the model evaluation `MUST`be documented on the [Documentation and model cards](Documentation-and-model-cards)

## Model registry

The IMTF AI Core MLFlow instance is the single authoritative model registry for all AI and ML components at IMTF. The SironOne AI Core serves the same purpose for customer deployments.

- Every AI and ML component `MUST` be registered in the IMTF AI Core MLFlow model registry before it is deployed to any environment.
- Model artifacts `MUST` be stored in ONNX, Safetensors or MCP format in MLFlow.
- Every registered model version `MUST` include all of the following as MLFlow artifacts or logged metadata:

| Artifact / metadata                  | Description                                                         |
| ------------------------------------ | ------------------------------------------------------------------- |
| ONNX, Safetensor, MCP model artifact | Serialised model binary                                             |
| Model card                           | See [Documentation and model cards](#documentation-and-model-cards) |
| Training dataset reference           | Delta Lake path and pinned version                                  |
| Test dataset reference               | Delta Lake path and pinned version                                  |
| DQ check results                     | For both training and test datasets                                 |
| Performance metrics                  | All metrics from `metrics.custom_metrics()`                         |
| Input data schema                    | Field names, data types, nullability                                |
| Parameter configuration              | All hyperparameters and configuration values                        |

- MLFlow lifecycle stages (`Staging`, `Production`, `Archived`) `MUST` only be transitioned following the approval process in [Model approvals](#model-approvals).
- No model `SHOULD` remain in `Staging` in the production registry without an active approval in progress.
- All model design experiments `MUST` be recorded with their MLFlow `run-id` in `design/model-design.ipynb` along with a description of the experiment.

## Data versioning

- All training data `MUST` be loaded exclusively from a versioned Delta Lake dataset via the Spark Connect Server. Direct file system reads bypass versioning and `MUST NOT` be used.
- Data transforms `MUST` be exclusively contained in `src.mainData.transform()`. The function's input and output contracts `MUST` be strictly adhered to.
- Feature engineering `MUST NOT` appear in training loops (`src.mainModel.train_*()`).
- Every dataset used for training or evaluation `MUST` be registered using `src.mainData.update_registered_data()` before model artifacts are stored in MLFlow.
- Training runs `MUST` reference a pinned Delta Lake dataset version so that results are fully reproducible.
- Hold-out and test data `MUST` be kept strictly separate from training data and `MUST NOT` be accessible to model engineers during development. This separation `SHOULD` be enforced via Delta Lake access controls (Apache Kyuubi or native dynamic views).
- Data lineage from raw ingestion through to model input features `MUST` be traceable via Delta Lake versioning and MLFlow dataset registration.

## Documentation and model cards

- Every model `MUST` produce a model card using `doc.custom_modelcard.py`. Model card content is populated from MLFlow and written into the canonical template.
- Model cards `MUST` be stored as MLFlow artifacts alongside the model version and `MUST` be updated with every version release.
- Model cards `MUST` include at minimum:

| Section               | Required content                                                           |
| --------------------- | -------------------------------------------------------------------------- |
| Purpose               | Intended use, functional scope, and out-of-scope uses                      |
| Training data         | Delta Lake dataset reference (path and version), data description          |
| Features              | Feature definitions, data types, and engineering decisions                 |
| Bias evaluation       | Results for gender, age, nationality, and other protected attributes       |
| Drift detection       | Approach, monitoring thresholds, and escalation procedure                  |
| Performance metrics   | All metrics, evaluation methodology, and acceptance thresholds             |
| DQ rules              | Rules applied at training and at inference                                 |
| Regulatory            | EU AI Act classification, GDPR considerations, ISO 27001 controls          |
| Control Configuration | Parameter settings used to influence the model performance (if applicable) |
| ADR references        | Cross-references to relevant entries in `adr/`                             |

- All model repositories `MUST` maintain architectural decision records in `adr/` for any significant design decision affecting the model service.
- Changes to `design/model-design.ipynb` are exempt from code review and quality control requirements.

## Data quality metrics

Every model `MUST` define DQ checks covering both training data and inference inputs. There `MUST` be no deployed model for which DQ rules do not exist.

- DQ checks `MUST` be implemented in the following functions:
  - `dq.custom_distributed()` — distributed checks executed with a Spark session
  - `dq.custom_local()` — local checks executed with a pandas DataFrame
- DQ checks `MUST` cover at minimum:

| Check category           | Examples                                                      |
| ------------------------ | ------------------------------------------------------------- |
| Schema conformance       | Field names, data types, nullability constraints              |
| Value range validation   | Min/max bounds, allowed enum values                           |
| Statistical distribution | Mean, standard deviation, percentiles vs. registered baseline |
| Missing value rate       | Null and empty rates per field                                |
| Duplicate rate           | Row-level deduplication check                                 |
| Referential integrity    | Foreign key consistency where applicable                      |

- All DQ check results `MUST` be logged to MLFlow as part of every training run and as part of the model validation CICD pipeline.
- DQ checks `MUST` pass for both training data and inference data before any model version can be promoted to `Production`.
- For simulation and analytics models, DQ checks `MUST` additionally validate that simulated output distributions are statistically consistent with observed real-world outcomes (see [Simulation and analytics models](#simulation-and-analytics-models)).

## Model performance metrics

- All model performance metrics `MUST` be defined in `metrics.custom_metrics()`. Every metric defined there is automatically computed as part of the model validation CICD process.
- Metrics `MUST` be computed against both the registered training dataset version and the held-out test dataset version.
- All metrics `MUST` be logged to MLFlow at the end of every training run.
- Model engineers are responsible for defining metrics appropriate to their model type. The following metrics are required as a minimum:

| Model type             | Required metrics                                             |
| ---------------------- | ------------------------------------------------------------ |
| Binary classifier      | Precision, recall, F1, AUC-ROC, AUC-PR                       |
| Multi-class classifier | Per-class precision, recall, F1, macro-average F1            |
| Regression / scoring   | MAE, RMSE, R², mean error (bias)                             |
| Simulation / analytics | MAE vs. ground truth, PSI, KS statistic, coverage error rate |
| LLM / generative       | Domain-specific quality metric, latency P50/P95, error rate  |

- A model version `MUST NOT` be promoted to `Production` if any metric regresses below the registered baseline for the current production version. Exceptions must be documented in the model card.
- When introducing a new metric, the baseline model is automatically re-evaluated against the same metric as part of the CICD pipeline. The candidate metrics are used for evaluation of both old and new models.

## Validation and DevOps

### Four-way validation

The CICD pipeline enforces a four-way validation as part of every pull request to the integration branch. This is the mandatory gate for model quality assurance and `MUST` be passing before any merge to `integration` or `main`.

```
                        Old data version    New data version
Old (baseline) model         [1]                 [2]
New (candidate) model        [3]                 [4]
```

- The model validation script (`scripts/evaluate-pr.sh`) `MUST` execute all four combinations and report complete model metrics and DQ check results for each combination.
- A merge to the integration branch `MUST NOT` proceed unless all four validations pass at or above the baseline for every metric and DQ check.
- The four-way validation `MUST` be controlled via `.github/workflows/model-validation.yml` and `scripts/evaluate-pr.sh`. These files are system engineering remit and `MUST NOT` be modified without consultation with a system engineering peer.

### Branch strategy & commit guidance

Three protected branches are maintained per model repository:

| Branch        | Purpose                                     | Merge strategy        | Requirements                                                                                             |
| ------------- | ------------------------------------------- | --------------------- | -------------------------------------------------------------------------------------------------------- |
| `main`        | Production source code                      | Squash                | All integration checks passing + tech lead approval or two product owner / engineering manager approvals |
| `integration` | Production-ready, consumable by other teams | Automatic on pass     | 4-way validation passing for all metrics and DQ, no merge conflicts, no out-of-remit changes             |
| `development` | Combined feature branch changes             | Non-squash, automatic | Linting and security checks passing                                                                      |

Feature branches `MUST` follow the naming convention `feat/AI-0000`.

Commits `MUST`follow the [conventional commit](https://www.conventionalcommits.org/en/v1.0.0/#specification) specification and `MUST`include a `REF: <mlflow_model_id>` to indicate which model is effected by the commit.

### Pre-commit and CI enforcement

- Pre-commit hooks (`.pre-commit-config.yaml` and `scripts/check_allowed_functions.py`) and GitHub Actions `MUST` enforce that no code changes are made outside the permitted boundaries for model and data engineers.
- A `--no-verify` flag is required to override pre-commit enforcement; any such override `MUST` be explicitly justified in the PR description.
- Dependency security scanning `MUST` run as a GitHub Action on every push.
- Before merging to `main`, engineers `MUST` pull the latest `main` of the [ai-core-template](https://github.com/imtf-group/ai-core-template) to incorporate the latest GitHub Actions, DQ checks, model metrics, pre-commit rules, and approved Helm charts.

## Model approvals

- No model version `MUST` be deployed to production without completing the full approval process.
- Promotion from `Staging` to `Production` in MLFlow requires all of the following:
  - Four-way validation passing for all metrics and DQ checks at or above the current production baseline
  - A complete model card stored as an MLFlow artifact
  - All DQ check results and performance metrics logged in MLFlow for the candidate version
  - Approval from either a tech lead or two product owners or engineering managers
- Architectural decisions affecting the model service `MUST` be recorded in `adr/` prior to implementation and referenced in the PR description.
- All schema changes to model inputs or outputs `MUST` follow the breaking change rules defined in the applicable API guidelines.

## Logging

- All AI components `MUST` comply with the IMTF [observability guidelines](https://github.com/imtf-group/imtf-adrs/blob/main/guidelines/0002-observability.md) and internal [logging guidelines](https://portal.imtf.dev/docs/policies/logging).
- AI-specific logging `MUST` be implemented via `monitoring/custom_otel.py` within the ai-core-template framework including logging OpenTelemtry MLFlow logging.
- Every inference request `MUST` produce a structured log entry including at minimum and similarly tracing OpenTelemtry to MLFlow:

| Field                   | Notes                                               |
| ----------------------- | --------------------------------------------------- |
| Timestamp               | ISO 8601                                            |
| `model.name`            | As registered in MLFlow                             |
| `model.version`         | Exact version string from MLFlow                    |
| `input.schema.version`  | Version of the input feature schema                 |
| `inference.duration_ms` | Inference latency in milliseconds                   |
| `traceparent`           | OTel trace context (added by instrumentation agent) |
| `correlation-id`        | Business correlation ID where applicable            |

- Training runs `MUST` log start and end timestamps, dataset version references, all hyperparameters, metric values, and DQ results to both the application log and MLFlow.
- Sensitive data (PII, personally identifiable financial data, secrets, tokens) `MUST NOT` appear in log messages, MLFlow run parameters, or metric tags.
- All logs `MUST` be structured (JSON format) when emitted as OTel signals.
- The `service.name` resource attribute `MUST` be set for all AI service components.

## Usage monitoring and billing

- All inference calls to AI Service Manager endpoints `MUST` be instrumented with OTel metrics to support usage reporting and cost allocation.
- The following metrics `MUST` be captured per model per consumer:

| Metric name                     | Description                                 |
| ------------------------------- | ------------------------------------------- |
| `ai.inference.request.count`    | Total inference requests                    |
| `ai.inference.request.duration` | Inference latency histogram (P50, P95, P99) |
| `ai.inference.error.count`      | Inference errors by error type              |
| `ai.training.run.count`         | Number of training runs triggered           |
| `ai.training.duration`          | Wall-clock training duration                |
| `ai.token.consumed.count`       | Token count for LLM-backed components       |

- The attributes `model.name` and `model.version` `MUST` be attached to all AI metrics to enable per-model aggregation.
- Consumer identity (calling service or team) `MUST` be attached to each inference metric to enable billing allocation. End-user PII `MUST NOT` be included.
- Usage metrics `MUST` be exported to the centralised OpenTelemetry Collector in accordance with the [observability guidelines](https://github.com/imtf-group/imtf-adrs/blob/main/guidelines/0002-observability.md).
- Cardinality `MUST` be controlled: dynamic values such as input record IDs `MUST NOT` be used as metric attributes.
- A model with no usage signal for 90 days `SHOULD` be reviewed for archival in the MLFlow registry.

## Security

- All AI service endpoints `MUST` require authentication before accepting inference or training requests.
- The AI Service Manager `MUST` verify a valid license token before processing any request (see [Licensing](#licensing)).
- All secrets (AWS credentials, Kubernetes secrets, license tokens, database passwords) `MUST` be managed as Kubernetes secrets and `MUST NOT` be committed to source code repositories. The `.gitignore` file in each model repository enforces this; pre-commit hooks provide a secondary guard.
- Spark Connect Server access `MUST` be authenticated via IMTF SSO or customer SSO. Unauthenticated access to compute resources and Delta Lake data `MUST NOT` be permitted, and is especially critical for SironOne AI Core deployments at customer sites.
- Training data and hold-out data `MUST` be stored in separately access-controlled Delta Lake paths. Model engineers `MUST NOT` have read access to hold-out data outside the model validation pipeline.
- Data encryption at rest and in transit `MUST` be implemented for all production deployments. RPO and RTO objectives `MUST` be defined for each production model before go-live.
- Port exposure within the Kubernetes cluster `MUST` be limited to the minimum required. The Spark WebUI `MUST NOT` be accessible outside the cluster namespace.
- The model validation CICD pipeline `MUST` execute in an isolated environment with no access to production data.
- Any `--no-verify` bypass of pre-commit hooks `MUST` be explicitly justified in the PR description and reviewed by a system engineering peer.

## Licensing

- Each model version registered in MLFlow `MUST` carry a license token. The AI Service Manager `MUST` verify that the requesting consumer is either already authorized under a registered license or is supplying a valid license key before serving any response.
- License verification `MUST` be enforced at the AI Service Manager level to ensure a consistent enforcement boundary across all consumers.
- License tokens `MUST` be stored as Kubernetes secrets and referenced by environment variable. They `MUST NOT` be embedded in source code or container images.
- Customer-built models may be granted a license exemption on an exception basis. Such exceptions `MUST` be documented in the model card and approved by the Architecture Board.
- License assignments, associated model versions, and expiration dates `MUST` be tracked and auditable.

## Simulation and analytics models

Simulation models and analytics pipelines are subject to all rules in this document without exception. Additionally:

- A simulation or analytics component `MUST` demonstrate with quantitative metrics that its outputs reliably match actual observed outcomes before it can be promoted to `Production`. Passing thresholds `MUST` be defined in the model card and approved by the architecture board.
- Backtesting results against historical ground truth `MUST` be stored as MLFlow metrics for each model version.
- The following validation metrics `MUST` be defined and enforced in the CICD pipeline for all simulation and analytics models:

| Metric                               | Purpose                                                           |
| ------------------------------------ | ----------------------------------------------------------------- |
| Population Stability Index (PSI)     | Detect distribution shift between simulated and real outcomes     |
| Kolmogorov–Smirnov (KS) statistic    | Validate distributional similarity against ground truth           |
| Mean Absolute Error vs. ground truth | Measure the magnitude of deviation from observed outcomes         |
| Coverage error rate                  | Proportion of cases where simulation fails to bound actual values |

- Simulation outputs `MUST NOT` be used to inform operational decisions until the model version has passed all four metrics at the thresholds defined in the model card.
- Simulation models are subject to the same four-way validation process as predictive models.
- DQ checks for simulation models `MUST` validate that generated output distributions are statistically consistent with observed real-world distributions (e.g., using KS test or PSI). Failure of these checks `MUST` block promotion.

## Repository structure

All AI model repositories `MUST` derive from the [ai-core-template](https://github.com/imtf-group/ai-core-template) and `MUST` maintain the following standard structure. Files outside this structure are system engineering remit and `MUST NOT` be modified by model or data engineers without explicit coordination.

```
design/model-design.ipynb       # Experiment design (exempt from review)
demo/                           # Demo instructions (setup and demo flow), scripts and data
src/mainData.py                 # Data transform pipeline (transform() only)
src/mainModel.py                # Training loops (no feature engineering)
src/mainInference.py            # Inference logic
src/mainAgent.py                # Agent logic (where applicable)
dq/                             # DQ check implementations (dq.custom_*())
metrics/                        # Model metric implementations (custom_metrics())
doc/custom_modelcard.py         # Model card generator
doc/configuration.md            # Environment variables and configuration options
monitoring/custom_otel.py       # OTel instrumentation
adr/                            # Architectural decision records
tests/                          # Functional unit tests (system engineering remit)
scripts/deploy*-dev.sh          # Self-contained dev environment deployment
scripts/deploy*-prod.sh         # Production deployment (Helm-based)
scripts/evaluate-pr.sh          # Four-way model validation (system engineering remit)
scripts/check_allowed_functions.py  # Remit enforcement (system engineering remit)
requirements_api.txt            # Python package dependencies
.github/workflows/              # GitHub Actions CICD (system engineering remit)
.pre-commit-config.yaml         # Pre-commit hooks (system engineering remit)
```

- Additional Python packages `MUST` be added to `requirements_api.txt` to be included in the AI Service Manager.
- Deploy scripts `MUST` be self-contained: they `MUST NOT` rely on files outside the repository and `MUST` create or download any temporary files required at runtime.
- Production deployments `MUST` build from IMTF TechOps Helm charts with minimal additional configuration.

## Configuration and environment variables

To ensure AI Core deployments can operate in a diverse set of environments, including air-gaped installations.

- All AI Core model parameters, library versions, licensing, API and other deployment parameters `MUST` be exposed as configuration options through environment parameters.
- AI Core environment variables `MUST`start with a `AIC_` prefix followed by a product or service indicator, e.g. `AIC_CUS_`for a model used in custumer screening.
- Environment variables `MUST` be version agnostic. If a new service version requires a new and changed setting which might represent a breaking change the release version `MUST`be apended, e.g., `AIC_CUS_SPARK_VERSION_R1_1_3`.
- All configuration options `MUST` be described in `doc/configuration.md ` to ensure that operational manuals and user manuals can be created.

## Operational data storage & shared knowledge graph

All AI components requiring persistent operational state, embedding storage, or shared knowledge graph traversal `MUST` use a dedicated `ai_core` database on the existing PostgreSQL instance (`postgresql` service, port 5432, namespace `od-aps-demo`). No AI component `MUST NOT` write to any product database (`customers`, `screening`, `strategy`, `watch_list`, etc.).

### Database and user provisioning

- A dedicated database `ai_core` `MUST` be created on the shared PostgreSQL instance.
- A dedicated service role `aic_svc` `MUST` be created with login rights restricted to `ai_core`. It `MUST NOT` be granted access to any product database.
- The following PostgreSQL extensions `MUST` be enabled in `ai_core` before any AI component is deployed:

| Extension  | Minimum version | Purpose                                                                            |
| ---------- | --------------- | ---------------------------------------------------------------------------------- |
| `pgvector` | 0.7             | Per-entity and per-account embedding storage and cosine / L2 similarity search     |
| `age`      | 1.5             | Property graph storage and OpenCypher query support for the shared knowledge graph |

- The `search_path` for `aic_svc` `MUST` be set to `ag_catalog, embeddings, knowledge_graph, "$user", public` so that AGE Cypher functions resolve without explicit schema qualification.
- All credentials `MUST` be stored as Kubernetes secrets and referenced via environment variables. They `MUST NOT` be committed to any repository.

### Schema layout

Two schemas `MUST` be created inside `ai_core`:

| Schema            | Owner     | Purpose                                                |
| ----------------- | --------- | ------------------------------------------------------ |
| `embeddings`      | `aic_svc` | Vector tables — one table per model and embedding type |
| `knowledge_graph` | `aic_svc` | Apache AGE graph and supporting SQL fallback tables    |

### Vector storage standard

Each AI component that produces or consumes embeddings `MUST` follow this table structure:

```sql
CREATE TABLE embeddings.<aic_indicator>_vectors (
    entity_key    TEXT         NOT NULL,   -- business key: customer_id, entity_id, etc.
    model_name    TEXT         NOT NULL,   -- MLFlow registered model name
    model_version TEXT         NOT NULL,   -- exact MLFlow version string
    embedding     vector(<N>)  NOT NULL,   -- dimension N fixed per model version
    computed_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    PRIMARY KEY (entity_key, model_name, model_version)
);
```

- The embedding dimension `N` `MUST` be fixed per model version and documented in the model card.
- An index on the `embedding` column `MUST` be created at table creation time:
  - **HNSW** (`m = 16, ef_construction = 64`) for datasets up to 1 M rows — preferred for recall and query latency.
  - **IVFFlat** (`lists ≈ √row_count`) for datasets exceeding 1 M rows — preferred for memory efficiency at scale.
  - Both `MUST` use `vector_cosine_ops` as the operator class.
- Embeddings `MUST NOT` be stored alongside PII or sensitive customer data in the same row. Only the business key is stored; PII resolution `MUST` be delegated to the owning service at query time.
- The table name prefix `<aic_indicator>` `MUST` follow the `AIC_` service indicator convention (e.g., `cus` for customer screening, `ns` for name screening, `ns_watch` for watch-list entities).

### Knowledge graph standard

The shared knowledge graph `MUST` use Apache AGE within the `ai_core` database. A single named AGE graph `sironone_kg` serves as the authoritative property graph for all relationships, cross-list deduplication, and network traversal.

**Required node labels and mandatory properties:**

| Label     | Mandatory properties     | Description                                                                                                                  |
| --------- | ------------------------ | ---------------------------------------------------------------------------------------------------------------------------- |
| `Entity`  | `id TEXT`, `source TEXT` | A named entity from a watch-list source (OFAC, EU, SECO, etc.), customer source system or external data provider or registry |
| `Account` | `id TEXT`                | A financial account linked to one or entities                                                                                |
| `Address` | `id TEXT`                | An address entity associated with a person or organisation                                                                   |

**Required edge types:**

| Edge type    | Direction        | Meaning                                                                 |
| ------------ | ---------------- | ----------------------------------------------------------------------- |
| `LINKED_TO`  | Account → Entity | Account associated with this entity                                     |
| `ADDRESS_OF` | Address → Entity | Address belongs to this person or organisation                          |
| `SAME_AS`    | Entity → Entity  | Cross-list deduplication: both IDs refer to the same real-world subject |

- GIN indexes `MUST` be created on the `properties` column of every AGE label table to support fast property lookups.
- A SQL fallback table `knowledge_graph.entity_relations (source_id TEXT, relation TEXT, target_id TEXT, PRIMARY KEY (source_id, relation, target_id))` `MUST` be kept in sync with the AGE edges. This guarantees graph traversal via standard SQL joins for entities that fall outside the in-memory AGE-loaded subset and allows querying without the `ag_catalog` dependency.
- The AGE graph `MUST` be populated by the AI component's loader script and enriched by its enricher script, both stored under `scripts/` in the model repository following the `ai-core-template` structure. The enrichment pipeline `MUST` support the three entity-to-entity relation types (`ADDRESS_OF`, `SAME_AS`, `ISSUED_BY`) derived from the OpenSanctions FtM bulk feed or equivalent authoritative source.
- The graph loader `MUST NOT` load the entire entity set into AGE in a single transaction. Batched node and edge inserts (batch size ≤ 200) `MUST` be used to avoid lock contention.

### Access controls and environment variables

- `aic_svc` `MUST` be granted `CONNECT` on `ai_core` and `USAGE` / `CREATE` on `embeddings` and `knowledge_graph` schemas only.
- Inference-only services `SHOULD` use a separate read-only role `aic_ro` granted `SELECT` on both schemas, to enforce least-privilege at the database level.
- All AI components `MUST` reference the following standard environment variables for database connectivity:

| Variable          | Value                      | Notes                                                 |
| ----------------- | -------------------------- | ----------------------------------------------------- |
| `AIC_PG_HOST`     | `postgresql`               | Kubernetes service name in the cluster namespace      |
| `AIC_PG_PORT`     | `5432`                     | PostgreSQL default port                               |
| `AIC_PG_DB`       | `ai_core`                  | AI core database                                      |
| `AIC_PG_USER`     | `aic_svc`                  | Service account (or `aic_ro` for read-only inference) |
| `AIC_PG_PASSWORD` | _(from Kubernetes secret)_ | `MUST NOT` be hard-coded or logged                    |
