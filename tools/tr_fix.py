# -*- coding: utf-8 -*-
"""받은 번역 검수 자동 수정 (2026-11-22 코드R, 하스피 «인물 용어 명사 말투 토큰 줄넘침 확인, 문장부호 우리 것으로»)
work/tr_in/coder_*.tsv(받은 그대로) → work/tr/coder_*.tsv(빌더가 읽음) + work/tr/changes.tsv(줄마다 바뀐 사유)
 · JP 칸 = 원본 내보내기(my files/tsv) 그대로(번역 도구가 「…。」를 「….」로 바꾼 6줄 되돌림)
 · 이름(거센소리 규칙, 그 한자가 원문에 있는 줄에서만): 고지→코지 · 마쓰오→마츠오 · 데라다→테라다 · 가쓰야→카츠야 · 다카시→타카시 ·
   다다시/마사시→타다시(正) · 지에→치에 · 겐조→켄조 · 데쓰야→테츠야 · 니타→닛타(仁田) · 좌량→사라(左良)
 · 走り屋 → «레이서»(하스피 선택) + 조사 받침
 · 이름표 【…】: 안쪽 3칸(원문과 같은 폭 — 둘째 줄 들여쓰기 5칸과 맞게): 1자 «　X　» · 2자 «X　Y» · 「　正　」=타다시 · 「　男　」=남자 · ギャラリー=갤러리
 · 문장부호: «...» → «…» · 장음 «ㅡ»«−» → «ー» (전각화·부호 뒤 공백 삭제는 빌더 norm 이 함)
python tools/tr_fix.py"""
import os, re, sys, glob, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
ORIG = os.path.join(ROOT, 'my files', 'tsv'); TIN = os.path.join(ROOT, 'work', 'tr_in'); OUT = os.path.join(ROOT, 'work', 'tr')
SP = '　'

# (원문 조건 정규식, 틀린 표기, 바른 표기)
NAME_RULES = [
    (r'宏司', '고지', '코지'), (r'松尾', '마쓰오', '마츠오'), (r'寺田', '데라다', '테라다'),
    (r'克弥|克也', '가쓰야', '카츠야'), (r'タカシ', '다카시', '타카시'),
    (r'正さん|落合正|【　正　】', '다다시', '타다시'), (r'正さん|落合正|【　正　】', '마사시', '타다시'),
    (r'千絵', '지에', '치에'), (r'健三', '겐조', '켄조'), (r'哲也', '데쓰야', '테츠야'),
    (r'仁田', '니타', '닛타'), (r'左良', '좌량', '사라'),
]
TAG_OVERRIDE = {}
TAG_PICK = {'女の子': '여자애', '占い婆': '점쟁이', '男の声': '남자 목소리', '　女　': '여자', '子　供': '아이', '　子供　': '아이', 'サラリーマン': '샐러리맨'}   # 다수표 대신 정한 것
TAG_FIX = {'　正　': '타다시', '　男　': '남자', 'ギャラリー': '갤러리'}
# 走り屋: 받침 있는 옛 표기 → 받침 없는 «레이서» (조사 바꿈)
RUNNER_OLD = ('주행꾼', '주행족')
JOSA = [('이라고', '라고'), ('이라는', '라는'), ('이라면', '라면'), ('이라', '라'), ('이었', '였'), ('이야', '야'), ('이에요', '예요'),
        ('으로', '로'), ('이랑', '랑'), ('이나', '나'), ('이고', '고'), ('이지', '지'), ('이다', '다'), ('이네', '네'),
        ('은', '는'), ('이', '가'), ('을', '를'), ('과', '와'), ('아', '야')]


# ── 줄 다시 접기(창 폭 24칸, 이름표 줄은 다음 줄 5칸 들여쓰기 — 스샷 실측 2026-11-22) ──
N = chr(92) + 'n'; WIDTH = 24; IND = SP * 5
TIGHT = ('요', '죠', '지도', '까지', '으니까', '서', '는', '잖아', '겠지', '라고', '되어', '힐을')   # 번역자가 어미를 다음 줄로 넘긴 이음매는 붙임


