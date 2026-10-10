"""Reuse runtime fixtures on target private IPs, with credentials kept in memory."""
import importlib.util
import json
from pathlib import Path
import socket
import subprocess
import urllib.request

ROOT = Path('/data/singux-migration-20261009')


def main():
    assert json.loads((ROOT / 'runtime-start-result.json').read_text())['status'] == 'RUNTIME_READY'
    spec = importlib.util.spec_from_file_location('fixtures', ROOT / 'verify-production-runtime.py')
    fixtures = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixtures)
    fixtures.HERE = ROOT
    fixtures.PROJECT = 'singux-migration-web-check-20261010'
    fixtures.DESKTOP_PROJECT = 'singux-migration-desktop-check-20261010'
    fixtures.USER = 'singux-migration-user-check-20261010'
    key = json.loads(Path('/data/singux-update/services-runtime-20261009-r1/rcoder.private.json').read_text())['api_key_auth']['api_key']
    endpoints = {}
    for port, name, internal in [(16000, 'file-server', 60000), (18096, 'rcoder', 8090), (18088, 'gateway', 8088)]:
        obj = json.loads(subprocess.check_output(['docker', 'inspect', 'singux-runtime-' + name + '-1']))[0]
        endpoints[port] = (obj['NetworkSettings']['Networks']['singux_default']['IPAddress'], internal)
    original_open = urllib.request.urlopen
    original_socket = socket.create_connection

    def open_private(url, *args, **kwargs):
        if isinstance(url, str):
            for port, (host, internal) in endpoints.items():
                url = url.replace('http://127.0.0.1:' + str(port), 'http://' + host + ':' + str(internal))
        return original_open(url, *args, **kwargs)

    def connect_private(address, *args, **kwargs):
        if address == ('127.0.0.1', 18088):
            address = endpoints[18088]
        return original_socket(address, *args, **kwargs)

    def request(port, path, body=None):
        host, internal = endpoints[port]
        req = urllib.request.Request('http://' + host + ':' + str(internal) + path,
                    headers={'Content-Type': 'application/json', 'x-api-key': key},
                    data=json.dumps(body).encode() if body is not None else None)
        with original_open(req, timeout=240) as r:
            result = json.load(r)
        assert result.get('success') is not False, 'Runtime fixture rejected'
        return result

    fixtures.request = request
    urllib.request.urlopen = open_private
    socket.create_connection = connect_private
    try:
        fixtures.main()
    finally:
        urllib.request.urlopen = original_open
        socket.create_connection = original_socket


if __name__ == '__main__':
    main()
