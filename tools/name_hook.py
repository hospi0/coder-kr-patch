# -*- coding: utf-8 -*-
"""조합형 한글 이름 입력 훅 (2026-11-22 코드R, 하스피 «글꼴 넉넉하니 조합형»)
원본 글자 넣기 = ADV.EXE 0x06063E54~: name[pos] = @R6 → 그 칸 다시 그림(0x06057ABC) → pos++ → pos>2 면 확인 함수(0x06063D38)·확인 모드.
훅: 0x06063E54 에 «NAMEDIC 버퍼 주소(@0x06071150)+0x190 으로 jmp» 스텁. 조합 코드·표는 NAMEDIC.FNT 안(이름 화면에서만 올라옴, 위치 독립).
  NAMEDIC 앞 400 B = 漢字 모드 50묶음 전부 빈칸(0,0) — 漢字 모드는 안 씀.
규칙 = tools/jamo.py combine(기준). 대상 칸 = FULL·pos==2 면 2, 아니면 LAST==pos-1 인 LAST. 합치면 그 칸만 고쳐 다시 그림.
받침 넘김(N)은 다음 칸이 있을 때만. 다 찬 상태에서 안 합쳐지는 글자 → 원래 확인 경로(0x06063E8A, r1=3, r10=&pos).
python tools/name_hook.py test   → 흉내기로 조합기 전수 대조 + 입력 순서 시험"""
import os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import sh2asm, jamo

HOOK = 0x06063E54
CONFIRM = 0x06063E8A
EPILOGUE = 0x06063EBC
NAME = 0x06049ED4
POS = 0x0607139C
NDPTR = 0x06071150
DRAW = 0x06057ABC
DRAWBASE = 0x0607122C
DRAWFLAG = 0x0603E5B8
CODE_OFF = 0x4C0     # blob() 가 묶음 길이로 다시 정함

