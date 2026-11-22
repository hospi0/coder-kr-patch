# -*- coding: utf-8 -*-
"""번역 2차 점검(2026-11-22) — work/tr 대상, 보고만
 ① 남은 가나·한자 ② 빈 번역 ③ 따옴표·괄호 짝·겹친 부호 ④ 가타카나 고유명사(원문) → 번역 표기 흔들림
 ⑤ %u/%U(주인공 이름) 바로 뒤 조사 ⑥ 부호 앞 공백"""
import os, re, sys, glob, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
N = chr(92) + 'n'; SP = '　'


def rows():
    out = []
    for p in sorted(glob.glob(os.path.join(ROOT, 'work', 'tr', 'coder_*.tsv'))):
        L = open(p, encoding='utf-8').read().split('\n'); h = L[0].split('\t')
        for l in L[1:]:
            c = l.split('\t')
            if len(c) < len(h): continue
            out.append((os.path.basename(p), c[0], c[h.index('JP')], c[len(h) - 1]))
    return out


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    R = rows()
    def show(title, L, n=12):
        print('■ %s %d' % (title, len(L)))
        for x in L[:n]: print('    ', x)
    show('① 가나·한자 남음', [(f, i, re.findall(r'[぀-ヿ一-鿿]+', k)) for f, i, j, k in R if re.search(r'[぀-ゟ゠-ヾ一-鿿]', re.sub(r'[ー・]', '', k))])
    show('② 빈 번역', [(f, i, j[:40]) for f, i, j, k in R if not k.strip()])
    pairs = [('『', '』'), ('「', '」'), ('（', '）'), ('(', ')')]
    bad = []
    for f, i, j, k in R:
        for a, b in pairs:
            if k.count(a) != k.count(b): bad.append((f, i, a + b, k[:60]))
        if k.count("'") % 2 or k.count('"') % 2: bad.append((f, i, 'quote', k[:60]))
    show('③ 괄호·따옴표 짝 안 맞음', bad)
    q = [(f, i, k[:70]) for f, i, j, k in R if re.search(r"['\"‘’“”]", k)]
    show('③ 반각/둥근 따옴표 쓴 줄(원문은 『』「」)', q, 8)
    dup = [(f, i, m) for f, i, j, k in R for m in re.findall(r'[.,!?。、，．]{2,}|[!?！？][.．]|[.．][!?！？]', k) if m not in ('?!', '!?', '!!', '??', '!!!', '???', '?!?', '!?!')]
    show('③ 겹친 부호', dup, 10)
    # ④ 가타카나 고유명사 → 번역에서 그 줄에 나오는 한글 낱말 후보(같은 원문 낱말끼리 첫 번역 낱말 비교는 어렵다 → 원문 낱말별 «번역에 흔히 같이 나오는 한글 낱말» 상위 둘)
    kata = collections.Counter(w for f, i, j, k in R for w in re.findall(r'[ァ-ヴー]{3,}', j))
    print('■ ④ 원문 가타카나 낱말(5회 이상) → 번역 후보 상위')
    for w, n in kata.most_common(60):
        if n < 5: break
        c = collections.Counter()
        for f, i, j, k in R:
            if w in j: c.update(set(re.findall(r'[가-힣A-Za-zＡ-Ｚａ-ｚ]{2,}', k)))
        print('    %s(%d): %s' % (w, n, ', '.join('%s %d' % x for x in c.most_common(4))))
    josa = collections.Counter(m for f, i, j, k in R for m in re.findall(r'%[uU]([가-힣]{1,2})', k))
    print('■ ⑤ %u/%U 바로 뒤 글자:', josa.most_common(25))
    sp = [(f, i, m) for f, i, j, k in R for m in re.findall(r'[가-힣][ 　]+[,.!?，．！？]', k)]
    show('⑥ 부호 앞 공백', sp, 8)


if __name__ == '__main__':
    main()
