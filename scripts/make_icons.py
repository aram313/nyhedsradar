"""Draw the Khabar app icon (a bold white K with a red live dot on black) as PNG files, standard library only."""
import math
import struct
import sys
import zlib
from pathlib import Path

BG = (0, 0, 0)
INK = (255, 255, 255)
DOT = (225, 6, 0)
# the K as thick strokes, in icon coordinates (centre = 0,0; up is negative)
STROKES = [((-.17, -.25), (-.17, .25)),     # stem
           ((-.14, .03), (.17, -.25)),       # upper arm
           ((-.07, -.04), (.19, .25))]       # leg
WIDTH = .115
DOT_AT, DOT_R = (.25, -.24), .055
SIGNATURE = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])


def dist_to_segment(px, py, a, b):
    (ax, ay), (bx, by) = a, b
    dx, dy = bx - ax, by - ay
    t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def in_stroke(px, py, a, b):
    # square-ended strokes: inside the band and between the two end caps
    (ax, ay), (bx, by) = a, b
    dx, dy = bx - ax, by - ay
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    return 0 <= t <= 1 and dist_to_segment(px, py, a, b) < WIDTH / 2


def chunk(kind, payload):
    return struct.pack('>I', len(payload)) + kind + payload + struct.pack('>I', zlib.crc32(kind + payload) & 0xffffffff)


def png(path, size):
    rows = []
    for y in range(size):
        row = bytearray([0])
        for x in range(size):
            acc = [0, 0, 0]
            for sy in (0.17, 0.5, 0.83):          # 3x3 supersampling for smooth edges
                for sx in (0.17, 0.5, 0.83):
                    px, py = (x + sx) / size - .5, (y + sy) / size - .5
                    col = BG
                    if any(in_stroke(px, py, a, b) for a, b in STROKES):
                        col = INK
                    if math.hypot(px - DOT_AT[0], py - DOT_AT[1]) < DOT_R:
                        col = DOT
                    acc = [a + c for a, c in zip(acc, col)]
            row += bytes(a // 9 for a in acc)
        rows.append(bytes(row))
    header = struct.pack('>IIBBBBB', size, size, 8, 2, 0, 0, 0)
    Path(path).write_bytes(SIGNATURE + chunk(b'IHDR', header) + chunk(b'IDAT', zlib.compress(b''.join(rows), 9)) + chunk(b'IEND', b''))


if __name__ == '__main__':
    out = Path(sys.argv[1] if len(sys.argv) > 1 else 'public/icons')
    out.mkdir(parents=True, exist_ok=True)
    for s in (180, 192, 512):
        png(out / f'icon-{s}.png', s)
    print('icons written to', out)
