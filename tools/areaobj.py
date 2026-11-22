# -*- coding: utf-8 -*-
"""AREAOBJ.SPR — 앞 512 B = 팔레트 256색(RGB555 BE), 뒤 = 8bpp 스프라이트(크기 표 없음, 위치·크기는 스테이트 VDP1 명령으로 확인)
날짜 띠: 숫자 16×24 · am/pm 32×24 · 요일 64×24 · 日目 40×24 (2026-11-22 코드R)"""
import os, struct
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, 'work', 'iso', 'AREAOBJ.SPR')
# (이름, 파일 오프셋, 폭, 높이) — 0xD400 日曜日 · 0x1D700 日目 는 스테이트 명령에서 확인, 나머지 요일은 64×24 = 1536 B 간격(확인 ⏳)
def load(): return open(P, 'rb').read()
def pal(f): return [struct.unpack_from('>H', f, i * 2)[0] for i in range(256)]
def rgb(e): return ((e & 31) << 3, ((e >> 5) & 31) << 3, ((e >> 10) & 31) << 3)
def img(f, off, w, h):
    pl = pal(f); im = Image.new('RGBA', (w, h)); px = im.load()
    for i in range(w * h):
        c = f[off + i]; px[i % w, i // w] = rgb(pl[c]) + (255,) if c else (0, 0, 0, 0)
    return im
