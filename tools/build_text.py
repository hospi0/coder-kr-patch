# -*- coding: utf-8 -*-
"""번역 넣기 (2026-11-22 코드R) — my files/tsv/coder_NNN.tsv(대사·ADV_CNDT) + coder_exe.tsv(실행 파일)
KO 가 비면 원문 그대로. 반환 = {파일: 새 바이트} + 보고.
정리: 반각 부호·숫자·영문·공백 → 전각(변수 %…·\\n·{0A} 는 그대로), 문장부호 뒤 공백 삭제, 글꼴 없는 글자 = 실패.
대사 줄 폭 24칸 — 넘으면 띄어쓰기 자리에서 접음(화자 줄은 둘째 줄부터 전각 5칸 들여쓰기). 원문보다 줄 수가 늘면 보고.
예산: 대사 파일 ≤ 0x16000(적재 0x0600C770/C4EC 상한), 실행 파일 = 원문 자리(고정 칸은 전각 공백으로 채움).
python tools/build_text.py   → 검사·보고만 (빌드는 tools/build.py)"""
import os, re, sys, glob, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import mg, cndt, font, exestr, extract_exe
ISO = os.path.join(ROOT, 'work', 'iso')
TSV = os.path.join(ROOT, 'work', 'tr')                       # 2026-11-22 받은 번역 검수본(tools/tr_fix.py) — 원본 내보내기는 my files/tsv
WIDTH = 24
MG_MAX = 0x16000
SP = '　'
TOK = re.compile(r'(%[%0-9a-zA-Z]+|\\n|\{0A\})')
HALF = {' ': SP, '!': '！', '?': '？', ',': '，', '.': '．', ':': '：', ';': '；', '(': '（', ')': '）', '~': '〜', '～': '〜',
        '-': '－', '/': '／', '"': '”', "'": '’', '&': '＆', '+': '＋', '=': '＝', '<': '＜', '>': '＞', '*': '＊', '#': '＃',
        '[': '［', ']': '］', '…': '…', '·': '・'}
EXTRA_ROOM = {'哲也': 16}     # 기본 이름 자리: 원문 4 B 뒤 0 12 B (이름 최대 3글자 = 6 B)
PUNCT_AFTER = '，．、。！？…）」』：；'


def load(stem_glob, ncol):
    out = {}
    for p in sorted(glob.glob(os.path.join(TSV, stem_glob))):
        for ln in open(p, encoding='utf-8').read().split('\n')[1:]:
            if not ln.strip(): continue
            q = ln.split('\t')
            jp, ko = q[2], (q[ncol] if len(q) > ncol else '').rstrip(chr(13) + chr(10) + ' ')   # ★앞 전각 공백(들여쓰기 창 5칸)은 지우면 안 됨 — strip() 쓰다 첫 줄 들여쓰기가 사라졌음(2026-11-22)
            if ko.strip(): out[jp] = ko
    return out


def norm(ko, keep_punct_space=False):
    parts = TOK.split(ko); out = []
    for k, s in enumerate(parts):
        if k % 2: out.append(s); continue
        t = []
        for c in s:
            if c in HALF: c = HALF[c]
            elif '0' <= c <= '9' or 'A' <= c <= 'Z' or 'a' <= c <= 'z': c = chr(ord(c) + 0xFEE0)
            t.append(c)
        s = ''.join(t)
        if not keep_punct_space:                                                # 실행 파일 고정 칸에서 원문도 «부호+공백»이면 유지(선택지 칸 위치, 2026-11-22)
            s = re.sub('([%s])%s+' % (re.escape(PUNCT_AFTER), SP), r'\1', s)      # 부호 뒤 공백 삭제
        out.append(s)
    return ''.join(out)


def cells(s):
    """화면 칸 수(전각 1, 변수는 이름 칸 3으로 어림)"""
    s = re.sub(r'%[uU]', '＊＊＊', s); s = re.sub(r'%[%0-9a-zA-Z]+', '＊＊', s)
    return len(s)


def wrap(ko, jp):
    if jp.startswith('・'): return ko                                            # 선택지는 접지 않음(창 폭 넘으면 경고만, 2026-11-22)
    lines = ko.split('\\n'); spk = bool(re.match('^【', lines[0])); ind = SP * 5 if spk else ''
    out = []
    for i, ln in enumerate(lines):
        while cells(ln) > WIDTH:
            cut = None; acc = 0
            for k, c in enumerate(ln):
                acc = cells(ln[:k + 1])
                if acc > WIDTH: break
                if c == SP and k > 6: cut = k
            if cut is None: break                                              # 접을 자리 없음 → 보고
            out.append(ln[:cut]); ln = ind + ln[cut + 1:].lstrip(SP)
        out.append(ln)
    return '\\n'.join(out)


def enc(s, have): return font.enc(s, have)


