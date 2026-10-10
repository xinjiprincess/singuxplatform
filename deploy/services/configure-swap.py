"""Run explicitly on the Linux server; creates a new 8 GiB swap file only."""
import argparse
import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess

TARGET = Path('/data/singux.swap')
SIZE = 8 * 1024 ** 3
TUNING = Path('/etc/sysctl.d/99-z-singux-swap.conf')


def run(*args):
    return subprocess.check_output(args, text=True).strip()


def verify(before, backup):
    rows = Path('/proc/swaps').read_text().splitlines()[1:]
    item = next(line.split() for line in rows if line.split()[0] == str(TARGET))
    assert item[1] == 'file' and int(item[4]) == 10
    size, used = int(item[2]) * 1024, int(item[3]) * 1024
    assert size >= SIZE - 65536 and TARGET.stat().st_size == SIZE
    assert (TARGET.stat().st_mode & 0o777) == 0o600
    assert run('sysctl', '-n', 'vm.swappiness') == '10'
    assert '/data/singux.swap none swap defaults,nofail,pri=10 0 0' in Path('/etc/fstab').read_text()
    assert 'vm.swappiness = 10' in TUNING.read_text()
    after = run('docker', 'ps', '--no-trunc', '--format', '{{.ID}} {{.Image}}')
    assert before.strip() == after.strip(), 'Container inventory changed; investigate'
    unit = run('systemd-escape', '--path', '--suffix=swap', str(TARGET))
    assert 'What=/data/singux.swap' in run('systemctl', 'cat', unit), 'Boot swap unit missing'
    result = {'status': 'SWAP_ENABLED', 'path': str(TARGET), 'sizeBytes': size,
              'usedBytes': used, 'swappiness': 10, 'backup': str(backup),
              'bootUnit': unit, 'containersUnchanged': True, 'rebootTested': False}
    (backup / 'result.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--verify-backup')
    args = parser.parse_args()
    assert os.geteuid() == 0, 'Requires Linux root'
    if args.verify_backup:
        assert not args.apply, 'Verification cannot apply changes'
        backup = Path(args.verify_backup).resolve()
        assert backup.parent == Path('/root/singux-swap-backups'), 'Unexpected backup path'
        verify((backup / 'containers.before').read_text(), backup)
        return
    mount = json.loads(run('findmnt', '-J', '-T', '/data'))['filesystems'][0]
    assert mount['target'] == '/data' and mount['fstype'] == 'xfs', 'Unexpected data mount'
    assert Path('/data').resolve() == Path('/data'), 'Data directory must not be a symlink'
    assert not TARGET.exists() and not TARGET.is_symlink(), 'Refuse to overwrite an existing file'
    assert not TUNING.exists() and not TUNING.is_symlink(), 'Tuning file already exists'
    assert len(Path('/proc/swaps').read_text().splitlines()) == 1, 'Existing swap requires manual review'
    assert shutil.disk_usage('/data').free >= SIZE + 10 * 1024 ** 3, 'Insufficient free space'
    fstab = Path('/etc/fstab')
    assert not fstab.is_symlink(), 'Unexpected fstab symlink'
    original = fstab.read_bytes()
    assert b'/data/singux.swap' not in original, 'Existing fstab entry requires review'
    before = run('docker', 'ps', '--no-trunc', '--format', '{{.ID}} {{.Image}}')
    old_swappiness = run('sysctl', '-n', 'vm.swappiness')
    print('SWAP_CHECK_OK sizeGiB=8 freeGiB=' + str(round(shutil.disk_usage('/data').free / 1024 ** 3, 1)), flush=True)
    if not args.apply:
        return
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup = Path('/root/singux-swap-backups') / stamp
    backup.mkdir(parents=True, mode=0o700)
    shutil.copy2(fstab, backup / 'fstab.before')
    (backup / 'swappiness.before').write_text(old_swappiness + '\n')
    (backup / 'containers.before').write_text(before + '\n')
    descriptor = os.open(TARGET, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    os.close(descriptor)
    try:
        run('fallocate', '-l', str(SIZE), str(TARGET))
        assert TARGET.stat().st_size == SIZE and TARGET.stat().st_blocks * 512 >= SIZE, 'File has holes'
        run('mkswap', '-L', 'singux-swap', str(TARGET))
        run('swapon', '--priority', '10', str(TARGET))
        entry = b'/data/singux.swap none swap defaults,nofail,pri=10 0 0\n'
        assert fstab.read_bytes() == original, 'fstab changed concurrently'
        descriptor = os.open(fstab, os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW)
        try:
            os.write(descriptor, (b'\n' if not original.endswith(b'\n') else b'') + entry)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        with TUNING.open('x') as stream:
            stream.write('# Singu X: disk swap is a peak-memory buffer, not extra RAM.\nvm.swappiness = 10\n')
        os.chmod(TUNING, 0o644)
        run('sysctl', '-w', 'vm.swappiness=10')
        run('systemctl', 'daemon-reload')
        verify(before, backup)
    except Exception:
        # Never automatically swapoff: draining active pages could itself cause OOM.
        (backup / 'failure-note.txt').write_text('Inspect active swap and configuration before retry. Do not automatically swapoff or delete the swap file.\n')
        print('SWAP_ERROR inspect_backup=' + str(backup), flush=True)
        raise


if __name__ == '__main__':
    main()
