# -*- coding: utf-8 -*-
"""번역용 TSV — 대사(ADV_MG*·ADV_EVMG) + ADV_CNDT 문자열, 같은 원문은 한 줄(첫 위치), 18 KB 단위로 my files/tsv/coder_NNN.tsv
열: 번호 · 위치(파일:오프셋) · JP · KO   (\n = 줄바꿈, %u 이름 · %U 성 등 변수는 그대로)"""
import os, sys, struct, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mg
ROOT = mg.ROOT
SPLIT = 18 * 1024


def cndt_strings():
    """ADV_CNDT.DAT — 0x28F0 부터 끝까지 문자열(파일 기준 상대 포인터로 전부 참조됨 확인)"""
    b = open(os.path.join(mg.ISO, 'ADV_CNDT.DAT'), 'rb').read(); i = 0x28F0; out = []
    while i < len(b):
        if b[i] in (0, 9): i += 1; continue
        j = b.index(b'\0', i); out.append((i, b[i:j])); i = j
    return out


def write_split(folder, stem, head, lines):
    os.makedirs(folder, exist_ok=True)
    for f in os.listdir(folder):
        if f.startswith(stem + '_') and f.endswith('.tsv'): os.remove(os.path.join(folder, f))
    chunks = []; cur = []; size = len(head.encode('utf-8'))
    for ln in lines:
        n = len(ln.encode('utf-8'))
        if cur and size + n > SPLIT: chunks.append(cur); cur = []; size = len(head.encode('utf-8'))
        cur.append(ln); size += n
    if cur: chunks.append(cur)
    for i, c in enumerate(chunks, 1):
        with open(os.path.join(folder, '%s_%03d.tsv' % (stem, i)), 'w', encoding='utf-8', newline='\n') as w:
            w.write(head + ''.join(c))
    return len(chunks)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    uniq = collections.OrderedDict(); total = 0
    for fn in mg.FILES:
        b = open(os.path.join(mg.ISO, fn), 'rb').read()
        tend, ptrs, tg, strs = mg.parse(b)
        for t in tg:
            jp = mg.dec(strs[t]); total += 1
            uniq.setdefault(jp, '%s:%05X' % (fn, t))
    for off, s in cndt_strings():
        jp = mg.dec(s); total += 1
        uniq.setdefault(jp, 'ADV_CNDT.DAT:%05X' % off)
    for jp in uniq: assert '\t' not in jp and '\n' not in jp
    lines = ['%05d\t%s\t%s\t\n' % (i, pos, jp) for i, (jp, pos) in enumerate(uniq.items(), 1)]
    n = write_split(os.path.join(ROOT, 'my files', 'tsv'), 'coder', '번호\t위치\tJP\tKO\n', lines)
    print('원문 %d줄 → 고유 %d줄 → TSV %d개 (my files/tsv/coder_001~%03d.tsv)' % (total, len(uniq), n, n))


if __name__ == '__main__':
    main()