def cells(s):
    s = re.sub(r'%[uU]', '***', s); s = re.sub(r'%[%0-9a-zA-Z]+', '**', s)
    return len(s)


def mode(jp):
    f = jp.split(N)[0]
    if f.startswith('【'): return 'spk'
    if f.startswith(IND): return 'ind'
    return 'none'


def reflow(jp, ko, corpus, force=False):
    """넘치는 줄이 있을 때만 → (새 번역, 줄 수). 아니면 (ko, None)"""
    if '{0A}' in jp or re.search(r'(^|' + re.escape(N) + r')[\u3000 ]*・', jp): return ko, None
    lines = ko.split(N)
    if not force and all(cells(l) <= WIDTH for l in lines): return ko, None
    md = mode(jp); tag = ''
    if md == 'spk':
        m = re.match(r'【[^】]*】', lines[0])
        if not m: return ko, None
        tag = m.group(0); lines[0] = lines[0][len(tag):]
    parts = [l.strip(SP + ' ') for l in lines if l.strip(SP + ' ')]
    text = parts[0] if parts else ''
    for b in parts[1:]:
        lw = re.findall('[가-힣]+$', text); rw = re.findall('^[가-힣]+', b)
        if lw and rw and rw[0] in TIGHT and corpus[lw[0] + rw[0]] > 0: text += b
        else: text += ' ' + b
    words = [w for w in text.split(' ') if w]
    first_pre = tag if md == 'spk' else (IND if md == 'ind' else ''); next_pre = (SP * cells(tag)) if md == 'spk' else (IND if md == 'ind' else '')   # 이름표 줄 다음 = 이름표 폭(【子供】 4칸 등)
    out = []; cur = first_pre; empty = True
    for w in words:
        cand = cur + w if empty else cur + ' ' + w
        if cells(cand) > WIDTH and not empty:
            out.append(cur); cur = next_pre + w
        else: cur = cand
        empty = False
    out.append(cur)
    return N.join(out), len(out)


TERM_RULES = [(r'フロムジュピター', '프롬쥬피터', '프롬 주피터'), (r'フロムムーン', '프롬문', '프롬 문'), (r'左良市', '左良市', '사라시'), (r'エッソ', '에소', '에쏘'), (r'ガソリン', '휘발유', '가솔린'), (r'テレビ', 'TV', '텔레비전'), (r'ヒルクライム|クライムヒル', '클라임 힐', '힐클라임')]


BSN = chr(92) + 'n'
CHOICE_FIX = {'・あたりを見る': '・주변을 둘러본다', '・あたり': '・주변을 둘러본다', '・まわりを見る': '・주변을 둘러본다',
              '・やめる': '・관둔다', '・やっぱりやめる': '・역시 관둔다', '・子供連れの主婦': '・아이를 데리고 온 주부',
              '・フロムムーン': '・프롬 문', '・フロムジュピター': '・프롬 주피터', '・サラリーマン': '・샐러리맨',
              '・自信はあるけどね': '・자신은 있지만', '・秋目峠、ダウンヒルで勝負': '・아키메 고개, 다운힐로 승부',
              '・秋目峠、ヒルクライムで勝負': '・아키메 고개, 힐클라임으로 승부',
              '・車が出来る日まで、スキップ': '・차 나올 때까지 건너뛴다', '・しょうがないのでバイトする': '・어쩔 수 없으니 알바한다'}   # 원문 «・あたり»는 이 장소만 잘림


def fix_tag_indent(jp, ko):
    """이름표 대사 다음 줄 들여쓰기 = 번역 이름표 폭 — 원문에서 «들여쓰기 = 원문 이름표 폭»인 줄만(원문 2976/2985).
    이름표를 3칸으로 맞추면(【子供】→【아　이】) 원문 4칸 들여쓰기가 남아 한 칸 어긋났음(2026-11-22 실기)"""
    mj = re.match(r'【[^】]*】', jp); mk = re.match(r'【[^】]*】', ko)
    if not (mj and mk): return ko
    tj, tk = cells(mj.group(0)), cells(mk.group(0))
    jl, kl = jp.split(N), ko.split(N)
    if len(jl) != len(kl): return ko
    out = [kl[0]]
    for j, k in zip(jl[1:], kl[1:]):
        ij = len(j) - len(j.lstrip(SP))
        if ij == tj and k.strip(SP + ' '): k = SP * tk + k.lstrip(SP + ' ')
        out.append(k)
    return N.join(out)


