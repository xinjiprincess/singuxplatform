FROM singux/backend:1.1.10-20260924-r1
COPY --chown=app:app app.jar /app/app.jar
LABEL org.opencontainers.image.version="1.1.10-20260928-r2"
