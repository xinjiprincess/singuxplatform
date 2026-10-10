"""Narrow production hotfix: preserve the deployed app and disable missing mobile app routing."""
import datetime
import json
import pathlib
import shutil
import subprocess

def run(*args):
    subprocess.run(args, check=True)

root = pathlib.Path('/home/singu-x-1.1.10-20260924-r1-linux-amd64')
backup = pathlib.Path('/data/singux-backups') / ('web-entry-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
backup.mkdir(parents=True)
compose = root / 'compose.json'
nginx = pathlib.Path('/etc/nginx/conf.d/ciyuan.conf')
shutil.copy2(compose, backup / 'compose.json')
shutil.copy2(nginx, backup / 'ciyuan.conf')
run('docker', 'cp', 'singux-frontend-1:/usr/share/nginx/html/index.html', str(backup / 'index.original.html'))
html = (backup / 'index.original.html').read_text()
needle = 'const isMobile = /Android|iPhone|iPad|iPod|Mobile|Tablet/i.test(navigator.userAgent);'
if html.count(needle) != 1:
    raise RuntimeError('Unexpected deployed entry; no changes applied')
(backup / 'index.html').write_text(html.replace(needle, 'const isMobile = false; // No standalone mobile app deployed'), encoding='utf-8')
config = json.loads(compose.read_text())
image = config['services']['frontend']['image']
if '\n' in image or ' ' in image:
    raise RuntimeError('Unexpected image reference')
(backup / 'Dockerfile').write_text('FROM ' + image + '\nCOPY index.html /usr/share/nginx/html/index.html\n')
tag = 'singux/frontend:1.1.10-20260928-entry-fix'
run('docker','build','-t',tag,str(backup))
new_nginx = nginx.read_text()
anchor = '    client_max_body_size 100m;'
if new_nginx.count(anchor) != 1 or 'gzip on;' in new_nginx:
    raise RuntimeError('Unexpected nginx configuration; inspect before applying')
new_nginx = new_nginx.replace(anchor, anchor + '\n    gzip on;\n    gzip_vary on;\n    gzip_min_length 1024;\n    gzip_comp_level 5;\n    gzip_types application/javascript text/css image/svg+xml;')
try:
    nginx.write_text(new_nginx)
    run('nginx','-t')
    config['services']['frontend']['image'] = tag
    compose.write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n')
    run('docker','compose','-f',str(compose),'up','-d','--no-deps','--wait','--wait-timeout','90','frontend')
    run('systemctl','reload','nginx')
except Exception:
    shutil.copy2(backup/'ciyuan.conf',nginx)
    shutil.copy2(backup/'compose.json',compose)
    run('docker','compose','-f',str(compose),'up','-d','--no-deps','frontend')
    run('nginx','-t')
    run('systemctl','reload','nginx')
    raise
print('BACKUP:',backup)
print('IMAGE:',tag)