def fix_quotes(jp, ko):
    """번역의 반각·둥근 따옴표 짝 → 원문이 그 자리에 쓴 괄호(『』 먼저, 다음 「」) — 원문에 없으면 『』(‘ 는 글꼴에 없음)"""
    br = re.findall(r'[『「]', jp)
    out = []; k = 0; opened = None
    for ch in ko:
        if ch in "'\"‘’“”":
            if opened is None:
                b = br[k] if k < len(br) else '『'; k += 1                # ‘’ 는 글꼴에 없음(A1C6) → 『』
                opened = {'『': '』', '「': '」', '‘': '’'}[b]; out.append(b)
            else:
                out.append(opened); opened = None
        else: out.append(ch)
    return ''.join(out) if opened is None else ko


def rows(d):
    out = collections.OrderedDict(); heads = {}
    for p in sorted(glob.glob(os.path.join(d, 'coder_*.tsv'))):
        L = open(p, encoding='utf-8-sig').read().split('\n'); h = L[0].split('\t'); heads[os.path.basename(p)] = h
        for l in L[1:]:
            if not l.strip(): continue
            c = l.split('\t'); out[(os.path.basename(p), c[0])] = c
    return out, heads


def _bat(ch):
    o = ord(ch) - 0xAC00
    return None if not (0 <= o < 11172) else o % 28            # 0 = 받침 없음, 8 = ㄹ


def term_replace(ko, a, b):
    """낱말 a → b 바꾸면서 바로 뒤 조사를 b 받침에 맞춤(휘발유가 → 가솔린이, 2026-11-22 «가솔린가»)"""
    ba, bb = _bat(a[-1]), _bat(b[-1])
    alts = sorted({x for pair in JOSA for x in pair}, key=len, reverse=True)
    def sub(m):
        j = m.group(1) or ''
        if not j or bb is None: return b + j
        for bat, nob in JOSA:
            if j in (bat, nob):
                if (bat, nob) == ('으로', '로'): return b + ('로' if bb in (0, 8) else '으로')
                return b + (nob if bb == 0 else bat)
        return b + j
    return re.sub(re.escape(a) + r'(' + '|'.join(re.escape(x) for x in alts) + r')?(?=[^가-힣]|$)', sub, ko).replace(a, b)


def fix_runner(jp, ko):
    if '走り屋' not in jp: return ko
    for old in RUNNER_OLD:
        def sub(m):
            j = m.group(1) or ''
            for a, b in JOSA:
                if j == a: return '레이서' + b
            return '레이서' + j
        ko = re.sub(old + r'(' + '|'.join(re.escape(a) for a, _ in JOSA) + r')?(?![가-힣])', sub, ko)
        ko = ko.replace(old, '레이서')                       # 남은 것(뒤에 다른 글자: 주행꾼들 등)
    return ko


def fix_tag(jp, ko):
    jt = re.findall(r'【([^】]*)】', jp); kt = list(re.finditer(r'【([^】]*)】', ko))
    if len(jt) != len(kt): return ko
    out = ko
    for j, m in reversed(list(zip(jt, kt))):
        inner = m.group(1)
        if j in TAG_FIX: inner = TAG_FIX[j]
        if '%' in inner: continue
        s = inner.replace(SP, '').replace(' ', '')
        if len(s) == 1: s = SP + s + SP
        elif len(s) == 2: s = s[0] + SP + s[1]
        elif len(s) == 3 or len(inner.replace(SP, '')) > 3: s = s if len(s) == 3 else inner.strip(SP + ' ')
        out = out[:m.start(1)] + s + out[m.end(1):]
    return out


