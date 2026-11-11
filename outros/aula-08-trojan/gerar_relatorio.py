"""Diagrama o relatório da Aula 8 a partir do Markdown, em quatro páginas A4."""
from pathlib import Path
import re
from xml.sax.saxutils import escape

from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle, Spacer, KeepTogether
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import black, HexColor
from reportlab.lib.pagesizes import A4

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUTPUT = ROOT / 'output/pdf/relatorio-aula08-preliminar.pdf'
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
for name, file in [('TimesNewRoman', 'times.ttf'), ('TimesNewRoman-Bold', 'timesbd.ttf'),
                   ('TimesNewRoman-Italic', 'timesi.ttf'), ('TimesNewRoman-BoldItalic', 'timesbi.ttf')]:
    pdfmetrics.registerFont(TTFont(name, str(Path('C:/Windows/Fonts') / file)))
pdfmetrics.registerFontFamily('TimesNewRoman', normal='TimesNewRoman', bold='TimesNewRoman-Bold',
                            italic='TimesNewRoman-Italic', boldItalic='TimesNewRoman-BoldItalic')

W, H = A4
LEFT, RIGHT, TOP, BOTTOM, GAP = 50, 50, 49, 44, 12
FULL = W - LEFT - RIGHT
COL = (FULL-GAP)/2
styles = {
    'body': ParagraphStyle('body', fontName='TimesNewRoman', fontSize=10, leading=11.7,
                           alignment=TA_JUSTIFY, firstLineIndent=10, spaceAfter=4),
    'h2': ParagraphStyle('h2', fontName='TimesNewRoman-Bold', fontSize=14, leading=16.3,
                         spaceBefore=11, spaceAfter=7, keepWithNext=True),
    'h3': ParagraphStyle('h3', fontName='TimesNewRoman-Bold', fontSize=11.6, leading=13.4,
                         spaceBefore=8, spaceAfter=6, keepWithNext=True),
    'caption': ParagraphStyle('caption', fontName='TimesNewRoman', fontSize=8.6, leading=10,
                              spaceBefore=4, spaceAfter=5),
    'cell': ParagraphStyle('cell', fontName='TimesNewRoman', fontSize=9, leading=10.5),
    'cellhead': ParagraphStyle('cellhead', fontName='TimesNewRoman-Bold', fontSize=9, leading=10.5),
    'ref': ParagraphStyle('ref', fontName='TimesNewRoman', fontSize=9, leading=10.5,
                          alignment=TA_LEFT, spaceAfter=6),
}

def markup(s):
    s = escape(s)
    s = re.sub(r'(https://[^\s]+)', lambda m: '<link href="'+m[1]+'">'+m[1]+'</link>', s)
    return s

def p(text, kind='body'):
    return Paragraph(markup(text), styles[kind])

def parse(text):
    blocks = re.split(r'\n\s*\n', text.strip())
    result = []
    for b in blocks:
        b = b.strip()
        if not b or b.startswith('<!--') or b.startswith('# '):
            continue
        if b.startswith('### '):
            result.append(p(b[4:], 'h3'))
        elif b.startswith('## '):
            result.append(p(b[3:], 'h2'))
        elif b.startswith('|'):
            rows = [[x.strip() for x in line.strip().strip('|').split('|')]
                    for line in b.splitlines() if not re.match(r'^\|\s*---', line)]
            data = [[p(cell, 'cellhead' if i==0 else 'cell') for cell in row]
                    for i,row in enumerate(rows)]
            widths = [64, COL-64] if 'Código' in rows[0][0] else [30, COL-30]
            t = Table(data, colWidths=widths, hAlign='LEFT')
            t.setStyle(TableStyle([
                ('VALIGN',(0,0),(-1,-1),'TOP'), ('LEFTPADDING',(0,0),(-1,-1),4),
                ('RIGHTPADDING',(0,0),(-1,-1),4), ('TOPPADDING',(0,0),(-1,-1),4),
                ('BOTTOMPADDING',(0,0),(-1,-1),4),
                ('LINEABOVE',(0,0),(-1,0),0.6,black),
                ('LINEBELOW',(0,0),(-1,0),0.4,black),
                ('LINEBELOW',(0,-1),(-1,-1),0.6,black),
                ('ROWBACKGROUNDS',(0,1),(-1,-1),[HexColor('#f3f3f3'),HexColor('#ffffff')])]))
            result.extend([t, Spacer(1,7)])
        elif b.startswith('Tabela '):
            result.append(p(b,'caption'))
        elif re.match(r'^\[\d\]',b):
            result.append(p(b,'ref'))
        else:
            result.append(p(' '.join(b.splitlines())))
    return result