ASM = r'''
entry:
  mov.l r11,@-r15
  mov.l r12,@-r15
  mov.l r13,@-r15
  mov r1,r8
  mov.w @r6,r11
  extu.w r11,r11
  mov.l #0x%(NAME)08x,r9
  mov.l #0x%(POS)08x,r10
  mov.l #%(V_LAST)d,r0
  mov.b @(r0,r8),r12
  mov.w @r10,r13
  mov.l #0xA9A1,r1
  mov r11,r2
  sub r1,r2
  mov #40,r1
  cmp/hs r1,r2
  bt append_ch
  mov.l #%(V_FULL)d,r0
  mov.b @(r0,r8),r1
  tst r1,r1
  bt not_full
  mov #2,r1
  cmp/eq r1,r13
  bf not_full
  mov #2,r12
  bra have_tgt
  nop
not_full:
  cmp/pz r12
  bf append_ch
  mov r13,r1
  add #-1,r1
  cmp/eq r12,r1
  bf append_ch
have_tgt:
  mov r12,r0
  add r0,r0
  mov.w @(r0,r9),r4
  extu.w r4,r4
  mov r11,r5
  bsr combine
  nop
  tst r0,r0
  bt append_ch
  tst r1,r1
  bt no_n
  mov #2,r2
  cmp/ge r2,r12
  bt append_ch
no_n:
  mov r0,r3
  mov r12,r0
  add r0,r0
  mov.w r3,@(r0,r9)
  mov r1,r11
  mov r12,r4
  bsr redraw
  nop
  tst r11,r11
  bt done
  mov r12,r13
  add #1,r13
  bra put
  nop
append_ch:
  mov.w @r10,r13
  mov.l #%(V_FULL)d,r0
  mov.b @(r0,r8),r1
  tst r1,r1
  bt put
  mov #2,r1
  cmp/eq r1,r13
  bt confirm
put:
  mov #2,r1
  cmp/gt r1,r13
  bt confirm
  mov r13,r0
  add r0,r0
  mov.w r11,@(r0,r9)
  mov r13,r4
  bsr redraw
  nop
  mov.l #%(V_LAST)d,r0
  mov.b r13,@(r0,r8)
  mov #2,r1
  cmp/eq r1,r13
  bt set_full
  mov.l #%(V_FULL)d,r0
  mov #0,r1
  mov.b r1,@(r0,r8)
  add #1,r13
  mov.w r13,@r10
  bra done
  nop
set_full:
  mov.l #%(V_FULL)d,r0
  mov #1,r1
  mov.b r1,@(r0,r8)
  mov.w r13,@r10
done:
  mov.l @r15+,r13
  mov.l @r15+,r12
  mov.l @r15+,r11
  mov.l #0x%(EPILOGUE)08x,r0
  jmp @r0
  nop
confirm:
  mov.l @r15+,r13
  mov.l @r15+,r12
  mov.l @r15+,r11
  mov.l #0x%(POS)08x,r10
  mov #3,r1
  mov.l #0x%(CONFIRM)08x,r0
  jmp @r0
  nop

redraw:
  sts.l pr,@-r15
  mov.l r4,@-r15
  mov.l #0x%(DRAWFLAG)08x,r1
  mov.b @r1,r2
  mov.l r2,@-r15
  mov #0,r2
  mov.b r2,@r1
  mov.l @(4,r15),r4
  mov r4,r5
  add r5,r5
  add r9,r5
  mov r4,r1
  shll2 r1
  shll r1
  mov r1,r2
  shll r2
  add r2,r1
  mov.l #0x%(DRAWBASE)08x,r2
  mov.l @r2,r4
  add r1,r4
  mov #72,r6
  mov.l #0x%(DRAW)08x,r0
  jsr @r0
  nop
  mov.l @r15+,r2
  mov.l #0x%(DRAWFLAG)08x,r1
  mov.b r2,@r1
  add #4,r15
  lds.l @r15+,pr
  rts
  nop

combine:
  sts.l pr,@-r15
  mov.l #0xA9A1,r1
  mov r5,r2
  sub r1,r2
  mov.l #%(V_K)d,r0
  mov.b r2,@(r0,r8)
  mov r4,r3
  sub r1,r3
  mov #40,r6
  cmp/hs r6,r3
  bt c_hangul
  mov #19,r6
  cmp/hs r6,r3
  bt c_fail
  cmp/hs r6,r2
  bf c_fail
  mov r3,r4
  mov r2,r5
  add #-19,r5
  mov #0,r6
  bsr syl
  nop
  mov #0,r1
  bra c_ret
  nop
c_hangul:
  mov r4,r3
  shlr8 r3
  add #-128,r3
  add #-48,r3
  mov #25,r6
  cmp/hs r6,r3
  bt c_fail
  extu.b r4,r7
  add #-128,r7
  add #-33,r7
  mov #94,r6
  cmp/hs r6,r7
  bt c_fail
  mov r3,r0
  shll r0
  mov r0,r1
  shll r0
  add r0,r1
  shll r0
  add r0,r1
  shll r0
  add r0,r1
  shll2 r0
  add r0,r1
  add r7,r1
  mov.l #2350,r6
  cmp/hs r6,r1
  bt c_fail
  add r1,r1
  mov.l #%(T_KEY)d,r0
  add r8,r0
  mov.w @(r0,r1),r3
  extu.w r3,r3
  mov r3,r4
  shlr8 r4
  shlr2 r4
  mov r3,r5
  shlr2 r5
  shlr2 r5
  shlr r5
  mov #31,r1
  and r1,r5
  mov r3,r6
  and r1,r6
  mov.l #%(V_K)d,r0
  mov.b @(r0,r8),r2
  extu.b r2,r2
  mov #19,r1
  cmp/hs r1,r2
  bt c_vowel
  tst r6,r6
  bf c_comp
  mov.l #%(T_JOC)d,r0
  add r8,r0
  mov.b @(r0,r2),r6
  extu.b r6,r6
  tst r6,r6
  bt c_fail
  bsr syl
  nop
  mov #0,r1
  bra c_ret
  nop
c_comp:
  mov.l #%(T_COMP)d,r7
  add r8,r7
  mov #%(N_COMP)d,r3
c_comp_l:
  mov.b @r7,r1
  cmp/eq r1,r6
  bf c_comp_n
  mov.b @(1,r7),r0
  cmp/eq r0,r2
  bf c_comp_n
  mov.b @(2,r7),r0
  extu.b r0,r6
  bsr syl
  nop
  mov #0,r1
  bra c_ret
  nop
c_comp_n:
  add #3,r7
  dt r3
  bf c_comp_l
  bra c_fail
  nop
c_vowel:
  add #-19,r2
  tst r6,r6
  bf c_split
  mov.l #%(T_VCOMP)d,r7
  add r8,r7
  mov #%(N_VCOMP)d,r3
c_v_l:
  mov.b @r7,r1
  cmp/eq r1,r5
  bf c_v_n
  mov.b @(1,r7),r0
  cmp/eq r0,r2
  bf c_v_n
  mov.b @(2,r7),r0
  extu.b r0,r5
  mov #0,r6
  bsr syl
  nop
  mov #0,r1
  bra c_ret
  nop
c_v_n:
  add #3,r7
  dt r3
  bf c_v_l
  bra c_fail
  nop
c_split:
  mov.l #%(V_V)d,r0
  mov.b r2,@(r0,r8)
  mov r6,r0
  add r0,r0
  mov.l #%(T_SPLIT)d,r1
  add r8,r1
  add r0,r1
  mov.b @r1,r6
  extu.b r6,r6
  mov.b @(1,r1),r0
  mov r0,r2
  mov.l #%(V_C2)d,r0
  mov.b r2,@(r0,r8)
  bsr syl
  nop
  tst r0,r0
  bt c_fail
  mov.l #%(V_P)d,r1
  add r8,r1
  mov.w r0,@r1
  mov.l #%(V_C2)d,r0
  mov.b @(r0,r8),r4
  extu.b r4,r4
  mov.l #%(V_V)d,r0
  mov.b @(r0,r8),r5
  extu.b r5,r5
  mov #0,r6
  bsr syl
  nop
  tst r0,r0
  bt c_fail
  mov r0,r1
  mov.l #%(V_P)d,r2
  add r8,r2
  mov.w @r2,r0
  extu.w r0,r0
  bra c_ret
  nop
c_fail:
  mov #0,r0
  mov #0,r1
c_ret:
  lds.l @r15+,pr
  rts
  nop

syl:
  mov r4,r7
  shll8 r7
  shll2 r7
  mov r5,r0
  shll2 r0
  shll2 r0
  shll r0
  or r0,r7
  or r6,r7
  mov #0,r1
  mov.l #2350,r2
  mov.l #%(T_KEY)d,r6
  add r8,r6
s_loop:
  cmp/hs r2,r1
  bt s_none
  mov r1,r3
  add r2,r3
  shlr r3
  mov r3,r4
  add r4,r4
  mov r6,r0
  mov.w @(r0,r4),r5
  extu.w r5,r5
  cmp/eq r7,r5
  bt s_found
  cmp/hs r7,r5
  bt s_hi
  mov r3,r1
  add #1,r1
  bra s_loop
  nop
s_hi:
  mov r3,r2
  bra s_loop
  nop
s_found:
  mov #0,r0
  mov #94,r4
s_div:
  cmp/hs r4,r3
  bf s_divd
  sub r4,r3
  add #1,r0
  bra s_div
  nop
s_divd:
  add #-80,r0
  extu.b r0,r0
  shll8 r0
  add #-95,r3
  extu.b r3,r3
  or r3,r0
  rts
  nop
s_none:
  mov #0,r0
  rts
  nop
.pool
'''


