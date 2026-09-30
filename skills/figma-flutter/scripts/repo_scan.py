#!/usr/bin/env python3
"""repo_scan.py — prints a "Repo Profile" for a Flutter repo: where the design
system lives, which tokens exist, where features put their widgets, which
verification tooling is already there. Read-only, standard library only,
runs on Windows, macOS and Linux.

Usage:
  python3 scripts/repo_scan.py [repo-root] [feature]      # macOS / Linux
  py -3 scripts\\repo_scan.py [repo-root] [feature]        # Windows

`feature` (optional) spotlights that feature's package, docs and tests.
`scripts/repo_scan.sh` is a thin wrapper around this file for shells that
already have bash; both print the same profile.
"""
from __future__ import annotations

import os
import re
import sys
from collections import Counter
from pathlib import Path

PRUNE = {".dart_tool", "build", ".fvm", "node_modules", "ios", "android",
         "macos", "linux", "windows", ".symlinks", ".git", ".idea", ".vscode"}
TOKEN_CLASS = re.compile(
    r'(?:abstract |final )?class ([A-Z][A-Za-z]*(?:Colors?|Color(?:Scheme|s)|Spacing|Space|Sizes?|'
    r'Typography|TextStyles|Text(?:Theme|Styles)|Radi(?:us|i)|Shadows?|Elevations?|Icons|Tokens|'
    r'Gaps?|Dimens|Insets))\b')
CONTEXT_EXT = re.compile(r'extension [A-Za-z]+ on BuildContext')
CONTEXT_EXT_BODY = re.compile(r'(extension [A-Za-z]+ on BuildContext)\s*\{(.{0,1500}?)\n\}', re.S)
TOKEN_WORDS = re.compile(r'\b(?:[A-Z]\w*(?:Colors?|Spacing|Typography|TextStyles|Radi(?:us|i)|Shadows|Tokens)|'
                         r'ThemeExtension|extension<|colorScheme|textTheme)\b')
DS_DIR_NAMES = ("design", "design_system", "ds", "theme", "ui_kit", "tokens", "foundation")
LINT_RULE = re.compile(r'extends\s+(?:DartLintRule|LintRule|AnalysisRule|MultiAnalysisRule|LintCode)\b')
IMAGE_WRAPPER = re.compile(r'class\s+([A-Z]\w*?(?:Image|Picture|Svg|Icon|Avatar|Illustration)\w*|'
                           r'(?:Image|Picture|Svg|Illustration)\w*)\s+extends\s+'
                           r'(?:StatelessWidget|StatefulWidget)')
RAW_IMAGE = re.compile(r'\b(?:Image\.(?:asset|network|file|memory)|SvgPicture\.(?:asset|network|file|memory|string)|'
                       r'CachedNetworkImage\()')
ICON_FAMILY = re.compile(
    r'\b(Icons|CupertinoIcons|LucideIcons|PhosphorIcons|FontAwesomeIcons|HeroIcons|[A-Z][A-Za-z]*Icons)\.[a-zA-Z0-9_]+')
TOOLING = re.compile(
    r'^\s+(theme_tailor|theme_tailor_annotation|design_tokens_builder|design_builder|flutter_gen|'
    r'flutter_gen_runner|google_fonts|flutter_svg|vector_graphics|vector_graphics_compiler|'
    r'lucide_icons_flutter|phosphor_flutter|flutter_screenutil|responsive_framework|widgetbook|'
    r'widgetbook_annotation|alchemist|golden_toolkit|flutter_test_goldens|freezed|bloc|flutter_bloc|'
    r'riverpod|flutter_riverpod|provider|get_it|auto_route|go_router|flutter_modular|melos):', re.M)
FONT_FAMILY = re.compile(r'^\s+- family:\s*(\S.*)$', re.M)
ENV_FLAG = re.compile(r'(?:bool|String)\.fromEnvironment\([^)\n]*\)')