def build(have=None, report=True):
    if have is None: _, _, have = font.build()
    dlg = load('coder_[0-9]*.tsv', 3); exe = load('coder_exe.tsv', 4)
    rep = collections.Counter(); warn = []; files = {}
    def conv(jp, ko, where):
        k2 = wrap(norm(ko), jp)
        a = TOK.findall(jp.replace('\\n', '')); b = TOK.findall(k2.replace('\\n', ''))
        if sorted(x for x in a if x != '{0A}') != sorted(x for x in b if x != '{0A}'):
            warn.append('변수 다름 %s: %s | %s' % (where, jp, ko)); return None
        for ln in k2.split('\\n'):
            if cells(ln) > WIDTH: warn.append('폭 %d칸 %s: %s' % (cells(ln), where, ln))
        if k2.count('\\n') > max(2, jp.count('\\n')): warn.append('줄 늘어남 %d→%d %s: %s' % (jp.count('\\n') + 1, k2.count('\\n') + 1, where, k2))
        return enc(k2, have)
    # 대사
    for fn in mg.FILES:
        b = open(os.path.join(ISO, fn), 'rb').read(); tend, ptrs, tg, strs = mg.parse(b); texts = {}
        for t in tg:
            jp = mg.dec(strs[t])
            if jp in dlg:
                nb = conv(jp, dlg[jp], '%s:%05X' % (fn, t))
                if nb is not None: texts[t] = nb; rep['대사 번역'] += 1
            else: rep['대사 원문'] += 1
        nb = mg.rebuild(b, texts)
        if len(nb) > MG_MAX: raise SystemExit('%s 크기 %d > 0x16000 — 번역을 줄여야 함' % (fn, len(nb)))
        if texts: files[fn] = nb
        rep['%s 여유' % fn] = MG_MAX - len(nb)
    # ADV_CNDT
    b = open(cndt.P, 'rb').read(); st = cndt.strings(b); texts = {}
    for t, s in st.items():
        jp = mg.dec(s)
        if jp in dlg:
            nb = conv(jp, dlg[jp], 'ADV_CNDT:%05X' % t)
            if nb is not None: texts[t] = nb; rep['CNDT 번역'] += 1
    if texts: files['ADV_CNDT.DAT'] = cndt.rebuild(b, texts)
    # 실행 파일(제자리)
    items = extract_exe.items()
    by_jp = collections.defaultdict(list)
    for fn, o, jp, n in items: by_jp[jp].append((fn, o))
    for jp, ko in exe.items():
        if jp not in by_jp: warn.append('실행 파일 원문 못 찾음: %s' % jp); continue
        k2 = norm(ko, keep_punct_space=bool(re.search('[%s]%s' % (re.escape(PUNCT_AFTER), SP), jp)))
        a = TOK.findall(jp); b2 = TOK.findall(k2)
        if sorted(a) != sorted(b2): warn.append('변수 다름(실행 파일): %s | %s' % (jp, ko)); continue
        nb = enc(k2, have)
        targets = set(fn for fn, _ in by_jp[jp]) | ({'ADVE.EXE'} if any(fn == 'ADV.EXE' for fn, _ in by_jp[jp]) else set())
        for fn in sorted(targets):
            buf = bytearray(files.get(fn) or open(os.path.join(ISO, fn), 'rb').read())
            old = mg_enc_jp(jp); k = buf.find(old + b'\0'); n = 0
            while k >= 0:
                pad = len(old) - len(nb)
                room = EXTRA_ROOM.get(jp)
                if pad < 0 and room and buf[k + len(old):k + room] == b'\0' * (room - len(old)) and len(nb) < room:
                    buf[k:k + room] = nb + b'\0' * (room - len(nb)); n += 1; k = buf.find(old + b'\0', k + 1); continue
                if pad < 0: warn.append('길이 넘침 %s %s: %d > %d B' % (fn, jp, len(nb), len(old))); break
                tail = old.endswith(b'\xa1\xa1')                         # 고정 칸(전각 공백 채움) 이면 공백으로
                buf[k:k + len(old)] = nb + ((b'\xa1\xa1' * (pad // 2) + b'\0' * (pad % 2)) if tail else b'\0' * pad)
                n += 1; k = buf.find(old + b'\0', k + 1)
            if n: files[fn] = bytes(buf); rep['실행 파일 번역'] += n
    if report:
        for k, v in sorted(rep.items()): print(' ', k, v)
        print('  경고', len(warn))
        for w in warn[:40]: print('   ', w)
    return files, warn


def mg_enc_jp(jp):
    out = bytearray(); i = 0
    while i < len(jp):
        if jp.startswith('\\n', i): out += b'\n\n'; i += 2; continue
        if jp.startswith('{0A}', i): out += b'\n'; i += 4; continue
        c = jp[i]; i += 1
        out += bytes([ord(c)]) if ord(c) < 0x80 else c.encode('euc_jp')
    return bytes(out)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    files, warn = build()
    same = all(open(os.path.join(ISO, k), 'rb').read() == v for k, v in files.items())
    print('바뀐 파일', sorted(files), '(번역 없으면 원본과 같음:', same, ')')
