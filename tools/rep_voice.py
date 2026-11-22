# -*- coding: utf-8 -*-
"""리플레이(이벤트 대본) 음성 꺼내기·받아쓰기 (2026-11-22 하스피 «코드알 음성자막 훅»)
 ALLLDX.HDH = [이름 8 B][u32 HDC 위치] × 85 · ALLLDX.HDC = LDX 마다 [클립 이름 8 B][u32 섹터(2048) 위치] 줄
 REPGA*.LDX = ADX 를 섹터 정렬로 이어 붙인 것(머리 없음). 대본 = EVENT.DAT(얼굴 그림 RU_03… + 음성 M_F_151… + CLEAR).
  python tools/rep_voice.py split   → work/voice/<클립>.adx · .wav(16 kHz) · work/voice/clips.tsv
  (받아쓰기는 위스퍼 venv: C:\\claude\\utils\\whisper-venv\\Scripts\\python.exe tools/rep_voice.py asr → work/voice/asr.tsv)"""
import os, re, struct, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ISO = os.path.join(ROOT, 'work', 'iso'); OUT = os.path.join(ROOT, 'work', 'voice')
FFMPEG = r'C:\claude\utils\ffmpeg-9.0.1-essentials_build\bin\ffmpeg.exe'


def index():
    h = open(os.path.join(ISO, 'ALLLDX.HDH'), 'rb').read(); c = open(os.path.join(ISO, 'ALLLDX.HDC'), 'rb').read()
    ents = [(h[i:i + 8].rstrip(b'\0').decode(), struct.unpack('>I', h[i + 8:i + 12])[0]) for i in range(0, len(h), 12) if h[i]]
    offs = sorted(o for _, o in ents) + [len(c)]
    out = {}
    for n, o in ents:
        e = offs[offs.index(o) + 1]
        out[n] = [(c[p:p + 8].rstrip(b'\0').decode(), struct.unpack('>I', c[p + 8:p + 12])[0]) for p in range(o, e - 11, 12)]
    return out


def used_in_event():
    b = open(os.path.join(ISO, 'EVENT.DAT'), 'rb').read()
    return [m.group().decode() for m in re.finditer(rb'[MF]_[A-I]_\d\d\d', b)]


def split():
    os.makedirs(OUT, exist_ok=True)
    idx = index(); rows = []
    for ldx, clips in sorted(idx.items()):
        if not ldx.startswith('REPGA'): continue
        d = open(os.path.join(ISO, ldx + '.LDX'), 'rb').read()
        clips = [x for x in clips if x[0]]
        secs = [s for _, s in clips] + [(len(d) + 2047) // 2048]
        for (nm, s), e in zip(clips, secs[1:]):
            if not nm: continue                        # 줄 끝 빈 칸
            a = d[s * 2048:e * 2048]
            assert a[:2] == b'\x80\x00', (ldx, nm)
            hl = struct.unpack('>H', a[2:4])[0] + 4
            rate = struct.unpack('>I', a[8:12])[0]; n = struct.unpack('>I', a[12:16])[0]
            p = os.path.join(OUT, nm + '.adx'); open(p, 'wb').write(a)
            w = os.path.join(OUT, nm + '.wav')
            if not os.path.exists(w):
                subprocess.run([FFMPEG, '-v', 'error', '-y', '-i', p, '-ac', '1', '-ar', '16000', w], check=True)
            rows.append((nm, ldx, s, rate, n / rate))
    with open(os.path.join(OUT, 'clips.tsv'), 'w', encoding='utf-8') as f:
        f.write('클립\tLDX\t섹터\t주파수\t초\n')
        for r in rows: f.write('%s\t%s\t%d\t%d\t%.2f\n' % r)
    used = set(used_in_event())
    print('클립 %d개 · 합 %.0f초 · EVENT.DAT 가 부르는 것 %d(없는 이름 %d)' % (len(rows), sum(r[4] for r in rows),
          len(used & {r[0] for r in rows}), len(used - {r[0] for r in rows})))


def asr():
    import wave, numpy as np
    from faster_whisper import WhisperModel
    m = WhisperModel('large-v3', device='cuda', compute_type='float16')
    rows = [l.rstrip('\n').split('\t') for l in open(os.path.join(OUT, 'clips.tsv'), encoding='utf-8')][1:]
    with open(os.path.join(OUT, 'asr.tsv'), 'w', encoding='utf-8') as f:
        f.write('클립\t초\t받아쓰기\t받아쓰기(VAD 끔)\n')
        for nm, _, _, _, sec in rows:
            w = wave.open(os.path.join(OUT, nm + '.wav'))
            a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
            outs = []
            for vad in (True, False):
                segs, _ = m.transcribe(a, language='ja', beam_size=5, condition_on_previous_text=False, vad_filter=vad)
                outs.append(''.join(s.text for s in segs).strip())
            f.write('%s\t%s\t%s\t%s\n' % (nm, sec, outs[0], outs[1])); f.flush()
            print(nm, outs[1])


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    {'split': split, 'asr': asr}[sys.argv[1]]()