def _utf8_stdout() -> None:
    """Windows consoles and pipes may default to cp1252; the report uses arrows
    and multiplication signs, so force UTF-8 (Python 3.7+) and never crash on it."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except (AttributeError, ValueError):
        pass


def h(title: str) -> None:
    print(f"\n## {title}")


def walk(root: Path, max_depth: int | None = None):
    """os.walk with the build/tool directories pruned. Yields (dir, subdirs, files)."""
    root_depth = len(root.parts)
    for cur, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in PRUNE)
        depth = len(Path(cur).parts) - root_depth
        if max_depth is not None and depth >= max_depth:
            dirs[:] = []
        yield Path(cur), dirs, files


def rel(p: Path, root: Path) -> str:
    return p.relative_to(root).as_posix()


def read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def main(argv: list[str]) -> int:
    _utf8_stdout()
    root = Path(argv[0] if argv else ".").resolve()
    feature = argv[1] if len(argv) > 1 else ""
    if not root.is_dir():
        print(f"no such dir: {root}")
        return 1

    # one pass collects everything we need
    dart_files: list[Path] = []
    pubspecs: list[Path] = []
    md_files: list[Path] = []
    dirs_named: dict[str, list[Path]] = {}
    for cur, dirs, files in walk(root):
        for d in dirs:
            dirs_named.setdefault(d.lower(), []).append(cur / d)
        for f in files:
            p = cur / f
            if f.endswith(".dart"):
                dart_files.append(p)
            elif f == "pubspec.yaml":
                pubspecs.append(p)
            elif f.lower().endswith(".md"):
                md_files.append(p)
    dart_src = {p: read(p) for p in dart_files if ".g.dart" not in p.name}
    pub_src = {p: read(p) for p in pubspecs}

    print(f"# Repo Profile — {root.name} ({root})")

    h("Toolchain")
    fvm: dict[str, str] = {}
    for name in (".fvmrc", ".fvm/fvm_config.json"):
        p = root / name
        if p.is_file():
            m = re.search(r'"(?:flutter|flutterSdkVersion)"\s*:\s*"([^"]+)"', read(p))
            if m:
                fvm[name] = m.group(1)
                print(f"- fvm: {m.group(1)} ({name})")
    if len(set(fvm.values())) > 1:
        print(f"  ⚠ fvm pins disagree — fvm 3 reads .fvmrc ({fvm.get('.fvmrc')}); "
              ".fvm/fvm_config.json is a legacy/local file. Run tools with the .fvmrc version")
    if (root / "melos.yaml").is_file():
        print("- melos.yaml present (monorepo)")
    if re.search(r"^workspace:", read(root / "pubspec.yaml"), re.M):
        print("- pub workspace (monorepo) in root pubspec")
    mk = root / "Makefile"
    if mk.is_file():
        targets = re.findall(r"^([a-zA-Z_-]+):", read(mk), re.M)
        print(f"- Makefile targets: {' '.join(targets)[:160]}")

    h("Architecture docs (read these before writing code)")
    doc_names = re.compile(r"^(CLAUDE|ARCHITECTURE.*|CONTRIBUTING.*|AGENTS|DESIGN.*)\.md$", re.I)
    for p in sorted(md_files):
        if doc_names.match(p.name) and len(p.relative_to(root).parts) <= 3:
            print(f"- {rel(p, root)}")
    for up in (root.parent, root.parent.parent):
        for name in ("CLAUDE.md", "AGENTS.md"):
            if (up / name).is_file():
                print(f'- parent: {up / name}  ← inherited rules (e.g. "plan mode first")')
    if (root / "docs/README.md").is_file():
        print("- docs/README.md (index)")
    adr = root / "docs/adr"
    if adr.is_dir():
        adrs = sorted(x.name for x in adr.glob("*.md"))
        key = [a for a in adrs if re.search(r"design|token|widget|test|icon|arch", a, re.I)]
        print(f"- docs/adr/: {len(adrs)} ADRs — {' '.join(key)}")
    specs = root / "docs/specs"
    if specs.is_dir():
        print(f"- docs/specs/: {' '.join(sorted(x.name for x in specs.iterdir()))[:200]}")
    if feature:
        for p in sorted(md_files):
            if feature.lower() in p.name.lower() and len(p.relative_to(root).parts) <= 4:
                print(f"- feature doc: {rel(p, root)}")
    for d in ("docs", "doc"):
        for p in dirs_named.get(d, [])[:5]:
            print(f"- dir: {rel(p, root)}")
    caps = [rel(p, root) for n in ("design", "figma", "captures") for p in dirs_named.get(n, [])
            if "docs" in p.parts]
    print(f"- design captures already in repo: {' '.join(caps)}")

    h("Packages (pubspec.yaml)")
    for p in sorted(pubspecs, key=lambda x: rel(x, root)):
        if len(p.relative_to(root).parts) > 5:
            continue
        m = re.search(r"^name:\s*(\S+)", pub_src[p], re.M)
        name = m.group(1) if m else "?"
        d = rel(p.parent, root) or "."
        tag = ""
        if re.search(r"design|ui_kit|uikit|theme|foundation|components|widgets|core_ui|_ui$", f"{name} {d}", re.I):
            tag = " ← design-system candidate"
        if re.search(r"feature", d, re.I):
            tag = " (feature)"
        if re.search(r"widgetbook|storybook|catalog", d, re.I):
            tag = " (component catalog)"
        print(f"- {name} → {d}{tag}")

    h("Design-system signals")
    print("- barrels (lib/*.dart exporting src/):")
    for p in sorted(dart_files):
        parts = p.relative_to(root).parts
        if len(parts) >= 2 and parts[-2] == "lib" and "src" not in parts:
            src = dart_src.get(p, "")
            if re.search(r"^export 'src/", src, re.M):
                n = len(re.findall(r"^export ", src, re.M))
                print(f"    {rel(p, root)} ({n} exports)")
    print("- ThemeExtension classes:")
    for p, src in sorted(dart_src.items()):
        if "extends ThemeExtension<" in src:
            print(f"    {rel(p, root)}")
    print("- token-like classes (Colors/Spacing/Typography/Radius/Shadows/Elevation/Icons):")
    token_at: dict[str, list[str]] = {}
    for p, src in sorted(dart_src.items()):
        if "test" in p.relative_to(root).parts:
            continue
        for name in TOKEN_CLASS.findall(src):
            token_at.setdefault(name, []).append(rel(p, root))
    for name, paths in sorted(token_at.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:25]:
        extra = f" (+{len(paths) - 1} more)" if len(paths) > 1 else ""
        print(f"    {name} — {paths[0]}{extra}")
    print("- design-system dirs inside lib/ (not a package):")
    ds_dirs = [rel(p, root) for n in DS_DIR_NAMES for p in dirs_named.get(n, [])
               if "lib" in p.relative_to(root).parts and "test" not in p.relative_to(root).parts]
    for d in sorted(ds_dirs)[:8]:
        print(f"    {d}")
    print("- BuildContext extensions (context.colors / context.spacing …):")
    token_ext, other_ext = [], []
    for p, src in sorted(dart_src.items()):
        for m in CONTEXT_EXT_BODY.finditer(src):
            body = m.group(2)
            line = f"{m.group(1)} — {rel(p, root)}"
            (token_ext if TOKEN_WORDS.search(body) else other_ext).append(line)
    for line in token_ext[:8]:
        print(f"    {line}  ← token access")
    if not token_ext:
        print("    (none exposes tokens — access is probably static: AppColors.x / Theme.of(context))")
    if other_ext:
        print(f"    + {len(other_ext)} other extensions (helpers: sheets, toasts, navigation …)")
    print("- token codegen / theme tooling:")
    tools = Counter(m for src in pub_src.values() for m in TOOLING.findall(src))
    for name, n in tools.most_common():
        print(f"    {name} (×{n})")
    fonts = sorted({m.strip() for src in pub_src.values() for m in FONT_FAMILY.findall(src)})
    print(f"- fonts declared in pubspec: {' '.join(fonts) or '(none)'}")
    gf_files = sorted({f"{rel(p, root)}/" for p in dirs_named.get("google_fonts", [])
                       if "lib" not in p.relative_to(root).parts})
    for d in gf_files:
        ttf = sorted(x.name for x in (root / d).iterdir() if x.suffix.lower() in (".ttf", ".otf"))
        print(f"- google_fonts bundled offline: {d} {' '.join(ttf)[:160]}")
    uses_gf = any("GoogleFonts." in src for src in dart_src.values())
    if uses_gf:
        offline = any(re.search(r"allowRuntimeFetching\s*=\s*false", src) for src in dart_src.values())
        print(f"- google_fonts used in code; runtime fetching disabled somewhere: {'yes' if offline else 'NO'}"
              " — tests need the TTFs registered, or text is measured with Ahem")
    print("- design-system catalog docs:")
    for p in sorted(md_files):
        if re.search(r"catalog|components|tokens|design[-_]system", p.name, re.I) and len(p.relative_to(root).parts) <= 5:
            print(f"    {rel(p, root)}")

    h("Lint rules (they encode the design-system contract — read them)")
    inherited = 0
    for p in sorted(root.rglob("analysis_options.yaml")):
        if any(x in PRUNE for x in p.relative_to(root).parts) or len(p.relative_to(root).parts) > 4:
            continue
        src = read(p)
        inc = re.findall(r"^include:\s*(\S+)", src, re.M)
        plugins = re.findall(r"^\s*plugins:\s*\n((?:\s+-?\s*\S+.*\n?)+)", src, re.M)
        names = re.findall(r"[\w-]+", " ".join(plugins))
        if not names and inc and all(i.startswith("..") for i in inc):
            inherited += 1
            continue
        print(f"- {rel(p, root)}: include {' '.join(inc) or '—'}; analyzer plugins {' '.join(names) or '—'}")
    if inherited:
        print(f"- + {inherited} package analysis_options that only include a parent")
    rules = []
    for p, src in sorted(dart_src.items()):
        if not LINT_RULE.search(src):
            continue
        codes = re.findall(r"""(?:name|code)\s*[:=]\s*['"]([a-z][a-z0-9_]+)['"]""", src)
        rules += [f"{c} — {rel(p, root)}" for c in dict.fromkeys(codes)]
    for r in rules[:30]:
        print(f"    rule: {r}")
    if not rules:
        print("    (no custom lint rule classes found)")

    h("Image / icon rendering component (feature code must go through it)")
    raw_users = Counter()
    wrappers = []
    for p, src in sorted(dart_src.items()):
        if "test" in p.relative_to(root).parts:
            continue
        for cls in IMAGE_WRAPPER.findall(src):
            if RAW_IMAGE.search(src):
                wrappers.append((cls, rel(p, root)))
        for m in RAW_IMAGE.findall(src):
            raw_users[rel(p, root)] += 1
    used = Counter()
    for cls, _ in wrappers:
        pat = re.compile(rf"\b{cls}\b")
        used[cls] = sum(1 for src in dart_src.values() if pat.search(src))
    top = sorted(wrappers, key=lambda w: -used[w[0]])[:5]
    for cls, path in top:
        print(f"- {cls} — {path} (used in {used[cls]} files)")
    if top:
        print("  → render assets through the most-referenced wrapper; raw Image.*/SvgPicture.* "
              "belongs only inside it")
    else:
        print("- none: raw Image.asset / SvgPicture.asset is the repo's pattern")
    print(f"- files calling raw Image.*/SvgPicture.* directly: {len(raw_users)}")

    h("Assets")
    shown = 0
    for p in dirs_named.get("assets", []) + dirs_named.get("asset", []):
        if "web" in p.parts or len(p.relative_to(root).parts) > 5:
            continue
        svg = png = 0
        subs: list[str] = []
        for cur, dirs, files in walk(p):
            if cur == p:
                subs = dirs[:]
            for f in files:
                low = f.lower()
                svg += low.endswith(".svg")
                png += low.endswith((".png", ".webp", ".jpg", ".jpeg"))
        print(f"- {rel(p, root)} — svg:{svg} raster:{png} — subdirs: {' '.join(subs)}")
        shown += 1
        if shown >= 12:
            break
    scale_dirs = [rel(p, root) for n in ("2.0x", "3.0x") for p in dirs_named.get(n, [])][:3]
    for s in scale_dirs:
        print(f"- scale dirs: {s}")
    for p, src in sorted(dart_src.items()):
        if ("gen/" in rel(p, root) or p.name.endswith(".gen.dart")) and re.search(r"flutter_gen|class Assets\b", src):
            print(f"- generated assets class: {rel(p, root)}")
            break
    svg_users = sum(1 for src in dart_src.values() if re.search(r"SvgPicture|VectorGraphic", src))
    print(f"- SVG rendering: {svg_users} files use flutter_svg/vector_graphics")
    fam = Counter(m for src in dart_src.values() for m in ICON_FAMILY.findall(src))
    print("- icon families in code: " + " ".join(f"{k}(×{v})" for k, v in fam.most_common(5)))

    h("Where feature widgets live (top-level layout under lib/)")
    libs = [p for p in dirs_named.get("lib", []) if len(p.relative_to(root).parts) <= 4
            and not re.search(r"widgetbook|example", rel(p, root))][:6]
    for lib in libs:
        top = sorted(d.name for d in lib.iterdir() if d.is_dir() and d.name not in PRUNE)
        label = " ".join(top)
        if top == ["src"]:
            label = "src/: " + " ".join(sorted(d.name for d in (lib / "src").iterdir() if d.is_dir()))
        print(f"- {rel(lib, root)}: {label}")
        for cur, dirs, files in walk(lib, max_depth=3):
            if cur.name.lower() in {"features", "modules", "pages", "presentation", "ui", "screens", "views"}:
                inner = sorted(os.listdir(cur))[:12]
                print(f"    {rel(cur, root)}/: {' '.join(inner)}")
                break

    if feature:
        h(f"Feature spotlight: {feature}")
        hits = [p for lst in dirs_named.values() for p in lst
                if feature.lower() in p.name.lower() and not re.search(r"/test/|/build/|widgetbook", rel(p, root) + "/")
                and len(p.relative_to(root).parts) <= 5][:4]
        for d in hits:
            print(f"- {rel(d, root)}")
            for p in sorted(x for x in dart_files if d in x.parents and "lib" in x.parts)[:40]:
                print(f"    {p.relative_to(d).as_posix()}")
        tests = [rel(p, root) for lst in dirs_named.values() for p in lst
                 if feature.lower() in p.name.lower() and "test" in p.parts][:2]
        print(f"- tests: {' '.join(tests)}")

    h("Verification tooling already present")
    probes = [rel(p, root) for p, src in sorted(dart_src.items())
              if re.search(r"probeDesign|expectDesignSnapshot|design_probe", src)][:3]
    print(f"- design probe / snapshot: {' '.join(probes)}")
    goldens = sum(1 for src in dart_src.values() if re.search(r"matchesGoldenFile|goldenTest\(|GoldenTestGroup", src))
    print(f"- golden tests: {goldens} files")
    cfg = [rel(p, root) for p in dart_files if p.name == "flutter_test_config.dart"][:3]
    print(f"- flutter_test_config.dart: {' '.join(cfg)}")
    fl = [rel(p, root) for p, src in sorted(dart_src.items()) if re.search(r"loadAppFonts|FontLoader\(", src)][:3]
    print(f"- font loading in tests: {' '.join(fl)}")
    wb = [rel(p, root) for n, lst in dirs_named.items() if n.startswith("widgetbook") for p in lst
          if len(p.relative_to(root).parts) <= 4]
    print(f"- widgetbook/catalog dirs: {' '.join(wb)}")
    mains = [rel(p, root) for p in sorted(dart_files)
             if p.name.startswith("main") and p.parent.name == "lib" and len(p.relative_to(root).parts) <= 5]
    print(f"- entrypoints (main*.dart): {' '.join(mains)}")
    flags = sorted({m for src in dart_src.values() for m in ENV_FLAG.findall(src)})[:6]
    print(f"- fake/mock data flags: {' '.join(flags)}")
    web = (root / "web").is_dir() or bool(list(root.glob("*/web"))) or bool(list(root.glob("*/*/web")))
    print(f"- web target enabled: {'yes' if web else 'no'}")

    h("Next")
    print("Confirm the design-system candidate by opening its barrel; if there is more than one token file, "
          "find the one that generates code before editing (see references/repo-scan.md).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
