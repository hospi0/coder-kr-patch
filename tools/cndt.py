# -*- coding: utf-8 -*-
"""ADV_CNDT.DAT — 적재 코드(ADV.EXE 0x06055244)가 재배치하는 구조 그대로 읽기
머리: [0]=A 오프셋, [4]=B 오프셋. i=0..5: B[i]+=base, A[i]+=base → A[i] = 목록 L(0 끝) → L[j]+=base → 목록 M(0 끝) → M[k]+=base
→ 재배치되는 워드 = A·B·L·M 항목. 문자열 포인터 = M 항목 중 문자열을 가리키는 것."""
import os, struct, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, 'work', 'iso', 'ADV_CNDT.DAT')
W = lambda b, o: struct.unpack_from('>I', b, o)[0]


def reloc_words(b):
    a, bb = W(b, 0), W(b, 4); words = {}
    for i in range(6):
        words[bb + 4 * i] = ('B', W(b, bb + 4 * i)); words[a + 4 * i] = ('A', W(b, a + 4 * i))
        l = W(b, a + 4 * i); j = 0
        while W(b, l + 4 * j):
            words[l + 4 * j] = ('L', W(b, l + 4 * j)); m = W(b, l + 4 * j); k = 0
            while W(b, m + 4 * k):
                words[m + 4 * k] = ('M', W(b, m + 4 * k)); k += 1
            j += 1
    return words


TEXT0 = 0x28F0


def strings(b):
    out = {}; i = TEXT0
    while i < len(b):
        if b[i] in (0, 9): i += 1; continue
        j = b.index(b'\0', i); out[i] = b[i:j]; i = j
    return out


def rebuild(b, texts):
    """texts = {원래 오프셋: 새 바이트} — 문자열 영역(0x28F0~끝)만 다시 쌓고 M 포인터 고침(채움 규칙은 mg.pad)"""
    import mg
    st = strings(b); w = reloc_words(b)
    ptr = [o for o, (k, v) in w.items() if k == 'M']
    assert all(W(b, o) in st for o in ptr) and len(set(W(b, o) for o in ptr)) == len(st)
    out = bytearray(b[:TEXT0]); newpos = {}
    for n, t in enumerate(sorted(st)):
        if n: mg.pad(out)
        newpos[t] = len(out); out += texts.get(t, st[t]) + b'\0'
    if not texts: out += b[len(out):]
    else: mg.pad(out)
    for o in ptr: struct.pack_into('>I', out, o, newpos[W(b, o)])
    return bytes(out)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    b = open(P, 'rb').read(); w = reloc_words(b)
    import collections
    print(collections.Counter(k for k, _ in w.values()))
    starts = set(); i = 0x28F0
    while i < len(b):
        if b[i] in (0, 9): i += 1; continue
        j = b.index(b'\0', i); starts.add(i); i = j
    tp = {o: v for o, (k, v) in w.items() if v in starts}
    print('문자열 가리키는 재배치 워드', len(tp), '종류', collections.Counter(w[o][0] for o in tp))
    old = [j for j in range(0, 0x28F0, 4) if W(b, j) in starts]
    print('예전 «값이 같은 워드» 방식', len(old), '재배치 밖', [hex(j) for j in old if j not in w][:20])
    print('문자열 중 참조 없는 것', len(starts - set(tp.values())))
    mm = [v for o, (k, v) in w.items() if k == 'M' and v not in starts]
    print('M 인데 문자열 아님', len(mm), [hex(x) for x in mm[:10]])
