"""Render the complete project manual with embedded Chinese fonts and navigation."""
import html
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, PageBreak,
    LongTable, TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'tmp/pdfs'
OUTPUT = ROOT / 'output/pdf'
OUTPUT.mkdir(parents=True, exist_ok=True)
tokens = json.loads((WORK / 'manual-tokens.json').read_text(encoding='utf-8'))
pdfmetrics.registerFont(TTFont('Body', 'C:/Windows/Fonts/Deng.ttf'))
pdfmetrics.registerFont(TTFont('Heading', 'C:/Windows/Fonts/Dengb.ttf'))
pdfmetrics.registerFont(TTFont('Code', 'C:/Windows/Fonts/consola.ttf'))
pdfmetrics.registerFontFamily('Body', normal='Body', bold='Heading', italic='Body', boldItalic='Heading')
pdfmetrics.registerFontFamily('Heading', normal='Heading', bold='Heading', italic='Heading', boldItalic='Heading')
available = set(pdfmetrics.getFont('Body').face.charWidths)
removed = set()
def readable(text):
    for symbol, label in {'✅': '[是]', '❌': '[否]', '⚠': '[注意]', '⏰': '[定时]', '⏱': '[耗时]', '🔴': '[红]', '🟡': '[黄]', '🟢': '[绿]', '🔵': '[蓝]', '▶': '>'}.items():
        text = text.replace(symbol, label)
    text = text.replace('\u2011', '-').replace('\u2013', '-').replace('\u2014', '-')
    for char in text:
        if ord(char) > 31 and ord(char) not in available:
            removed.add(char)
    return ''.join(c for c in text if ord(c) < 32 or ord(c) in available)

ink = colors.HexColor('#223047')
blue = colors.HexColor('#2458A6')
base = dict(fontName='Body', fontSize=9.5, leading=15, textColor=ink, wordWrap='CJK', spaceAfter=6)
styles = {
    'body': ParagraphStyle('body', **base),
    'note': ParagraphStyle('note', **{**base, 'fontSize': 8.5, 'leading': 13, 'textColor': colors.HexColor('#596779'), 'leftIndent': 9, 'borderColor': colors.HexColor('#CBD6E5'), 'borderWidth': 0.5, 'borderPadding': 6, 'spaceBefore': 4, 'spaceAfter': 10}),
    'code': ParagraphStyle('code', **{**base, 'fontSize': 7.4, 'leading': 10.5, 'leftIndent': 7, 'rightIndent': 7, 'spaceAfter': 0, 'backColor': colors.HexColor('#F1F4F8')}),
    'cell': ParagraphStyle('cell', **{**base, 'fontSize': 7.4, 'leading': 11, 'spaceAfter': 0}),
    'th': ParagraphStyle('th', **{**base, 'fontName': 'Heading', 'fontSize': 7.4, 'leading': 11, 'spaceAfter': 0}),
}
for level in range(1, 7):
    sizes = {1: 22, 2: 17, 3: 13.5, 4: 11.3, 5: 10.3, 6: 9.7}
    styles['h'+str(level)] = ParagraphStyle('h'+str(level), fontName='Heading', fontSize=sizes[level], leading=sizes[level]*1.45, textColor=blue if level < 4 else ink, wordWrap='CJK', spaceBefore=16 if level < 4 else 10, spaceAfter=8, keepWithNext=True)

# Resolve local chapter links to PDF bookmarks.
headings = {}
for i, token in enumerate(tokens):
    if token['type'] == 'heading_open' and i + 1 < len(tokens):
        text = tokens[i+1]['content']
        headings.setdefault(text.strip(), 'section-' + str(i))
coverage = json.loads((ROOT / 'docs/user-manual/coverage.json').read_text(encoding='utf-8'))
chapter_anchors = {c['name']: headings.get(c['title']) for c in coverage}
chapter_anchors['project-guide.md'] = headings.get('项目操作指南')

