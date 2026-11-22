# -*- coding: utf-8 -*-
"""조합형 이름 입력 — 기준(파이썬) 조합기와 표 (2026-11-22 코드R)
자모 코드 = 0xA9A1 + k (k 0~18 초성 ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ, 19~39 중성 ㅏ…ㅣ) — EUC-JP 9행(빈 행), 한글 EUC-KR 과 안 겹침.
음절 = KS X 1001 2350자만(코드 = EUC-KR). 없는 음절은 «안 합침»."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from font import ks_hangul

CHO = 'ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ'
JUNG = 'ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ'
JONG = ' ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ'
JAMO0 = 0xA9A1
JAMO = list(CHO) + list(JUNG)                       # k → 자모 글자(표시용 호환 자모)
JONG_OF_CHO = [JONG.find(c) if c in JONG else 0 for c in CHO]          # 받침이 될 수 있는 초성 → 종성 번호
COMP = [(JONG.index(a), CHO.index(b), JONG.index(c)) for a, b, c in
        ('ㄱㅅㄳ', 'ㄴㅈㄵ', 'ㄴㅎㄶ', 'ㄹㄱㄺ', 'ㄹㅁㄻ', 'ㄹㅂㄼ', 'ㄹㅅㄽ', 'ㄹㅌㄾ', 'ㄹㅍㄿ', 'ㄹㅎㅀ', 'ㅂㅅㅄ')]
SPLIT = [(0, 0)] * 28                                 # 종성 → (남는 종성, 넘어가는 초성)
for t in range(1, 28):
    hit = [(a, b) for a, b, c in COMP if c == t]
    SPLIT[t] = hit[0] if hit else (0, CHO.index(JONG[t]))
VCOMP = [(JUNG.index(a), JUNG.index(b), JUNG.index(c)) for a, b, c in
         ('ㅗㅏㅘ', 'ㅗㅐㅙ', 'ㅗㅣㅚ', 'ㅜㅓㅝ', 'ㅜㅔㅞ', 'ㅜㅣㅟ', 'ㅡㅣㅢ')]
KS = ks_hangul()
KEY = [((ord(s) - 0xAC00) // 588 << 10) | ((ord(s) - 0xAC00) // 28 % 21 << 5) | (ord(s) - 0xAC00) % 28 for s in KS]
assert KEY == sorted(KEY)


def code_of_idx(i): return ((0xB0 + i // 94) << 8) | (0xA1 + i % 94)
def idx_of_code(c): return ((c >> 8) - 0xB0) * 94 + (c & 0xFF) - 0xA1


def syl(c, v, t):
    k = (c << 10) | (v << 5) | t
    import bisect
    i = bisect.bisect_left(KEY, k)
    return code_of_idx(i) if i < len(KEY) and KEY[i] == k else 0


def combine(prev, ch, allow_split=True):
    """(P, N) 또는 None — P = 앞 칸 새 글자, N = 다음 칸에 넣을 글자(0 = 없음)"""
    k = ch - JAMO0
    if not 0 <= k < 40: return None
    if JAMO0 <= prev < JAMO0 + 40:
        pk = prev - JAMO0
        if pk < 19 and k >= 19:
            p = syl(pk, k - 19, 0); return (p, 0) if p else None
        return None
    if not (0xB0A1 <= prev <= 0xC8FE and (prev & 0xFF) >= 0xA1 and (prev & 0xFF) <= 0xFE): return None
    i = idx_of_code(prev)
    if not 0 <= i < 2350: return None
    key = KEY[i]; c, v, t = key >> 10, key >> 5 & 31, key & 31
    if k < 19:
        if t == 0:
            jt = JONG_OF_CHO[k]
            if not jt: return None
            p = syl(c, v, jt); return (p, 0) if p else None
        for a, b, cc in COMP:
            if a == t and b == k:
                p = syl(c, v, cc); return (p, 0) if p else None
        return None
    V = k - 19
    if t == 0:
        for a, b, cc in VCOMP:
            if a == v and b == V:
                p = syl(c, cc, 0); return (p, 0) if p else None
        return None
    if not allow_split: return None
    t1, c2 = SPLIT[t]
    p = syl(c, v, t1); n = syl(c2, V, 0)
    return (p, n) if p and n else None


def board():
    """かな판(15칸 × 6줄) — 0: 기본 자음 14, 1: 된소리 5, 2: 기본 모음 10, 3: 나머지 모음 11"""
    rows = [list('ㄱㄴㄷㄹㅁㅂㅅㅇㅈㅊㅋㅌㅍㅎ'), list('ㄲㄸㅃㅆㅉ'), list('ㅏㅑㅓㅕㅗㅛㅜㅠㅡㅣ'), list('ㅐㅒㅔㅖㅘㅙㅚㅝㅞㅟㅢ'), [], []]
    out = []
    for r in rows:
        for x in r + [None] * (15 - len(r)): out.append(JAMO0 + JAMO.index(x) if x else 0xA1A1)
    return out


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    def s(c): return chr(c) if c < 0x100 else (bytes([c >> 8, c & 255]).decode('euc_kr') if c < JAMO0 or c >= JAMO0 + 40 else JAMO[c - JAMO0])
    J = lambda x: JAMO0 + JAMO.index(x)
    seq = [J(x) for x in 'ㅊㅓㄹㅅㅜ']
    name = []
    for ch in seq:
        r = combine(name[-1], ch) if name else None
        if r: name[-1] = r[0]; (name.append(r[1]) if r[1] else None)
        else: name.append(ch)
        print(''.join(s(c) for c in name))
