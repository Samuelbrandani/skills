#!/usr/bin/env python3
"""png_diff.py — compares the Figma screenshot of a screen with the app render
and says *where* they differ, with numbers, before anyone squints at two PNGs.

Usage:
  scripts/png_diff.py <figma.png> <app.png> [--width 390] [--out diff.png]
                      [--threshold 24] [--band 16]

  --width N      logical width of the Figma frame. Both images are resized
                 (box filter) to this width first, so a 2x Figma export and a
                 3x device capture compare at the same scale. Default: the
                 narrower image's width.
  --out FILE     writes a heatmap: the Figma image dimmed, differing pixels red.
  --threshold T  per-pixel difference (0–255, max over RGB) that counts as a
                 divergence (default 48). Lower it for flat surfaces with close
                 colors; raise it when both sides were resampled heavily.
  --band H       height in logical px of the horizontal bands in the report.
  --shift S      a pixel only diverges if no pixel within S px in the other
                 image matches it (default 1): absorbs resampling and
                 antialiasing, still catches a 2 px padding drift.

Output: overall % of differing pixels, the height mismatch (a taller app
render usually means extra spacing somewhere above), and the bands where the
divergence concentrates, top to bottom — each one is a place to open the
probe JSON and the Figma node. Exit code 1 when more than 2% of the image or
5% of any band differs. Resampling the same screen from another scale stays
around 1% overall; a 2 px padding drift shows as ~6% in its bands.

Standard library only (zlib + struct). Reads 8-bit PNG: gray, gray+alpha,
RGB, RGBA and palette, non-interlaced — what Figma, simulators, emulators,
browsers and `flutter screenshot` produce.
"""
import struct
import sys
import zlib
from pathlib import Path


def _utf8_stdout() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except (AttributeError, ValueError):
        pass


def read_png(path: Path):
    """Returns (width, height, rows) with rows as lists of (r, g, b) over white."""
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{path}: not a PNG")
    pos, idat, palette, trns = 8, [], None, None
    width = height = depth = ctype = interlace = 0
    while pos < len(data):
        length, kind = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if kind == b"IHDR":
            width, height, depth, ctype, _, _, interlace = struct.unpack(">IIBBBBB", body)
        elif kind == b"PLTE":
            palette = [tuple(body[i:i + 3]) for i in range(0, len(body), 3)]
        elif kind == b"tRNS":
            trns = body
        elif kind == b"IDAT":
            idat.append(body)
        elif kind == b"IEND":
            break
    if depth != 8 or interlace:
        raise ValueError(f"{path}: only 8-bit non-interlaced PNG is supported "
                         f"(bit depth {depth}, interlace {interlace}); re-save it as 8-bit")
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ctype]
    raw = zlib.decompress(b"".join(idat))
    stride = width * channels
    prev = bytearray(stride)
    rows, i = [], 0
    for _ in range(height):
        f = raw[i]
        line = bytearray(raw[i + 1:i + 1 + stride])
        i += 1 + stride
        for x in range(stride):
            a = line[x - channels] if x >= channels else 0
            b = prev[x]
            c = prev[x - channels] if x >= channels else 0
            if f == 1:
                line[x] = (line[x] + a) & 255
            elif f == 2:
                line[x] = (line[x] + b) & 255
            elif f == 3:
                line[x] = (line[x] + ((a + b) >> 1)) & 255
            elif f == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pred = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
                line[x] = (line[x] + pred) & 255
        prev = line
        row = []
        for x in range(width):
            px = line[x * channels:(x + 1) * channels]
            if ctype == 0:
                r = g = bl = px[0]; al = 255
            elif ctype == 4:
                r = g = bl = px[0]; al = px[1]
            elif ctype == 2:
                r, g, bl = px; al = 255
            elif ctype == 6:
                r, g, bl, al = px
            else:
                r, g, bl = palette[px[0]]
                al = trns[px[0]] if trns and px[0] < len(trns) else 255
            if al < 255:  # composite over white, like the Figma canvas
                r = (r * al + 255 * (255 - al)) // 255
                g = (g * al + 255 * (255 - al)) // 255
                bl = (bl * al + 255 * (255 - al)) // 255
            row.append((r, g, bl))
        rows.append(row)
    return width, height, rows


