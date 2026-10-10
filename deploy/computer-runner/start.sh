#!/bin/bash
set -euo pipefail
mkdir -p "$HOME" /app/logs
rm -f /tmp/vnc_ready
Xvfb :1 -screen 0 1280x800x24 -nolisten tcp > /app/logs/xvfb.log 2>&1 &
xvfb=$!
for i in $(seq 1 50); do
    if xdpyinfo -display :1 >/dev/null 2>&1; then break; fi
    sleep 0.1
done
xdpyinfo -display :1 >/dev/null
dbus-run-session openbox > /app/logs/desktop.log 2>&1 &
desktop=$!
# The local preview runs as root; production needs an isolated non-root runner.
chromium --no-sandbox --disable-dev-shm-usage --no-first-run --no-default-browser-check --user-data-dir="$HOME/.desktop-browser" about:blank > /app/logs/browser.log 2>&1 &
browser=$!
# VNC is loopback-only. The outer web gateway must authenticate WebSocket access.
x11vnc -display :1 -localhost -rfbport 5900 -nopw -forever -shared > /app/logs/vnc.log 2>&1 &
vnc=$!
websockify --web=/usr/share/novnc 6080 localhost:5900 > /app/logs/websockify.log 2>&1 &
web=$!
/app/bin/agent_runner --port 8086 > /app/logs/agent.log 2>&1 &
agent=$!
trap 'rm -f /tmp/vnc_ready; kill "$agent" "$web" "$vnc" "$browser" "$desktop" "$xvfb" 2>/dev/null || true' EXIT
trap 'exit 0' TERM INT
# Match agent_runner's readiness contract; never mark an unopened desktop ready.
python3 - <<'PY'
import socket
import time
import urllib.request
from pathlib import Path

for attempt in range(100):
    try:
        with socket.create_connection(('127.0.0.1', 5900), timeout=2) as stream:
            banner = b''
            while len(banner) < 12:
                chunk = stream.recv(12 - len(banner))
                if not chunk:
                    raise OSError('Incomplete RFB greeting')
                banner += chunk
            if not banner.startswith(b'RFB ') or not banner.endswith(b'\n'):
                raise OSError('Invalid RFB greeting')
        with urllib.request.urlopen('http://127.0.0.1:6080/vnc.html', timeout=2) as response:
            if b'noVNC' not in response.read():
                raise OSError('Missing noVNC page')
        Path('/tmp/vnc_ready').touch()
        break
    except OSError:
        time.sleep(0.2)
else:
    raise SystemExit('Desktop readiness probe failed')
PY
wait -n "$agent" "$web" "$vnc" "$desktop" "$xvfb"
exit 1