def far(text):
    """bt/bf 를 «반대 조건으로 건너뛰기 + bra» 로 펴서 거리 제한(±256 B) 없앰"""
    out = []; n = 0
    for ln in text.split(chr(10)):
        q = ln.strip().split()
        if len(q) == 2 and q[0] in ('bt', 'bf'):
            n += 1; inv = 'bf' if q[0] == 'bt' else 'bt'
            out += ['  %s _f%d' % (inv, n), '  bra %s' % q[1], '  nop', '_f%d:' % n]
        else: out.append(ln)
    return chr(10).join(out)


def tables():
    key = b''.join(struct.pack('>H', k) for k in jamo.KEY)
    joc = bytes(jamo.JONG_OF_CHO) + b'\0'
    comp = b''.join(bytes(x) for x in jamo.COMP)
    vcomp = b''.join(bytes(x) for x in jamo.VCOMP)
    split = b''.join(bytes(x) for x in jamo.SPLIT)
    return key, joc, comp, vcomp, split


def blob(prefix=None):
    """NAMEDIC.FNT 새 내용 = 음절 묶음(name_kr.groups) + 코드 + 표 + 변수 — 코드 자리 = 묶음 뒤 4바이트 정렬"""
    global CODE_OFF
    if prefix is None:
        import name_kr; prefix = name_kr.groups()
    CODE_OFF = (len(prefix) + 3) & ~3
    key, joc, comp, vcomp, split = tables()
    P = dict(NAME=NAME, POS=POS, CONFIRM=CONFIRM, EPILOGUE=EPILOGUE, DRAW=DRAW, DRAWBASE=DRAWBASE, DRAWFLAG=DRAWFLAG,
             N_COMP=len(jamo.COMP), N_VCOMP=len(jamo.VCOMP))
    for _ in range(3):                                   # 표 위치(코드 길이에 따름) 맞을 때까지
        names = ['T_KEY', 'T_JOC', 'T_COMP', 'T_VCOMP', 'T_SPLIT', 'V_LAST', 'V_FULL', 'V_K', 'V_V', 'V_C2', 'V_P']
        for n in names: P.setdefault(n, 0)
        code = sh2asm.assemble(far(ASM % P), 0)
        o = (len(code) + 3) & ~3; lay = {}
        for n, d in (('T_KEY', key), ('T_JOC', joc), ('T_COMP', comp), ('T_VCOMP', vcomp), ('T_SPLIT', split)):
            lay[n] = o; o += len(d); o = (o + 1) & ~1
        for n in ('V_LAST', 'V_FULL', 'V_K', 'V_V', 'V_C2'): lay[n] = o; o += 1
        o = (o + 1) & ~1; lay['V_P'] = o; o += 2
        if all(P[k] == v for k, v in lay.items()): break
        P.update(lay)
    out = bytearray(prefix + b'\0' * (CODE_OFF - len(prefix))) + code
    def put(off, d):
        nonlocal out
        a = CODE_OFF + off
        if len(out) < a + len(d): out += b'\0' * (a + len(d) - len(out))
        out[a:a + len(d)] = d
    put(P['T_KEY'], key); put(P['T_JOC'], joc); put(P['T_COMP'], comp); put(P['T_VCOMP'], vcomp); put(P['T_SPLIT'], split)
    put(P['V_LAST'], b'\xff'); put(P['V_FULL'], b'\0'); put(P['V_P'] + 2, b'\0' * 2)
    return bytes(out), P


