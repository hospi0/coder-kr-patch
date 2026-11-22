# -*- coding: utf-8 -*-
r"""코드R 리플레이(이벤트 대본) 음성 자막 훅 (2026-11-22, 게임 천국 tools/voicesub.py 를 옮김 — SGL 2.12)
  ■ 게임
    · 커널 0KERNL.BIN(램 0x06004000, 부팅 때 BSS 0x06036C10~0x0604C094 지움 — 시작 리터럴 0x06004208)
      SGL VBlank-OUT 처리기 0x060329BA(등록 리터럴 0x06032BB8) · DMA 표 마지막 END 견본 0x06034C7E(리터럴 0x06034C98 = 0x86034C7E)
      SGL VDP2 레지스터 사본 0x060FFCC0(TVMD +0 · SPCTL +0xE0 · CRAOFB +0xE6 · RAMCTL +0x0E · PRISB +0xF2)
    · RACE.EXE(0x06050000) 대본 해석기 0x06060B68: 명령 18 B {u16 종류, …, +6 이름} → 처리기 표[종류](r5 = 명령).
      종류 3 = LDX 음성 재생 0x0606173C(이름 «M_F_151»). 표 칸 0x060738DC(EVENT.DAT)·0x06073CF8(RACEEVT.DAT).
  ■ 훅: 표 칸 → vwrap(이름 → 열쇠 → 쪽 목록, 없으면 끔) → 원래 처리기
        VBO 리터럴 → vbo: sub(프레임 +1 · 쪽 찾아 그림 · END 견본을 «건너뛰고 VRAM 자막 명령»으로) → 원래 처리기
        END 견본 리터럴 → 우리 견본 TPL(보일 때 0x5000 건너뛰기 → CMDV, 아니면 END 0x8000)
  ■ 모양(하스피 2026-11-22 «검은 배경 말고 흰 글자 + 검은 테두리» = 게임 천국 빌드 36): 투명 바탕 · 1px 8방향 테두리 · 갈무리9
  ■ 그림: VDP1 VRAM 0x67900(240×32 4비트) · 색표 0x68800 · 명령 0x68820 — 리플레이·포즈 스테이트 6장 모두 0 인 4 KB(0x67900~0x68900)
  ■ 자리: BLOCK 0x06037800(커널 BSS 안, 스테이트 31장 모두 0 · 0x0603D300 까지) → 0KERNL.BIN 을 늘려 싣고 BSS 지우기 시작을 블록 뒤로.
          COMP(그림 만들 곳) = 0x0604C100(커널 BSS 끝 뒤, 31장 모두 0 · 자막 중에만 씀)
  ■ 자료: work/voice/voice_ko.tsv(클립·번역) + work/voice/clips.tsv(길이)
  python tools/voicesub.py   → 크기 보고 · 검산은 tools/test_voicesub.py"""
import importlib.util, os, re, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
GT = r'C:\claude\project\gametengoku-kr-patch\tools'


def _load(name, path):
    sp = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


A = _load('gt_sh2asm', os.path.join(GT, 'sh2asm.py')).A
bdf = _load('gt_bdf', os.path.join(GT, 'bdf.py'))

KBASE = 0x06004000; RBASE = 0x06050000
BSS0 = 0x06036C10; BSS_LIT = 0x06004208
BLOCK = 0x06037800; BLOCK_MAX = 0x0603D300
VAR = BLOCK + 0x10                                  # 0 cur · 4 frame · 8 shown · 12 쪽 목록 주소
SAVEPRI = BLOCK + 0x0C                              # 올리기 전 PRISB(0xFFFFFFFF = 안 올림)
LOCC = BLOCK + 0x20; SPR = BLOCK + 0x40; ENDC = BLOCK + 0x60
CODE = BLOCK + 0x80
VBO_ORIG = 0x060329BA; VBO_LIT = 0x06032BB8
END_LIT = 0x06034C98; END_ORIG = 0x86034C7E
EVT_FN = 0x0606173C; EVT_LITS = (0x060738DC, 0x06073CF8)
ADX_FN = 0x0600DEAC; ADX_KLITS = (0x0600DD00, 0x0600E124); ADX_RLITS = (0x06061AAC,)   # 커널 ADX 파일 재생(r4 = «CRADX05.ADX»)
ADX_KIND = {'CRADX': 0, 'CREVE': 1, 'CRREP': 2}
BKIND = '12345678KMSY'
RPFX = ['AK', 'FU', 'KA', 'KI', 'KO', 'MA', 'SZ', 'YO', 'Z1', 'Z2', 'Z3']   # 레이스 중 라이벌 «XX0B?_NN» 사람                              # 배틀 시작 대화 클립 «B?000_NN» 종류
SH = 0x060FFCC0
CRAM = 0x25F00000
W_, H_ = 240, 32; ROWB = W_ // 2; BMPSZ = ROWB * H_
TEXO = 0x67900; LUTO = TEXO + BMPSZ; CMDV = LUTO + 0x20
assert LUTO == 0x68800 and CMDV + 0x60 <= 0x68900
TEX = 0x25C00000 + TEXO; LUT = 0x25C00000 + LUTO
COMP = 0x06040700                                  # 그림 만들 곳(커널 BSS 안, 31장 모두 0 · 자막 중에만 씀)
BLOCK2 = 0x0604C100; BLOCK2_MAX = 0x06050000   # (옛 2구역 — 디스크 읽기로 바꾼 뒤 안 씀)
HEAP_END = 0x002F4000; HEAP_END_LIT = 0x06004280; LFLOOR = 0x002F0000   # 하위 RAM 힙(0x200000~0x2F4000, 커널 시작 0x06004124 에서 한 번 초기화) 끝 인자
LBASE = LFLOOR; LMAX = HEAP_END                     # 자료 A(쪽) = 힙 끝을 LBASE 로 낮춰 힙이 안 쓰게 한 자리. ★옛 0x2DE300 은 힙 안이라 스토리 리플레이에서 덮여 크래시(2026-11-22)
BLOCK_SAFE = 0x0603B000                             # 블록 쪽 B 한도 — 0x06037800~0x0603B800 = SGL 작업 버퍼 64 B×256(원본 31장 모두 0), 위 2 KB 는 남김
CBASE = 0x002FC800; CMAX = 0x00300000               # 자료 C(열쇠표·폭·글꼴) — 음성 이름 목록(0x2F4000~0x2FC19C, ALLLDX.HDC 33,180 B) 위, 스테이트 37장 모두 0
CMAGIC = 0x43525343                                 # 'CRSC'
SUBFILE2 = 'CDR_BIB.TXT'                            # 자료 C 를 담는 파일(원래 = 디스크 서지 설명문, 게임이 안 읽음)
GESC = 0xF0                                         # 글자 번호: < 0xF0 이면 1바이트, 아니면 2바이트(0xF0|번호>>8, 번호&0xFF) — 글꼴은 많이 쓰는 순
LMAGIC = 0x43525344                                 # 'CRSD'
SUBFILE = 'CDR_ABS.TXT'                             # 자막 자료를 담는 파일(원래 = 디스크 설명문, 게임이 안 읽음)
LOAD_FN = 0x0600C4EC; LOAD_R8 = 0x060225EA          # 커널 파일 읽기(r4 = 이름, r5 = 버퍼, r6 = 크기) · 머리 리터럴 0x0600C60C 값
LOAD_BACK = 0x0600C4F8       # 쪽·폭·글꼴(커널 BSS 끝 0x0604C094 뒤 · 실행 파일 0x06050000 앞, 31장 모두 0 — 커널 파일을 여기까지 늘림)
GROWS = 12; FROW0, FROWS = 1, 10; FONT_B = FROWS + 2
GALMURI = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri9.bdf'
NANUM = r'C:\claude\utils\font\nanum-gothic\NanumGothicBold.ttf'
MAXW = W_ - 8; FPS = 60
LY = (2, 17)                                        # 두 줄 y(한 줄이면 아래 줄 자리)
DELAY = 8                                           # 명령 → 소리까지(프레임) — 실기 보고 맞출 것
TAIL = 0.6                                          # 말 끝난 뒤 더 보임(초)
GPF = 3                                             # 프레임마다 그리는 글자 수
PUNCT_SP = re.compile(r'([,.!?:;)\]}\'"~、。，．！？：；）］｝」』】〉》”’…‥・·～〜♪♥]) (?! )')
TYPES = [(14, 4, 0x7FF), (13, 8, 0x7FF), (14, 2, 0x7FF), (13, 4, 0x7FF), (13, 4, 0x3FF), (12, 8, 0x7FF), (12, 8, 0x3FF), (12, 8, 0x1FF)]


