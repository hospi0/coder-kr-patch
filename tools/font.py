# -*- coding: utf-8 -*-
"""전체 글꼴 — FONTDIC.FNT(EUC 코드 3252칸) + FONT24.FNT(24×24 1bpp, 8×8 조각 3×3) (2026-11-22 코드R)
칸 = 원본 비한자(기호·가나·전각 영숫자, A1~A8) + 이름 입력 자모 40(A9A1~) + 원본 한자 중 코드 C9 이상(남는 만큼) + KS X 1001 한글 2350자.
글꼴 찾기는 사전을 처음부터 차례로(ADV.EXE 0x06057476) → 순서 자유, 같은 코드 중복은 앞 것.
한글 글리프 = 나눔고딕 21px 문턱 60(하스피 PoC 선택 2번)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
from poc import hangul_glyph
ISO = os.path.join(ROOT, 'work', 'iso')
N = 3252


def ks_hangul():
    out = []
    for hi in range(0xB0, 0xC9):
        for lo in range(0xA1, 0xFF):
            try: ch = bytes([hi, lo]).decode('euc_kr')
            except UnicodeDecodeError: continue
            if '가' <= ch <= '힣': out.append(ch)
    assert len(out) == 2350
    return out


def build():
    dic = open(os.path.join(ISO, 'FONTDIC.FNT'), 'rb').read(); f24 = open(os.path.join(ISO, 'FONT24.FNT'), 'rb').read()
    codes = [dic[i:i + 2] for i in range(0, len(dic), 2)]
    keep, seen = [], set()
    for i, c in enumerate(codes):
        if c in seen: continue
        if c[0] < 0xB0 or c[0] >= 0xC9: keep.append((c, f24[i * 72:(i + 1) * 72])); seen.add(c)
    hg = ks_hangul()
    import jamo                                                        # 조합형 이름 입력 자모 40자(A9A1~, EUC-JP 빈 9행)
    jm = [(bytes([(jamo.JAMO0 + k) >> 8, (jamo.JAMO0 + k) & 255]), hangul_glyph(jamo.JAMO[k])) for k in range(40)]
    room = N - len(hg) - len(jm)
    kanji = [x for x in keep if x[0][0] >= 0xC9]; other = [x for x in keep if x[0][0] < 0xC9]
    keep = other + kanji[:room - len(other)]                          # 2수준 한자는 남는 만큼만(앞쪽부터)
    out = keep + jm + [(ch.encode('euc_kr'), hangul_glyph(ch)) for ch in hg]
    assert len(out) <= N, len(out)
    blank = next(g for c, g in keep if c == b'\xa1\xa1')
    while len(out) < N: out.append((b'\xa1\xa1', blank))          # 남는 칸 = 전각 공백(앞 것이 먼저 잡힘)
    D = b''.join(c for c, _ in out); F = b''.join(g for _, g in out)
    assert len(D) == len(dic) and len(F) == len(f24)
    return D, F, {c for c, _ in out}


def enc(s, have=None):
    """번역문 → 바이트: 한글 = EUC-KR, 나머지 = EUC-JP, \\n = 0A 0A, {0A} = 0A. 글꼴에 없는 글자는 빌드 실패."""
    out = bytearray(); i = 0
    while i < len(s):
        if s.startswith('\\n', i): out += b'\n\n'; i += 2; continue
        if s.startswith('{0A}', i): out += b'\n'; i += 4; continue
        c = s[i]; i += 1
        if '가' <= c <= '힣': b = c.encode('euc_kr')
        elif ord(c) < 0x80: out.append(ord(c)); continue
        else:
            c2 = {'～': '〜', '－': '−', '·': '・', '‥': '‥'}.get(c, c)
            try: b = c2.encode('euc_jp')
            except UnicodeEncodeError: raise SystemExit('인코딩 없음: %r' % c)
        if have is not None and b not in have: raise SystemExit('글꼴에 없는 글자: %r (%s)' % (c, b.hex()))
        out += b
    return bytes(out)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    D, F, have = build()
    print('칸', len(D) // 2, '한글', sum(1 for i in range(0, len(D), 2) if 0xB0 <= D[i] < 0xC9))
