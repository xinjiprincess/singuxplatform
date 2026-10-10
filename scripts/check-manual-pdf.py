import json
import re
import sys
from pathlib import Path
from pypdf import PdfReader
import pypdfium2 as pdfium
from PIL import Image, ImageDraw

sys.stdout.reconfigure(encoding='utf-8')
root = Path(__file__).resolve().parents[1]
work = root / 'tmp/pdfs'
pdf_file = root / 'output/pdf/SinguX-User-Manual.pdf'
reader = PdfReader(str(pdf_file))
page_texts = [p.extract_text() or '' for p in reader.pages]
all_text = '\n'.join(page_texts)
coverage = json.loads((root / 'docs/user-manual/coverage.json').read_text(encoding='utf-8'))
normalize = lambda s: re.sub(r'\s+', '', s)
joined = normalize(all_text)
missing = [c['title'] for c in coverage if normalize(c['title']) not in joined]
checks = {
    'pages': len(reader.pages), 'bytes': pdf_file.stat().st_size,
    'chapters_expected': len(coverage), 'missing_chapter_titles': missing,
    'old_brand_found': bool(re.search(r'女娲|nuwax|\bxagi\b', all_text, re.I)),
    'replacement_glyph_found': '\ufffd' in all_text,
    'outline_root_entries': len(reader.outline),
    'source': 'docs/user-manual.md',
}
samples = [0, 1, 2, 6, 12, len(reader.pages)-1]
for needle in ['接口地址', '请求参数', '工作流', 'Hook']:
    matches = [i for i, t in enumerate(page_texts) if needle in t and i > 7]
    if matches:
        samples.append(matches[len(matches)//2])
samples = sorted(set(samples))
doc = pdfium.PdfDocument(str(pdf_file))
thumbs = []
for i in samples:
    image = doc[i].render(scale=1.15).to_pil().convert('RGB')
    image.save(work / ('page-%03d.png' % (i+1)))
    image.thumbnail((420, 595))
    cell = Image.new('RGB', (440, 630), '#dce2ea')
    cell.paste(image, ((440-image.width)//2, 25))
    ImageDraw.Draw(cell).text((12, 8), 'Page %d' % (i+1), fill='black')
    thumbs.append(cell)
cols = 3
rows = (len(thumbs)+cols-1)//cols
sheet = Image.new('RGB', (cols*440, rows*630), '#dce2ea')
for n, image in enumerate(thumbs):
    sheet.paste(image, ((n%cols)*440, (n//cols)*630))
sheet.save(work / 'contact-sheet.png')
checks['rendered_pages'] = [i+1 for i in samples]
(work / 'pdf-validation.json').write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(checks, ensure_ascii=False, indent=2))
if missing or checks['old_brand_found'] or checks['replacement_glyph_found']:
    sys.exit(1)
