#!/usr/bin/env python3
"""svg_check.py — flags SVG features that flutter_svg / vector_graphics do not
render (or render differently), before an exported Figma asset is committed.

Usage:  scripts/svg_check.py path/to/icon.svg [more.svg ...] [--dir assets/icons]
Exit code 1 when any file has a blocking issue. No third-party dependencies.

Why: a Figma export can carry <filter> (drop shadow / blur), CSS <style>
blocks, embedded raster <image>, <foreignObject>, text, or masks that
flutter_svg silently drops or paints wrong. Catching that here is cheaper
than noticing a blank icon on a device.
"""
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

NS = "{http://www.w3.org/2000/svg}"

BLOCKING = {
    "filter": "filter (blur/drop-shadow) is not rendered — flatten in Figma or export PNG/WebP",
    "foreignObject": "foreignObject is not supported",
    "image": "embedded/linked <image> — export as raster or inline the raster separately",
    "text": "<text> is not rendered — outline the text in Figma before exporting",
    "style": "CSS <style> block — flutter_svg only reads presentation attributes; re-export with 'outline' / no CSS",
    "script": "script tag — remove",
    "switch": "<switch> not supported",
    "pattern": "<pattern> fill not supported",
}
WARN = {
    "mask": "mask — partial support; check the render",
    "clipPath": "clipPath — supported, but nested/text clips can fail; check the render",
    "use": "<use>/<symbol> — supported by flutter_svg ≥2, check vector_graphics compile",
    "symbol": "<symbol> — see <use>",
    "linearGradient": "linearGradient — supported; check 'gradientTransform' and objectBoundingBox units",
    "radialGradient": "radialGradient — supported; focal points and spread methods can differ",
}


def check(path: Path):
    issues, warns, info = [], [], []
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
        root = ET.fromstring(raw)
    except Exception as e:  # noqa: BLE001
        return [f"unparseable SVG: {e}"], [], []

    tags = {}
    for el in root.iter():
        tag = el.tag.replace(NS, "")
        tags[tag] = tags.get(tag, 0) + 1

    for tag, msg in BLOCKING.items():
        if tag in tags:
            issues.append(f"{msg} (×{tags[tag]})")
    for tag, msg in WARN.items():
        if tag in tags:
            warns.append(f"{msg} (×{tags[tag]})")

    # Size / viewBox hygiene
    if "viewBox" not in root.attrib:
        issues.append("no viewBox — the icon will not scale; export with viewBox")
    w, h = root.attrib.get("width"), root.attrib.get("height")
    if w and h:
        info.append(f"intrinsic size {w}×{h}")
    vb = root.attrib.get("viewBox")
    if vb:
        parts = vb.replace(",", " ").split()
        if len(parts) == 4 and parts[2] != parts[3]:
            info.append(f"non-square viewBox {vb} — fine for illustrations, suspicious for an icon")

    # Hard-coded colors: an icon that must be tinted should use currentColor or a single fill
    colors = set(re.findall(r'(?:fill|stroke)="(#[0-9a-fA-F]{3,8})"', raw))
    colors |= set(re.findall(r'(?:fill|stroke):\s*(#[0-9a-fA-F]{3,8})', raw))
    if len(colors) > 1:
        info.append(f"{len(colors)} distinct colors {sorted(colors)} — multi-color asset; a monochrome icon should be a single color so `colorFilter` can tint it")
    elif len(colors) == 1:
        info.append(f"single color {colors.pop()} — tintable with ColorFilter / currentColor")

    # Figma export leftovers
    if re.search(r'fill-opacity="0"|opacity="0"', raw):
        warns.append("fully transparent element(s) — Figma export leftover, remove")
    # Sub-pixel strokes matter only relative to the viewBox: a Lucide icon at
    # 16 px has stroke 1.333 (= 2/24) and is fine; 0.3 on a 24 box is not.
    vb_side = None
    if vb:
        parts = vb.replace(",", " ").split()
        if len(parts) == 4:
            try:
                vb_side = max(float(parts[2]), float(parts[3]))
            except ValueError:
                vb_side = None
    strokes = [float(x) for x in re.findall(r'stroke-width="([0-9.]+)"', raw)]
    if strokes and vb_side and min(strokes) / vb_side < 0.03:
        warns.append(f"stroke {min(strokes):g} on a {vb_side:g} viewBox — will look hairline at 1x")
    if re.search(r'<g[^>]*opacity="', raw):
        warns.append("group opacity — rendered per element in some versions (overlaps look darker); check")
    if len(raw) > 60_000:
        warns.append(f"large file ({len(raw)//1024} KB) — run svgo or reconsider raster")
    if tags.get("path", 0) > 200:
        warns.append(f"{tags['path']} paths — heavy for an icon; consider raster or simplifying")
    return issues, warns, info


def main(argv):
    files = []
    args = list(argv)
    while args:
        a = args.pop(0)
        if a == "--dir":
            files += sorted(Path(args.pop(0)).rglob("*.svg"))
        else:
            files.append(Path(a))
    if not files:
        print(__doc__)
        return 2
    bad = 0
    for f in files:
        issues, warns, info = check(f)
        status = "BLOCK" if issues else ("WARN" if warns else "OK")
        bad += bool(issues)
        print(f"[{status}] {f}")
        for i in issues:
            print(f"    ✗ {i}")
        for w in warns:
            print(f"    ! {w}")
        for n in info:
            print(f"    · {n}")
    print(f"\n{len(files)} file(s), {bad} blocking")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
