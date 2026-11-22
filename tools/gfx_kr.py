# -*- coding: utf-8 -*-
"""그림 글자 한글화 (2026-11-22 코드R) — FONT_10/11.SCB(레이스 포즈·리플레이 종료) · AREAOBJ.SPR(날짜 띠 요일·日目)
원칙: 원본 글자 범위(상자) 밖 화소 0, 늘면 가로로만 좁힘. 색 = 원본 팔레트 번호 그대로.
python tools/gfx_kr.py preview  → work/preview/그림글자_원본_한글.png
python tools/gfx_kr.py build    → work/gfx/*.SCB·AREAOBJ.SPR"""
import os, sys, collections
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import scb, areaobj as A
NGEB = r'C:\claude\utils\font\nanum-gothic\NanumGothicExtraBold.ttf'
NGB = r'C:\claude\utils\font\nanum-gothic\NanumGothicBold.ttf'

# SCB 문구: (파일, 줄 y0, y1, 한글) — 상자 x 는 원본 잉크에서 잰다
SCB_TEXT = [('SAVEMISS', 0, 15, '기록을 제대로 저장하지'), ('SAVEMISS', 16, 31, '못했습니다.'),
            ('FONT_10', 0, 15, '포즈'), ('FONT_11', 0, 15, '리플레이를 끝낼까요?'), ('FONT_11', 16, 31, '한 번 더 볼까요?')]
# 팔레트 번호: (테두리, 가장자리 단계 어두움→밝음, 속)
PAL_SPEC = {'FONT_10': (240, [241, 242, 243, 244, 245, 246], 247), 'FONT_11': (240, [241, 242, 243, 244, 245, 246], 247),
            'SAVEMISS': (15, [13, 11, 9, 7, 5, 3], 1)}
SIZE = {'포즈': 17}      # 받침 없는 두 글자라 키워야 원본 ポーズ 높이(14px)
GAP = {'포즈': 5}        # ㅗ·ㅡ 가로획이 이어져 밑줄처럼 보임 → 띄움
FULL_ROW = set()  # «일시정지»는 칸 180 > 176 이라 «포즈»(원본 폭 안)로     # 한 줄(80px)이 통째로 칸으로 찍힘 → 상자 = 그 줄 전체 폭(원본 잉크 42px 로는 4글자 안 읽힘)
DAYS = '월화수목금토일'
DAY_OFF = [0xB600 + 0x600 * k for k in range(7)]        # 64×24, 색 251(노랑)·252(토)·253(일)
NICHIME = (0x1E900, 40, 24, '일째')


