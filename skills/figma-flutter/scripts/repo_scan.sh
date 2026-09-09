#!/usr/bin/env bash
# repo_scan.sh — prints a "Repo Profile" for a Flutter repo: where the design
# system lives, which tokens exist, where features put their widgets, which
# verification tooling is already there. Read-only. Usage:
#   scripts/repo_scan.sh [repo-root]
set -u
ROOT="${1:-.}"
FEATURE="${2:-}"   # optional feature name (e.g. profile) to spotlight its package, spec, and tests
cd "$ROOT" || { echo "no such dir: $ROOT"; exit 1; }
# ff DEPTH EXPR... → find with build/tool dirs pruned. Example: ff 5 -name pubspec.yaml
ff() { local d="$1"; shift; find . -maxdepth "$d" \( -name .dart_tool -o -name build -o -name .fvm -o -name node_modules -o -name ios -o -name android -o -name macos -o -name linux -o -name windows -o -name .symlinks -o -name .git \) -prune -o \( "$@" \) -print 2>/dev/null; }
# G ARGS... → recursive grep over .dart files with the same dirs excluded
G() { grep -r --exclude-dir=.dart_tool --exclude-dir=build --exclude-dir=.fvm --exclude-dir=node_modules --exclude-dir=ios --exclude-dir=android --exclude-dir=.git --include='*.dart' "$@" . 2>/dev/null; }
GY() { grep -r --exclude-dir=.dart_tool --exclude-dir=build --exclude-dir=.fvm --exclude-dir=node_modules --exclude-dir=ios --exclude-dir=android --exclude-dir=.git --include='pubspec.yaml' "$@" . 2>/dev/null; }

h() { printf '\n## %s\n' "$1"; }
have() { command -v "$1" >/dev/null 2>&1; }

echo "# Repo Profile — $(basename "$(pwd)") ($(pwd))"

h "Toolchain"
[ -f .fvmrc ] && echo "- fvm: $(grep -o '"flutter"[^,}]*' .fvmrc | head -1)"
[ -f .fvm/fvm_config.json ] && echo "- fvm: $(grep -o '"flutterSdkVersion"[^,}]*' .fvm/fvm_config.json)"
[ -f melos.yaml ] && echo "- melos.yaml present (monorepo)"
grep -q '^workspace:' pubspec.yaml 2>/dev/null && echo "- pub workspace (monorepo) in root pubspec"
[ -f Makefile ] && echo "- Makefile targets: $(grep -oE '^[a-zA-Z_-]+:' Makefile | tr -d ':' | tr '\n' ' ' | cut -c1-160)"

h "Architecture docs (read these before writing code)"
ff 3 -iname 'CLAUDE.md' -o -iname 'ARCHITECTURE*.md' -o -iname 'CONTRIBUTING*.md' -o -iname 'AGENTS.md' -o -iname 'DESIGN*.md' | sed 's|^\./||' | sed 's/^/- /'
# a monorepo sub-project often inherits CLAUDE.md from a parent directory
for up in .. ../..; do [ -f "$up/CLAUDE.md" ] && echo "- parent: $(cd "$up" && pwd)/CLAUDE.md  ← inherited rules (e.g. \"plan mode first\")"; done
[ -f docs/README.md ] && echo "- docs/README.md (index)"
[ -d docs/adr ] && echo "- docs/adr/: $(ls docs/adr/*.md 2>/dev/null | wc -l | tr -d ' ') ADRs — $(ls docs/adr 2>/dev/null | grep -iE 'design|token|widget|test|icon|arch' | tr '\n' ' ')"
[ -d docs/specs ] && echo "- docs/specs/: $(ls docs/specs 2>/dev/null | tr '\n' ' ' | cut -c1-200)"
[ -n "$FEATURE" ] && ff 4 -type f -iname "*${FEATURE}*.md" | sed 's|^\./||' | sed "s/^/- feature doc: /"
ff 4 -type d \( -iname 'docs' -o -iname 'doc' \) | head -5 | sed 's|^\./||' | sed 's/^/- dir: /'
echo "- design captures already in repo: $(ff 5 -type d \( -iname 'design' -o -iname 'figma' -o -iname 'captures' \) -path '*docs*' | tr '\n' ' ')"

