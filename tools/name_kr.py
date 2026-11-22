# -*- coding: utf-8 -*-
"""한글 이름 입력 표 (2026-11-22 코드R) — 조합형(tools/name_hook.py) + 고르기 판
입력판(ADV.EXE·ADVE.EXE, 15칸 × 6줄, EUC 2 B): 英数 그대로 · かな → «한글»(자모 판, 조합) · カナ → «자주»(흔한 이름 음절 90)
漢字 → «음절»: 읽기판(5줄 × 앞 10칸) = 초성 19 → NAMEDIC 묶음 = 그 초성의 받침 없는 음절(KS 2350 안)
NAMEDIC.FNT = 묶음 50칸 머리·글자(해석 ADV.EXE 0x06062F0C: [u32 쓰는 줄][u32 열] + 6줄×열 글자, 빈칸 0,0) + 뒤에 조합 코드(name_hook)."""
import os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import jamo
ISO = os.path.join(ROOT, 'work', 'iso')
SP = '　'
FREQ = ('김이박최정강조윤장임한오서신권황안송류홍전고문손양배백허남심노하곽성차주우구민진지엄채원천방공현함변'
        '염여추도석선설마길연위표명기반왕금옥육인제모탁국은용예경봉수영준혁훈호희철동재상태환광승형범빈미혜아나유다')
GRID_CHO = [list('ㄱㄴㄷㄹㅁㅂㅅㅇㅈㅊ'), list('ㅋㅌㅍㅎㄲㄸㅃㅆㅉ') + [None], [None] * 10, [None] * 10, [None] * 10]


def e(c):
    if c is None or c == SP: return b'\xa1\xa1'
    if c in jamo.JAMO: k = jamo.JAMO0 + jamo.JAMO.index(c); return bytes([k >> 8, k & 255])
    return c.encode('euc_kr')


def board(cells, rows):
    cells = list(cells) + [None] * (15 * rows - len(cells)); assert len(cells) == 15 * rows
    return b''.join(e(c) for c in cells)


def groups():
    """읽기판 50칸 순서(줄 우선)대로 NAMEDIC 묶음"""
    out = bytearray()
    for row in GRID_CHO:
        for c in row:
            if c is None: out += struct.pack('>II', 0, 0); continue
            ci = jamo.CHO.index(c)
            ss = [s for s in jamo.KS if (ord(s) - 0xAC00) // 588 == ci and (ord(s) - 0xAC00) % 28 == 0]
            cols = max(15, -(-len(ss) // 6)); rows = -(-len(ss) // cols)     # ★게임은 한 줄을 늘 15칸 그림(원본 묶음 열 ≥15) — 4열로 넣으면 다음 묶음까지 읽음(2026-11-22 실기)
            out += struct.pack('>II', rows, cols) + b''.join(e(x) for x in ss + [SP] * (6 * cols - len(ss)))
    return bytes(out)


def tables():
    jb = b''.join(bytes([c >> 8, c & 255]) for c in jamo.board())
    freq = list(dict.fromkeys(FREQ))[:90]
    grid = []
    for row in GRID_CHO: grid += row + [None] * 5
    return jb, board(freq, 6), board(grid, 5)


DEFAULT_NAME = '테츠야'     # 이름 최대 3글자
SCREEN = {  # 원문 → 시험용 한글(같은 칸 수). 번역 TSV 가 오면 그쪽이 우선
    '名前を入力して下さい。': '이름을' + SP + '입력해' + SP + '주세요．',
    '英数': '영문', 'かな': '한글', 'カナ': '자주', '漢字': '음절',
    '（Ｘ／Ｚで文字カーソル移動）': '（Ｘ／Ｚ：커서' + SP + '이동）' + SP * 5,
    'この名前でよろしいですか？': '이' + SP + '이름으로' + SP + '할까요？' + SP * 2,
    'いいえ': '아니요', 'はい': '예' + SP}


def patch_exe(b):
    b = bytearray(b)
    kana = 'あかさたなはまやらわがざだばぱ'.encode('euc_jp'); kata = 'アカサタナハマヤラワガザダバパ'.encode('euc_jp')
    i = b.find(kana); j = b.find(kata); assert i > 0 and j == i + 180, (hex(i), hex(j))
    g = j + 180; assert b[g:g + 20] == 'あかさたなはまやらわ'.encode('euc_jp'), hex(g)
    t1, t2, t3 = tables(); assert len(t1) == 180 and len(t2) == 180 and len(t3) == 150
    b[i:i + 180] = t1; b[j:j + 180] = t2; b[g:g + 150] = t3
    # 기본 이름 哲也 → 테츠야(하스피 «초기이름도 고쳐야지», 거센소리 규칙) — 자리 = 哲也 4 B + 뒤 0 12 B
    old = '哲也'.encode('euc_jp') + b'\0' * 12; k = b.find(b'\0	' + old)
    if k >= 0:
        k += 2; new = DEFAULT_NAME.encode('euc_kr'); assert len(new) <= 6
        b[k:k + 16] = new + b'\0' * (16 - len(new))
    for jp, kr in SCREEN.items():
        assert len(kr) >= len(jp), jp
        old = jp.encode('euc_jp'); k = b.find(old); n = 0
        while k >= 0:
            extra = len(kr) - len(jp)
            assert b[k + len(old):k + len(old) + 2 * extra] == b'\xa1\xa1' * extra, ('뒤 공백 모자람', jp)
            new = b''.join(c.encode('euc_kr') if '가' <= c <= '힣' else c.encode('euc_jp') for c in kr)
            b[k:k + len(new)] = new; n += 1; k = b.find(old, k + len(new))
        # n == 0 = 번역 TSV 가 이미 그 칸을 바꿈(그쪽 우선, 2026-11-22)
    return bytes(b)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    g = groups(); print('묶음', len(g), 'B')
    for fn in ('ADV.EXE', 'ADVE.EXE'):
        b = open(os.path.join(ISO, fn), 'rb').read(); p = patch_exe(b)
        print(fn, '바뀐 바이트', sum(1 for x, y in zip(b, p) if x != y))
