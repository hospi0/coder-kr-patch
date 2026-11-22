# -*- coding: utf-8 -*-
"""코드R 트랙1 빌드 (2026-11-22)
  전체 글꼴(tools/font.py: 한글 2350 + 자모 40 + 기호·가나 + 2수준 한자 일부)
  + 번역(tools/build_text.py) + 백업 오류 화면(tools/bup_kr.py) + SAVEMISS + 그림 글자(tools/gfx_kr.py)
  + 한글 이름 입력(tools/name_kr.py 입력판·화면 글 / tools/name_hook.py 조합 훅 = ADV.EXE 만, NAMEDIC = 음절 묶음 + 조합 코드)
python tools/build.py   → work/build/Code R (Japan) (Track 1).bin  (F: 설치는 하스피 허락 뒤 따로)"""
import os, sys, hashlib
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import gfx_kr, isopatch, font, name_kr, name_hook, build_text, bup_kr, voicesub
SRC = r'C:\claude\roms\ss\Code R (Japan)\Code R (Japan) (Track 1).bin'
DST = os.path.join(ROOT, 'work', 'build', 'Code R (Japan) (Track 1).bin')
ISO = os.path.join(ROOT, 'work', 'iso')


def rd(n): return open(os.path.join(ISO, n), 'rb').read()


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    D, F, have = font.build()
    files, warn = build_text.build(have)                                  # 번역(my files/tsv) — 비면 원문
    files['FONTDIC.FNT'] = D; files['FONT24.FNT'] = F
    files['BUP_ERR.BM8'] = bup_kr.build()[0]
    res, area = gfx_kr.build()
    for nm, (S, idx, b) in res.items(): files[nm + '.SCB'] = gfx_kr.scb_encode(S, idx, b)
    files['AREAOBJ.SPR'] = area
    nd, P = name_hook.blob()                                              # ★먼저 — 스텁이 쓰는 CODE_OFF 를 묶음 길이로 정함(2026-11-22)
    adv = name_kr.patch_exe(files.get('ADV.EXE') or rd('ADV.EXE')); adv, at = name_hook.apply_exe(adv); files['ADV.EXE'] = adv
    files['ADVE.EXE'] = name_kr.patch_exe(files.get('ADVE.EXE') or rd('ADVE.EXE'))             # ADVE 는 코드 배치가 달라 훅 없음(입력판만)
    assert len(nd) <= len(rd('NAMEDIC.FNT')); files['NAMEDIC.FNT'] = nd
    # 리플레이 음성 자막(tools/voicesub.py, 2026-11-22): 0KERNL.BIN 늘림(블록 0x06037800~) + RACE.EXE 처리기 표 2칸
    files['0KERNL.BIN'], files['RACE.EXE'], files[voicesub.SUBFILE], _, vlay = voicesub.patch(rd('0KERNL.BIN'), files.get('RACE.EXE') or rd('RACE.EXE'))
    files[voicesub.SUBFILE2] = vlay['LD2']                               # 자료 C(열쇠표·폭·글꼴·쪽 C) — 2026-11-22 자리 옮김
    print('음성 자막 상주 0x%08X~0x%08X · 자료 %s %d B' % (voicesub.BLOCK, vlay['END'], voicesub.SUBFILE, len(files[voicesub.SUBFILE])))
    for k, v in files.items():
        o = rd(k)
        if k not in ('NAMEDIC.FNT', 'ADV_CNDT.DAT', '0KERNL.BIN', voicesub.SUBFILE, voicesub.SUBFILE2) and not k.startswith('ADV_MG') and k != 'ADV_EVMG.DAT': assert len(o) == len(v), k
    print('조합 훅 스텁 ADV.EXE+%#x · NAMEDIC %d B(코드 %#x)' % (at, len(nd), name_hook.CODE_OFF))
    os.makedirs(os.path.dirname(DST), exist_ok=True)
    isopatch.patch(SRC, DST, files); isopatch.verify(DST, files)
    print('트랙1 MD5', hashlib.md5(open(DST, 'rb').read()).hexdigest())
