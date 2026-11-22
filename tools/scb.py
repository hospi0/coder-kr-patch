# -*- coding: utf-8 -*-
"""SCB(무압축 칸 그림 + 지도) 읽기·그리기·쓰기 — 2026-11-22 코드R
머리 16 B: u16 종류(0x8010 4bpp / 0x8100 8bpp) · u16 bpp · u32 칸 수 · u32 0x80000000|가로칸 · u32 0x80000000|세로칸
→ 팔레트(16/256색 RGB555) → 칸 그림(8×8, 32/64 B) × 칸 수 → 지도 u16 × 가로×세로
python tools/scb.py FONT_10 ...  → work/scb/<이름>.png"""
import os, struct, sys
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def parse(b):
    typ, bpp, n, w, h = struct.unpack_from('>HHIII', b, 0)
    w &= 0x7fffffff; h &= 0x7fffffff
    ncol = 16 if bpp == 4 else 256; csz = 32 if bpp == 4 else 64
    pal = list(struct.unpack_from('>%dH' % ncol, b, 16)); p = 16 + ncol * 2
    cells = [b[p + i * csz:p + (i + 1) * csz] for i in range(n)]; p += n * csz
    mp = list(struct.unpack_from('>%dH' % (w * h), b, p)); p += w * h * 2
    assert p == len(b), (p, len(b))
    return dict(typ=typ, bpp=bpp, w=w, h=h, pal=pal, cells=cells, map=mp)


def rgb(e): return ((e & 31) << 3, ((e >> 5) & 31) << 3, ((e >> 10) & 31) << 3)


def render(S):
    im = Image.new('RGBA', (S['w'] * 8, S['h'] * 8)); px = im.load()
    for k, m in enumerate(S['map']):
        cx, cy = (k % S['w']) * 8, (k // S['w']) * 8
        ci = (m & 0x3ff) // (2 if S['bpp'] == 8 else 1)          # 8bpp 칸 번호는 32 B 단위(2배)
        c = S['cells'][ci] if ci < len(S['cells']) else bytes(64)
        for y in range(8):
            for x in range(8):
                idx = (c[y * 4 + x // 2] >> (4 * (1 - x % 2))) & 15 if S['bpp'] == 4 else c[y * 8 + x]
                px[cx + x, cy + y] = rgb(S['pal'][idx]) + (255,) if idx else (0, 0, 0, 0)
    return im


if __name__ == '__main__':
    os.makedirs(os.path.join(ROOT, 'work', 'scb'), exist_ok=True)
    for nm in sys.argv[1:]:
        S = parse(open(os.path.join(ROOT, 'work', 'iso', nm + '.SCB'), 'rb').read())
        print(nm, S['bpp'], 'bpp', S['w'], 'x', S['h'], '칸', len(S['cells']), '지도 최대', hex(max(S['map'])))
        render(S).save(os.path.join(ROOT, 'work', 'scb', nm + '.png'))
