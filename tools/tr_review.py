# -*- coding: utf-8 -*-
"""받은 번역 TSV 검수 (2026-11-22 코드R) — work/tr_in/coder_*.tsv(받은 것) 를 my files/tsv(원본 내보내기)와 대조
  python tools/tr_review.py survey   → 빠진 줄·원문 다름·토큰·줄 수·문장부호 분포·이름표 표기 집계"""
import os, re, sys, glob, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
ORIG = os.path.join(ROOT, 'my files', 'tsv'); TIN = os.path.join(ROOT, 'work', 'tr_in')
TOKS = re.compile(r'%[%0-9a-zA-Z]|\{0A\}|【|】')


def rows(d):
    out = {}
    for p in sorted(glob.glob(os.path.join(d, 'coder_*.tsv'))):
        L = open(p, encoding='utf-8-sig').read().split('\n'); h = L[0].split('\t')
        for l in L[1:]:
            if not l.strip(): continue
            c = l.split('\t'); out[(os.path.basename(p), c[0])] = dict(zip(h, c))
    return out


def survey():
    O = rows(ORIG); T = rows(TIN)
    miss = collections.Counter(k[0] for k in O if k not in T)
    print('받은 줄', len(T), '원본 줄', len(O), '빠진 줄', sum(miss.values()), miss.most_common(5))
    for k, v in T.items():
        if O[k]['JP'] != v['JP']: print('  원문 다름', k, repr(O[k]['JP'][:50]), '→', repr(v['JP'][:50]))
    tok = []; nl = 0; empty = 0
    for k, v in T.items():
        jp, ko = v['JP'], v.get('KO', '')
        if not ko.strip(): empty += 1; continue
        if collections.Counter(TOKS.findall(jp)) != collections.Counter(TOKS.findall(ko)): tok.append((k, jp[:60], ko[:60]))
        if ko.count('\\n') != jp.count('\\n'): nl += 1
    print('빈 번역', empty, '· 토큰 다름', len(tok), '· 줄 수 다름', nl)
    for t in tok[:15]: print('  ', t)
    pc = collections.Counter(c for v in T.values() for c in v.get('KO', '') if not ('가' <= c <= '힣' or c.isalnum() or c in ' 　\\'))
    print('번역 부호', pc.most_common(45))
    pj = collections.Counter(c for v in T.values() for c in v['JP'] if c in '、。！？…‥・「」『』（）〜ー―：；，．!?.,~')
    print('원문 부호', pj.most_common(30))
    # 이름표
    tags = collections.defaultdict(collections.Counter)
    for v in T.values():
        a = re.findall(r'【([^】]*)】', v['JP']); b = re.findall(r'【([^】]*)】', v.get('KO', ''))
        for x, y in zip(a, b): tags[x][y] += 1
    print('이름표', len(tags))
    for x, c in sorted(tags.items(), key=lambda t: -sum(t[1].values())):
        print('  %s → %s' % (x, dict(c.most_common(4))))


NAMES = {'晶': '아키라', '寛': '히로시', 'さゆり': '사유리', '美穂': '미호', '美由樹': '미유키', '正': '타다시', '千絵': '치에',
         '志津子': '시즈코', '宏司': '코지', '裕子': '유코', '昭二': '쇼지', '南': '미나미', '健三': '켄조', '不二彦': '후지히코',
         '克弥': '카츠야', '克也': '카츠야', '洋介': '요스케', '昌哉': '마사야', '章吾': '쇼고', '落合': '오치아이', 'タカシ': '타카시',
         '真一': '신이치', '新一': '신이치', '誠': '마코토', 'マコト': '마코토', 'セブン': '세븐', 'キング': '킹', 'クイーン': '퀸',
         '哲也': '테츠야', '宮崎': '미야자키', '寺田': '테라다', '植木': '우에키', '松尾': '마츠오'}


def strip_sp(s): return s.replace('　', '').replace(' ', '')


def namecheck():
    T = rows(TIN); miss = collections.defaultdict(list); var = collections.defaultdict(collections.Counter)
    for k, v in T.items():
        jp = re.sub(r'【[^】]*】', '', v['JP']); ko = strip_sp(re.sub(r'【[^】]*】', '', v.get('KO', '')))
        for n, kr in NAMES.items():
            if len(n) == 1 and n in '正南誠寛晶':          # 한 글자 이름은 낱말 일부일 수 있음 — 앞뒤가 한자가 아닐 때만
                if not re.search(r'(?<![一-鿿])%s(?![一-鿿])' % n, jp): continue
            elif n not in jp: continue
            if kr not in ko: miss[n].append((k, v['JP'][:40].replace('　', ''), v.get('KO', '')[:40].replace('　', '')))
    for n, L in sorted(miss.items(), key=lambda t: -len(t[1])):
        print('%s(%s) 없음 %d' % (n, NAMES[n], len(L)))
        for x in L[:6]: print('    ', x)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    {'survey': survey, 'names': namecheck}[sys.argv[1]]()
