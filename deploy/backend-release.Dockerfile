FROM maven:3.9.9-eclipse-temurin-17 AS builder
WORKDIR /workspace
COPY pom.xml ./
COPY fast-boot-dependencies/ fast-boot-dependencies/
COPY app-platform-foundation/ app-platform-foundation/
COPY app-platform-modules/ app-platform-modules/
COPY app-platform-bootstrap/ app-platform-bootstrap/
RUN cp app-platform-bootstrap/app-platform-web-bootstrap/src/main/resources/application-prod.sample.yml \
       app-platform-bootstrap/app-platform-web-bootstrap/src/main/resources/application-prod.yml
RUN --mount=type=cache,target=/root/.m2 \
    mvn -B -ntp -Pprod -DskipTests=false \
    '-Dtest=Tenant*,Portal*,PlatformAccessServiceTest,OpenAiApiStreamTest,ModelEndpointTest,McpDeployTaskServiceImplTest,McpExecutionLoggingTest,ElasticsearchDeletionTest' \
    -Dsurefire.failIfNoSpecifiedTests=false clean package

FROM singux/backend:1.1.10-20260924-r1
COPY --from=builder --chown=app:app /workspace/app-platform-bootstrap/app-platform-web-bootstrap/target/app-platform-web-bootstrap-*.jar /app/app.jar
ARG RELEASE_VERSION=1.1.10-20261008-tenant-admin-r2
LABEL org.opencontainers.image.version="${RELEASE_VERSION}"
