# -*- coding: utf-8 -*-
"""실행 파일 문자열 번역 TSV → my files/tsv/coder_exe_NNN.tsv
열: 번호 · 위치 · JP · 최대(전각 칸 = 원문 바이트/2, 제자리 덮어쓰기 예산) · KO
대상: ADV.EXE(ADVE.EXE 같은 문자열 → 빌더가 둘 다), 0KERNL.BIN, SET.EXE, RACE.EXE  (STF.EXE 스태프롤 제외)"""
import os, re, struct, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exestr, mg
from extract import write_split
ROOT = mg.ROOT
SRC = [('ADV.EXE', 0x06050000, True), ('0KERNL.BIN', 0x06004000, True), ('SET.EXE', None, False), ('RACE.EXE', None, False)]
KEEP = {('ADV.EXE', 0x0E880)}                     # 한 글자지만 화면 문자열(시계 «時»)
KANA = re.compile('[぀-ヿ一-鿿０-ｚ]')


def items():
    out = []
    for fn, base, need_ref in SRC:
        b = open(os.path.join(mg.ISO, fn), 'rb').read()
        words = collections.Counter(struct.unpack_from('>I', b, j)[0] for j in range(0, len(b) - 3, 4))
        for o, s in exestr.runs(b):
            if need_ref and not words.get(base + o): continue
            try: jp = mg.dec(s)
            except Exception: continue
            core = re.sub(r'\\n|%[%0-9a-zA-Z]+|[ 　]', '', jp)
            if (fn, o) in KEEP: out.append((fn, o, jp, len(s) // 2)); continue
            if len(KANA.findall(core)) < 2 and not re.fullmatch(r'[぀-ヿ]', core): continue   # 한 글자 한자·찌꺼기
            if '/' in jp: continue
            tailjp = re.sub(r'(\\n)+$', '', jp)
            if re.search(r'[A-Za-z]{1,2}$', tailjp) and not jp.endswith(('ＡＭ', 'ＰＭ')) and '%' not in jp[-4:]: continue
            if not need_ref and len(core) < 2: continue
            out.append((fn, o, jp, len(s) // 2))
    return out


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    its = items(); uniq = collections.OrderedDict()
    for fn, o, jp, n in its:
        if jp not in uniq: uniq[jp] = ('%s:%05X' % (fn, o), n)
        else: uniq[jp] = (uniq[jp][0], min(uniq[jp][1], n))
    lines = ['%05d\t%s\t%s\t%d\t\n' % (i, pos, jp, n) for i, (jp, (pos, n)) in enumerate(uniq.items(), 1)]
    folder = os.path.join(ROOT, 'my files', 'tsv')               # 하스피 «실행파일 tsv 두 개 하나로»(11-21) → 한 파일
    for f in os.listdir(folder):
        if f.startswith('coder_exe'): os.remove(os.path.join(folder, f))
    with open(os.path.join(folder, 'coder_exe.tsv'), 'w', encoding='utf-8', newline='\n') as w:
        w.write('번호\t위치\tJP\t최대\tKO\n' + ''.join(lines))
    k = 1
    c = collections.Counter(fn for fn, *_ in its)
    print('문자열', len(its), dict(c), '→ 고유', len(uniq), '→ TSV', k, '개')
