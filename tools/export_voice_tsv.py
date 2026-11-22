# -*- coding: utf-8 -*-
"""리플레이 음성 자막 번역 TSV (2026-11-22) — work/voice/asr.tsv(위스퍼) → my files/tsv/coder_voice.tsv
 줄 = EVENT.DAT 대본이 부르는 클립(처음 나오는 순서 — 대화 흐름), 같은 클립은 한 줄.
 열 = 번호 · 위치(클립 이름·길이) · JP(받아쓰기: VAD 켠 결과, 비면 VAD 끈 결과) · KO(빈칸)
 18 KB 넘으면 coder_voice_NN.tsv 로 나눔."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import rep_voice

LIMIT = 18 * 1024


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    asr = {}
    for ln in list(open(os.path.join(ROOT, 'work', 'voice', 'asr.tsv'), encoding='utf-8'))[1:]:
        nm, sec, a, b = (ln.rstrip('\n').split('\t') + ['', ''])[:4]
        asr[nm] = (float(sec), a.strip() or b.strip())
    order = list(dict.fromkeys(rep_voice.used_in_event()))
    miss = [n for n in order if n not in asr]
    assert not miss, ('받아쓰기 없는 클립', miss[:5])
    rows = [('%05d' % (i + 1), '%s (%.1f초)' % (n, asr[n][0]), asr[n][1], '') for i, n in enumerate(order)]
    head = '번호\t위치\tJP\tKO\n'
    chunks, cur = [], head
    for r in rows:
        line = '\t'.join(r) + '\n'
        if len((cur + line).encode('utf-8')) > LIMIT and cur != head: chunks.append(cur); cur = head
        cur += line
    chunks.append(cur)
    out = os.path.join(ROOT, 'my files', 'tsv')
    names = ['coder_voice.tsv'] if len(chunks) == 1 else ['coder_voice_%02d.tsv' % (k + 1) for k in range(len(chunks))]
    for n, c in zip(names, chunks):
        open(os.path.join(out, n), 'w', encoding='utf-8').write(c)
    empty = sum(1 for r in rows if not r[2])
    print('%d줄 → %s (받아쓰기 빈 줄 %d)' % (len(rows), ', '.join(names), empty))


if __name__ == '__main__':
    main()
