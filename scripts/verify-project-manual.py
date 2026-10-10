"""Build an offline source edition and validate the Markdown delivery."""
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')
root = Path(__file__).resolve().parents[1]
archive = root / 'docs/manual-archive'
out = root / 'docs/user-manual'
manifest = json.loads((archive / 'manifest.json').read_text(encoding='utf-8'))
offline = archive / 'offline'
offline.mkdir(exist_ok=True)
page_paths = {p['path']: p['file'] for p in manifest['pages']}
media = {p['url']: '../assets/' + p['file'] for p in manifest['assets']}
for p in manifest['pages']:
    raw = (archive / 'html' / p['file']).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == p['sha256'], p['file']
    doc = BeautifulSoup(raw, 'html.parser')
    article = doc.select_one('.vp-doc')
    for n in article.select('script, style, iframe, button'):
        n.decompose()
    for n in article.select('[src]'):
        u = urljoin(manifest['entry'].replace('/user-manual.html', p['path']), n['src'])
        if u in media:
            n['src'] = media[u]
    for n in article.select('a[href]'):
        u = urlparse(urljoin(manifest['entry'].replace('/user-manual.html', p['path']), n['href']))
        if unquote(u.path) in page_paths:
            n['href'] = page_paths[unquote(u.path)] + ('#' + u.fragment if u.fragment else '')
    markup = '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>' + p['title'] + '</title><style>body{max-width:960px;margin:32px auto;font:16px/1.75 sans-serif;padding:0 24px}img{max-width:100%;height:auto}pre{overflow:auto;background:#f5f5f5;padding:16px}table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:8px}</style><body>' + str(article) + '</body></html>'
    (offline / p['file']).write_text(markup, encoding='utf-8')
index = '# 原始手册下载档案\n\n下载日期：2026-10-04。仅用于来源追溯，保留原站品牌和法律文本，不属于发布版本。\n\n来源：[原手册入口](' + manifest['entry'] + ')。\n\n- html：原始 HTML，SHA-256 已核对。\n- assets：成功下载的正文素材。\n- offline：移除脚本、连接本地图片的阅读页。\n- manifest.json：URL、文件、哈希、素材与失败记录。\n\n共 ' + str(len(manifest['pages'])) + ' 篇正文及 ' + str(len(manifest['assets'])) + ' 个素材。下载范围为可访问的手册及关联正文，不包含外部网站、远程视频或动态服务。\n\n## 原站缺失\n\n'
index += '\n'.join('- ' + e['url'] + '：' + e['error'] for e in manifest['errors'])
index += '\n\n其中一个外部产品页无手册正文结构；其余为 404 链接及两张 451 图片。未绕过访问限制或伪造成功。\n\n## 离线正文\n\n'
index += '\n'.join('- [' + p['title'] + '](offline/' + p['file'] + ')' for p in manifest['pages']) + '\n'
(archive / 'README.md').write_text(index, encoding='utf-8')
coverage = json.loads((out / 'coverage.json').read_text(encoding='utf-8'))
assert len(coverage) == len(manifest['pages'])
files = list(out.glob('*.md')) + [root / 'docs/user-manual.md']
broken, brand, fence_errors = [], [], []
for p in files:
    text = p.read_text(encoding='utf-8')
    if re.search(r'女娲|nuwax|nuwa(?:claw)?|\bxagi\b', text, re.I):
        brand.append(str(p.relative_to(root)))
    in_fence = None
    fence_pattern = r'^\s*(' + chr(96) + r'{3,}|~{3,})(.*)$'
    for line in text.splitlines():
        m = re.match(fence_pattern, line)
        if m:
            marker = m.group(1)
            if in_fence is None:
                in_fence = marker
            elif marker[0] == in_fence[0] and len(marker) >= len(in_fence) and not m.group(2).strip():
                in_fence = None
    if in_fence:
        fence_errors.append(str(p))
    # Fenced examples describe files in a user's skill package, not delivery links.
    marker = chr(96)
    link_text = re.sub(r'(?ms)^' + marker + r'{3,}[^\n]*\n.*?^' + marker + r'{3,}\s*$', '', text)
    for target in re.findall(r'\]\(([^)\s]+)(?:\s+"[^"]*")?\)', link_text):
        if target.startswith(('http:', 'https:', '#', 'mailto:', 'data:')):
            continue
        target = unquote(target.split('#')[0])
        if target and not (p.parent / target).exists():
            broken.append({'file': str(p.relative_to(root)), 'target': target})
report = {'date': '2026-10-04', 'source_pages': len(manifest['pages']), 'downloaded_assets': len(manifest['assets']), 'chapters': len(coverage), 'markdown_files_checked': len(files), 'brand_residuals': brand, 'broken_local_links': broken, 'unclosed_fences': fence_errors, 'source_failures': len(manifest['errors'])}
(out / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
if brand or broken or fence_errors:
    sys.exit(1)