MANUAL = {}                                       # work/tr_manual.tsv — 손으로 고친 줄(파일·번호·고친 번역·사유), 자동 수정 뒤 덮음
_mp = os.path.join(ROOT, 'work', 'tr_manual.tsv')
if os.path.exists(_mp):
    for _l in open(_mp, encoding='utf-8').read().split(chr(10))[1:]:
        if _l.strip(): _q = _l.split(chr(9)); MANUAL[(_q[0], _q[1])] = (_q[2], _q[3] if len(_q) > 3 else '')


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    O, _ = rows(ORIG); T, heads = rows(TIN)
    global CORPUS, OVER
    CORPUS = collections.Counter(w for c in T.values() for w in re.findall(r'[가-힣]+', re.sub(r'【[^】]*】', '', c[-1]).replace(N, ' ')))
    OVER = []
    os.makedirs(OUT, exist_ok=True)
    log = []; why_n = collections.Counter()
    for key, c in T.items():
        h = heads[key[0]]; ji = h.index('JP'); ki = len(h) - 1
        c[ji] = O[key][ji]                                      # 원문 되돌림
        jp = c[ji]; ko = c[ki] if len(c) > ki else ''
        if not ko.strip(): continue
        k0 = ko; why = []
        ko = re.sub(r'【([^】%]*)】', lambda m: '【' + m.group(1).replace(SP, '') + '】', ko)   # 이름표 안 공백 빼고 이름 바꾸기(fix_tag 가 다시 채움)
        for cond, a, b in NAME_RULES:
            if (re.search(cond, jp) or re.search(cond, jp.replace(SP, ''))) and a in ko: ko = ko.replace(a, b); why.append('이름 %s→%s' % (a, b))
        k1 = fix_runner(jp, ko)
        if k1 != ko: why.append('走り屋→레이서'); ko = k1
        k1 = fix_tag(jp, ko)
        if k1 != ko: why.append('이름표'); ko = k1
        k1 = re.sub(r'\.{3,}', '…', ko)
        if k1 != ko: why.append('...→…'); ko = k1
        k1 = re.sub('배틀 (하|해|했|한|할)', lambda m: '배틀' + m.group(1), ko)     # 동사 «배틀하다» 붙여 씀(번역 다수 표기)
        if k1 != ko: why.append('배틀하다'); ko = k1
        k1 = fix_quotes(jp, ko)
        if k1 != ko: why.append('따옴표'); ko = k1
        k1 = ko.replace('?,', '?').replace('!,', '!')
        if k1 != ko: why.append('겹친 부호'); ko = k1
        for cond, a, b in TERM_RULES:
            if re.search(cond, jp) and a in ko: ko = term_replace(ko, a, b); why.append('용어 %s→%s' % (a, b))
        k1 = ko.replace('ㅡ', 'ー').replace('−', 'ー')                 # 장음을 자모·수학 빼기로 쓴 것 → 원문 장음 ー(글꼴에 있음)
        if k1 != ko: why.append('장음ー'); ko = k1
        if key in MANUAL: ko = MANUAL[key][0]; why.append('손 수정: ' + MANUAL[key][1])
        if '・' in jp:                                                      # 같은 선택지는 같은 번역(2026-11-22 하스피 «왜 여기만 주변이야»)
            jl, kl = jp.split(BSN), ko.split(BSN)
            if len(jl) == len(kl):
                k1 = BSN.join(CHOICE_FIX.get(j, k) for j, k in zip(jl, kl))
                if k1 != ko: why.append('선택지 통일'); ko = k1
        k1 = fix_tag_indent(jp, ko)
        if k1 != ko: why.append('이름표 들여쓰기'); ko = k1
        if key[0] != 'coder_exe.tsv':
            k1, nl = reflow(jp, ko, CORPUS)
            if nl is not None and k1 != ko:
                why.append('다시 접음'); ko = k1
            if nl is not None and nl > 3: OVER.append((key[0], key[1], nl, jp, ko))
            ko = re.sub('배틀 (하|해|했|한|할)', lambda m: '배틀' + m.group(1), ko)   # 다시 접기가 이음매를 띄운 경우
        if ko != k0:
            c[ki] = ko; log.append((key[0], key[1], ','.join(why), k0, ko))
            for w in why: why_n[w.split(' ')[0] if w.startswith('이름 ') is False else w] += 1
    # 이름표 통일(하스피 2026-11-22 «이름표 통일해»): 원문 이름표마다 가장 많이 쓴 번역 표기(공백 빼고 셈)로
    ZEN = str.maketrans('0123456789', '０１２３４５６７８９')
    cnt = collections.defaultdict(collections.Counter)
    for key, c in T.items():
        h = heads[key[0]]; jp = c[h.index('JP')]; ko = c[len(h) - 1] if len(c) >= len(h) else ''
        for j, k in zip(re.findall(r'【([^】]*)】', jp), re.findall(r'【([^】]*)】', ko)):
            if '%' not in j:
                raw = k.strip(SP + ' ').translate(ZEN)
                raw = raw if len(raw.replace(SP, '').replace(' ', '')) > 3 else raw.replace(SP, '').replace(' ', '')   # 짧은 이름은 칸 맞춤 공백 빼고 셈
                cnt[j][raw.replace(SP, ' ')] += 1
    major = {j: c.most_common(1)[0][0] for j, c in cnt.items()}
    TAG_OVERRIDE.update({j: v for j, v in TAG_PICK.items()})
    for j, v in TAG_OVERRIDE.items(): major[j] = v
    unify = collections.Counter()
    for key, c in T.items():
        h = heads[key[0]]; ki = len(h) - 1; jp = c[h.index('JP')]
        if len(c) <= ki or '【' not in c[ki]: continue
        jt = re.findall(r'【([^】]*)】', jp); kt = list(re.finditer(r'【([^】]*)】', c[ki]))
        if len(jt) != len(kt): continue
        ko = c[ki]
        for j, m in reversed(list(zip(jt, kt))):
            if j not in major or '%' in m.group(1): continue
            want = major[j]
            if len(want) == 1: want = SP + want + SP
            elif len(want) == 2: want = want[0] + SP + want[1]
            if m.group(1) != want:
                ko = ko[:m.start(1)] + want + ko[m.end(1):]; unify[(j, m.group(1), want)] += 1
        if ko != c[ki]:
            first = c[ki]
            ko = fix_tag_indent(jp, ko)                                       # 이름표 폭이 바뀌면 들여쓰기·접기 다시(점쟁이 할멈)
            if key[0] != 'coder_exe.tsv':
                k1, nl = reflow(jp, ko, CORPUS, force=len(ko.split(N)) != len(jp.split(N)))   # 이름표 폭이 바뀌어 원문보다 줄이 많으면 다시 접음
                if nl is not None: ko = k1
                if nl is not None and nl > 3: OVER.append((key[0], key[1], nl, jp, ko))
            c[ki] = ko
            log.append((key[0], key[1], '이름표 통일', first, ko))
    for (j, a, b), n in sorted(unify.items(), key=lambda t: -t[1]):
        if a.replace(SP, '') != b.replace(SP, '') : print('  이름표 통일 %s: %s → %s (%d)' % (j, a, b, n))
    by = collections.defaultdict(list)
    for key, c in T.items(): by[key[0]].append('\t'.join(c))
    for fn, L in by.items():
        open(os.path.join(OUT, fn), 'w', encoding='utf-8').write('\t'.join(heads[fn]) + '\n' + '\n'.join(L) + '\n')
    with open(os.path.join(OUT, 'changes.tsv'), 'w', encoding='utf-8') as f:
        f.write('파일\t번호\t사유\t받은 번역\t고친 번역\n')
        for r in log: f.write('\t'.join(r) + '\n')
    with open(os.path.join(OUT, 'overflow.tsv'), 'w', encoding='utf-8') as f:
        f.write('파일\t번호\t줄 수\t원문\t번역\n')
        for r in OVER: f.write('%s\t%s\t%d\t%s\t%s\n' % r)
    print('고친 줄 %d / %d · 3줄 넘침 %d(work/tr/overflow.tsv)' % (len(log), len(T), len(OVER)))
    for w, n in why_n.most_common(): print('  %s %d' % (w, n))


if __name__ == '__main__':
    main()
