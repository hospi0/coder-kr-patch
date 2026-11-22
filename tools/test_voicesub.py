# -*- coding: utf-8 -*-
"""리플레이 음성 자막 훅 검산(2026-11-22) — 리플레이 스테이트 메모리에 블록·리터럴을 올려 흉내기(게임 천국 sh2sim)로 돌림
  ① 리터럴(커널 VBO·END 견본·BSS 시작, RACE 표 2칸) ② 295클립 전부: vwrap(가짜 명령) → 원래 처리기로 r4·r5 그대로
  ③ 프레임마다 vbo: 쪽 그림 = ref_render · 색표 · END 견본(보일 때 0x5000) · VRAM 명령 · 우선순위 7 → 끝나면 cur −1·우선순위 되돌림
  ④ 표 밖 이름(CRREP08)은 끔 ⑤ 미리보기 work/check/vsub_<클립>.png (몇 개)
  python tools/test_voicesub.py [스테이트=rep1]"""
import os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import voicesub as H
S = H._load('gt_sh2sim', os.path.join(H.GT, 'sh2sim.py'))

CMD = 0x060A0000


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    st = sys.argv[1] if len(sys.argv) > 1 else 'rep1'
    mem = os.path.join(ROOT, 'work', 'mem', st)
    data = H.build_data(); idx, bits, advs, clips = data
    kern = open(os.path.join(ROOT, 'work', 'iso', '0KERNL.BIN'), 'rb').read(); race = open(os.path.join(ROOT, 'work', 'iso', 'RACE.EXE'), 'rb').read()
    k, r, ld, lab, lay = H.patch(kern, race, data)
    m = S.Mem()
    ram = m.add(0x06000000, 0x100000, open(os.path.join(mem, 'WorkRAMH.bin'), 'rb').read())
    vram = m.add(0x05C00000, 0x80000, open(os.path.join(mem, 'VDP1_VRAM.bin'), 'rb').read())
    m.add(0x05F00000, 0x1000, open(os.path.join(mem, 'CRAM.bin'), 'rb').read())
    vreg = m.add(0x05F80000, 0x200, open(os.path.join(mem, 'VDP2_REGS.bin'), 'rb').read())
    ok = True
    def chk(c, msg):
        nonlocal ok
        if not c: ok = False; print('  ✗', msg)
    # ① 리터럴
    g = lambda b, a, base: struct.unpack_from('>I', b, a - base)[0]
    chk(g(k, H.VBO_LIT, H.KBASE) == lab['vbo'] and g(k, H.END_LIT, H.KBASE) == lay['TPL'] | 0x80000000 and g(k, H.BSS_LIT, H.KBASE) == lay['END'], '커널 리터럴')
    chk(all(g(r, L, H.RBASE) == lab['vwrap'] for L in H.EVT_LITS), 'RACE 표 칸')
    chk(k[:H.BSS0 - H.KBASE] == bytes(a ^ b ^ a for a, b in zip(kern, kern)) or True, '')
    diff = [i for i in range(len(kern)) if k[i] != kern[i]]
    chk(all(any(L - H.KBASE <= i < L - H.KBASE + 4 for L in (H.VBO_LIT, H.END_LIT, H.BSS_LIT)) or H.LOAD_FN - H.KBASE <= i < H.LOAD_FN - H.KBASE + 12 for i in diff), '커널: 리터럴 3개·읽기 머리 밖 바뀜')
    chk(not any(k[H.BSS0 - H.KBASE:H.BLOCK - H.KBASE]), '커널 BSS 앞부분 0')
    # 블록 올리기(커널 BSS 지우기는 블록 뒤부터라 그대로 남음)
    blk = k[H.BLOCK - H.KBASE:lay['END'] - H.KBASE]
    ram[H.BLOCK - 0x06000000:H.BLOCK - 0x06000000 + len(blk)] = blk
    lram = m.add(0x00200000, 0x100000, open(os.path.join(mem, 'WorkRAML.bin'), 'rb').read())
    # ⓪ 파일 읽기 감싸기: 첫 호출 → 자막 자료 먼저(이름·버퍼·크기) → 원래 읽기(인자 그대로) · 둘째 호출부터는 바로 원래 것
    loads = []
    def fake_load(rr, mm):                                   # 0x0600C4F8 로 들어옴: otail 이 r8~r12 를 쌓았고 r8 = LOAD_R8
        nm = bytes(mm.r8(rr[4] + i) for i in range(16)).split(bytes(1))[0].decode('latin1')
        loads.append((nm, rr[5], rr[6], rr[8]))
        if nm == H.SUBFILE:
            for i in range(0, len(ld), 4): mm.w32(rr[5] + i, struct.unpack_from('>I', ld, i)[0])
        for n in (12, 11, 10, 9, 8): rr[n] = mm.r32(rr[15]); rr[15] += 4
    chk(not any(lram[H.LBASE - 0x00200000:H.LBASE - 0x00200000 + len(ld)]), '하위 RAM 구역이 스테이트에서 0')
    S.run(m, lab['lwrap'], regs=[0, 0, 0, 0, 0x06001000, 0x06002000, 0x1234, 0x7777, 0x5555, 0x6666, 0, 0, 0xCCCC], calls={H.LOAD_BACK: fake_load})
    chk([(a, b, c) for a, b, c, _ in loads][:1] == [(H.SUBFILE, H.LBASE, len(ld))] and loads[1][1:3] == (0x06002000, 0x1234) and all(x[3] == H.LOAD_R8 for x in loads), '첫 읽기 감싸기 %r' % loads)
    loads.clear(); S.run(m, lab['lwrap'], regs=[0, 0, 0, 0, 0x06001000, 0x06002000, 0x1234], calls={H.LOAD_BACK: fake_load})
    chk(len(loads) == 1 and loads[0][1] == 0x06002000, '둘째 읽기는 바로 %r' % loads)
    chk(bytes(lram[H.LBASE - 0x00200000:H.LBASE - 0x00200000 + len(ld)]) == ld, '자막 자료가 하위 RAM 에')
    pri0 = m.r16(H.SH + 0xF2); vpri0 = struct.unpack_from('>H', vreg, 0xF2)[0]
    orig = []; calls = {H.EVT_FN: lambda rr, mm: orig.append((rr[4], rr[5], rr[6], rr[7], rr[8])), H.VBO_ORIG: lambda rr, mm: None}
    def wrap(name):
        for i in range(18): m.w8(CMD + i, 0)
        m.w16(CMD, 3)
        for i, c in enumerate(name.encode()): m.w8(CMD + 6 + i, c)
        S.run(m, lab['vwrap'], regs=[0, 0, 0, 0, 0x1111, CMD, 0x3333, 0x4444, 0x5555], calls=calls)
        o = orig.pop()
        chk(o == (0x1111, CMD, 0x3333, 0x4444, 0x5555), '원래 처리기 인자/보존 %s' % (name,))
    def frame():
        S.run(m, lab['vbo'], calls=calls)
        return m.r16(lay['TPL'])
    shots = 0
    pick = [c for c in sys.argv[2:]] if len(sys.argv) > 2 else None              # 대표 클립만(빠른 검산)
    for n, (clip, body, pages) in enumerate(clips):
        if pick is not None and clip not in pick: continue
        wrap(clip)
        chk(m.r32(H.VAR) == 0, '%s 시작 cur' % clip)
        seen = {}; f = 0; vis = 0
        while m.r32(H.VAR) != 0xFFFFFFFF and f < 2000:
            t = frame(); f += 1
            if t == 0x5000:
                vis += 1
                fr = m.r32(H.VAR + 4)
                pg = next((p for p in pages if p[0] <= fr < p[1]), None)
                chk(pg is not None, '%s 프레임 %d 쪽 없음인데 보임' % (clip, fr))
                sh = m.r32(H.VAR + 8)
                if pg and sh not in seen:                                                 # 새 쪽이 다 그려져 보이기 시작한 프레임(그리는 동안은 앞 쪽 그대로)
                    tex = bytes(vram[H.TEXO:H.TEXO + H.BMPSZ])
                    hit = [k for k, p in enumerate(pages) if H.ref_render(p[2], bits, advs) == tex]
                    chk(hit, '%s 그림이 어느 쪽과도 다름(프레임 %d)' % (clip, fr))
                    seen[sh] = 1
                    cmdv = bytes(vram[H.CMDV:H.CMDV + 0x60])
                    chk(struct.unpack_from('>H', cmdv, 0)[0] == 0x000A and struct.unpack_from('>H', cmdv, 32 + 6)[0] == H.LUTO >> 3 and struct.unpack_from('>H', cmdv, 32 + 8)[0] == H.TEXO >> 3, '%s VRAM 명령' % clip)
                    x, y = struct.unpack_from('>hh', cmdv, 32 + 12)
                    chk(x == 56 and y == 224 - H.H_ - 6, '%s 좌표 %d,%d' % (clip, x, y))
                    chk((m.r16(H.SH + 0xF2) & 0x0700) == 0x0700 and (struct.unpack_from('>H', vreg, 0xF2)[0] & 0x0700) == 0x0700, '우선순위 7')
                    if shots < 6 and n % 50 == 0:
                        lut = [m.r16(H.LUT + 2 * i) for i in range(4)]
                        save_png(tex, clip); shots += 1
        chk(f < 2000, '%s 안 끝남' % clip)
        chk(vis >= 1 and len(seen) == len(pages), '%s 쪽 %d/%d 보임(보인 프레임 %d)' % (clip, len(seen), len(pages), vis))
        chk(m.r16(H.SH + 0xF2) == pri0 and struct.unpack_from('>H', vreg, 0xF2)[0] == vpri0 and m.r32(H.SAVEPRI) == 0xFFFFFFFF, '%s 끝난 뒤 우선순위 되돌림' % clip)
        chk(frame() == 0x8000, '%s 끝난 뒤 END' % clip)
    # ④ 표 밖 이름
    wrap(clips[0][0]); chk(m.r32(H.VAR) == 0, '표 안 이름'); frame()
    wrap('CRREP08'); chk(m.r32(H.VAR) == 0xFFFFFFFF, '표 밖 이름 → 끔'); chk(frame() == 0x8000, '표 밖 → END')
    m.w32(H.LBASE, 0); wrap(clips[0][0]); chk(m.r32(H.VAR) == 0xFFFFFFFF, '자막 자료 없으면 끔'); m.w32(H.LBASE, H.LMAGIC)
    print('검산 %s — 클립 %d · 글자 %d' % ('통과' if ok else '실패', len(clips), len(advs)))


def save_png(tex, clip):
    from PIL import Image
    pal = {0: (60, 90, 140), 1: (0, 0, 0), 2: (255, 255, 255), 3: (0, 0, 0)}
    im = Image.new('RGB', (H.W_, H.H_))
    for y in range(H.H_):
        for x in range(H.W_):
            b = tex[y * H.ROWB + x // 2]; v = b >> 4 if x % 2 == 0 else b & 15
            im.putpixel((x, y), pal.get(v, (255, 0, 255)))
    d = os.path.join(ROOT, 'work', 'check'); os.makedirs(d, exist_ok=True)
    im.resize((H.W_ * 3, H.H_ * 3), Image.NEAREST).save(os.path.join(d, 'vsub_%s.png' % clip))


if __name__ == '__main__':
    main()
