#!/bin/sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

if [ "$(uname -m)" != x86_64 ]; then
  echo 'This package requires a Linux x86_64 (amd64) server.' >&2
  exit 1
fi
docker info >/dev/null
docker compose version
echo 'Verifying package files ...'
sha256sum -c SHA256SUMS

if [ ! -f .env ]; then
  umask 077
  random_secret() { od -An -N32 -tx1 /dev/urandom | tr -d ' \n'; }
  sed \
    -e "s/^MYSQL_ROOT_PASSWORD=.*/MYSQL_ROOT_PASSWORD=$(random_secret)/" \
    -e "s/^REDIS_PASSWORD=.*/REDIS_PASSWORD=$(random_secret)/" \
    -e "s/^JWT_SECRET_KEY=.*/JWT_SECRET_KEY=$(random_secret)/" \
    -e "s/^MINIO_ROOT_PASSWORD=.*/MINIO_ROOT_PASSWORD=$(random_secret)/" \
    .env.example > .env
  echo 'Created .env with generated service credentials. Keep this file for future restarts.'
fi
if grep -q GENERATE_ON_DEPLOY .env; then
  echo 'Replace GENERATE_ON_DEPLOY placeholders in .env before starting.' >&2
  exit 1
fi
docker compose --env-file .env -f compose.json config --quiet
docker load -i images.tar
docker compose --env-file .env -f compose.json up -d --no-build --pull never --wait --wait-timeout 600
docker compose --env-file .env -f compose.json exec -T mysql sh -c \
  'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql --default-character-set=utf8mb4 -uroot "$MYSQL_DATABASE"' \
  < migrations/login-account-label.sql
docker compose --env-file .env -f compose.json ps
echo 'Ready. Open http://SERVER_IP:8080 (or FRONTEND_PORT configured in .env).'
echo 'Administrator login: admin / 123456. Change the initial password after signing in.'
