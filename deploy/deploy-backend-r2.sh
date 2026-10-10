#!/bin/sh
set -eu
umask 077
[ "$#" -eq 2 ] || { echo 'Usage: sh deploy-backend-r2.sh DEPLOY_DIR RELEASE_DIR' >&2; exit 1; }
deployment=$(CDPATH= cd -- "$1" && pwd)
release=$(CDPATH= cd -- "$2" && pwd)
image=singux/backend:1.1.10-20260928-r2
cd "$release"
sha256sum -c SHA256SUMS
docker build --pull=false -f Dockerfile -t "$image" .
cd "$deployment"
compose() { docker compose -f compose.json "$@"; }
compose config --quiet
backend=$(compose ps -q backend)
mysql=$(compose ps -q mysql)
[ -n "$backend" ] && [ -n "$mysql" ]
backup="/data/singux-backups/backend-20260928-r2-$(date -u +%Y%m%dT%H%M%SZ)-$$"
mkdir -p "$backup"
cp -p compose.json "$backup/compose.json"
cp -p .env "$backup/.env"
docker inspect --format '{{.Image}}' "$backend" > "$backup/backend-image-id"
stopped=0
finish() {
    result=$?
    trap - EXIT HUP INT TERM
    if [ "$result" -ne 0 ] && [ "$stopped" -eq 1 ]; then
        cp -p "$backup/compose.json" compose.json
        compose up -d --no-deps --pull never --wait --wait-timeout 300 backend || echo 'ROLLBACK FAILED' >&2
        echo "Deployment failed. Backup: $backup" >&2
    fi
    exit "$result"
}
trap finish EXIT
trap 'exit 130' HUP INT TERM
stopped=1
compose stop backend
docker exec "$mysql" sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysqldump -uroot --databases agent_platform agent_custom_table --single-transaction --routines --events --triggers --set-gtid-purged=OFF' > "$backup/databases.sql"
[ -s "$backup/databases.sql" ]
sha256sum "$backup/databases.sql" > "$backup/databases.sql.sha256"
for migration in 20260926-tenant-policy.sql 20260926-tenant-membership.sql; do
    docker exec -i "$mysql" sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot agent_platform' < "$release/$migration"
done
python3 - "$image" <<'PY'
import json
import os
import stat
import sys
from pathlib import Path
path = Path('compose.json')
data = json.loads(path.read_text())
data['services']['backend']['image'] = sys.argv[1]
temporary = path.with_name('compose.backend-r2.tmp')
temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
temporary.chmod(stat.S_IMODE(path.stat().st_mode))
os.replace(temporary, path)
PY
compose up -d --no-deps --pull never --wait --wait-timeout 300 backend
stopped=0
echo "DEPLOYMENT_OK image=$image backup=$backup"
compose ps backend
