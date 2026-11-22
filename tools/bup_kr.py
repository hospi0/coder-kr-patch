# -*- coding: utf-8 -*-
"""BUP_ERR.BM8(백업 준비 안 됨 화면, 352×224 8bpp: u16 폭·높이 + 팔레트 256 + 화소) 한글화 (2026-11-22 코드R)
사진 위 흰 글씨+검은 테두리 → 글씨 자리(흰 화소 + 둘레 2px)를 주변으로 메움(OpenCV inpaint) → 같은 줄 자리에 한글(흰 속·검은 테두리)
→ 원래 팔레트 256색에서 가장 가까운 색으로. 글씨 상자 밖 화소는 원본 그대로.
python tools/bup_kr.py   → work/preview/백업오류_원본_한글.png"""
import os, struct, sys
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
P = os.path.join(ROOT, 'work', 'iso', 'BUP_ERR.BM8')
NGB = r'C:\claude\utils\font\nanum-gothic\NanumGothicBold.ttf'
BOX = (12, 98, 341, 206)              # 글씨 상자(x0,y0,x1,y1) — 원본 6줄(흰 글씨 103~198 + 테두리)
LINES = ['백업 준비가 아직 되지 않았습니다.',
         '세가새턴 본체의 저장 데이터 관리 화면에서',
         '모든 게임 데이터의 기록을 지워 주십시오.',
         'L 버튼 또는 R 버튼을 누른 채로',
         '리셋 버튼을 누르면 세가새턴 본체의',
         '저장 데이터 관리 화면으로 넘어갑니다.']


def load():
    b = open(P, 'rb').read(); w, h = struct.unpack_from('>HH', b, 0)
    pal = np.array([[(e & 31) << 3, ((e >> 5) & 31) << 3, ((e >> 10) & 31) << 3] for e in struct.unpack_from('>256H', b, 4)], np.uint8)
    idx = np.frombuffer(b[516:516 + w * h], np.uint8).reshape(h, w)
    return b, w, h, pal, idx


def build():
    b, w, h, pal, idx = load(); rgb = pal[idx].copy()
    x0, y0, x1, y1 = BOX
    box = np.zeros((h, w), bool); box[y0:y1, x0:x1] = True
    white = (rgb.min(axis=2) >= 232) & box
    gray = (rgb.min(axis=2) >= 150) & ((rgb.max(axis=2).astype(int) - rgb.min(axis=2)) < 30) & box   # 글씨 가장자리(밝은 회색)
    near = cv2.dilate(white.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
    dark = (rgb.max(axis=2) <= 70) & near & box                               # 일본어 검은 테두리(흰 글씨 3px 안의 어두운 화소)
    near2 = cv2.dilate(white.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    mask = cv2.dilate((white | dark | (gray & near2)).astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & box
    # 줄 끝 「。」 처럼 흰 화소(≥232) 없이 회색으로만 된 부호: 각 줄 띠(흰 줄 ±2) 안, 그 줄 흰 글씨 가로 범위 +14px 까지의 회색·검정
    rws = [y for y in range(y0, y1) if white[y].sum() > 2]; gg = []
    for y in rws:
        if gg and y - gg[-1][1] <= 2: gg[-1][1] = y
        else: gg.append([y, y])
    for a_, c_ in gg:
        xs = np.where(white[a_:c_ + 1].any(axis=0))[0]
        band = np.zeros((h, w), bool); band[max(y0, a_ - 2):min(y1, c_ + 3), max(x0, xs.min() - 6):min(x1, xs.max() + 15)] = True
        g2 = gray & band; d2 = (rgb.max(axis=2) <= 70) & band & cv2.dilate(g2.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
        mask |= cv2.dilate((g2 | d2).astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & band
    bg = cv2.inpaint(rgb, mask.astype(np.uint8) * 255, 4, cv2.INPAINT_TELEA)
    # 원래 줄 위치(흰 화소 줄 묶음)
    rows = [y for y in range(y0, y1) if white[y].sum() > 2]; g = []
    for y in rows:
        if g and y - g[-1][1] <= 2: g[-1][1] = y
        else: g.append([y, y])
    assert len(g) == len(LINES), g
    ss = 4; img = Image.fromarray(bg); out = np.array(img)
    for (a, c), txt in zip(g, LINES):
        hgt = c - a + 1; cy = (a + c) / 2
        fo = ImageFont.truetype(NGB, 14 * ss)          # 속 높이 ≈ 원본 흰 글씨 12px(줄 간격 17) — 16 은 위아래 줄 겹침(하스피 11-22)
        t = Image.new('L', (w * ss, 30 * ss)); d = ImageDraw.Draw(t)
        d.text((0, 0), txt, font=fo, fill=255); bb = t.getbbox(); t = t.crop(bb)
        pad = 3 * ss; T = Image.new('L', (t.width + 2 * pad, t.height + 2 * pad)); T.paste(t, (pad, pad))
        Ob = cv2.dilate(np.array(T), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * 9 + 1, 2 * 9 + 1)))   # 4배에서 9px ≈ 2px 테두리
        tw, th = T.width // ss, T.height // ss
        scale = min(1.0, (x1 - x0 - 2) / tw)
        tw2 = int(tw * scale)
        Cf = np.array(T.resize((tw2, th), Image.BOX)) / 255.0                       # 속 덮임(부드럽게)
        Co = np.array(Image.fromarray(Ob).resize((tw2, th), Image.BOX)) / 255.0     # 테두리 덮임
        ox = (x0 + x1 - tw2) // 2; oy = int(round(cy - th / 2))
        reg = out[oy:oy + th, ox:ox + tw2].astype(float); bx = box[oy:oy + th, ox:ox + tw2][..., None]
        reg = reg * (1 - Co[..., None])                                             # 검은 테두리
        reg = reg * (1 - Cf[..., None]) + 255 * Cf[..., None]                       # 흰 속
        out[oy:oy + th, ox:ox + tw2] = np.where(bx, np.clip(reg, 0, 255), out[oy:oy + th, ox:ox + tw2]).astype(np.uint8)
    # 팔레트로(가장 가까운 색), 상자 밖은 원본 번호 그대로
    flat = out.reshape(-1, 3).astype(int); pl = pal.astype(int)
    d2 = ((flat[:, None, :] - pl[None, :, :]) ** 2).sum(-1); near = d2.argmin(1).reshape(h, w).astype(np.uint8)
    new = idx.copy(); new[box] = near[box]
    return b[:516] + new.tobytes() + b[516 + w * h:], pal, idx, new


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    nb, pal, idx, new = build()
    a = Image.fromarray(pal[idx]); c = Image.fromarray(pal[new])
    s = Image.new('RGB', (a.width * 2 + 8, a.height), (255, 0, 255)); s.paste(a, (0, 0)); s.paste(c, (a.width + 8, 0))
    s = s.resize((s.width * 2, s.height * 2), Image.NEAREST)
    p = os.path.join(ROOT, 'work', 'preview', '백업오류_원본_한글.png'); s.save(p); print(p, len(nb))
