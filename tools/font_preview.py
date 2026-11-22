# -*- coding: utf-8 -*-
"""한글 글꼴 후보 미리보기 — 원본 대사 한 줄 vs 후보별 한글 (work/preview/poc_글꼴후보.png)"""
from PIL import Image, ImageDraw, ImageFont
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
f = open(os.path.join(ROOT, 'work/iso/FONT24.FNT'), 'rb').read(); d = open(os.path.join(ROOT, 'work/iso/FONTDIC.FNT'), 'rb').read()
codes = [d[i:i + 2] for i in range(0, len(d), 2)]
def glyph_img(i):
    g = f[i * 72:(i + 1) * 72]; im = Image.new('1', (24, 24))
    for y in range(24):
        for x in range(24):
            if (g[((y // 8) * 3 + (x // 8)) * 8 + y % 8] >> (7 - x % 8)) & 1: im.putpixel((x, y), 1)
    return im
def orig(ch): return glyph_img(codes.index(ch.encode('euc_jp')))
def ttf(path, size, ch, th=110):
    if not ('가' <= ch <= '힣'): return orig({'～': '〜'}.get(ch, ch))
    fo = ImageFont.truetype(path, size); im = Image.new('L', (24, 24)); dr = ImageDraw.Draw(im)
    bb = dr.textbbox((0, 0), ch, font=fo); w = bb[2] - bb[0]; h = bb[3] - bb[1]
    dr.text(((24 - w) // 2 - bb[0], (24 - h) // 2 - bb[1]), ch, font=fo, fill=255)
    return im.point(lambda v: 255 if v >= th else 0).convert('1')
def gal2x(ch):
    if not ('가' <= ch <= '힣'): return orig({'～': '〜'}.get(ch, ch))
    fo = ImageFont.truetype(r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri11.ttf', 12)
    im = Image.new('L', (12, 12)); ImageDraw.Draw(im).text((0, 0), ch, font=fo, fill=255)
    return im.resize((24, 24), Image.NEAREST).point(lambda v: 255 if v >= 128 else 0).convert('1')
if __name__ == '__main__':
    jp = 'まったく…よくこう、簡単に眠れるなぁ〜。'
    kr = '정말…이렇게 쉽게도 잠이 드는구나～。'
    NG = r'C:\claude\utils\font\nanum-gothic\NanumGothic.ttf'
    rows = [('원본', [orig(c) if c != ' ' else Image.new('1', (24, 24)) for c in jp])]
    for nm, fn in [('나눔고딕 22', lambda c: ttf(NG, 22, c)), ('나눔고딕 21 진하게', lambda c: ttf(NG, 21, c, 60)),
                   ('맑은고딕 21', lambda c: ttf(r'C:\Windows\Fonts\malgun.ttf', 21, c)), ('갈무리11 2배', gal2x),
                   ('갈무리14', lambda c: ttf(r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri14.ttf', 21, c, 128))]:
        rows.append((nm, [fn(c) if c != ' ' else Image.new('1', (24, 24)) for c in kr]))
    S = 2; W = 22 * 24 * S + 200; H = len(rows) * 30 * S
    sheet = Image.new('RGB', (W, H), (40, 40, 70)); dr = ImageDraw.Draw(sheet); lab = ImageFont.truetype(r'C:\Windows\Fonts\malgun.ttf', 20)
    for r, (nm, gl) in enumerate(rows):
        y = r * 30 * S + 6; dr.text((6, y + 10), '%d %s' % (r, nm), font=lab, fill=(255, 255, 0))
        for i, g in enumerate(gl):
            sheet.paste((255, 255, 255), (200 + i * 24 * S, y), g.convert('L').resize((24 * S, 24 * S), Image.NEAREST))
    sheet.save(os.path.join(ROOT, 'work/preview/poc_글꼴후보.png')); print('ok')
