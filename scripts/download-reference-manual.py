"""Download the linked documentation corpus and its article assets, without executing it."""
import concurrent.futures
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote

import requests
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')
BASE = 'https://nuwax.com/'
ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'docs/manual-archive'
HTML = ARCHIVE / 'html'
ASSETS = ARCHIVE / 'assets'
HTML.mkdir(parents=True, exist_ok=True)
ASSETS.mkdir(parents=True, exist_ok=True)

def get(url):
    for attempt in range(3):
        try:
            r = requests.get(url, timeout=45)
            r.raise_for_status()
            return r.content
        except requests.RequestException:
            if attempt == 2:
                raise
            time.sleep(attempt + 1)

entry_file = ARCHIVE / 'entry-original.html'
index = entry_file.read_bytes() if entry_file.exists() else get(BASE + 'user-manual.html')
entry_file.write_bytes(index)
soup = BeautifulSoup(index, 'html.parser')
paths = sorted({urlparse(urljoin(BASE, a['href'])).path for a in soup.select('.VPSidebar a[href]') if urlparse(urljoin(BASE, a['href'])).netloc == urlparse(BASE).netloc})
# Include article-to-article links recursively, but not site navigation, marketing, or external sites.
pending = set(paths)
pages = {}
errors = []
assets = set()

def page(path):
    data = index if path == '/user-manual.html' else get(urljoin(BASE, path))
    doc = BeautifulSoup(data, 'html.parser')
    article = doc.select_one('.vp-doc')
    if article is None:
        raise ValueError('No article: ' + path)
    filename = path.strip('/').replace('/', '__') or 'index.html'
    (HTML / filename).write_bytes(data)
    links = []
    for a in article.select('a[href]'):
        target = urlparse(urljoin(BASE + path.lstrip('/'), a['href']))
        if target.netloc == urlparse(BASE).netloc and target.path.endswith('.html'):
            links.append(target.path)
    media = []
    for img in article.select('img[src], video[src], source[src]'):
        target = urljoin(BASE + path.lstrip('/'), img['src'])
        if target.startswith(('https://', 'http://')):
            media.append(target)
    h = article.find('h1')
    title = h.get_text(' ', strip=True).replace('\u200b', '').strip() if h else filename
    return {'path': path, 'file': filename, 'title': title, 'sha256': hashlib.sha256(data).hexdigest(), 'assets': media}, links

while pending:
    batch = sorted(pending - pages.keys())
    pending = set()
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(page, p): p for p in batch}
        for f in concurrent.futures.as_completed(futures):
            p = futures[f]
            try:
                record, links = f.result()
                pages[p] = record
                assets.update(record['assets'])
                pending.update(x for x in links if x not in pages and x not in batch)
            except Exception as e:
                errors.append({'url': urljoin(BASE, p), 'error': str(e)})
    print('pages:', len(pages), 'remaining:', len(pending), flush=True)

def asset(url):
    suffix = Path(unquote(urlparse(url).path)).suffix or '.bin'
    name = hashlib.sha256(url.encode()).hexdigest()[:20] + suffix
    data = get(url)
    (ASSETS / name).write_bytes(data)
    return {'url': url, 'file': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

asset_records = []
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
    futures = {pool.submit(asset, u): u for u in sorted(assets)}
    for f in concurrent.futures.as_completed(futures):
        try:
            asset_records.append(f.result())
        except Exception as e:
            errors.append({'url': futures[f], 'error': str(e)})

manifest = {'retrieved': '2026-10-04', 'entry': BASE + 'user-manual.html', 'pages': sorted(pages.values(), key=lambda x: x['path']), 'assets': sorted(asset_records, key=lambda x: x['url']), 'errors': errors}
(ARCHIVE / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'pages': len(pages), 'assets': len(asset_records), 'errors': errors}, ensure_ascii=False), flush=True)
if errors:
    sys.exit(1)
