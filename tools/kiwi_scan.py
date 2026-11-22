# -*- coding: utf-8 -*-
"""붙여 쓴 띄어쓰기 찾기(2026-11-22, asuka work/report/kiwi_scan2.py 꼴) — work/tr 번역, 보고만
  C:/claude/utils/kiwi-venv/Scripts/python tools/kiwi_scan.py → work/tr/kiwi_scan.tsv"""
import glob, re, sys, os
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
from kiwipiepy import Kiwi
K = Kiwi()
N = chr(92) + 'n'
NAMES = '아키라 히로시 사유리 미호 미유키 타다시 치에 시즈코 코지 유코 쇼지 미나미 켄조 후지히코 카츠야 요스케 마사야 쇼고 오치아이 테츠야 마코토 신이치 사카모토 테라다 마츠오 아라키 에노모토 아오키 아사노 와타베 이즈미 하시모토 우에키 닛타 아키메 겐부 사라 하야부사 에쏘 레이서 하치로쿠 다크포스'.split()
for w in NAMES:
    try: K.add_user_word(w, 'NNP', 0)
    except Exception: pass
SEG = re.compile(r'[가-힣]+(?:[가-힣 ]*[가-힣])?')
CONTENT = ('NN', 'NP', 'NR', 'VV', 'VA', 'MA', 'MM', 'XR', 'SL', 'SN', 'IC')


def joins(text):
    out = []
    for m in SEG.finditer(text):
        seg = m.group(0)
        try: toks = K.tokenize(seg)
        except Exception: continue
        for a, b in zip(toks, toks[1:]):
            if a.start + a.len != b.start: continue
            if seg[b.start - 1:b.start] == ' ' or seg[b.start:b.start + 1] == ' ': continue
            ta, tb = a.tag, b.tag
            ok = (ta.startswith('J') or ta.startswith('E')) and (tb.startswith(CONTENT) or (a.form == '지' and tb.startswith('VX') and b.form in ('않', '못', '말')))
            if ta == 'ETN' or b.form in ('하', '되', '시'): ok = False
            if ok: out.append(m.start() + b.start)
    return out


if __name__ == '__main__':
    out = []
    for p in sorted(glob.glob(os.path.join(ROOT, 'work', 'tr', 'coder_*.tsv'))):
        for l in open(p, encoding='utf-8').read().split('\n')[1:]:
            c = l.split('\t')
            if len(c) < 4 or not re.search('[가-힣]', c[-1]): continue
            kr = c[-1]; plain = kr.replace(N, '\x00\x00').replace('\u3000', ' ')
            js = joins(plain)
            if js:
                out.append((os.path.basename(p), c[0], ''.join(('^' if i in js else '') + ch for i, ch in enumerate(kr))))
    with open(os.path.join(ROOT, 'work', 'tr', 'kiwi_scan.tsv'), 'w', encoding='utf-8') as f:
        for r in out: f.write('\t'.join(r) + '\n')
    print('붙은 곳 있는 줄', len(out))
    for r in out[:40]: print('  ', r)
