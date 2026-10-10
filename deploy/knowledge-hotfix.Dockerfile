ARG BASE_IMAGE=singux/backend:knowledge-baseline-20261007
FROM ${BASE_IMAGE}
COPY --chown=app:app app.jar /app/app.jar
LABEL org.opencontainers.image.version="1.1.10-20261007-knowledge-singletenant-r1"