def scb_index(S):
    W, H = S['w'] * 8, S['h'] * 8; idx = [[0] * W for _ in range(H)]
    for k, m in enumerate(S['map']):
        c = S['cells'][(m & 0x3ff) // (2 if S['bpp'] == 8 else 1)]; cx, cy = (k % S['w']) * 8, (k // S['w']) * 8
        for y in range(8):
            for x in range(8):
                idx[cy + y][cx + x] = c[y * 8 + x] if S['bpp'] == 8 else (c[y * 4 + x // 2] >> (4 * (1 - x % 2))) & 15
    return idx


def text_mask_sp(txt, font, size, boxw, gap=2):
    """한 글자씩 그려 글자 사이 gap px — 테두리가 이웃 글자와 붙지 않게"""
    fo = ImageFont.truetype(font, size); parts = []
    for ch in txt:
        if ch == ' ': parts.append(Image.new('L', (size // 3, 1))); continue
        t = Image.new('L', (size * 2, size * 2)); d = ImageDraw.Draw(t); d.text((size // 2, size // 2), ch, font=fo, fill=255)
        bb = t.getbbox(); parts.append(t.crop((bb[0], size // 2 - 1, bb[2], size // 2 + size + 2)))
    H = max(p.height for p in parts); W = sum(p.width for p in parts) + gap * (len(parts) - 1)
    im = Image.new('L', (W, H)); x = 0
    for p in parts: im.paste(p, (x, 0)); x += p.width + gap
    bb = im.getbbox(); im = im.crop((0, bb[1], im.width, bb[3]))
    if im.width > boxw: im = im.resize((boxw, im.height), Image.LANCZOS)
    return im.point(lambda v: 255 if v >= 110 else 0)


def coverage(txt, font, size, boxw, boxh, gap=1, ss=4):
    """4배로 그려 줄인 «덮인 정도»(0~255) — 하스피 «원본은 부드러운데 우리껀 들쭉날쭉»(11-22)"""
    fo = ImageFont.truetype(font, size * ss); parts = []
    for ch in txt:
        if ch == ' ': parts.append(Image.new('L', (size * ss // 3, 1))); continue
        t = Image.new('L', (size * ss * 2, size * ss * 2)); ImageDraw.Draw(t).text((size * ss // 2, size * ss // 2), ch, font=fo, fill=255)
        bb = t.getbbox(); parts.append(t.crop((bb[0], size * ss // 2 - ss, bb[2], size * ss // 2 + size * ss + 2 * ss)))
    H = max(q.height for q in parts); W = sum(q.width for q in parts) + gap * ss * (len(parts) - 1)
    im = Image.new('L', (W, H)); x = 0
    for q in parts: im.paste(q, (x, 0)); x += q.width + gap * ss
    bb = im.getbbox(); im = im.crop((0, bb[1], im.width, bb[3]))
    w1 = min(boxw, (im.width + ss - 1) // ss); h1 = min(boxh, (im.height + ss - 1) // ss)
    return im.resize((w1, h1), Image.BOX)


def text_mask(txt, font, size, boxw, boxh, sx=1.0):
    """글자 모양(0/1) — 높이 boxh 안, 가로는 boxw 넘으면 좁힘"""
    fo = ImageFont.truetype(font, size); tmp = Image.new('L', (400, 60)); d = ImageDraw.Draw(tmp)
    bb = d.textbbox((0, 0), txt, font=fo); w, h = bb[2] - bb[0], bb[3] - bb[1]
    im = Image.new('L', (w + 2, h + 2)); ImageDraw.Draw(im).text((1 - bb[0], 1 - bb[1]), txt, font=fo, fill=255)
    nw = min(boxw, int(w * sx)); im = im.resize((max(1, nw), h + 2), Image.LANCZOS) if nw != w + 2 else im
    return im.point(lambda v: 255 if v >= 110 else 0)


def scb_apply(nm, idx, y0, y1, txt):
    W = len(idx[0])
    ink = [(x, y) for y in range(y0, y1 + 1) for x in range(W) if idx[y][x]]
    x0, x1 = min(x for x, _ in ink), max(x for x, _ in ink)
    if nm in FULL_ROW: x0, x1 = 12, W - 13          # 칸 수(176) 안에 들도록 56px
    # 줄별 채움 색(테두리 240 제외 최빈) → 한글 채움 그라데이션
    rowcol = {}
    for y in range(y0, y1 + 1):
        c = collections.Counter(idx[y][x] for x in range(x0, x1 + 1) if idx[y][x] not in (0, PAL_SPEC[nm][0]))
        rowcol[y] = c.most_common(1)[0][0] if c else None
    fills = [rowcol[y] for y in range(y0, y1 + 1) if rowcol[y]]
    for y in range(y0, y1 + 1):
        if rowcol[y] is None: rowcol[y] = fills[0] if y < y0 + 8 else fills[-1]
    for y in range(y0, y1 + 1):
        for x in range(W): idx[y][x] = 0
    bw, bh = x1 - x0 + 1, y1 - y0 + 1
    cv = coverage(txt, NGB, SIZE.get(txt, 14), bw - 2, bh - 2, gap=GAP.get(txt, 1))
    ox = x0 + (bw - cv.width) // 2; oy = y0 + (bh - cv.height) // 2; cp = cv.load()
    C = {}
    for yy in range(cv.height):
        for xx in range(cv.width): C[(ox + xx, oy + yy)] = cp[xx, yy] / 255
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            c = C.get((x, y), 0)
            o = max(C.get((x + dx, y + dy), 0) for dx in (-1, 0, 1) for dy in (-1, 0, 1))
            ol, ramp, fl = PAL_SPEC[nm]
            if c >= 0.72: idx[y][x] = fl                                     # 속 = 밝은 노랑
            elif c >= 0.12: idx[y][x] = ramp[min(len(ramp) - 1, int(c * len(ramp)))]  # 가장자리 = 어두운→밝은 노랑 단계
            elif o >= 0.35: idx[y][x] = ol                                   # 바깥 1px = 검은 테두리
    return (x0, y0, x1, y1)


def day_img(ch, col, w, h, txt=None):
    """기울임 한 색 글씨 — 4배로 그려 기울이고 줄인 뒤 문턱(획 고르게, 11-22)"""
    txt = txt or ch + '요일'; ss = 4
    fo = ImageFont.truetype(NGB, 21 * ss); t = Image.new('L', (w * ss * 3, h * ss * 2)); d = ImageDraw.Draw(t)
    d.text((w * ss // 2, h * ss // 4), txt, font=fo, fill=255)
    t = t.transform(t.size, Image.AFFINE, (1, 0.26, -h * ss * 0.26, 0, 1, 0), Image.BILINEAR)   # 기울임
    t = t.crop(t.getbbox())
    tw = min(w - 2, round(t.width / ss)); th = min(h - 2, round(t.height / ss))
    m = t.resize((tw, th), Image.BOX).point(lambda v: 255 if v >= 100 else 0)
    out = bytearray(w * h); ox = (w - m.width) // 2; oy = (h - m.height) // 2; mp = m.load()
    for y in range(m.height):
        for x in range(m.width):
            if mp[x, y]: out[(oy + y) * w + ox + x] = col
    return bytes(out)


def build():
    res = {}
    for nm in ('FONT_10', 'FONT_11', 'SAVEMISS'):
        b = open(os.path.join(ROOT, 'work', 'iso', nm + '.SCB'), 'rb').read(); S = scb.parse(b)
        idx = scb_index(S)
        for f, y0, y1, t in SCB_TEXT:
            if f == nm: scb_apply(nm, idx, y0, y1, t)
        res[nm] = (S, idx, b)
    f = bytearray(A.load())
    for k, o in enumerate(DAY_OFF):
        col = 252 if k == 5 else 253 if k == 6 else 251
        f[o:o + 1536] = day_img(DAYS[k], col, 64, 24)
    o, w, h, t = NICHIME; f[o:o + w * h] = day_img(None, 251, w, h, t)
    return res, bytes(f)


def scb_encode(S, idx, orig):
    """칸 다시 짜기(같은 칸 합침) — 칸 수가 원본 이하일 때만"""
    W, H = S['w'], S['h']; cells = []; seen = {}; mp = []
    for cy in range(H):
        for cx in range(W):
            c = bytes(idx[cy * 8 + y][cx * 8 + x] for y in range(8) for x in range(8)) if S['bpp'] == 8 else \
                bytes((idx[cy * 8 + y][cx * 8 + x] << 4) | idx[cy * 8 + y][cx * 8 + x + 1] for y in range(8) for x in range(0, 8, 2))
            if c not in seen: seen[c] = len(cells); cells.append(c)
            mp.append(seen[c] * (2 if S['bpp'] == 8 else 1))
    if len(cells) > len(S['cells']): raise SystemExit('칸 수 초과 %d > %d' % (len(cells), len(S['cells'])))
    while len(cells) < len(S['cells']): cells.append(bytes(len(cells[0])))       # 원본 크기 유지
    import struct
    ncol = 16 if S['bpp'] == 4 else 256
    out = orig[:16 + ncol * 2] + b''.join(cells) + struct.pack('>%dH' % len(mp), *mp)
    assert len(out) == len(orig); return out


def preview():
    res, f2 = build(); f1 = A.load(); rows = []
    for nm in ('FONT_10', 'FONT_11', 'SAVEMISS'):
        S, idx, b = res[nm]; o = scb.render(S)
        S2 = scb.parse(scb_encode(S, idx, b)); n = scb.render(S2)
        hh = 16 if nm == 'FONT_10' else 32
        rows.append((nm, o.crop((0, 0, o.width, hh)), n.crop((0, 0, n.width, hh))))
    for k, o in enumerate(DAY_OFF): rows.append((DAYS[k] + '요일', A.img(f1, o, 64, 24), A.img(f2, o, 64, 24)))
    o, w, h, t = NICHIME; rows.append(('日目', A.img(f1, o, w, h), A.img(f2, o, w, h)))
    Z = 4; W = max(a.width for _, a, _ in rows) * Z * 2 + 40; Ht = sum(a.height * Z + 8 for _, a, _ in rows)
    sheet = Image.new('RGB', (W, Ht), (40, 40, 60)); y = 0
    for nm, a, b2 in rows:
        for k, im in enumerate((a, b2)):
            r = im.resize((im.width * Z, im.height * Z), Image.NEAREST); sheet.paste(r, (k * (W // 2), y), r)
        y += a.height * Z + 8
    os.makedirs(os.path.join(ROOT, 'work', 'preview'), exist_ok=True)
    p = os.path.join(ROOT, 'work', 'preview', '그림글자_원본_한글.png'); sheet.save(p); print(p)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    if sys.argv[1:] == ['preview']: preview()
    elif sys.argv[1:] == ['build']:
        res, f2 = build(); os.makedirs(os.path.join(ROOT, 'work', 'gfx'), exist_ok=True)
        for nm, (S, idx, b) in res.items(): open(os.path.join(ROOT, 'work', 'gfx', nm + '.SCB'), 'wb').write(scb_encode(S, idx, b))
        open(os.path.join(ROOT, 'work', 'gfx', 'AREAOBJ.SPR'), 'wb').write(f2); print('ok')
