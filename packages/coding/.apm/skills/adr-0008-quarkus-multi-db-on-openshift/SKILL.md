---
name: imtf-adr-0008-quarkus-multi-db-on-openshift
description: "Apply when working on guideline, platform in any repo. IMTF adr 0008-quarkus-multi-db-on-openshift: Quarkus Multi-Database Support on OpenShift via Runtime"
---

# ADR-0008: Quarkus Multi-Database Support on OpenShift via Runtime Re-Augmentation

| Field  | Value                                                  |
| ------ | ------------------------------------------------------ |
| Date   | 2026-03-22                                             |
| Status | In-Progress \| **In-Review** \| Accepted \| Superseded |
| Tags   | guideline, platform                                    |

## Context

Quarkus performs build-time augmentation to optimize startup and reduce runtime overhead. This means database driver selection (`quarkus.datasource.db-kind`) is a build-time property, baked into the application at build. Teams that need to support multiple databases (PostgreSQL, Oracle, MySQL, MariaDB, MS SQL) from a single container image cannot simply switch the driver via an environment variable at runtime.

On OpenShift, containers typically run with a read-only root filesystem, which adds a further constraint since re-augmentation needs to write files.

## Decision

We use the Quarkus **mutable-jar** packaging format combined with **runtime re-augmentation** to produce a single container image that adapts to any supported database at startup.

The approach has four parts:

1. **Build a mutable-jar** instead of a standard fast-jar:

   ```
   # Maven
   ./mvnw package -DskipTests -Dquarkus.package.jar.type=mutable-jar

   # Gradle
   ./gradlew build -x test -Dquarkus.package.jar.type=mutable-jar
   ```

2. **Bake artifacts into a read-only path** (`/app`) in the container image. At startup an entrypoint script copies them to `/tmp`, which is already mounted as a writable `emptyDir` on OpenShift -- no extra volume definition needed.

3. **Re-augment at startup** by launching the application with `-Dquarkus.launch.rebuild=true`. The target database is selected via the `QUARKUS_DATASOURCE_DB_KIND` environment variable. The entrypoint also sets `QUARKUS_DATASOURCE_JDBC_DRIVER` explicitly, because some drivers (notably Oracle) do not register themselves via `DriverManager` during re-augmentation.

4. **After re-augmentation completes**, the application starts normally with the correct driver embedded.

### Dockerfile

```dockerfile
FROM registry.access.redhat.com/ubi9/openjdk-21:1.23

ENV LANGUAGE='en_US:en'

# Bake the mutable-jar into /app (read-only in k8s).
# The quarkus-app/ subdirectory is required so re-augmentation writes
# output to the parent (/tmp/) which is the writable emptyDir.
COPY --chmod=755 target/quarkus-app/lib/          /app/quarkus-app/lib/
COPY --chmod=755 target/quarkus-app/*.jar          /app/quarkus-app/
COPY --chmod=755 target/quarkus-app/app/           /app/quarkus-app/app/
COPY --chmod=755 target/quarkus-app/quarkus/       /app/quarkus-app/quarkus/

COPY --chmod=755 src/main/docker/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

EXPOSE 8080
WORKDIR /tmp
ENV JAVA_OPTS_APPEND="-Dquarkus.http.host=0.0.0.0 -Djava.util.logging.manager=org.jboss.logmanager.LogManager"
ENV JAVA_APP_JAR="/tmp/quarkus-app/quarkus-run.jar"
ENV JAVA_APP_DIR="/tmp/quarkus-app"

USER 1001

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
```

### Entrypoint script (`docker-entrypoint.sh`)

```sh
#!/bin/sh
set -e

# Step 1: Copy application artifacts to writable /tmp (emptyDir in k8s)
cp -r /app/* /tmp/

# Step 2: Set JDBC driver explicitly — some drivers (notably Oracle) do not
# register themselves via DriverManager during re-augmentation.
if [ -z "${QUARKUS_DATASOURCE_JDBC_DRIVER}" ]; then
    case "${QUARKUS_DATASOURCE_DB_KIND}" in
        postgresql) export QUARKUS_DATASOURCE_JDBC_DRIVER="org.postgresql.Driver" ;;
        oracle)     export QUARKUS_DATASOURCE_JDBC_DRIVER="oracle.jdbc.OracleDriver" ;;
        mysql)      export QUARKUS_DATASOURCE_JDBC_DRIVER="com.mysql.cj.jdbc.Driver" ;;
        mariadb)    export QUARKUS_DATASOURCE_JDBC_DRIVER="org.mariadb.jdbc.Driver" ;;
        mssql)      export QUARKUS_DATASOURCE_JDBC_DRIVER="com.microsoft.sqlserver.jdbc.SQLServerDriver" ;;
    esac
fi

# Step 3: Re-augment for the target DB.
# The first call runs with -Dquarkus.launch.rebuild=true which triggers
# re-augmentation and then exits. The second call (exec) starts the
# application normally. Two separate invocations are needed because
# passing rebuild=true to a single run would re-augment on every restart,
# creating an infinite loop.
JAVA_OPTS_APPEND="-Dquarkus.launch.rebuild=true ${JAVA_OPTS_APPEND}" \
    /opt/jboss/container/java/run/run-java.sh

# Step 4: Start the application with the re-augmented artifacts
exec /opt/jboss/container/java/run/run-java.sh
```

## Consequences

- A single container image supports all target databases; no per-database image build is needed.
- Startup time increases slightly due to the copy and re-augmentation steps.
- Re-augmentation uses `/tmp`, which OpenShift already mounts as a writable `emptyDir` -- no extra volume definition required.
- All target database JDBC drivers must be included as Maven dependencies at build time so they are available during re-augmentation.
