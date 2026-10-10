"""Temporarily prioritize core image transfer; only suspend known archive producers."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path('/data/singux-migration-20261009')
STATE = ROOT / 'bulk-pause.json'


def identity(pid):
    return Path('/proc/' + str(pid) + '/stat').read_text().rsplit(')', 1)[1].split()[19]


def resume():
    saved = json.loads(STATE.read_text())
    for item in saved['producers']:
        try:
            if identity(item['pid']) == item['startTicks']:
                os.kill(item['pid'], signal.SIGCONT)
        except (FileNotFoundError, ProcessLookupError):
            pass
    saved['status'] = 'RESUMED'
    STATE.write_text(json.dumps(saved))
    print('BULK_PRODUCERS_RESUMED', flush=True)


def pause():
    if STATE.exists():
        assert json.loads(STATE.read_text())['status'] == 'RESUMED'
    rows = [line.split(None, 3) for line in subprocess.check_output(['ps', '-eo', 'pid=,ppid=,comm=,args='], text=True).splitlines()]
    roots = set()
    for name in ['background-export-result.json', 'business-export-result.json']:
        obj = json.loads((ROOT / name).read_text())
        assert obj['status'].endswith('STREAM_RUNNING')
        assert 'run-migration-' in Path('/proc/' + str(obj['pid']) + '/cmdline').read_text()
        roots.add(obj['pid'])
    descendants = set(roots)
    while True:
        more = {int(pid) for pid, parent, comm, args in rows if int(parent) in descendants} - descendants
        if not more:
            break
        descendants.update(more)
    producers = [{'pid': int(pid), 'startTicks': identity(int(pid))} for pid, parent, comm, args in rows
                 if int(pid) in descendants and (comm in {'gzip', 'tar'} or args.startswith('docker save '))]
    assert len(producers) == 4, 'Unexpected producer tree; refuse broad process suspension'
    STATE.write_text(json.dumps({'status': 'PAUSED', 'producers': producers, 'maximumSeconds': 900}))
    # Start the bounded fail-safe before suspending any producer.
    with (ROOT / 'bulk-pause-watchdog.log').open('ab') as log:
        subprocess.Popen([sys.executable, str(Path(__file__).resolve()), 'watchdog'],
                         stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
    for item in producers:
        os.kill(item['pid'], signal.SIGSTOP)
    print('BULK_PRODUCERS_PAUSED_MAX_900_SECONDS', flush=True)


if __name__ == '__main__':
    os.umask(0o077)
    if sys.argv[1] == 'pause':
        pause()
    elif sys.argv[1] == 'resume':
        resume()
    elif sys.argv[1] == 'watchdog':
        time.sleep(900)
        resume()
    else:
        raise ValueError('Unknown operation')