def inline(children):
    result = []
    link_stack = []
    for t in children or []:
        typ = t['type']
        if typ in ('text', 'html_inline'):
            # The source may use br in a parameter table.
            content = t['content'].replace('<br>', '\n').replace('<br/>', '\n')
            result.append(html.escape(readable(content)).replace('\n', '<br/>'))
        elif typ == 'code_inline':
            result.append('<font color="#355B88">' + html.escape(readable(t['content'])) + '</font>')
        elif typ == 'strong_open': result.append('<b>')
        elif typ == 'strong_close': result.append('</b>')
        elif typ == 'em_open': result.append('<i>')
        elif typ == 'em_close': result.append('</i>')
        elif typ in ('softbreak', 'hardbreak'): result.append('<br/>')
        elif typ == 'link_open':
            attrs = dict(t.get('attrs') or [])
            href = attrs.get('href', '')
            anchor = chapter_anchors.get(Path(unquote(href.split('#')[0])).name)
            if anchor:
                result.append('<a href="#' + anchor + '" color="#2458A6">')
                link_stack.append(True)
            elif href.startswith(('https://', 'http://', 'mailto:')):
                result.append('<a href="' + html.escape(href, quote=True) + '" color="#2458A6">')
                link_stack.append(True)
            else:
                link_stack.append(False)
        elif typ == 'link_close':
            if link_stack and link_stack.pop(): result.append('</a>')
        elif typ == 'image':
            result.append(html.escape(readable(t.get('content', ''))))
        elif typ == 's_open': result.append('<strike>')
        elif typ == 's_close': result.append('</strike>')
    return ''.join(result)