def resize(w, h, rows, new_w):
    """Box-filter resize to new_w, keeping the aspect ratio."""
    if new_w == w:
        return w, h, rows
    scale = w / new_w
    new_h = max(1, round(h / scale))
    out = []
    for y in range(new_h):
        y0, y1 = int(y * scale), max(int(y * scale) + 1, int((y + 1) * scale))
        line = []
        for x in range(new_w):
            x0, x1 = int(x * scale), max(int(x * scale) + 1, int((x + 1) * scale))
            n = r = g = b = 0
            for yy in range(y0, min(y1, h)):
                src = rows[yy]
                for xx in range(x0, min(x1, w)):
                    pr, pg, pb = src[xx]
                    r += pr; g += pg; b += pb; n += 1
            line.append((r // n, g // n, b // n))
        out.append(line)
    return new_w, new_h, out


def write_png(path: Path, w, h, rows):
    raw = b"".join(b"\x00" + bytes(v for px in row for v in px) for row in rows)
    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def main(argv):
    _utf8_stdout()
    args = list(argv)
    opts = {"--width": None, "--out": None, "--threshold": "48", "--band": "16", "--shift": "1"}
    files = []
    while args:
        a = args.pop(0)
        if a in opts:
            opts[a] = args.pop(0)
        else:
            files.append(Path(a))
    if len(files) != 2:
        print(__doc__)
        return 2
    (fw, fh, frows), (aw, ah, arows) = read_png(files[0]), read_png(files[1])
    width = int(opts["--width"]) if opts["--width"] else min(fw, aw)
    fw, fh, frows = resize(fw, fh, frows, width)
    aw, ah, arows = resize(aw, ah, arows, width)
    threshold, band, shift = int(opts["--threshold"]), int(opts["--band"]), int(opts["--shift"])
    # a 1 px difference is rounding from the resize, not layout
    height = min(fh, ah) if abs(fh - ah) <= 1 else max(fh, ah)
    blank = [(255, 255, 255)] * width
    diff_rows, heat = [], []
    total = 0
    def close(p, q):
        return max(abs(p[0] - q[0]), abs(p[1] - q[1]), abs(p[2] - q[2])) <= threshold

    def near(px, rows, rh, x, y):
        for yy in range(max(0, y - shift), min(rh, y + shift + 1)):
            row = rows[yy]
            for xx in range(max(0, x - shift), min(width, x + shift + 1)):
                if close(px, row[xx]):
                    return True
        return False

    for y in range(height):
        f = frows[y] if y < fh else blank
        a = arows[y] if y < ah else blank
        n, hrow = 0, []
        for x in range(width):
            if y >= fh or y >= ah:
                bad = True
            elif close(f[x], a[x]):
                bad = False
            else:  # symmetric: each side must find its pixel near the other
                bad = not (near(f[x], arows, ah, x, y) and near(a[x], frows, fh, x, y))
            if bad:
                n += 1
                hrow.append((230, 30, 30))
            else:
                g = 200 + sum(f[x]) // 3 * 55 // 255
                hrow.append((g, g, g))
        diff_rows.append(n)
        heat.append(hrow)
        total += n
    pct = 100 * total / (width * height)
    print(f"compared at {width} px wide · figma {fh} px tall · app {ah} px tall"
          + (f" (app {ah - fh:+d} px — extra/missing spacing above the first divergent band)"
             if abs(ah - fh) > 1 else ""))
    print(f"differing pixels: {pct:.2f}% (threshold {threshold})")
    print(f"\nbands of {band} px with divergence (y range · % of band):")
    shown, worst = 0, 0.0
    for y0 in range(0, height, band):
        rows = diff_rows[y0:y0 + band]
        p = 100 * sum(rows) / (width * len(rows))
        worst = max(worst, p)
        if p >= 1:
            bar = "█" * min(40, int(p / 2.5) + 1)
            print(f"  y {y0:>5}–{min(y0 + band, height):<5} {p:5.1f}%  {bar}")
            shown += 1
    if not shown:
        print("  none above 1%")
    if opts["--out"]:
        write_png(Path(opts["--out"]), width, height, heat)
        print(f"\nheatmap: {opts['--out']}")
    return 1 if pct > 2 or worst >= 5 else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
