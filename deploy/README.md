# Nuwax full-stack Docker compose

This frontend repository can now act as the deployment entry point for a local
full-stack Nuwax environment.

## Layout

The compose file expects the backend repository to be available separately:

```text
parent/
  nuwax/           # this frontend repository
  nuwax-backend/   # https://github.com/nuwax-ai/nuwax-backend.git
```

If your backend checkout is elsewhere, set `NUWAX_BACKEND_DIR` in `.env`.
On Windows, prefer forward slashes:

```text
NUWAX_BACKEND_DIR=C:/Users/zhang/nuwax-backend
```

## Quick start

```bash
cp docker-compose.env.example .env
docker compose up --build
```

Frontend: http://localhost:8080

Backend health through the frontend nginx gateway:

```bash
curl http://localhost:8080/health
```

Backend health directly inside the compose network:

```bash
docker compose exec backend curl -fsS http://localhost:8081/health
```

## Notes

- The frontend image serves static assets with nginx.
- `/api/*`, `/health`, and `/ready` are proxied to the backend service.
- SSE endpoints use disabled nginx buffering and long proxy timeouts.
- The backend image copies `application-prod.sample.yml` to
  `application-prod.yml` during image build, then uses environment variables
  from compose for runtime configuration.
- MySQL imports backend SQL files from `${NUWAX_BACKEND_DIR}/sql` on first
  volume initialization only. To re-import from scratch, remove the
  `mysql-data` volume.
- AppDev-related external services such as mcp-proxy, build server, AI agent,
  docker proxy, and log service are configured through `.env` and default to
  `host.docker.internal`.