WIDTH, HEIGHT = A4
MARGIN = 18*mm
CONTENT_WIDTH = WIDTH - MARGIN*2
class ManualDoc(BaseDocTemplate):
    def __init__(self, filename):
        super().__init__(filename, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=22*mm, bottomMargin=20*mm, title='Singu X 智能体平台完整用户手册', author='Singu X', pageCompression=1)
        frame = Frame(MARGIN, 20*mm, CONTENT_WIDTH, HEIGHT-42*mm, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates(PageTemplate(id='manual', frames=[frame], onPage=self.decorate))
    def decorate(self, canvas, doc):
        canvas.saveState()
        if doc.page > 1:
            canvas.setFont('Body', 8)
            canvas.setFillColor(colors.HexColor('#627189'))
            canvas.drawString(MARGIN, HEIGHT-13*mm, 'Singu X  |  智能体平台用户手册')
            canvas.setStrokeColor(colors.HexColor('#DBE2EC'))
            canvas.line(MARGIN, HEIGHT-15*mm, WIDTH-MARGIN, HEIGHT-15*mm)
        canvas.setFont('Body', 8)
        canvas.setFillColor(colors.HexColor('#627189'))
        canvas.drawString(MARGIN, 11*mm, '2026-10-04  ·  项目化整理版')
        canvas.drawRightString(WIDTH-MARGIN, 11*mm, str(doc.page))
        canvas.restoreState()
    def afterFlowable(self, flowable):
        if hasattr(flowable, 'manual_anchor'):
            key = flowable.manual_anchor
            self.canv.bookmarkPage(key)
            level = flowable.manual_level
            if level in (2, 3):
                toc_level = level - 2
                text = flowable.getPlainText()
                self.notify('TOCEntry', (toc_level, text, self.page, key))
                self.canv.addOutlineEntry(text, key, level=toc_level, closed=toc_level == 0)

story = []
story.append(Spacer(1, 35*mm))
story.append(Paragraph('SINGU X', ParagraphStyle('brand', fontName='Heading', fontSize=18, leading=25, textColor=blue)))
story.append(Spacer(1, 10*mm))
story.append(Paragraph('智能体平台<br/>完整用户手册', ParagraphStyle('cover', fontName='Heading', fontSize=30, leading=44, textColor=ink)))
story.append(Spacer(1, 14*mm))
story.append(Paragraph('项目操作指南 · 85 篇功能及接口文档<br/>含 38 篇 API 参考', ParagraphStyle('subtitle', **{**base, 'fontSize': 13, 'leading': 22})))
story.append(Spacer(1, 14*mm))
story.append(Paragraph('2026-10-04<br/>适用于普通用户、开发者及管理员', styles['body']))
story.append(Spacer(1, 14*mm))
story.append(Paragraph('线上维持单租户。生产能力按当前部署与授权核对。<br/>整理版已移除原厂品牌、推广及含品牌截图。', styles['note']))
story.append(PageBreak())
story.append(Paragraph('目录', styles['h2']))
toc = TableOfContents()
toc.levelStyles = [
    ParagraphStyle('toc0', fontName='Heading', fontSize=10.5, leading=17, textColor=ink, spaceBefore=8, wordWrap='CJK'),
    ParagraphStyle('toc1', fontName='Body', fontSize=9, leading=14, leftIndent=14, firstLineIndent=0, textColor=ink, wordWrap='CJK'),
]
story.append(toc)
story.append(PageBreak())
quote_depth = 0
list_stack = []
item_start = False
stats = {'headings': 0, 'tables': 0, 'code_blocks': 0, 'paragraphs': 0}
i = 0
while i < len(tokens):
    t = tokens[i]
    typ = t['type']
    if typ == 'heading_open':
        level = int(t['tag'][1])
        content = tokens[i+1]
        if level != 1:
            if level == 2 and story:
                story.append(PageBreak())
            p = Paragraph(inline(content.get('children')), styles['h'+str(level)])
            p.manual_anchor = 'section-' + str(i)
            p.manual_level = level
            story.append(p)
            stats['headings'] += 1
        i += 3
        continue
    if typ == 'blockquote_open': quote_depth += 1
    elif typ == 'blockquote_close': quote_depth -= 1
    elif typ in ('bullet_list_open', 'ordered_list_open'):
        attrs = dict(t.get('attrs') or [])
        list_stack.append({'ordered': typ == 'ordered_list_open', 'n': int(attrs.get('start', 1))})
    elif typ in ('bullet_list_close', 'ordered_list_close'):
        if list_stack: list_stack.pop()
    elif typ == 'list_item_open':
        item_start = True
    elif typ == 'paragraph_open':
        if i+1 < len(tokens) and tokens[i+1]['type'] == 'inline':
            content = inline(tokens[i+1].get('children'))
            style = styles['note'] if quote_depth else styles['body']
            if list_stack:
                depth = len(list_stack)
                style = ParagraphStyle('list', parent=style, leftIndent=min(depth, 4)*12, firstLineIndent=-9, spaceAfter=4)
                if item_start:
                    current = list_stack[-1]
                    prefix = str(current['n']) + '. ' if current['ordered'] else '- '
                    current['n'] += 1
                    content = prefix + content
                    item_start = False
            story.append(Paragraph(content or ' ', style))
            stats['paragraphs'] += 1
            i += 3
            continue
    elif typ in ('fence', 'code_block'):
        story.append(Spacer(1, 5))
        for line in t['content'].splitlines():
            safe = html.escape(readable(line)).replace(' ', '&#160;')
            story.append(Paragraph(safe or '&#160;', styles['code']))
        story.append(Spacer(1, 8))
        stats['code_blocks'] += 1
    elif typ == 'table_open':
        rows, current = [], []
        j = i + 1
        while j < len(tokens) and tokens[j]['type'] != 'table_close':
            cell = tokens[j]
            if cell['type'] == 'tr_open': current = []
            elif cell['type'] == 'inline': current.append(cell)
            elif cell['type'] == 'tr_close': rows.append(current)
            j += 1
        if rows:
            columns = max(len(r) for r in rows)
            # Wide request parameter tables need smaller, consistently wrapped text.
            size = 7.4 if columns <= 6 else 6.7
            cell_style = ParagraphStyle('cell-' + str(stats['tables']), parent=styles['cell'], fontSize=size, leading=size*1.48)
            head_style = ParagraphStyle('th-' + str(stats['tables']), parent=cell_style, fontName='Heading')
            weights = [1.0] * columns
            for col in range(columns):
                samples = [len(row[col]['content']) for row in rows[:25] if len(row) > col]
                weights[col] = min(2.8, max(1, (max(samples, default=4) ** 0.45)/2))
            widths = [CONTENT_WIDTH*w/sum(weights) for w in weights]
            data = [[Paragraph(inline(c.get('children')) or ' ', head_style if n == 0 else cell_style) for c in row] + [Paragraph(' ', cell_style)]*(columns-len(row)) for n, row in enumerate(rows)]
            table = LongTable(data, colWidths=widths, repeatRows=1, splitByRow=1, splitInRow=1, hAlign='LEFT')
            table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#EAF0F8')),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFD')]),
                ('GRID', (0,0), (-1,-1), 0.35, colors.HexColor('#CDD7E5')),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('LEFTPADDING', (0,0), (-1,-1), 5), ('RIGHTPADDING', (0,0), (-1,-1), 5),
                ('TOPPADDING', (0,0), (-1,-1), 5), ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ]))
            story.append(table)
            story.append(Spacer(1, 9))
            stats['tables'] += 1
        i = j + 1
        continue
    elif typ == 'hr': story.append(Spacer(1, 8))
    i += 1

pdf_path = OUTPUT / 'SinguX-User-Manual.pdf'
doc = ManualDoc(str(pdf_path))
doc.multiBuild(story)
stats['removed_unsupported_symbols'] = sorted(removed)
stats['output'] = str(pdf_path)
(WORK / 'build-statistics.json').write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(stats, ensure_ascii=False))
