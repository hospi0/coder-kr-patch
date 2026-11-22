# -*- coding: utf-8 -*-
"""ADV_MG25~40·ADV_EVMG.DAT 대사 파일 — 읽기·다시 짜기
구조(2026-11-21 확인): 앞 = 포인터 표(빅엔디언 절대 주소 0x00242000+오프셋, 0 섞임), 뒤 = 문자열(EUC, 0 끝).
  문자열은 짝수 주소에서 시작, 홀수 자리를 0x09 로 채움, 파일 끝은 «09 00» 채움.
  표 끝 = 앞에서부터 «0 또는 파일 안 주소»가 아닌 첫 워드.
텍스트 표기: 0A 0A = \n, 홀로 된 0A = {0A}, 그 밖 1바이트 = 그대로(ASCII: %u %U %L …)
python tools/mg.py extract  → work/text/mg.tsv (id·파일·오프셋·참조 수·원문)
python tools/mg.py check    → 원문 그대로 다시 짜서 원본과 바이트 같음 검산"""
import glob, os, struct, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ISO = os.path.join(ROOT, 'work', 'iso')
BASE = 0x242000
FILES = sorted(os.path.basename(p) for p in glob.glob(os.path.join(ISO, 'ADV_MG*.DAT'))) + ['ADV_EVMG.DAT']


def parse(b):
    n = len(b); ws = [struct.unpack_from('>I', b, j)[0] for j in range(0, n - 3, 4)]
    k = 0
    while k < len(ws) and (ws[k] == 0 or BASE <= ws[k] < BASE + n): k += 1
    tend = k * 4
    ptrs = [(j * 4, w - BASE) for j, w in enumerate(ws[:k]) if w and w - BASE >= tend]   # (포인터 자리, 대상)
    tg = sorted({t for _, t in ptrs})
    strs = {t: b[t:b.index(b'\0', t)] for t in tg}
    return tend, ptrs, tg, strs


def dec(s):
    out = []; i = 0
    while i < len(s):
        c = s[i]
        if c >= 0xA1: out.append(s[i:i + 2].decode('euc_jp')); i += 2
        elif s[i:i + 2] == b'\n\n': out.append('\\n'); i += 2
        elif c == 0x0A: out.append('{0A}'); i += 1
        elif 0x20 <= c < 0x7F: out.append(chr(c)); i += 1
        else: raise ValueError('모르는 바이트 %02X' % c)
    return ''.join(out)


def pad(out):
    """4바이트 정렬 — 원본 꼴: 3칸이면 00 00 09, 1칸이면 00 (2칸은 원본에 없음 → 00 09)"""
    out += {0: b'', 1: b'\0', 2: b'\0\t', 3: b'\0\0\t'}[-len(out) % 4]


def rebuild(b, texts):
    """texts = {대상 오프셋: 새 바이트} — 표 구조 그대로, 문자열 영역만 처음부터 다시 쌓고 포인터 고침"""
    tend, ptrs, tg, strs = parse(b)
    out = bytearray(b[:tend]); newpos = {}
    first = tg[0]; out += b[tend:first]                     # 표 뒤 ~ 첫 문자열 사이(원본 그대로)
    for i, t in enumerate(tg):
        if i: pad(out)
        newpos[t] = len(out); out += texts.get(t, strs[t]) + b'\0'
    last = tg[-1] + len(strs[tg[-1]]) + 1                   # 원본 끝 채움(09 00 …)은 원본 꼴을 이어 붙임
    if not texts: out += b[last:]
    elif len(out) < len(b): out += (b'\0' + b'\t\0' * len(b))[:len(b) - len(out)]
    for at, t in ptrs: struct.pack_into('>I', out, at, BASE + newpos[t])
    return bytes(out)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'check'
    rows = []; ok = 0
    for fn in FILES:
        b = open(os.path.join(ISO, fn), 'rb').read()
        tend, ptrs, tg, strs = parse(b)
        refs = {}
        for _, t in ptrs: refs[t] = refs.get(t, 0) + 1
        for t in tg: rows.append((fn, t, refs[t], dec(strs[t])))
        r = rebuild(b, {})
        same = r == b; ok += same
        if not same:
            d = next(i for i in range(len(b)) if r[i] != b[i]); print('다름', fn, hex(d), len(r), len(b))
    print('다시 짜기 원본과 같음 %d/%d' % (ok, len(FILES)))
    if cmd == 'extract':
        p = os.path.join(ROOT, 'work', 'text', 'mg.tsv')
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            f.write('id\tfile\toff\trefs\tjp\n')
            for fn, t, n, s in rows: f.write('%s:%05X\t%s\t%05X\t%d\t%s\n' % (fn[4:-4], t, fn, t, n, s))
        print(p, len(rows), '줄', sum(len(s) for *_, s in rows), '글자(표기 포함)')
