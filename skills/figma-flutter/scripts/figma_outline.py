#!/usr/bin/env python3
"""figma_outline.py — prints a readable outline of a `get_metadata` result.

`get_metadata` on a section or page overflows the tool-result limit (150 KB+)
and the harness saves it to a file as a JSON array [{type, text}] or as raw
XML. Re-calling the tool does not help; this script reads the saved file and
prints frames with their sizes so you can pick the screen nodes and their
frame widths without loading the whole XML into context.

Usage:
  scripts/figma_outline.py <saved-result-file> [--depth N] [--node ID] [--all]

  --depth N   levels to print below the root (default 2 = top-level screens)
  --node ID   start from this node id (e.g. 8055:736) instead of the root
  --all       also print layers named Container/Text/Icon/Paragraph (noise)
"""
import json
import re
import sys
from pathlib import Path

NOISE = {"Container", "Container:margin", "Text", "Text:margin", "Icon",
         "Icon:margin", "Paragraph", "Frame"}
TAG = re.compile(r'<(\w+) id="([^"]+)" name="([^"]*)"(.*?)(/?)>')


def _utf8_stdout() -> None:
    """Windows consoles and pipes may default to cp1252; the report uses arrows
    and multiplication signs, so force UTF-8 (Python 3.7+) and never crash on it."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except (AttributeError, ValueError):
        pass


def load(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="replace")
    if raw.lstrip().startswith("["):
        try:
            data = json.loads(raw)
            return "".join(d.get("text", "") for d in data)
        except json.JSONDecodeError:
            pass
    return raw


def attr(rest: str, name: str):
    m = re.search(rf'{name}="([^"]+)"', rest)
    return m.group(1) if m else None


def main(argv):
    _utf8_stdout()
    if not argv:
        print(__doc__)
        return 2
    path = Path(argv[0])
    depth = 2
    start = None
    show_all = "--all" in argv
    if "--depth" in argv:
        depth = int(argv[argv.index("--depth") + 1])
    if "--node" in argv:
        start = argv[argv.index("--node") + 1]
    text = load(path)
    lines = text.splitlines()
    base = None
    printed = 0
    for line in lines:
        s = line.strip()
        if not s.startswith("<") or s.startswith("</"):
            continue
        m = TAG.match(s)
        if not m:
            continue
        kind, nid, name, rest, _ = m.groups()
        ind = (len(line) - len(line.lstrip())) // 2
        if start and base is None:
            if nid != start:
                continue
            base = ind
        if base is None:
            base = ind
        if ind < base:
            break
        level = ind - base
        if level > depth:
            continue
        if not show_all and name in NOISE and kind != "text" and nid != start:
            continue
        w, h = attr(rest, "width"), attr(rest, "height")
        size = f"{float(w):g}x{float(h):g}" if w and h else ""
        print(f'{"  " * level}{kind} {nid} "{name[:48]}" {size}')
        printed += 1
    if printed == 0:
        print("nothing matched — check --node id or the file format")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
