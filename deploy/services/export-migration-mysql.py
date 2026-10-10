"""Export application schemas online; never copy live MySQL volume files."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess


def main():
    os.umask(0o077)
    root = Path('/data/singux-migration-20261009')
    assert root.is_dir() and not root.is_symlink()
    target = root / 'application-databases.sql.gz'
    assert not target.exists()
    query = 'exec mysql --user=root --password="$MYSQL_ROOT_PASSWORD" --batch --skip-column-names -e "SHOW DATABASES"'
    result = subprocess.run(['docker', 'exec', 'singux-mysql-1', 'sh', '-c', query],
                            text=True, capture_output=True, check=True)
    databases = [name for name in result.stdout.splitlines()
                 if name not in {'mysql', 'sys', 'information_schema', 'performance_schema'}]
    assert databases and all(name.replace('_', '').isalnum() for name in databases)
    command = ('exec mysqldump --user=root --password="$MYSQL_ROOT_PASSWORD" '
               '--single-transaction --quick --routines --events --triggers --hex-blob '
               '--no-tablespaces --set-gtid-purged=OFF --databases ' + ' '.join(databases))
    partial = target.with_suffix(target.suffix + '.part')
    with (root / 'mysql-export.stderr').open('wb') as error:
        process = subprocess.Popen(['docker', 'exec', 'singux-mysql-1', 'sh', '-c', command],
                                   stdout=subprocess.PIPE, stderr=error)
        with gzip.open(partial, 'wb', compresslevel=1) as out:
            while chunk := process.stdout.read(1024 * 1024):
                out.write(chunk)
        process.stdout.close()
        assert process.wait() == 0, 'MySQL dump failed; inspect private stderr file'
    partial.rename(target)
    h = hashlib.sha256()
    with target.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    record = {'status': 'MYSQL_LOGICAL_SNAPSHOT', 'databases': databases,
              'bytes': target.stat().st_size, 'sha256': h.hexdigest(),
              'writesPaused': False, 'crossStoreConsistent': False,
              'note': 'InnoDB consistent dump only; later writes and external indexes/files need separate synchronization.'}
    (root / 'mysql-export.json').write_text(json.dumps(record, indent=2))
    print(json.dumps(record), flush=True)


if __name__ == '__main__':
    main()
