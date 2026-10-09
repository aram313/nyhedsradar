"""Draw the app icon (a radar sweep) as PNG files, using only the standard library."""
import math
import struct
import sys
import zlib
from pathlib import Path

BG = (24, 79, 149)        # deep blue
FG = (255, 255, 255)
ACCENT = (235, 104, 52)   # orange dot


def png(path, size):
    rows = []
    c = size / 2
    for y in range(size):
        row = bytearray([0])
        for x in range(size):
            # 3x3 supersampling for smooth edges
            acc = [0, 0, 0]
            for sy in (0.17, 0.5, 0.83):
                for sx in (0.17, 0.5, 0.83):
                    px, py = (x + sx - c) / size, (y + sy - c) / size
                    r = math.hypot(px, py)
                    ang = math.degrees(math.atan2(-py, px)) % 360
                    col = BG
                    for ring in (0.14, 0.25, 0.36):
                        if abs(r - ring) < 0.018:
                            col = FG
                    if r < 0.36 and 20 <= ang <= 75 and r > 0.03:
                        col = tuple(int(b + (f - b) * 0.35) for b, f in zip(BG, FG)) if col == BG else col
                    if math.hypot(px - 0.13, py + 0.17) < 0.045:
                        col = ACCENT
                    if r < 0.035:
                        col = FG
                    acc = [a + v for a, v in zip(acc, col)]
            row += bytes(int(a / 9) for a in acc)
        rows.append(bytes(row))
    raw = zlib.compress(b''.join(rows), 9)

    def chunk(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    data = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 2, 0, 0, 0)) + chunk(b'IDAT', raw) + chunk(b'IEND', b'')
    Path(path).write_bytes(data)


if __name__ == '__main__':
    out = Path(sys.argv[1] if len(sys.argv) > 1 else 'public/icons')
    out.mkdir(parents=True, exist_ok=True)
    for s in (180, 192, 512):
        png(out / f'icon-{s}.png', s)
    print('icons written to', out)