def stub():
    """0x06063E54: r1 = @NDPTR + CODE_OFF → jmp @r1 (리터럴은 바로 뒤, 원래 몸통 자리 — 확인 경로 0x06063E8A 앞에서 끝)"""
    asm = '''
      mov.l #0x%08x,r1
      mov.l @r1,r1
      mov.l #%d,r0
      add r0,r1
      jmp @r1
      nop
    ''' % (NDPTR, CODE_OFF)
    b = sh2asm.assemble(asm, HOOK)
    assert HOOK + len(b) <= CONFIRM, hex(HOOK + len(b))
    return b


def apply_exe(exe, base=0x06050000):
    """ADV.EXE/ADVE.EXE — 원래 몸통 머리(0x06063E54~)를 확인하고 스텁으로. ADVE 는 같은 코드가 다른 자리일 수 있어 내용으로 찾음."""
    b = bytearray(exe)
    a = open(os.path.join(ROOT, 'work', 'iso', 'ADV.EXE'), 'rb').read()
    sig = a[HOOK - 0x06050000:CONFIRM - 0x06050000]
    i = b.find(sig); assert i >= 0 and b.find(sig, i + 1) < 0, '훅 자리 못 찾음/여럿'
    s = stub()
    # 스텁의 리터럴 주소(NDPTR) 는 ADVE 에서도 같은가? → NDPTR 를 쓰는 NAMEDIC 로더 리터럴로 확인
    ndl = struct.pack('>I', NDPTR); assert ndl in bytes(b), 'NAMEDIC 포인터 변수가 이 실행 파일에 없음'
    b[i:i + len(s)] = s
    return bytes(b), i


# ---------------- 시험 ----------------
def _sim_env(bl):
    import sh2sim
    mem = sh2sim.Mem()
    mem.add(0x00200000, 0x100000)
    mem.add(0x06000000, 0x100000)
    BASE = 0x002A3970
    for k, v in enumerate(bl): mem.w8(BASE + k, v)
    mem.w32(NDPTR, BASE)
    return sh2sim, mem, BASE