h "Packages (pubspec.yaml)"
ff 5 -name pubspec.yaml | sed 's|^\./||' | sort | while read -r p; do
  name=$(grep -m1 '^name:' "$p" | awk '{print $2}')
  dir=$(dirname "$p")
  tag=""
  echo "$name $dir" | grep -qiE 'design|ui_kit|uikit|theme|foundation|components|widgets|core_ui|_ui$' && tag=" ← design-system candidate"
  echo "$dir" | grep -qiE 'feature' && tag=" (feature)"
  echo "$dir" | grep -qiE 'widgetbook|storybook|catalog' && tag=" (component catalog)"
  echo "- $name → $dir$tag"
done

h "Design-system signals"
echo "- barrels (lib/*.dart exporting src/):"
ff 6 -path '*/lib/*.dart' -not -path '*/lib/*/*' | while read -r f; do
  grep -q "^export 'src/" "$f" 2>/dev/null && echo "    $f ($(grep -c '^export' "$f") exports)"
done | sed 's|\./||' | head -20
echo "- ThemeExtension classes:"
G -lE 'extends ThemeExtension<' | head -12 | sed 's|^\./|    |'
echo "- token-like classes (Colors/Spacing/Typography/Radius/Shadows/Elevation/Icons):"
G -hoE '(abstract |final )?class [A-Z][A-Za-z]*(Colors?|Color(Scheme|s)|Spacing|Space|Sizes?|Typography|TextStyles|Text(Theme|Styles)|Radi(us|i)|Shadows?|Elevations?|Icons|Tokens|Gaps?|Dimens|Insets)\b' --exclude='*.g.dart' | sed -E 's/^(abstract |final )?class //' | sort | uniq -c | sort -rn | head -25 | awk '{printf "    %s (%s)\n",$2,$1}'
echo "- BuildContext extensions (context.colors / context.spacing …):"
G -hoE 'extension [A-Za-z]+ on BuildContext' | sort -u | head -8 | sed 's/^/    /'
echo "- token codegen / theme tooling:"
GY -hoE '^\s+(theme_tailor|theme_tailor_annotation|design_tokens_builder|design_builder|flutter_gen|flutter_gen_runner|google_fonts|flutter_svg|vector_graphics|vector_graphics_compiler|lucide_icons_flutter|phosphor_flutter|flutter_screenutil|responsive_framework|widgetbook|widgetbook_annotation|alchemist|golden_toolkit|flutter_test_goldens|freezed|bloc|flutter_bloc|riverpod|flutter_riverpod|provider|get_it|auto_route|go_router|flutter_modular|melos):' --include=pubspec.yaml . 2>/dev/null | tr -d ' :' | sort | uniq -c | sort -rn | awk '{printf "    %s (×%s)\n",$2,$1}'
echo "- fonts declared in pubspec:"
GY -hE '^\s+- family:' | awk '{print $3}' | sort -u | tr '\n' ' ' | sed 's/^/    /'; echo
echo "- design-system catalog docs:"
ff 5 -type f \( -iname '*catalog*.md' -o -iname '*components*.md' -o -iname '*tokens*.md' -o -iname '*design-system*.md' -o -iname '*design_system*.md' \) | sed 's|^\./|    |' | head -8

h "Assets"
ff 5 -type d \( -iname 'assets' -o -iname 'asset' \) -not -path '*/web/*' | sed 's|^\./||' | while read -r d; do
  svg=$(find "$d" -name '*.svg' 2>/dev/null | wc -l | tr -d ' '); png=$(find "$d" \( -name '*.png' -o -name '*.webp' -o -name '*.jpg' \) 2>/dev/null | wc -l | tr -d ' ')
  sub=$(find "$d" -maxdepth 1 -mindepth 1 -type d 2>/dev/null | sed 's|.*/||' | tr '\n' ' ')
  echo "- $d — svg:$svg raster:$png — subdirs: $sub"