def draw_flow(c, flow, x, y, width=COL):
    for f in flow:
        y -= f.getSpaceBefore()
        _, height = f.wrap(width, H)
        if y-height < BOTTOM:
            raise RuntimeError(f'Overflow na página {c.getPageNumber()}, coluna x={x}: {y-height:.1f}; {getattr(f,"text",str(f))[:110]}')
        f.drawOn(c, x, y-height)
        y -= height + f.getSpaceAfter()
    return y

def first_header(c):
    y = H-TOP
    c.setFont('TimesNewRoman',8)
    c.drawString(LEFT,y,'PCS5917 - IA Adversarial. Aula 8.')
    c.drawRightString(W-RIGHT,y,'Relatório preliminar - 11/11/2026')
    y -= 24
    c.setLineWidth(.5); c.line(LEFT,y,W-RIGHT,y)
    y -= 13
    title = Paragraph('Geração e detecção de trojans entre grupos',
                      ParagraphStyle('title',fontName='TimesNewRoman-Bold',fontSize=18,leading=21))
    _,h=title.wrap(FULL,H); title.drawOn(c,LEFT,y-h); y-=h+12
    metadata = [
        '<b>Arthur Moriggi Pimenta</b> - Nº USP: 9425636 - arthur.moriggi.pimenta@usp.br',
        '<b>Caio Vinícius Ribeiro da Silva</b> - Nº USP: 18083535 - caiovribeiro@usp.br',
        '<b>Roberto Spinelli Filho</b> - Nº USP: 3119088 - rspinelli@usp.br',
        '<b>Disciplina:</b> PCS5917 - IA Adversarial',
        '<b>Professor:</b> Dr. Victor Takashi Hayashi - victor.hayashi@usp.br',
        '<b>Instituição:</b> Universidade de São Paulo - Escola Politécnica',
    ]
    meta_style=ParagraphStyle('meta',fontName='TimesNewRoman',fontSize=8.6,leading=10.3)
    for line in metadata:
        f=Paragraph(line,meta_style); _,h=f.wrap(FULL,H);f.drawOn(c,LEFT,y-h);y-=h
    y-=6
    abstract = ('<b>Resumo.</b> Relatamos um desafio entre grupos de geração e detecção de trojans. '
        'Produzimos vinte variantes independentes do PicoRV32, dez deliberadamente incorretas e dez candidatas benignas, '
        'e enviamos o conjunto com IDs permutados. Na frente de detecção, analisamos estaticamente vinte versões de AES '
        'recebidas do grupo E. O grupo autor confirmou vinte acertos, com acurácia de 100%. A análise identificou '
        'gatilhos sobre dados e histórico e uma ressalva contratual em amostra benigna. A avaliação do ataque PicoRV32 '
        'permanece pendente. Discutimos os resultados da classificação e a contribuição de um ciclo purple team para a revisão entre grupos.')
    f=Paragraph(abstract,ParagraphStyle('abstract',fontName='TimesNewRoman',fontSize=9,leading=10.5,alignment=TA_JUSTIFY))
    _,h=f.wrap(FULL,H);f.drawOn(c,LEFT,y-h);y-=h+7
    f=Paragraph('<b>Palavras-chave:</b> Trojans, análise estática, PicoRV32, AES, purple team.',meta_style)
    _,h=f.wrap(FULL,H);f.drawOn(c,LEFT,y-h);y-=h+11
    c.line(LEFT,y,W-RIGHT,y)
    return y-5

source=(HERE/'relatorio-aula08-preliminar.md').read_text(encoding='utf-8')
pages=source.split('<!-- page -->')
assert len(pages)==4
c=canvas.Canvas(str(OUTPUT), pagesize=A4)
c.setTitle('Geração e detecção de trojans entre grupos - Aula 8 - Preliminar')
c.setAuthor('Arthur Moriggi Pimenta; Caio Vinícius Ribeiro da Silva; Roberto Spinelli Filho')
c.setSubject('PicoRV32 e AES; detecção confirmada em 20/20 casos; avaliação do ataque pendente')
for i,page in enumerate(pages,1):
    if i==1:
        start=first_header(c)
    else:
        c.setFont('TimesNewRoman',8)
        c.drawString(LEFT,H-30,'Aula 8: geração e detecção de trojans | Preliminar')
        c.drawRightString(W-RIGHT,H-30,'Pimenta, Silva e Spinelli Filho')
        start=H-49
    columns=page.split('<!-- column -->')
    assert len(columns)==2
    for j,col in enumerate(columns):
        end=draw_flow(c,parse(col),LEFT+j*(COL+GAP),start)
        print(f'Página {i}, coluna {j+1}: final y={end:.1f}; espaço livre={end-BOTTOM:.1f} pt')
    c.setFont('TimesNewRoman',9)
    c.drawCentredString(W/2,24,str(i))
    c.showPage()
c.save()
print(OUTPUT)