def test():
    sys.stdout.reconfigure(encoding='utf-8')
    bl, P = blob(); print('NAMEDIC 새 크기', len(bl), '원본', os.path.getsize(os.path.join(ROOT, 'work', 'iso', 'NAMEDIC.FNT')))
    sim, mem, BASE = _sim_env(bl)
    entry = BASE + CODE_OFF
    # 1) combine 전수(앞 글자 = 자모 40 + 한글 2350, 입력 = 자모 40)
    bad = 0; n = 0
    prevs = [jamo.JAMO0 + k for k in range(40)] + [jamo.code_of_idx(i) for i in range(2350)]
    import random; random.seed(1)
    sample = prevs[:40] + random.sample(prevs[40:], 700)
    for pv in sample:
        for k in range(40):
            ch = jamo.JAMO0 + k
            r, _ = sim.run(mem, entry + P['_combine'] if '_combine' in P else None, regs=None) if False else (None, 0)
            regs = [0] * 16; regs[4] = pv; regs[5] = ch; regs[8] = entry; regs[15] = 0x060FF000
            rr, _ = sim.run(mem, entry + COMB_OFF[0], regs=regs)
            got = (rr[0] & 0xFFFF, rr[1] & 0xFFFF)
            exp = jamo.combine(pv, ch) or (0, 0)
            n += 1
            if got != exp:
                bad += 1
                if bad < 10: print('다름', hex(pv), hex(ch), [hex(x) for x in got], [hex(x) for x in exp])
    print('combine 대조 %d건, 다름 %d' % (n, bad))
    # 2) 입력 순서 — 훅 진입부터(그리기·확인은 흉내)
    drawn = []
    def draw(r, mem): drawn.append(r[4])
    calls = {DRAW: draw}
    def typing(seq):
        for a in range(6): mem.w16(NAME + a * 2, 0)
        mem.w16(POS, 0); mem.w8(BASE + CODE_OFF + P['V_LAST'], 0xFF); mem.w8(BASE + CODE_OFF + P['V_FULL'], 0)
        mem.w32(DRAWBASE, 0x06080000)
        res = []
        for x in seq:
            mem.w16(0x060A0000, jamo.JAMO0 + jamo.JAMO.index(x))
            regs = [0] * 16; regs[6] = 0x060A0000; regs[15] = 0x060FF000; regs[14] = 0x060FF000
            # 훅 스텁 대신 바로 코드로(r1 = 코드 주소)
            regs[1] = entry
            class Confirm(Exception): pass
            def cf(r, m): raise Confirm()
            c = dict(calls); c[CONFIRM] = cf
            try:
                rr, _ = sim.run(mem, entry, regs=regs, calls=c, stop=EPILOGUE, limit=200000)   # jmp EPILOGUE = 정상 끝
                assert rr[15] == 0x060FF000, '스택 어긋남 %x' % rr[15]
            except Confirm:
                res.append('확인')
        nm = [mem.r16(NAME + a * 2) for a in range(3)]
        def s(c):
            if not c: return '_'
            if jamo.JAMO0 <= c < jamo.JAMO0 + 40: return jamo.JAMO[c - jamo.JAMO0]
            return bytes([c >> 8, c & 255]).decode('euc_kr')
        return ''.join(s(c) for c in nm), res, mem.r16(POS)
    for seq, exp in (('ㅊㅓㄹㅅㅜ', '철수_'), ('ㄱㅣㅁㅊㅓㄹㅅㅜ', '김철수'), ('ㅎㅏㄴㄱㅡㄹ', '한글_'), ('ㄷㅏㄹㄱ', '닭__'),
                     ('ㄷㅏㄹㄱㅏ', '달가_'), ('ㄱㅗㅏ', '과__'), ('ㅇㅢㅅㅏ', '의사_'), ('ㄱㅣㅁㅊㅓㄹㅅㅜㄴ', '김철순'),
                     ('ㄱㅣㅁㅊㅓㄹㅅㅜㄴㅏ', '김철순')):
        got, res, pos = typing(seq)
        print('OK ' if got == exp else '다름', seq, '→', got, '(기대', exp + ')', res, 'pos', pos)


COMB_OFF = [0]


if __name__ == '__main__':
    if sys.argv[1:] == ['test']:
        bl, P = blob()
        txt = ASM % P
        def asm_labels(text, base=0):          # sh2asm 은 라벨을 안 돌려줌 → 같은 규칙으로 combine 위치만 셈(.pool 은 끝이라 영향 없음)
            import re as _re
            lines = [l.split(';')[0].strip() for l in text.split('\n') if l.split(';')[0].strip()]
            pc = base; L = {}
            for ln in lines:
                m = _re.match(r'^(\w+):$', ln)
                if m: L[m.group(1)] = pc; continue
                if ln.startswith('.long'): pc += 4; continue
                if ln == '.pool': continue
                pc += 2
            return L
        COMB_OFF[0] = asm_labels(far(txt))['combine']
        test()