class S(A):
    """A + 중간 리터럴 풀(ltorg) — 게임 천국 voicesub.S 그대로"""
    def __init__(s, base): super().__init__(base); s.pools = []; s.cur = []
    def ld(s, rn, val): s.fix.append((len(s.c), 'lit', (rn, val, len(s.pools)))); s.c.append(0); s.cur.append(val)
    def ltorg(s):
        if (s.base + 2 * len(s.c)) % 4: s.c.append(0x0009)
        vals = list(dict.fromkeys(s.cur)); s.pools.append((len(s.c), vals)); s.c.extend([0, 0] * len(vals)); s.cur = []
    def build(s):
        if s.cur: s.ltorg()
        def val(v): return s.lab[v] if isinstance(v, str) else v
        for k, (at, vals) in enumerate(s.pools):
            for j, v in enumerate(vals):
                x = val(v) & 0xFFFFFFFF; s.c[at + 2 * j] = x >> 16; s.c[at + 2 * j + 1] = x & 0xFFFF
        for i, op, a in s.fix:
            pc = s.base + 2 * i
            if op == 'lit':
                rn, v, pk = a; at, vals = s.pools[pk]
                la = s.base + 2 * at + 4 * vals.index(v)
                d = la - ((pc & ~3) + 4); assert d >= 0 and d % 4 == 0 and d // 4 < 256, (hex(pc), d); s.c[i] = 0xD000 | (rn << 8) | d // 4
            else:
                d = (s.lab[a] - (pc + 4)) // 2
                if op in ('bra', 'bsr'): assert -2048 <= d < 2048; s.c[i] = (0xA000 if op == 'bra' else 0xB000) | (d & 0xFFF)
                else: assert -128 <= d < 128, (op, a, d); s.c[i] = {'bt': 0x8900, 'bf': 0x8B00, 'bts': 0x8D00, 'bfs': 0x8F00}[op] | (d & 0xFF)
        return b''.join(struct.pack('>H', x) for x in s.c)

    def mov(s, m, n): s.w(0x6003 | n << 8 | m << 4)
    def movi(s, i, n): s.w(0xE000 | n << 8 | (i & 0xFF))
    def addi(s, i, n): s.w(0x7000 | n << 8 | (i & 0xFF))
    def add(s, m, n): s.w(0x300C | n << 8 | m << 4)
    def sub(s, m, n): s.w(0x3008 | n << 8 | m << 4)
    def ldb(s, m, n): s.w(0x6000 | n << 8 | m << 4)
    def ldw(s, m, n): s.w(0x6001 | n << 8 | m << 4)
    def ldl(s, m, n): s.w(0x6002 | n << 8 | m << 4)
    def ldwp(s, m, n): s.w(0x6005 | n << 8 | m << 4)
    def ldbp(s, m, n): s.w(0x6004 | n << 8 | m << 4)
    def ldbx(s, m, n): s.w(0x000C | n << 8 | m << 4)
    def ldwx(s, m, n): s.w(0x000D | n << 8 | m << 4)
    def stb(s, m, n): s.w(0x2000 | n << 8 | m << 4)
    def stw(s, m, n): s.w(0x2001 | n << 8 | m << 4)
    def stl(s, m, n): s.w(0x2002 | n << 8 | m << 4)
    def ldld(s, d, m, n): assert d % 4 == 0 and d < 64; s.w(0x5000 | n << 8 | m << 4 | d // 4)
    def stld(s, m, d, n): assert d % 4 == 0 and d < 64; s.w(0x1000 | n << 8 | m << 4 | d // 4)
    def ldwd(s, d, m): assert d % 2 == 0 and d < 32; s.w(0x8500 | m << 4 | d // 2)
    def bfar(s, op, n):                                                            # 먼 조건 분기 = 반대 조건으로 건너뛰기 + bra
        s._fc = getattr(s, '_fc', 0) + 1; t = '_far%d' % s._fc
        s.br('bf' if op == 'bt' else 'bt', t); s.br('bra', n); s.nop(); s.L(t)
    def ldbd(s, d, m): assert d < 16; s.w(0x8400 | m << 4 | d)                    # mov.b @(d,Rm),R0
    def extub(s, m, n): s.w(0x600C | n << 8 | m << 4)
    def extuw(s, m, n): s.w(0x600D | n << 8 | m << 4)
    def cmpeq(s, m, n): s.w(0x3000 | n << 8 | m << 4)
    def cmphs(s, m, n): s.w(0x3002 | n << 8 | m << 4)
    def cmphi(s, m, n): s.w(0x3006 | n << 8 | m << 4)
    def cmpgt(s, m, n): s.w(0x3007 | n << 8 | m << 4)
    def cmpge(s, m, n): s.w(0x3003 | n << 8 | m << 4)
    def cmppz(s, n): s.w(0x4011 | n << 8)
    def tst(s, m, n): s.w(0x2008 | n << 8 | m << 4)
    def and_(s, m, n): s.w(0x2009 | n << 8 | m << 4)
    def or_(s, m, n): s.w(0x200B | n << 8 | m << 4)
    def andi(s, i): s.w(0xC900 | i)
    def tsti(s, i): s.w(0xC800 | i)
    def cmpeqi(s, i): s.w(0x8800 | (i & 0xFF))
    def shll(s, n): s.w(0x4000 | n << 8)
    def shlr(s, n): s.w(0x4001 | n << 8)
    def shll2(s, n): s.w(0x4008 | n << 8)
    def shlr2(s, n): s.w(0x4009 | n << 8)
    def shll8(s, n): s.w(0x4018 | n << 8)
    def shlr8(s, n): s.w(0x4019 | n << 8)
    def shll16(s, n): s.w(0x4028 | n << 8)
    def dt(s, n): s.w(0x4010 | n << 8)
    def push(s, n): s.w(0x2F06 | n << 4)
    def pop(s, n): s.w(0x60F6 | n << 8)
    def pushpr(s): s.w(0x4F22)
    def poppr(s): s.w(0x4F26)
    def jsr(s, m): s.w(0x400B | m << 8)
    def jmp(s, m): s.w(0x402B | m << 8)
    def rts(s): s.w(0x000B)
    def nop(s): s.w(0x0009)


def clip_key(name):
    """«M_F_151» → (F 면 0x4000) | (글자−A)<<10 | 번호 — vwrap 과 같은 셈 · «CRADX05» → 0x8000 | 종류<<8 | 번호 — awrap"""
    m = re.fullmatch(r'([A-Z0-9]{2})0B([012K])_(\d\d)', name)
    if m: return 0x8000 | '012K'.index(m.group(2)) << 11 | RPFX.index(m.group(1)) << 7 | int(m.group(3))
    m = re.fullmatch(r'B([1-8KMSY])000_(\d\d)', name)
    if m: return 0xC000 | BKIND.index(m.group(1)) << 8 | int(m.group(2))
    m = re.fullmatch(r'(CRADX|CREVE|CRREP)(\d\d)', name)
    if m: return 0x8000 | ADX_KIND[m.group(1)] << 8 | int(m.group(2))
    m = re.fullmatch(r'([MF])_([A-O])_(\d{3})', name); assert m, name
    return (0x4000 if m.group(1) == 'F' else 0) | (ord(m.group(2)) - 65) << 10 | int(m.group(3))


def code(lay):
    a = S(CODE)
    # ── vwrap(r4 = 해석기, r5 = 명령): 이름(+6) → 열쇠 → 표에서 찾으면 cur 0·쪽 목록, 없으면 cur −1 → 원래 처리기(r4~r7 그대로)
    a.L('vwrap'); a.pushpr()
    for n in (4, 5, 6, 7, 8): a.push(n)
    a.ld(1, lay['LBASE']); a.ldl(1, 0); a.ld(2, LMAGIC); a.cmpeq(2, 0); a.bfar('bf', 'vnf')   # 자막 자료가 안 읽혔으면 자막 없이
    a.ld(1, CBASE); a.ldl(1, 0); a.ld(2, CMAGIC); a.cmpeq(2, 0); a.bfar('bf', 'vnf')
    a.mov(5, 1); a.addi(6, 1)
    a.ldbd(1, 1); a.cmpeqi(ord('_')); a.br('bt', 'vsp')                                 # «M_F_151» 관중
    a.ldbd(3, 1); a.cmpeqi(ord('B')); a.br('bt', 'vrv')                                 # «MA0B0_19» 레이스 중 라이벌
    a.ldbp(1, 0); a.cmpeqi(ord('B')); a.br('bt', 'vb'); a.br('bra', 'vnf'); a.nop()   # «B1000_05» 배틀 시작 대화
    a.L('vsp')
    a.ldbp(1, 0); a.movi(0, 8); a.cmpeqi(ord('M')); a.br('bt', 'vm')
    a.cmpeqi(ord('F')); a.bfar('bf', 'vnf'); a.ld(8, 0x4000)
    a.L('vm'); a.ldbp(1, 0); a.cmpeqi(ord('_')); a.bfar('bf', 'vnf')
    a.ldbp(1, 0); a.addi(-65, 0); a.mov(0, 2); a.movi(15, 3); a.cmphi(3, 2); a.bfar('bt', 'vnf')   # 글자 A~O
    a.shll2(2); a.shll8(2); a.or_(2, 8)                                                   # <<10
    a.ldbp(1, 0); a.cmpeqi(ord('_')); a.bfar('bf', 'vnf')
    a.movi(0, 7); a.movi(3, 6)
    a.L('vd'); a.ldbp(1, 0); a.addi(-48, 0); a.mov(0, 2); a.movi(9, 3); a.cmphi(3, 2); a.bfar('bt', 'vnf')
    a.mov(7, 0); a.shll(0); a.shll2(7); a.shll(7); a.add(0, 7); a.add(2, 7)                # n = n×10 + d
    a.dt(6); a.br('bf', 'vd')
    a.or_(7, 8)                                                                           # r8 = 열쇠
    a.br('bra', 'vfind'); a.nop()
    # «B1000_05»·«BK000_03» (배틀 시작 대화) → 0xC000 | 종류<<8 | 번호 (종류 = '12345678KMSY' 안 위치)
    a.L('vb'); a.ldbp(1, 0); a.mov(0, 2); a.ld(3, lay['BKIND']); a.movi(12, 6); a.ld(8, 0xC000)
    a.L('vbk'); a.ldbp(3, 0); a.cmpeq(2, 0); a.br('bt', 'vbf')
    a.ld(0, 0x100); a.add(0, 8); a.dt(6); a.br('bf', 'vbk'); a.br('bra', 'vnfx'); a.nop()
    a.L('vbf'); a.movi(3, 6)
    a.L('vbz'); a.ldbp(1, 0); a.cmpeqi(ord('0')); a.bfar('bf', 'vnf'); a.dt(6); a.br('bf', 'vbz')
    a.ldbp(1, 0); a.cmpeqi(ord('_')); a.bfar('bf', 'vnf')
    a.movi(0, 7); a.movi(2, 6)
    a.L('vbd'); a.ldbp(1, 0); a.addi(-48, 0); a.mov(0, 2); a.movi(9, 3); a.cmphi(3, 2); a.bfar('bt', 'vnf')
    a.mov(7, 0); a.shll(0); a.shll2(7); a.shll(7); a.add(0, 7); a.add(2, 7)
    a.dt(6); a.br('bf', 'vbd')
    a.or_(7, 8)
    a.br('bra', 'vfind'); a.nop()
    a.L('vnfx'); a.br('bra', 'vnf'); a.nop()                                          # 먼 분기 디딤돌
    # «MA0B0_19»·«KA0BK_03» → 0x8000 | 종류(0 1 2 K)<<11 | 사람<<7 | 번호  (사람 = RPFX 안 위치)
    a.L('vrv'); a.ldbp(1, 0); a.extub(0, 2); a.shll8(2); a.ldbp(1, 0); a.extub(0, 0); a.or_(0, 2)   # r2 = 앞 두 글자
    a.ld(3, lay['RPFX']); a.movi(len(RPFX), 6); a.ld(8, 0x8000)
    a.L('vrk'); a.ldwp(3, 0); a.extuw(0, 0); a.cmpeq(2, 0); a.br('bt', 'vrf')
    a.addi(-128, 8); a.ld(0, 0x100); a.add(0, 8); a.dt(6); a.br('bf', 'vrk'); a.br('bra', 'vnfx'); a.nop()  # +0x80
    a.L('vrf'); a.addi(2, 1)                                                              # «0B» 건너뜀
    a.ldbp(1, 0); a.ld(2, 0x0000); a.cmpeqi(ord('0')); a.br('bt', 'vrs')
    a.ld(2, 0x0800); a.cmpeqi(ord('1')); a.br('bt', 'vrs')
    a.ld(2, 0x1000); a.cmpeqi(ord('2')); a.br('bt', 'vrs')
    a.ld(2, 0x1800); a.cmpeqi(ord('K')); a.bfar('bf', 'vnf')
    a.L('vrs'); a.or_(2, 8)
    a.ldbp(1, 0); a.cmpeqi(ord('_')); a.bfar('bf', 'vnf')
    a.movi(0, 7); a.movi(2, 6)
    a.L('vrd'); a.ldbp(1, 0); a.addi(-48, 0); a.mov(0, 2); a.movi(9, 3); a.cmphi(3, 2); a.bfar('bt', 'vnf')
    a.mov(7, 0); a.shll(0); a.shll2(7); a.shll(7); a.add(0, 7); a.add(2, 7)
    a.dt(6); a.br('bf', 'vrd')
    a.or_(7, 8)
    a.L('vfind'); a.ld(1, lay['KTAB']); a.ld(2, lay['NK'])
    a.L('vl2'); a.tst(2, 2); a.bfar('bt', 'vnf')
    a.ldw(1, 0); a.extuw(0, 0); a.cmpeq(8, 0); a.br('bt', 'vf')
    a.addi(4, 1); a.addi(-1, 2); a.br('bra', 'vl2'); a.nop()
    a.L('vf'); a.br('bsr', 'kdec'); a.nop()                                               # r8 = 쪽 목록
    a.ld(1, VAR); a.movi(-1, 0); a.stl(0, 1)                                              # 고르는 동안 그리지 않게
    a.br('bsr', 'pal'); a.nop()
    a.ld(1, lay['ST']); a.movi(0, 0); a.stl(0, 1)
    a.ld(1, VAR); a.stld(8, 12, 1); a.movi(-DELAY, 0); a.stld(0, 4, 1); a.movi(0, 0); a.stld(0, 8, 1); a.stl(0, 1)
    a.br('bra', 'vo'); a.nop()
    a.L('vnf'); a.ld(1, VAR); a.movi(-1, 0); a.stl(0, 1); a.movi(0, 0); a.stld(0, 8, 1); a.ld(1, lay['ST']); a.stl(0, 1)
    a.L('vo')
    for n in (8, 7, 6, 5, 4): a.pop(n)
    a.poppr(); a.ld(0, EVT_FN); a.jmp(0); a.nop()
    a.ltorg()
    # ── lwrap: 커널 파일 읽기 머리(0x0600C4EC) 스텁 → 처음 한 번 자막 자료(CDR_ABS.TXT → 하위 RAM) 먼저 읽고 → 원래 읽기
    a.L('lwrap'); a.ld(1, lay['LFLAG']); a.ldl(1, 0); a.tst(0, 0); a.br('bf', 'otail')
    a.movi(1, 0); a.stl(0, 1)
    a.pushpr()
    for n in (4, 5, 6, 7): a.push(n)
    a.ld(4, lay['LNAME']); a.ld(5, lay['LBASE']); a.ld(6, lay['LSIZE']); a.br('bsr', 'otail'); a.nop()
    a.ld(4, lay['LNAME2']); a.ld(5, CBASE); a.ld(6, lay['CSIZE']); a.br('bsr', 'otail'); a.nop()
    for n in (7, 6, 5, 4): a.pop(n)
    a.poppr()
    a.L('otail')                                                                          # 원래 머리(덮은 부분) 그대로 하고 0x0600C4F8 로
    for n in (8, 9, 10, 11): a.push(n)
    a.ld(8, LOAD_R8); a.push(12); a.ld(0, LOAD_BACK); a.jmp(0); a.nop()
    a.ltorg()
    # ── awrap(r4 = 파일 이름 «CRADX05.ADX»): 표에 있으면 cur 0·쪽 목록(없으면 그대로 — 배경음악이 자막을 끄지 않게) → 원래 함수(r4~r7 그대로)
    a.L('awrap'); a.pushpr()
    for n in (4, 5, 6, 7, 8): a.push(n)
    a.mov(4, 1)
    a.ldbp(1, 0); a.cmpeqi(ord('C')); a.br('bf', 'ao')
    a.ldbp(1, 0); a.cmpeqi(ord('R')); a.br('bf', 'ao')
    a.ldbp(1, 0); a.ld(8, 0x8000); a.cmpeqi(ord('A')); a.br('bt', 'ak')
    a.ld(8, 0x8100); a.cmpeqi(ord('E')); a.br('bt', 'ak')
    a.ld(8, 0x8200); a.cmpeqi(ord('R')); a.br('bf', 'ao')
    a.L('ak'); a.addi(2, 1); a.movi(0, 7); a.movi(2, 6)
    a.L('ad'); a.ldbp(1, 0); a.addi(-48, 0); a.mov(0, 2); a.movi(9, 3); a.cmphi(3, 2); a.br('bt', 'ao')
    a.mov(7, 0); a.shll(0); a.shll2(7); a.shll(7); a.add(0, 7); a.add(2, 7)
    a.dt(6); a.br('bf', 'ad')
    a.ldbp(1, 0); a.cmpeqi(ord('.')); a.br('bf', 'ao')
    a.or_(7, 8)
    a.ld(1, lay['KTAB']); a.ld(2, lay['NK'])
    a.L('al'); a.tst(2, 2); a.br('bt', 'ao')
    a.ldw(1, 0); a.extuw(0, 0); a.cmpeq(8, 0); a.br('bt', 'af')
    a.addi(4, 1); a.addi(-1, 2); a.br('bra', 'al'); a.nop()
    a.L('af'); a.br('bsr', 'kdec'); a.nop()
    a.ld(1, VAR); a.movi(-1, 0); a.stl(0, 1)
    a.br('bsr', 'pal'); a.nop()
    a.ld(1, lay['ST']); a.movi(0, 0); a.stl(0, 1)
    a.ld(1, VAR); a.stld(8, 12, 1); a.movi(-DELAY, 0); a.stld(0, 4, 1); a.movi(0, 0); a.stld(0, 8, 1); a.stl(0, 1)
    a.L('ao')
    for n in (8, 7, 6, 5, 4): a.pop(n)
    a.poppr(); a.ld(0, ADX_FN); a.jmp(0); a.nop()
    a.ltorg()
    # ── kdec(r1 = 열쇠표 칸): 값 v = @(2,r1) → r8 = 지역 바탕(v>>14: 0 PA · 1 PB · 2 PC) + (v&0x3FFF)*2
    a.L('kdec'); a.mov(1, 0); a.addi(2, 0); a.ldw(0, 8); a.extuw(8, 8)
    a.ld(2, lay['PA']); a.ld(3, 0x4000); a.tst(3, 8); a.br('bt', 'kd1'); a.ld(2, lay['PB'])
    a.L('kd1'); a.ld(3, 0x8000); a.tst(3, 8); a.br('bt', 'kda'); a.ld(2, lay['PC'])
    a.L('kda'); a.ld(3, 0x3FFF); a.and_(3, 8); a.shll(8); a.add(2, 8); a.rts(); a.nop()
    a.ltorg()
    # ── vbo: sub → 원래 처리기
    a.L('vbo'); a.pushpr(); a.br('bsr', 'sub'); a.nop(); a.ld(0, VBO_ORIG); a.jsr(0); a.nop(); a.poppr(); a.rts(); a.nop()
    a.ltorg()
    # ── sub
    a.L('sub'); a.ld(1, lay['TPL']); a.ld(0, 0x8000); a.stw(0, 1); a.ld(6, VAR)
    a.ldld(0, 6, 7); a.cmppz(7); a.br('bt', 'sub1')
    a.L('unpri'); a.ld(1, SAVEPRI); a.ldl(1, 0); a.cmppz(0); a.br('bf', 'uret')          # 올려 둔 우선순위 되돌림
    a.ld(2, SH + 0xF2); a.stw(0, 2); a.ld(2, 0x25F800F2); a.stw(0, 2); a.movi(-1, 0); a.stl(0, 1)
    a.L('uret'); a.rts(); a.nop()
    a.L('sub1')
    a.ldld(4, 6, 3); a.addi(1, 3); a.stld(3, 4, 6)                                       # r3 = 프레임
    a.ldld(12, 6, 1); a.tst(1, 1); a.br('bt', 'kill')
    a.ldwp(1, 5); a.extuw(5, 5)                                                           # r5 = 쪽 수, r1 = 첫 쪽
    a.cmppz(3); a.br('bf', 'gap')                                                        # 명령 뒤 DELAY 동안(프레임 < 0)
    a.L('pl'); a.tst(5, 5); a.br('bt', 'kill')
    a.ldwd(2, 1); a.cmpgt(3, 0); a.br('bt', 'found')                                       # 쪽 머리 = 크기·끝 프레임·줄 수
    a.ldwd(0, 1); a.extuw(0, 0); a.add(0, 1); a.addi(-1, 5); a.br('bra', 'pl'); a.nop()
    a.L('found')
    a.ldld(8, 6, 0); a.cmpeq(1, 0); a.br('bt', 'patch')
    a.ld(2, lay['ST']); a.ldl(2, 0); a.cmpeq(1, 0); a.br('bt', 'step')
    a.pushpr(); a.push(1); a.mov(1, 4); a.br('bsr', 'rstart'); a.nop(); a.pop(1); a.poppr()
    a.L('step'); a.ld(2, lay['ST']); a.movi(GPF, 0); a.stld(0, 24, 2)
    a.pushpr(); a.push(1); a.br('bsr', 'rstep'); a.nop(); a.pop(1); a.poppr()
    a.ld(6, VAR); a.tst(0, 0); a.br('bt', 'nd')
    a.stld(1, 8, 6); a.ld(2, lay['ST']); a.movi(0, 0); a.stl(0, 2)
    a.ld(1, COMP); a.ld(2, TEX); a.ld(5, BMPSZ // 4)
    a.L('cp'); a.ldl(1, 0); a.stl(0, 2); a.addi(4, 1); a.addi(4, 2); a.dt(5); a.br('bf', 'cp')
    a.br('bra', 'patch'); a.nop()
    a.L('nd'); a.ldld(8, 6, 0); a.tst(0, 0); a.br('bt', 'ret')
    a.L('patch'); a.ld(1, VAR); a.ldld(4, 1, 0); a.tsti(3); a.br('bf', 'nopal')
    a.pushpr(); a.br('bsr', 'pal'); a.nop(); a.poppr()
    a.L('nopal')
    # 화면 아래 가운데 절대 좌표(TVMD HRESO 비트0 → 352 폭 +16, VRES → 224/240/256)
    a.ld(1, SH); a.ldw(1, 0); a.mov(0, 3); a.andi(1); a.shll2(0); a.shll2(0); a.addi((320 - W_) // 2, 0)
    a.ld(1, SPR + 12); a.stw(0, 1)
    a.mov(3, 0); a.shlr2(0); a.shlr2(0); a.andi(3); a.shll2(0); a.shll2(0); a.ld(2, 224 - H_ - 6); a.add(2, 0)
    a.ld(1, SPR + 14); a.stw(0, 1)
    a.ld(1, LOCC); a.ld(2, 0x25C00000 + CMDV); a.movi(24, 5)
    a.L('cc'); a.ldl(1, 0); a.stl(0, 2); a.addi(4, 1); a.addi(4, 2); a.dt(5); a.br('bf', 'cc')
    a.ld(1, lay['TPL']); a.ld(0, 0x5000); a.stw(0, 1)
    # 자막 PR 레지스터 3(PRISB 윗바이트) 우선순위 = 7 — 처음 올릴 때 원래 값 저장(끝나면 unpri 가 되돌림)
    a.ld(1, SAVEPRI); a.ldl(1, 0); a.cmppz(0); a.br('bt', 'psv')
    a.ld(2, SH + 0xF2); a.ldw(2, 0); a.extuw(0, 0); a.stl(0, 1)
    a.L('psv'); a.ld(1, SH + 0xF2); a.ldw(1, 0); a.ld(2, 0xF8FF); a.and_(2, 0); a.ld(2, 0x0700); a.or_(2, 0); a.stw(0, 1)
    a.ld(1, 0x25F800F2); a.stw(0, 1)
    a.L('ret'); a.rts(); a.nop()
    a.L('gap'); a.movi(0, 0); a.stld(0, 8, 6); a.br('bra', 'ret'); a.nop()
    a.L('kill'); a.movi(-1, 0); a.stld(0, 0, 6); a.movi(0, 0); a.stld(0, 8, 6); a.ld(1, lay['ST']); a.stl(0, 1)
    a.br('bra', 'unpri'); a.nop()
    a.ltorg()

    # ── pal: 장면 레지스터·CRAM → 색 참조표(4 칸). r8~r13 보존 (게임 천국 그대로)
    a.L('pal')
    for n in (8, 9, 10, 11, 12, 13): a.push(n)
    a.ld(1, SH + 0xE0); a.ldw(1, 0); a.andi(7); a.mov(0, 2)
    a.ld(1, lay['TSH']); a.ldbx(1, 8); a.extub(8, 8)
    a.ld(1, lay['TCN']); a.mov(2, 0); a.ldbx(1, 9); a.extub(9, 9)
    a.ld(1, lay['TDC']); a.mov(2, 0); a.shll(0); a.ldwx(1, 5); a.extuw(5, 5)
    a.mov(9, 10); a.addi(-1, 10); a.movi(3, 0); a.cmpgt(0, 10); a.br('bf', 'pdone'); a.mov(0, 10)
    a.L('pdone'); a.tst(8, 8); a.br('bt', 'shd')
    a.L('sl'); a.shll(10); a.dt(8); a.br('bf', 'sl')
    a.L('shd')
    a.ld(1, SH + 0xE6); a.ldw(1, 0); a.shlr2(0); a.shlr2(0); a.andi(7); a.shll8(0); a.mov(0, 6)
    a.ld(1, SH + 0x0E); a.ldw(1, 0); a.extuw(0, 0); a.shlr8(0); a.shlr2(0); a.shlr2(0); a.andi(3)
    a.ld(7, 2047); a.tst(0, 0); a.br('bf', 'nm'); a.ld(7, 1023)
    a.L('nm'); a.movi(1, 4); a.ld(8, 0x7FFF); a.movi(1, 9); a.movi(-1, 11); a.movi(1, 12); a.ld(13, CRAM)
    a.L('sc'); a.cmphi(5, 4); a.br('bt', 'scd')
    a.mov(6, 0); a.add(4, 0); a.and_(7, 0); a.shll(0); a.add(13, 0); a.ldw(0, 1); a.extuw(1, 1)
    a.mov(1, 0); a.andi(31); a.mov(0, 2)
    a.mov(1, 0); a.shlr2(0); a.shlr2(0); a.shlr(0); a.andi(31); a.add(0, 2)
    a.mov(1, 0); a.shlr8(0); a.shlr2(0); a.andi(31); a.add(0, 2)
    a.cmpgt(2, 8); a.br('bf', 'nmin'); a.mov(2, 8); a.mov(4, 9)
    a.L('nmin'); a.cmpgt(11, 2); a.br('bf', 'nmax'); a.mov(2, 11); a.mov(4, 12)
    a.L('nmax'); a.addi(1, 4); a.br('bra', 'sc'); a.nop()
    a.L('scd'); a.ld(1, LUT)
    a.movi(0, 0); a.stw(0, 1)
    a.mov(10, 0); a.or_(9, 0); a.mov(1, 2); a.addi(2, 2); a.stw(0, 2); a.addi(4, 2); a.stw(0, 2)
    a.mov(10, 0); a.or_(12, 0); a.mov(1, 2); a.addi(4, 2); a.stw(0, 2)
    for n in (13, 12, 11, 10, 9, 8): a.pop(n)
    a.rts(); a.nop()
    a.ltorg()

    # ── rstart(r4 = 쪽): 그림 버퍼 투명(0)으로 지움 · 이어 그리기 상태 시작. r8~r14 보존
    a.L('rstart')
    for n in (8, 9, 10, 11, 12, 13, 14): a.push(n)
    a.mov(4, 14)
    a.ld(1, COMP); a.ld(2, BMPSZ // 4); a.movi(0, 0)
    a.L('rc'); a.stl(0, 1); a.addi(4, 1); a.dt(2); a.br('bf', 'rc')
    a.ld(1, lay['ST']); a.stl(14, 1)
    a.mov(14, 0); a.addi(6, 0); a.stld(0, 4, 1)                                           # 쪽 머리 6 B(크기·끝·줄 수)
    a.ldwd(4, 14); a.extuw(0, 0); a.stld(0, 8, 1)
    a.movi(0, 0); a.stld(0, 12, 1)
    for n in (14, 13, 12, 11, 10, 9, 8): a.pop(n)
    a.rts(); a.nop()
    a.ltorg()
    # ── rstep: 이번 프레임 몫(ST+24 글자)만 그림 → r0 = 1 다 그림 / 0 아직. r8~r14 보존
    a.L('rstep')
    for n in (8, 9, 10, 11, 12, 13, 14): a.push(n)
    a.pushpr()
    a.ld(1, lay['ST']); a.ldld(4, 1, 12); a.ldld(12, 1, 13); a.ldld(16, 1, 8)
    a.L('s0'); a.tst(13, 13); a.br('bf', 'shg')
    a.ld(1, lay['ST']); a.ldld(8, 1, 0); a.tst(0, 0); a.br('bt', 'sdone')
    a.addi(-1, 0); a.stld(0, 8, 1)
    a.mov(0, 2); a.ldbp(12, 8); a.extub(8, 8); a.ldbp(12, 13); a.extub(13, 13)           # 줄 머리 = x·글자 수(바이트)
    a.movi(LY[1], 0); a.tst(2, 2); a.br('bt', 'sy'); a.movi(LY[0], 0)                       # y = 마지막 줄이면 아래 줄 자리
    a.L('sy'); a.stld(0, 20, 1)
    a.br('bra', 's0'); a.nop()
    a.L('shg'); a.ld(1, lay['ST']); a.ldld(24, 1, 0); a.tst(0, 0); a.br('bt', 'spause')
    a.addi(-1, 0); a.stld(0, 24, 1)
    a.ldld(20, 1, 9)
    a.br('bsr', 'gidx'); a.nop()                                                          # r0 = 글자 번호(1·2바이트)
    a.mov(0, 1); a.shll2(1); a.shll2(0); a.shll(0); a.add(1, 0)                           # 번호×12
    a.ld(10, lay['FONT']); a.add(0, 10); a.movi(FROWS, 11); a.addi(FROW0, 9)
    a.mov(10, 0); a.addi(FROWS, 0); a.ldw(0, 0); a.shll16(0); a.ld(1, lay['ST']); a.stld(0, 28, 1)
    a.L('grow'); a.ldbp(10, 14); a.extub(14, 14); a.shll16(14); a.shll8(14)
    a.ld(1, lay['ST']); a.ldld(28, 1, 0); a.shll(0); a.stld(0, 28, 1); a.br('bf', 'gc8')
    a.ld(0, 0x00800000); a.or_(0, 14)
    a.L('gc8'); a.tst(14, 14); a.br('bt', 'gnext')
    a.mov(8, 4)
    a.L('gcol'); a.shll(14); a.br('bf', 'gskip')
    a.mov(4, 0); a.push(0); a.movi(3, 6); a.movi(1, 7)
    a.addi(-1, 4); a.mov(9, 5); a.addi(-1, 5); a.br('bsr', 'pix'); a.nop()
    a.addi(1, 4); a.br('bsr', 'pix'); a.nop()
    a.addi(1, 4); a.br('bsr', 'pix'); a.nop()
    a.mov(9, 5); a.br('bsr', 'pix'); a.nop()
    a.addi(-2, 4); a.br('bsr', 'pix'); a.nop()
    a.mov(9, 5); a.addi(1, 5); a.br('bsr', 'pix'); a.nop()
    a.addi(1, 4); a.br('bsr', 'pix'); a.nop()
    a.addi(1, 4); a.br('bsr', 'pix'); a.nop()
    a.pop(4); a.mov(9, 5); a.movi(2, 6); a.movi(0, 7); a.br('bsr', 'pix'); a.nop()
    a.L('gskip'); a.addi(1, 4); a.tst(14, 14); a.br('bf', 'gcol')
    a.L('gnext'); a.addi(1, 9); a.dt(11); a.br('bf', 'grow')
    a.br('bsr', 'gidx'); a.nop(); a.mov(1, 3)                                             # r0 = 번호, r3 = 바이트 수
    a.ld(1, lay['ADV']); a.ldbx(1, 2); a.extub(2, 2); a.add(2, 8)                          # 폭 1바이트
    a.add(3, 12); a.addi(-1, 13)
    a.br('bra', 's0'); a.nop()
    a.L('spause'); a.stld(12, 4, 1); a.stld(13, 12, 1); a.stld(8, 16, 1); a.movi(0, 0); a.br('bra', 'sret'); a.nop()
    a.L('sdone'); a.movi(1, 0)
    a.L('sret'); a.poppr()
    for n in (14, 13, 12, 11, 10, 9, 8): a.pop(n)
    a.rts(); a.nop()
    a.ltorg()
    a.L('gidx'); a.ldb(12, 0); a.extub(0, 0); a.mov(0, 1); a.shlr2(1); a.shlr2(1); a.movi(15, 2); a.cmpeq(2, 1)
    a.br('bf', 'g1'); a.andi(0x0F); a.shll8(0); a.mov(12, 1); a.addi(1, 1); a.ldb(1, 1); a.extub(1, 1); a.or_(1, 0)
    a.movi(2, 1); a.rts(); a.nop()
    a.L('g1'); a.movi(1, 1); a.rts(); a.nop()
    a.L('pix'); a.ld(0, W_); a.cmphs(0, 4); a.br('bt', 'pret'); a.movi(H_, 0); a.cmphs(0, 5); a.br('bt', 'pret')
    assert ROWB == 120
    a.mov(5, 0); a.shll(0); a.shll2(0); a.shll2(0); a.shll2(0)                              # r0 = y×128
    a.mov(5, 1); a.shll(1); a.shll2(1); a.sub(1, 0)                                         # r0 = y×128 − y×8 = y×120
    a.mov(4, 1); a.shlr(1); a.add(1, 0); a.ld(2, COMP); a.add(0, 2)
    a.ldb(2, 1); a.extub(1, 1); a.mov(4, 0); a.tsti(1); a.br('bf', 'podd')
    a.mov(1, 3); a.shlr2(3); a.shlr2(3)
    a.tst(7, 7); a.br('bt', 'pe1'); a.movi(0, 0); a.cmpeq(0, 3); a.br('bf', 'pret')
    a.L('pe1'); a.mov(1, 0); a.andi(0x0F); a.mov(6, 3); a.shll2(3); a.shll2(3); a.or_(3, 0); a.stb(0, 2); a.rts(); a.nop()
    a.L('podd'); a.mov(1, 0); a.andi(0x0F); a.mov(0, 3)
    a.tst(7, 7); a.br('bt', 'po1'); a.movi(0, 0); a.cmpeq(0, 3); a.br('bf', 'pret')
    a.L('po1'); a.mov(1, 0); a.andi(0xF0); a.or_(6, 0); a.stb(0, 2)
    a.L('pret'); a.rts(); a.nop()
    return a


# ───────── 자료 ─────────
def build_font(chars, order=None):
    """갈무리9 비트맵(한글 잉크 윗선 정렬) — 없는 글자만 나눔고딕 1비트 (게임 천국 그대로)"""
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np
    g = bdf.Font(GALMURI)
    ys = [y for c in '가각힣맑앙' for x, y in g.draw(c)[0]]
    top, bot = min(ys), max(ys); off = -top + max(0, (GROWS - (bot - top + 1)) // 2)
    order = order or sorted(chars); idx = {c: i for i, c in enumerate(order)}
    bits, advs, miss = [], [], []
    for c in order:
        rows = [0] * GROWS
        if ord(c) in g.g:
            pts, w = g.draw(c)
            for x, y in pts:
                yy = y + off
                if 0 <= yy < GROWS and 0 <= x < 16: rows[yy] |= 0x8000 >> x
            adv = 4 if c == ' ' else max(1, min(16, w))
        else:
            fb = ImageFont.truetype(NANUM, 56); im = Image.new('L', (64, 64), 0)
            ImageDraw.Draw(im).text((0, -fb.getbbox('가')[1]), c, font=fb, fill=255)
            cov = np.array(im.resize((16, 16), Image.BOX), float) / 255
            for y in range(GROWS):
                rows[y] = sum(0x8000 >> x for x in range(16) if cov[y, x] > 0.45)
            adv = max(1, min(16, int(round(ImageFont.truetype(NANUM, 14).getlength(c))))); miss.append(c)
        bits.append(b''.join(struct.pack('>H', r) for r in rows)); advs.append(adv)
    if miss: print('  갈무리9 에 없는 글자(나눔으로):', ''.join(miss))
    return idx, bits, advs


def wrap(t, W, maxw):
    out = []; cur = ''
    for w in t.split(' '):
        cand = (cur + ' ' + w) if cur else w
        if W(cand) <= maxw: cur = cand
        else:
            assert cur, ('낱말 하나가 폭 넘침', w); out.append(cur); cur = w
    if cur: out.append(cur)
    return out


def rows():
    """[(클립, 길이 초, 번역)] — voice_ko.tsv 순서(대본 순서)"""
    dur = {}
    for cp in ('clips.tsv', os.path.join('bt', 'clips.tsv'), os.path.join('rv', 'clips.tsv')):                      # 리플레이 관중 + 배틀 시작 대화(EVT_B*.LDX)
        for l in list(open(os.path.join(ROOT, 'work', 'voice', cp), encoding='utf-8'))[1:]:
            dur[l.split('\t')[0]] = float(l.rstrip('\n').split('\t')[4])
    lines = []
    for tv in ('voice_ko.tsv', 'voice_ko_battle.tsv', 'voice_ko_rival1.tsv', 'voice_ko_rival2.tsv', 'voice_ko_story.tsv'):   # story = 스토리 리플레이 해설 78(2026-11-22)
        lines += list(open(os.path.join(ROOT, 'work', 'voice', tv), encoding='utf-8'))[1:]
    out = []
    for ln in lines:
        p = (ln.rstrip('\n').split('\t') + [''])[:3]
        ko = PUNCT_SP.sub(r'\1', p[1].strip())
        if not ko: continue
        assert not re.search(r'[぀-ヿ一-鿿]', ko), ('가나·한자 남음', p[0], ko)
        out.append((p[0], dur[p[0]], ko))
    return out


def build_data():
    """→ (글자 번호, 글꼴, 폭, [(클립, 쪽 목록 바이트, 쪽들)])"""
    rs = rows()
    import collections
    freq = collections.Counter(''.join(ko for *_, ko in rs)); freq[' '] += 0
    order = sorted(freq, key=lambda c: (-freq[c], c))                                     # 많이 쓰는 글자 먼저(앞 0xF0 자 = 1바이트)
    idx, bits, advs = build_font(set(order), order)
    W = lambda s: sum(advs[idx[c]] for c in s)
    out = []
    for clip, d, ko in rs:
        t0, t1 = 0.0, d; end = t1 + TAIL
        ls = wrap(ko, W, MAXW); grp = [ls[k:k + 2] for k in range(0, len(ls), 2)]
        tot = sum(len(''.join(g)) for g in grp); t = t0; pages = []
        for k, g in enumerate(grp):
            b = end if k == len(grp) - 1 else t + (t1 - t0) * len(''.join(g)) / tot
            pages.append((int(t * FPS), max(int(b * FPS), int(t * FPS) + 1), g)); t = b
        body = struct.pack('>H', len(pages)); pp = []
        for f0, f1, g in pages:
            ys = LY if len(g) == 2 else LY[1:]
            lines = [((W_ - W(l)) // 2, y, [idx[c] for c in l]) for l, y in zip(g, ys)]
            pb = struct.pack('>2H', f1, len(lines))                                           # 쪽 머리 = 크기·끝·줄 수(6 B), 시작 = 앞 쪽 끝
            for x, y, gl in lines:
                gb = b''.join(bytes([k]) if k < GESC else bytes([GESC | k >> 8, k & 0xFF]) for k in gl)
                assert 0 <= x < 256 and len(gl) < 256
                pb += bytes([x, len(gl)]) + gb                                               # 줄 머리 = x·글자 수, y 는 줄 순서
            pb += b'\0' * (len(pb) & 1)                                                       # 쪽은 짝수 자리
            pb = struct.pack('>H', 2 + len(pb)) + pb
            body += pb; pp.append((f0, f1, lines))
        out.append((clip, body, pp))
    return idx, bits, advs, out


def layout(nfont, nk, plen_b, asize=0x800, lbase=HEAP_END - 0x800, plen_c=0):
    """상주 블록 = 코드·표 + 쪽 B(자료 A 에 안 들어간 것) · 자료 A(하위 RAM 0x2F0000) = 머리 16 B + 쪽 A · 자료 C(0x2FC800) = 머리 16 B + 열쇠표 4 B 칸 + 폭 1 B + 글꼴"""
    names = ('KTAB', 'NK', 'TPL', 'ST', 'TSH', 'TCN', 'TDC', 'FONT', 'ADV', 'BKIND', 'RPFX', 'LFLAG', 'LNAME', 'LSIZE', 'PA', 'PB', 'LNAME2', 'CSIZE', 'LBASE', 'PC')
    tmp = {k: 0x0A0B0C00 + 0x10 * i for i, k in enumerate(names)}
    n0 = len(code(tmp).build())
    lay = {'NK': nk}; p = (CODE + n0 + 31) & ~31
    lay['TPL'] = p; p += 32
    lay['ST'] = p; p += 32
    lay['TSH'] = p; p += 8; lay['TCN'] = p; p += 8; lay['TDC'] = p; p += 16
    lay['BKIND'] = p; p += 16
    lay['RPFX'] = p; p += 2 * len(RPFX) + 2
    lay['LFLAG'] = p; p += 4
    lay['LNAME'] = p; p += 16
    lay['LNAME2'] = p; p += 16
    lay['PB'] = (p + 3) & ~3; p = lay['PB'] + plen_b
    lay['END'] = (p + 15) & ~15
    lay['LBASE'] = lbase; lay['PA'] = lbase + 16
    lay['LSIZE'] = asize; lay['LEND'] = lbase + asize
    q = CBASE + 16
    lay['KTAB'] = q; q += 4 * nk
    lay['ADV'] = q; q += (nfont + 3) & ~3
    lay['FONT'] = q; q += FONT_B * nfont
    lay['PC'] = (q + 3) & ~3; q = lay['PC'] + plen_c                # 자료 C 남는 자리에도 쪽
    lay['CEND'] = (q + 2047) & ~2047; lay['CSIZE'] = lay['CEND'] - CBASE
    a = code(lay); c = a.build(); assert len(c) <= n0, (len(c), n0)          # 실제 값이 겹치면 리터럴 풀이 줄 수 있음
    assert lay['END'] <= BLOCK_SAFE, ('블록(코드+쪽 B)이 한도를 넘음', hex(lay['END']))
    assert lay['LEND'] == HEAP_END and lbase >= LFLOOR, ('자료 A 가 힙 위 자리(0x2F0000~0x2F4000)를 넘음', hex(lbase))
    assert lay['CEND'] <= CMAX, ('자료 C 가 0x300000 을 넘음', hex(lay['CEND']))
    assert COMP + BMPSZ <= 0x06042700 and lay['END'] <= COMP
    return lay, a, c


def build_block(data):
    """→ (상주 블록 바이트, 자료 A 파일, 라벨, 배치) — 자료 C 파일은 lay['LD2']"""
    idx, bits, advs, clips = data
    seen = {}; order = []
    for clip, b, _ in clips:                         # 같은 쪽 목록(같은 번역·길이)은 한 벌
        if b not in seen: seen[b] = None; order.append(b)
    pre, _, _ = layout(len(advs), len(clips), 0)
    capb = BLOCK_SAFE - pre['PB'] - 16               # 블록 쪽 B → 자료 C 남는 자리 → 넘치는 것만 자료 A(힙 줄임)
    capc = CMAX - pre['PC'] - 16
    pa = b''; pbb = b''; pcc = b''; where = {}
    for b in order:
        assert len(b) % 2 == 0
        if len(pbb) + len(b) <= capb: where[b] = (1, len(pbb)); pbb += b
        elif len(pcc) + len(b) <= capc: where[b] = (2, len(pcc)); pcc += b
        else: where[b] = (0, len(pa)); pa += b
    asize = (16 + len(pa) + 2047) & ~2047
    lay, a, c = layout(len(advs), len(clips), len(pbb), asize, HEAP_END - asize, len(pcc))
    assert len(pa) // 2 < 0x4000 and len(pbb) // 2 < 0x4000 and len(pcc) // 2 < 0x4000
    blk = bytearray(lay['END'] - BLOCK)
    blk[0:4] = b'CRV3'
    struct.pack_into('>I', blk, SAVEPRI - BLOCK, 0xFFFFFFFF)
    struct.pack_into('>4I', blk, VAR - BLOCK, 0xFFFFFFFF, 0, 0, 0)
    blk[LOCC - BLOCK:LOCC - BLOCK + 32] = struct.pack('>16H', 0x000A, *[0] * 15)
    blk[SPR - BLOCK:SPR - BLOCK + 32] = struct.pack('>16H', 0x0000, 0, 0x0088, LUTO >> 3, TEXO >> 3, (W_ // 8) << 8 | H_, 0, 0, *[0] * 8)
    blk[ENDC - BLOCK:ENDC - BLOCK + 32] = struct.pack('>16H', 0x8000, *[0] * 15)
    blk[lay['TPL'] - BLOCK:lay['TPL'] - BLOCK + 32] = struct.pack('>16H', 0x8000, CMDV >> 3, *[0] * 14)
    blk[CODE - BLOCK:CODE - BLOCK + len(c)] = c
    for t, (sh, cn, dc) in enumerate(TYPES):
        blk[lay['TSH'] - BLOCK + t] = sh; blk[lay['TCN'] - BLOCK + t] = cn; struct.pack_into('>H', blk, lay['TDC'] - BLOCK + 2 * t, dc)
    blk[lay['BKIND'] - BLOCK:lay['BKIND'] - BLOCK + len(BKIND)] = BKIND.encode()
    blk[lay['RPFX'] - BLOCK:lay['RPFX'] - BLOCK + 2 * len(RPFX)] = ''.join(RPFX).encode()
    blk[lay['LNAME'] - BLOCK:lay['LNAME'] - BLOCK + len(SUBFILE)] = SUBFILE.encode()
    blk[lay['LNAME2'] - BLOCK:lay['LNAME2'] - BLOCK + len(SUBFILE2)] = SUBFILE2.encode()
    blk[lay['PB'] - BLOCK:lay['PB'] - BLOCK + len(pbb)] = pbb
    A_ = bytearray(asize); struct.pack_into('>II', A_, 0, LMAGIC, asize); A_[16:16 + len(pa)] = pa
    C_ = bytearray(lay['CSIZE']); o = lambda ad: ad - CBASE
    struct.pack_into('>II', C_, 0, CMAGIC, lay['CSIZE'])
    keys = sorted((clip_key(clip), clip, b) for clip, b, _ in clips)
    assert len({k for k, _, _ in keys}) == len(keys)
    for k, (key, clip, b) in enumerate(keys):
        reg, off = where[b]
        struct.pack_into('>HH', C_, o(lay['KTAB']) + 4 * k, key, reg << 14 | off // 2)
    for i, w in enumerate(advs):
        assert 0 < w < 256; C_[o(lay['ADV']) + i] = w
    f = o(lay['FONT'])
    for i, g in enumerate(bits):
        assert not any(g[:2 * FROW0]) and not any(g[2 * (FROW0 + FROWS):]), ('글꼴 줄이 저장 범위 밖', i)
        rw = [struct.unpack_from('>H', g, 2 * r)[0] for r in range(FROW0, FROW0 + FROWS)]
        assert not any(w & 0x7F for w in rw), ('글꼴이 9열을 넘음', i)
        m9 = 0
        for k, w in enumerate(rw): m9 |= ((w >> 7) & 1) << (15 - k)
        C_[f + FONT_B * i:f + FONT_B * (i + 1)] = bytes(w >> 8 for w in rw) + struct.pack('>H', m9)
    C_[o(lay['PC']):o(lay['PC']) + len(pcc)] = pcc
    lay['LD2'] = bytes(C_)
    return bytes(blk), bytes(A_), a.lab, lay


def patch(kernel, race, data=None):
    """→ (새 0KERNL.BIN, 새 RACE.EXE, 자막 자료 파일(CDR_ABS.TXT), 라벨, 배치)"""
    data = data or build_data()
    blk, ldata, lab, lay = build_block(data)
    k = bytearray(kernel); r = bytearray(race)
    assert len(k) == BSS0 - KBASE, '0KERNL.BIN 크기가 원본과 다름'
    for L, fn, nm in ((VBO_LIT, VBO_ORIG, lab['vbo']), (END_LIT, END_ORIG, lay['TPL'] | 0x80000000), (BSS_LIT, BSS0, lay['END']), (HEAP_END_LIT, HEAP_END, lay['LBASE'])):
        assert struct.unpack_from('>I', k, L - KBASE)[0] == fn, hex(L); struct.pack_into('>I', k, L - KBASE, nm)
    # 파일 읽기 머리 0x0600C4EC: push r8·r9·r10·r11 · mov.l @(lit),r8 · push r12 → «mov.l @(1,pc),r0 / jmp @r0 / nop / nop / lwrap»
    o = LOAD_FN - KBASE
    assert k[o:o + 12].hex() == '2f862f962fa62fb6d8452fc6' and struct.unpack_from('>I', k, 0x0600C60C - KBASE)[0] == LOAD_R8
    k[o:o + 12] = struct.pack('>HHHHI', 0xD001, 0x402B, 0x0009, 0x0009, lab['lwrap'])
    for L in EVT_LITS:
        assert struct.unpack_from('>I', r, L - RBASE)[0] == EVT_FN, hex(L); struct.pack_into('>I', r, L - RBASE, lab['vwrap'])
    k += bytes(BLOCK - KBASE - len(k)); k += blk
    return bytes(k), bytes(r), ldata, lab, lay


def ref_render(lines, font_bits, advs):
    """rstep 과 같은 셈(검산용) — 투명 바탕 · 8방향 테두리 3 · 글자 2"""
    px = [[0] * W_ for _ in range(H_)]
    for x, ly, gl in lines:
        for g in gl:
            bits = font_bits[g]
            for r in range(GROWS):
                v = bits[2 * r] << 8 | bits[2 * r + 1]
                for c in range(16):
                    if v & (0x8000 >> c):
                        xx, yy = x + c, ly + r
                        for dx, dy in ((-1, -1), (0, -1), (1, -1), (1, 0), (-1, 0), (-1, 1), (0, 1), (1, 1)):
                            ax, ay = xx + dx, yy + dy
                            if 0 <= ax < W_ and 0 <= ay < H_ and px[ay][ax] == 0: px[ay][ax] = 3
                        if xx < W_ and yy < H_: px[yy][xx] = 2
            x += advs[g]
    return bytes(px[y][x] << 4 | px[y][x + 1] for y in range(H_) for x in range(0, W_, 2))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    d = build_data()
    kern = open(os.path.join(ROOT, 'work', 'iso', '0KERNL.BIN'), 'rb').read(); race = open(os.path.join(ROOT, 'work', 'iso', 'RACE.EXE'), 'rb').read()
    k, r, ld, lab, lay = patch(kern, race, d)
    print('자막 클립 %d · 글자 %d · 상주 0x%08X~0x%08X(한도 0x%08X, 쪽 B 0x%08X~) · 자료 A %s %d B → 0x%08X~0x%08X(한도 0x%08X) · 자료 C %s %d B → 0x%08X~0x%08X(한도 0x%08X) · 코드 %d B' % (
        len(d[3]), len(d[2]), BLOCK, lay['END'], BLOCK_SAFE, lay['PB'], SUBFILE, len(ld), lay['LBASE'], lay['LEND'], LMAX, SUBFILE2, len(lay['LD2']), CBASE, lay['CEND'], CMAX, lay['TPL'] - CODE))
    print('  하위 RAM 힙 끝 0x%06X → 0x%06X (힙 %d B 줄임)' % (HEAP_END, lay['LBASE'], HEAP_END - lay['LBASE']))
