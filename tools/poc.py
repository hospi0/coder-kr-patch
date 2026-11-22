# -*- coding: utf-8 -*-
"""PoC — ADV_MG26 寛 첫 대사 한 줄을 한글로. 한글 = EUC-KR 코드 + FONTDIC/FONT24 칸 교체(글꼴 검색은 처음부터 차례로, 0x06057476).
python tools/poc.py          → work/poc/ 에 FONTDIC.FNT·FONT24.FNT·ADV_MG26.DAT, 미리보기 work/preview/poc_대사줄.png
python tools/poc.py build    → 위 + 트랙1 새로 쓰기 work/build/
"""
import os, sys, shutil, struct
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
ISO = os.path.join(ROOT, 'work', 'iso')
NG = r'C:\claude\utils\font\nanum-gothic\NanumGothic.ttf'


def hangul_glyph(ch):
    """나눔고딕 21px · 문턱 60(하스피 선택 2번, 2026-11-21) → 72 B(8×8 조각 3×3)"""
    fo = ImageFont.truetype(NG, 21); im = Image.new('L', (24, 24)); dr = ImageDraw.Draw(im)
    bb = dr.textbbox((0, 0), ch, font=fo); w = bb[2] - bb[0]; h = bb[3] - bb[1]
    dr.text(((24 - w) // 2 - bb[0], (24 - h) // 2 - bb[1]), ch, font=fo, fill=255)
    px = im.load(); out = bytearray(72)
    for y in range(24):
        for x in range(24):
            if px[x, y] >= 60: out[((y // 8) * 3 + x // 8) * 8 + y % 8] |= 0x80 >> (x % 8)
    return bytes(out)


def enc(s):
    """한글 = EUC-KR, 나머지(가나·부호·전각 공백) = EUC-JP, \n = 0A 0A(원문 줄바꿈 꼴)"""
    out = bytearray()
    for c in s:
        if c == '\n': out += b'\n\n'
        elif '가' <= c <= '힣': out += c.encode('euc_kr')
        else: out += c.encode('euc_jp')
    return bytes(out)


def main():
    font = bytearray(open(os.path.join(ISO, 'FONT24.FNT'), 'rb').read())
    dic = bytearray(open(os.path.join(ISO, 'FONTDIC.FNT'), 'rb').read())
    mg = bytearray(open(os.path.join(ISO, 'ADV_MG26.DAT'), 'rb').read())
    codes = [bytes(dic[i:i + 2]) for i in range(0, len(dic), 2)]
    # 대사 바꾸기 — 포인터 0xB68 → 0x242000+0x2DD0, 원문 62 B
    S, E = 0x2DD0, 0x2E0E
    assert struct.unpack_from('>I', mg, 0xB68)[0] == 0x242000 + S and mg[E] == 0
    assert mg[S:E].decode('euc_jp') == '【　寛　】まったく…よくこう、\n\n　　　　　簡単に眠れるなぁ〜。'
    kr = '【　寛　】정말…이렇게　쉽게도\n　　　　　잠이　드는구나〜。'
    new = enc(kr); assert len(new) <= E - S, len(new)
    mg[S:E] = new + b'\0' * (E - S - len(new))
    # 글꼴 칸: 한글 코드가 이미 사전에 있으면 그 칸, 없으면 이 장면·실행 파일에 안 쓰이는 한자 칸을 빌림
    used = set()
    for fn in ('ADV_MG26.DAT', 'ADV.EXE'):
        b = open(os.path.join(ISO, fn), 'rb').read()
        used |= {b[i:i + 2] for i in range(len(b) - 1)}
    victims = [i for i, c in enumerate(codes) if c[0] >= 0xB0 and c not in used]
    for ch in sorted({c for c in kr if '가' <= c <= '힣'}):
        k = ch.encode('euc_kr')
        i = codes.index(k) if k in codes else victims.pop()
        codes[i] = k; dic[i * 2:i * 2 + 2] = k; font[i * 72:(i + 1) * 72] = hangul_glyph(ch)
        print(ch, k.hex(), '칸', i)
    os.makedirs(os.path.join(ROOT, 'work', 'poc'), exist_ok=True)
    out = {'FONTDIC.FNT': bytes(dic), 'FONT24.FNT': bytes(font), 'ADV_MG26.DAT': bytes(mg)}
    for k, v in out.items(): open(os.path.join(ROOT, 'work', 'poc', k), 'wb').write(v)
    # 미리보기: 바뀐 사전·글꼴로 게임처럼 다시 그림(사전 검색 → 칸)
    img = Image.new('L', (24 * 22, 24 * 3)); x = y = 0; b = mg[S:]; i = 0
    while b[i]:
        if b[i] == 0x0A: i += 1; continue
        c = bytes(b[i:i + 2]); i += 2
        if c == b'\xa1\xa1' and x == 0 and y == 0: pass
        if c in codes:
            g = codes.index(c); gi = Image.new('L', (24, 24)); p = gi.load()
            for yy in range(24):
                for xx in range(24):
                    if font[g * 72 + ((yy // 8) * 3 + xx // 8) * 8 + yy % 8] >> (7 - xx % 8) & 1: p[xx, yy] = 255
            img.paste(gi, (x * 24, y * 24))
        else: print('사전에 없음', c.hex())
        x += 1
        if b[i:i + 2] == b'\n\n': x = 0; y += 1; i += 2
    img.resize((img.width * 2, img.height * 2), Image.NEAREST).save(os.path.join(ROOT, 'work', 'preview', 'poc_대사줄.png'))
    return out


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    out = main()
    if len(sys.argv) > 1 and sys.argv[1] == 'build':
        import isopatch
        src = r'C:\claude\roms\ss\Code R (Japan)\Code R (Japan) (Track 1).bin'
        os.makedirs(os.path.join(ROOT, 'work', 'build'), exist_ok=True)
        dst = os.path.join(ROOT, 'work', 'build', 'Code R (Japan) (Track 1).bin')
        isopatch.patch(src, dst, out)
        isopatch.verify(dst, out)
