# -*- coding: utf-8 -*-
"""실행 파일 안 EUC 문자열 찾기 + 참조(4바이트 정렬 워드 = 적재주소+오프셋) 세기
python tools/exestr.py ADV.EXE 0x06050000 [--all]"""
import os, re, struct, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from mg import dec

RUN = re.compile(rb'(?:[\xa1-\xfe][\xa1-\xfe]|[\n\x20-\x7e])+\x00')


def runs(b):
    out = []
    for m in RUN.finditer(b):
        s = m.group()[:-1]; st = m.start()
        # 앞 아스키 찌꺼기 떼기: 첫 EUC 글자 또는 %·\n 부터
        k = re.search(rb'[\xa1-\xfe]', s)
        if not k: continue
        if not re.search(rb'[\xa4-\xfe][\xa1-\xfe]|\xa1[\xa2-\xfe]', s): continue
        lead = re.match(rb'[\n%A-Za-z0-9 ]*', s[:k.start()][::-1])
        cut = k.start() - (len(lead.group()) if lead else 0)
        # 문자열 시작은 앞 바이트가 0·09 이거나 정렬 경계
        out.append((st + cut, s[cut:]))
    return out


def refs(b, base, off):
    v = struct.pack('>I', base + off); return [j for j in range(0, len(b) - 3, 4) if b[j:j + 4] == v]


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    fn, base = sys.argv[1], int(sys.argv[2], 16)
    b = open(os.path.join(ROOT, 'work', 'iso', fn), 'rb').read()
    words = {}
    for j in range(0, len(b) - 3, 4): words.setdefault(struct.unpack_from('>I', b, j)[0], []).append(j)
    rs = runs(b); nref = 0
    for o, s in rs:
        r = words.get(base + o, [])
        nref += bool(r)
        try: t = dec(s)
        except Exception as e: t = repr(s)
        if '--all' in sys.argv or not r:
            print('%06X %2d %s' % (o, len(r), t[:60]))
    print('문자열', len(rs), '참조 있음', nref)
