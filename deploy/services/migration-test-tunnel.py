"""Loopback-only SSH tunnel to the pinned target HTTP service."""
import importlib.util
import os
from pathlib import Path
import select
import socketserver


def main():
    spec = importlib.util.spec_from_file_location('migration', Path(__file__).with_name('stage-migration-images.py'))
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    client = migration.t.paramiko.SSHClient()
    client.set_missing_host_key_policy(migration.Pinned())
    client.connect('113.219.170.192', username='root', password=os.environ.pop('SINGUX_SSH_PASSWORD'),
                   look_for_keys=False, allow_agent=False, timeout=20)
    transport = client.get_transport()
    transport.set_keepalive(30)

    class Handler(socketserver.BaseRequestHandler):
        def handle(self):
            channel = transport.open_channel('direct-tcpip', ('127.0.0.1', 80), self.client_address)
            try:
                while True:
                    readable, _, _ = select.select([self.request, channel], [], [], 120)
                    if not readable:
                        break
                    for source in readable:
                        data = source.recv(65536)
                        if not data:
                            return
                        (channel if source is self.request else self.request).sendall(data)
            finally:
                channel.close()

    class Server(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

    try:
        with Server(('127.0.0.1', 18109), Handler) as server:
            print('Target test tunnel: http://127.0.0.1:18109/login', flush=True)
            server.serve_forever()
    finally:
        client.close()


if __name__ == '__main__':
    main()
