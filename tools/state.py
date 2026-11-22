# -*- coding: utf-8 -*-
"""RetroArch rzip(#RZIPv) 스테이트 풀기 → Mednafen(Beetle Saturn) 상태에서 작업 RAM 꺼내기
python tools/state.py 파일 → work/state/<이름>.raw"""
import os, struct, sys, zlib
def unrzip(b):
    if not b.startswith(b'#RZIPv'): return b
    chunk = struct.unpack_from('<I', b, 8)[0]; total = struct.unpack_from('<Q', b, 12)[0]
    p = 20; out = bytearray()
    while p < len(b) and len(out) < total:
        n = struct.unpack_from('<I', b, p)[0]; p += 4
        out += zlib.decompress(b[p:p + n]); p += n
    return bytes(out)
if __name__ == '__main__':
    for fn in sys.argv[1:]:
        raw = unrzip(open(fn, 'rb').read())
        os.makedirs('work/state', exist_ok=True)
        o = os.path.join('work/state', os.path.basename(fn) + '.raw'); open(o, 'wb').write(raw)
        print(o, len(raw), raw[:16])
