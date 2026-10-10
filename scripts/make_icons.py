"""Draw the Nabd app icon (a pulse / ECG line) as PNG files, using only the standard library."""
import math
import struct
import sys
import zlib
from pathlib import Path

BG = (11, 11, 12)          # near black
LINE = (255, 77, 94)       # pulse red
# the heartbeat trace, in icon coordinates (centre = 0,0; up is negative)
TRACE = [(-.40, .02), (-.17, .02), (-.12, -.04), (-.07, .02), (-.03, .02), (.02, -.25), (.08, .2),
         (.12, .02), (.18, .02), (.23, -.06), (.28, .02), (.40, .02)]
WIDTH = .028
SIGNATURE = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])


def dist_to_segment(px, py, a, b):
    (ax, ay), (bx, by) = a, b
    dx, dy = bx - ax, by - ay
    t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def chunk(kind, payload):
    return struct.pack('>I', len(payload)) + kind + payload + struct.pack('>I', zlib.crc32(kind + payload) & 0xffffffff)


def png(path, size):
    rows = []
    for y in range(size):
        row = bytearray([0])
        for x in range(size):
            acc = 0.0
            for sy in (0.17, 0.5, 0.83):          # 3x3 supersampling for smooth edges
                for sx in (0.17, 0.5, 0.83):
                    px, py = (x + sx) / size - .5, (y + sy) / size - .5
                    d = min(dist_to_segment(px, py, TRACE[i], TRACE[i + 1]) for i in range(len(TRACE) - 1))
                    acc += 1.0 if d < WIDTH / 2 else 0.0
            k = acc / 9
            row += bytes(int(b + (l - b) * k) for b, l in zip(BG, LINE))
        rows.append(bytes(row))
    header = struct.pack('>IIBBBBB', size, size, 8, 2, 0, 0, 0)
    Path(path).write_bytes(SIGNATURE + chunk(b'IHDR', header) + chunk(b'IDAT', zlib.compress(b''.join(rows), 9)) + chunk(b'IEND', b''))


if __name__ == '__main__':
    out = Path(sys.argv[1] if len(sys.argv) > 1 else 'public/icons')
    out.mkdir(parents=True, exist_ok=True)
    for s in (180, 192, 512):
        png(out / f'icon-{s}.png', s)
    print('icons written to', out)