done | head -12
ff 6 -type d \( -name '2.0x' -o -name '3.0x' \) | head -3 | sed 's|^\./|- scale dirs: |'
G -lE 'flutter_gen|class Assets\b' | grep -E 'gen/|\.gen\.dart' | head -3 | sed 's|^\./|- generated assets class: |'
echo "- SVG rendering: $(G -lE 'SvgPicture|VectorGraphic' | wc -l | tr -d ' ') files use flutter_svg/vector_graphics"
echo "- icon families in code: $(G -hoE '\b(Icons|CupertinoIcons|LucideIcons|PhosphorIcons|FontAwesomeIcons|HeroIcons|[A-Z][A-Za-z]*Icons)\.[a-zA-Z0-9_]+' | cut -d. -f1 | sort | uniq -c | sort -rn | head -5 | awk '{printf "%s(×%s) ",$2,$1}')"

h "Where feature widgets live (top-level layout under lib/)"
for lib in $(ff 4 -type d -name lib | grep -vE 'widgetbook|example' | head -6); do
  top=$(find "$lib" -maxdepth 1 -mindepth 1 -type d | sed 's|.*/||' | sort | tr '\n' ' ')
  [ "$top" = "src " ] && top="src/: $(find "$lib/src" -maxdepth 1 -mindepth 1 -type d | sed 's|.*/||' | sort | tr '\n' ' ')"
  echo "- $lib: $top"
  for f in $(find "$lib" -maxdepth 3 -type d \( -iname 'features' -o -iname 'modules' -o -iname 'pages' -o -iname 'presentation' -o -iname 'ui' -o -iname 'screens' -o -iname 'views' \) | head -4); do
    inner=$(find "$f" -maxdepth 1 -mindepth 1 | sed 's|.*/||' | sort | head -12 | tr '\n' ' ')
    echo "    $f/: $inner"
  done
done
echo "- one sample feature (deepest 'presentation'/'ui' dir, first found):"
sample=$(ff 8 -type d \( -iname presentation -o -iname ui \) -path '*feature*' | head -1)
[ -n "$sample" ] && find "$sample" -maxdepth 2 | sed 's|^\./|    |' | head -15

if [ -n "$FEATURE" ]; then
  h "Feature spotlight: $FEATURE"
  for d in $(ff 5 -type d -iname "*${FEATURE}*" | grep -vE '/test/|/build/|widgetbook' | head -4); do
    echo "- $d"; find "$d" -type f -name '*.dart' -path '*lib*' | sed "s|^$d/|    |" | sort | head -40
  done
  echo "- tests: $(ff 5 -type d -iname "*${FEATURE}*" -path '*test*' | head -2 | tr '\n' ' ')"
fi

h "Verification tooling already present"
echo "- design probe / snapshot: $(G -lE 'probeDesign|expectDesignSnapshot|design_probe' | head -3 | tr '\n' ' ')"
echo "- golden tests: $(G -lE 'matchesGoldenFile|goldenTest\(|GoldenTestGroup' | wc -l | tr -d ' ') files"
echo "- flutter_test_config.dart: $(ff 7 -name flutter_test_config.dart | head -3 | tr '\n' ' ')"
echo "- font loading in tests: $(G -lE 'loadAppFonts|FontLoader\(' | head -3 | tr '\n' ' ')"
echo "- widgetbook/catalog dirs: $(ff 4 -type d -iname 'widgetbook*' | tr '\n' ' ')"
echo "- entrypoints (main*.dart): $(ff 5 -path '*/lib/main*.dart' | sed 's|^\./||' | tr '\n' ' ')"
echo "- fake/mock data flags: $(G -hoE 'bool\.fromEnvironment\([^)]*\)|String\.fromEnvironment\([^)]*\)' | sort -u | head -6 | tr '\n' ' ')"
echo "- web target enabled: $([ -d web ] || ls */web >/dev/null 2>&1 || ls */*/web >/dev/null 2>&1 && echo yes || echo no)"

h "Next"
echo "Confirm the design-system candidate by opening its barrel; if there is more than one token file, find the one that generates code before editing (see references/repo-scan.md)."
