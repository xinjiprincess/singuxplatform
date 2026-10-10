#!/bin/sh
# Image-only updates for the existing compose.json deployment, not source mounts.
set -eu
umask 077
die() { echo "$*" >&2; exit 1; }
[ "$#" -eq 2 ] || die 'Usage: sh update.sh DEPLOY_DIR RELEASE_DIR'
deployment=$(CDPATH= cd -- "$1" && pwd)
release=$(CDPATH= cd -- "$2" && pwd)
for cmd in docker jq sha256sum; do command -v "$cmd" >/dev/null || die "Missing command: $cmd"; done
cd "$deployment"
[ -f compose.json ] && [ -f .env ] || die 'Existing compose.json and .env required.'
manifest="$release/update.json"
jq -e '.schemaUnchanged == true and .dataBackwardCompatible == true and (.release | type == "string" and length > 0) and (.mode == "online" or .mode == "offline")' "$manifest" >/dev/null || die 'Only reviewed, schema-unchanged, backward-compatible releases are supported.'
mode=$(jq -r .mode "$manifest")
frontend=$(jq -er .frontend "$manifest")
backend=$(jq -er .backend "$manifest")
for image in "$frontend" "$backend"; do
  if [ "$mode" = online ]; then
    printf '%s\n' "$image" | grep -Eq '^[a-zA-Z0-9][a-zA-Z0-9._:/-]*@sha256:[a-f0-9]{64}$' || die 'Online images must use repository@sha256:digest.'
  else
    printf '%s\n' "$image" | grep -Eq '^sha256:[a-f0-9]{64}$' || die 'Offline images must use immutable image IDs.'
  fi
done
mkdir .update-lock 2>/dev/null || die 'Update lock exists. Check whether another update is running.'
stopped=0
backup=
compose() { docker compose --env-file .env -f compose.json "$@"; }
finish() {
  status=$?
  trap - EXIT HUP INT TERM
  if [ "$status" -ne 0 ] && [ "$stopped" -eq 1 ]; then
    echo "Update failed; attempting previous images. Backup: $backup" >&2
    cp "$backup/compose.json" compose.json
    compose up -d --no-deps --no-build --pull never --wait --wait-timeout 600 frontend backend || echo 'ROLLBACK FAILED: operator intervention required.' >&2
  fi
  rm -f .update-lock/resolved.json .update-lock/next.json
  rmdir .update-lock
  exit "$status"
}
trap finish EXIT
trap 'exit 130' HUP INT TERM
docker info >/dev/null
docker compose version
compose config --quiet
compose config --format json > .update-lock/resolved.json
jq -e '.services.frontend and .services.backend and .services.mysql and (.services.frontend.healthcheck.disable != true) and .services.frontend.healthcheck.test and (.services.backend.healthcheck.disable != true) and .services.backend.healthcheck.test and ([.services.frontend.volumes[]? | select(.type == "bind") | select(.read_only != true or .target != "/etc/nginx/templates/default.conf.template")] | length == 0) and ([.services.backend.volumes[]? | select(.type == "bind")] | length == 0)' .update-lock/resolved.json >/dev/null || die 'Requires health checks; only the read-only frontend Nginx template bind mount is allowed.'
# Pin rollback to the actual running images, not potentially mutable tags.
for service in frontend backend mysql; do
  container=$(compose ps -q "$service")
  [ -n "$container" ] || die "Service not running: $service"
  [ "$(docker inspect --format '{{.State.Status}}' "$container")" = running ] || die "$service is not running"
  if [ "$service" = frontend ]; then old_frontend=$(docker inspect --format '{{.Image}}' "$container"); fi
  if [ "$service" = backend ]; then old_backend=$(docker inspect --format '{{.Image}}' "$container"); fi
done
if [ "$mode" = offline ]; then
  checksum=$(jq -er .archiveSha256 "$manifest")
  printf '%s\n' "$checksum" | grep -Eq '^[a-f0-9]{64}$' || die 'Invalid archive checksum.'
  [ "$(sha256sum "$release/images.tar" | cut -d ' ' -f1)" = "$checksum" ] || die 'Image archive checksum mismatch.'
  docker load -i "$release/images.tar"
else
  docker pull "$frontend"
  docker pull "$backend"
fi
docker image inspect "$frontend" "$backend" >/dev/null
backup="$deployment/backups/$(date -u +%Y%m%dT%H%M%SZ)-$$"
mkdir -p "$backup"
cp .env "$backup/.env"
cp compose.json "$backup/original-compose.json"
jq --arg f "$old_frontend" --arg b "$old_backend" '.services.frontend.image=$f | .services.backend.image=$b' compose.json > "$backup/compose.json"
cp "$manifest" "$backup/update.json"
jq --arg f "$frontend" --arg b "$backend" '.services.frontend.image=$f | .services.backend.image=$b' compose.json > .update-lock/next.json
docker compose --env-file .env -f .update-lock/next.json --project-directory "$deployment" config --quiet
stopped=1
compose stop frontend backend
compose exec -T mysql sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysqldump -uroot --all-databases --single-transaction --routines --events --triggers --set-gtid-purged=OFF' > "$backup/databases.sql"
[ -s "$backup/databases.sql" ] || die 'Database backup is empty.'
sha256sum "$backup/databases.sql" > "$backup/databases.sql.sha256"
cp .update-lock/next.json compose.json
compose up -d --no-deps --no-build --pull never --wait --wait-timeout 600 frontend backend
stopped=0
printf 'Updated successfully. Backup: %s\n' "$backup"
