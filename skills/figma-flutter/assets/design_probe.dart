// design_probe.dart — generic "measure the rendered tree" helper for Flutter
// widget tests. Copy this file into the repo (e.g. `test/support/design_probe.dart`
// or `lib/testing/design_probe.dart` of the design-system package) when the
// repo has no equivalent yet. No dependencies beyond flutter_test.
//
// What it does
//   probeDesign(element)         → JSON-able map of the rendered tree with the
//                                  values the eye cannot verify: rect, padding,
//                                  radius, border, shadow, gradient, color,
//                                  font family/size/weight/height/letterSpacing,
//                                  icon glyph/size/color, image asset/fit,
//                                  tap-target rects.
//   expectDesignSnapshot(...)    → writes the JSON on first run, fails on any
//                                  change afterwards. Accept intentional changes
//                                  with UPDATE_DESIGN_SNAPSHOTS=true.
//   expectMinTapTargets(...)     → every tappable widget is at least N logical px.
//   loadAppFonts()               → loads the fonts declared in pubspec so text is
//                                  measured with the real family, not Ahem.
//
// Why: image goldens run with the Ahem test font and no shadows, so they cannot
// see the exact defects that make a screen diverge from Figma. This probe
// compares number against number instead.

import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';

/// Environment variable that lets `expectDesignSnapshot` overwrite snapshots.
const String updateSnapshotsFlag = 'UPDATE_DESIGN_SNAPSHOTS';

/// Widget type names (runtimeType.toString()) that should be recorded with
/// their rect even though this file does not know their API — e.g.
/// `SvgPicture`, `CachedNetworkImage`, `Lottie`. Extend from your test setup.
final Set<String> extraRecordedTypes = <String>{
  'SvgPicture',
  'CachedNetworkImage',
  'LottieBuilder',
  'VectorGraphic',
};

// ---------------------------------------------------------------------------
// Probe
// ---------------------------------------------------------------------------

/// Describes the rendered subtree under [root]. Coordinates are relative to
/// [root]'s top-left corner, rounded to 2 decimals.
Map<String, Object?> probeDesign(Element root, {String? label}) {
  final origin = _globalOffset(root);
  final node = _describe(root, origin);
  return <String, Object?>{
    if (label != null) 'label': label,
    'tree': node,
  };
}

Offset _globalOffset(Element element) {
  final object = element.renderObject;
  if (object is RenderBox && object.hasSize && object.attached) {
    return object.localToGlobal(Offset.zero);
  }
  return Offset.zero;
}

Map<String, Object?>? _describe(Element element, Offset origin) {
  final children = <Map<String, Object?>>[];
  element.visitChildren((child) {
    final described = _describe(child, origin);
    if (described != null) children.add(described);
  });

  final own = _own(element, origin);
  if (own == null) {
    if (children.isEmpty) return null;
    if (children.length == 1) return children.first;
    return <String, Object?>{'type': '_group', 'children': children};
  }
  if (children.isNotEmpty) own['children'] = children;
  return own;
}

Map<String, Object?>? _own(Element element, Offset origin) {
  final widget = element.widget;
  final style = _style(widget, element);
  if (style == null) return null;

  final box = element.renderObject;
  final rect = box is RenderBox && box.hasSize && box.attached
      ? _rect(box, origin)
      : null;

  return <String, Object?>{
    'type': widget.runtimeType.toString(),
    if (widget.key != null) 'key': widget.key.toString(),
    if (rect != null) 'rect': rect,
    ...style,
  };
}

Map<String, Object?> _rect(RenderBox box, Offset origin) {
  final offset = box.localToGlobal(Offset.zero) - origin;
  return <String, Object?>{
    'x': _round(offset.dx),
    'y': _round(offset.dy),
    'w': _round(box.size.width),
    'h': _round(box.size.height),
  };
}

Map<String, Object?>? _style(Widget widget, Element element) {
  if (widget is RichText) return _text(element);
  if (widget is Icon) return _icon(widget);
  if (widget is Image) return _image(widget);
  if (widget is Padding) {
    return <String, Object?>{'padding': _edges(widget.padding)};
  }
  if (widget is ColoredBox) {
    return <String, Object?>{'color': _color(widget.color)};
  }
  if (widget is DecoratedBox) return _decoration(widget.decoration);
  if (widget is Material) return _material(widget);
  if (widget is PhysicalModel) {
    return <String, Object?>{
      'elevation': widget.elevation,
      'color': _color(widget.color),
      'shadowColor': _color(widget.shadowColor),
      'radius': _radius(widget.borderRadius),
    };
  }
  if (widget is PhysicalShape) {
    return <String, Object?>{
      'elevation': widget.elevation,
      'color': _color(widget.color),
      'shadowColor': _color(widget.shadowColor),
    };
  }
  if (widget is ClipRRect) {
    return <String, Object?>{'clipRadius': _radius(widget.borderRadius)};
  }
  if (widget is Opacity) {
    return <String, Object?>{'opacity': _round(widget.opacity)};
  }
  if (widget is SizedBox && (widget.width != null || widget.height != null)) {
    return <String, Object?>{
      if (widget.width != null) 'width': _round(widget.width!),
      if (widget.height != null) 'height': _round(widget.height!),
    };
  }
  if (widget is ConstrainedBox) {
    final c = widget.constraints;
    return <String, Object?>{
      'constraints': <String, Object?>{
        'minW': _finite(c.minWidth),
        'maxW': _finite(c.maxWidth),
        'minH': _finite(c.minHeight),
        'maxH': _finite(c.maxHeight),
      },
    };
  }
  if (widget is Flex) {
    return <String, Object?>{
      'direction': widget.direction.name,
      'spacing': widget.spacing,
      'mainAxisAlignment': widget.mainAxisAlignment.name,
      'crossAxisAlignment': widget.crossAxisAlignment.name,
      'mainAxisSize': widget.mainAxisSize.name,
    };
  }
  if (widget is Wrap) {
    return <String, Object?>{
      'direction': widget.direction.name,
      'spacing': widget.spacing,
      'runSpacing': widget.runSpacing,
    };
  }
  if (widget is Align && widget is! Center) {
    return <String, Object?>{'alignment': widget.alignment.toString()};
  }
  if (widget is Positioned) {
    return <String, Object?>{
      'positioned': <String, Object?>{
        if (widget.left != null) 'left': _round(widget.left!),
        if (widget.top != null) 'top': _round(widget.top!),
        if (widget.right != null) 'right': _round(widget.right!),
        if (widget.bottom != null) 'bottom': _round(widget.bottom!),
      },
    };
  }
  if (_isTapTarget(widget)) {
    return <String, Object?>{'tapTarget': true};
  }
  if (extraRecordedTypes.contains(widget.runtimeType.toString())) {
    return <String, Object?>{};
  }
  return null;
}

bool _isTapTarget(Widget widget) {
  if (widget is InkResponse) return widget.onTap != null;
  if (widget is GestureDetector) {
    return widget.onTap != null || widget.onTapDown != null;
  }
  if (widget is ButtonStyleButton) return widget.onPressed != null;
  if (widget is IconButton) return widget.onPressed != null;
  return false;
}

Map<String, Object?> _text(Element element) {
  final object = element.renderObject;
  final span = object is RenderParagraph ? object.text : null;
  final style = span?.style;
  return <String, Object?>{
    'text': span?.toPlainText(includeSemanticsLabels: false) ?? '',
    if (style != null) ...<String, Object?>{
      'fontFamily': style.fontFamily,
      'fontSize': style.fontSize,
      'fontWeight': style.fontWeight?.value,
      if (style.fontStyle == FontStyle.italic) 'fontStyle': 'italic',
      'height': style.height,
      'letterSpacing': style.letterSpacing,
      'color': _color(style.color),
      if (style.decoration != null && style.decoration != TextDecoration.none)
        'decoration': style.decoration.toString(),
    },
    if (object is RenderParagraph) ...<String, Object?>{
      'textAlign': object.textAlign.name,
      if (object.maxLines != null) 'maxLines': object.maxLines,
      'overflow': object.overflow.name,
      'didOverflow': object.didExceedMaxLines,
    },
  };
}

Map<String, Object?> _icon(Icon widget) => <String, Object?>{
      'codePoint': widget.icon?.codePoint,
      'iconFamily': widget.icon?.fontFamily,
      'size': widget.size,
      'color': _color(widget.color),
      if (widget.semanticLabel != null) 'semanticLabel': widget.semanticLabel,
    };

Map<String, Object?> _image(Image widget) {
  final provider = widget.image;
  String source = provider.runtimeType.toString();
  if (provider is AssetImage) source = provider.assetName;
  if (provider is ExactAssetImage) source = provider.assetName;
  if (provider is NetworkImage) source = provider.url;
  return <String, Object?>{
    'source': source,
    if (widget.width != null) 'width': _round(widget.width!),
    if (widget.height != null) 'height': _round(widget.height!),
    if (widget.fit != null) 'fit': widget.fit!.name,
    if (widget.color != null) 'tint': _color(widget.color),
  };
}

Map<String, Object?> _material(Material widget) {
  final shape = widget.shape;
  return <String, Object?>{
    'color': _color(widget.color),
    'elevation': widget.elevation,
    'shadowColor': _color(widget.shadowColor),
    if (widget.borderRadius case final BorderRadius radius)
      'radius': _radius(radius),
    if (shape is RoundedRectangleBorder) ...<String, Object?>{
      'radius': _radius(shape.borderRadius),
      'border': _side(shape.side),
    },
    if (shape is StadiumBorder) 'shape': 'stadium',
    if (shape is CircleBorder) 'shape': 'circle',
  };
}

Map<String, Object?>? _decoration(Decoration decoration) {
  if (decoration is! BoxDecoration) {
    if (decoration is ShapeDecoration) {
      final shape = decoration.shape;
      return <String, Object?>{
        'color': _color(decoration.color),
        if (shape is RoundedRectangleBorder) ...<String, Object?>{
          'radius': _radius(shape.borderRadius),
          'border': _side(shape.side),
        },
        if (decoration.shadows case final List<BoxShadow> shadows)
          'shadow': _shadows(shadows),
      };
    }
    return null;
  }
  final border = decoration.border;
  return <String, Object?>{
    'color': _color(decoration.color),
    if (decoration.shape != BoxShape.rectangle) 'shape': decoration.shape.name,
    if (decoration.borderRadius case final BorderRadius radius)
      'radius': _radius(radius),
    if (border is Border) 'border': _border(border),
    if (decoration.gradient case final Gradient gradient)
      'gradient': _gradient(gradient),
    if (decoration.image case final DecorationImage image)
      'image': <String, Object?>{
        'source': image.image is AssetImage
            ? (image.image as AssetImage).assetName
            : image.image.runtimeType.toString(),
        'fit': image.fit?.name,
      },
    if (decoration.boxShadow case final List<BoxShadow> shadows)
      'shadow': _shadows(shadows),
  };
}

List<Map<String, Object?>> _shadows(List<BoxShadow> shadows) => [
      for (final shadow in shadows)
        <String, Object?>{
          'color': _color(shadow.color),
          'dx': _round(shadow.offset.dx),
          'dy': _round(shadow.offset.dy),
          'blur': _round(shadow.blurRadius),
          'spread': _round(shadow.spreadRadius),
          if (shadow.blurStyle != BlurStyle.normal)
            'blurStyle': shadow.blurStyle.name,
        },
    ];

Map<String, Object?> _gradient(Gradient gradient) => <String, Object?>{
      'kind': gradient.runtimeType.toString(),
      'colors': [for (final c in gradient.colors) _color(c)],
      if (gradient.stops != null)
        'stops': [for (final s in gradient.stops!) _round(s)],
      if (gradient is LinearGradient) ...<String, Object?>{
        'begin': gradient.begin.toString(),
        'end': gradient.end.toString(),
      },
      if (gradient is RadialGradient) ...<String, Object?>{
        'center': gradient.center.toString(),
        'radius': _round(gradient.radius),
      },
    };

Object? _border(Border border) {
  if (border.isUniform) return _side(border.top);
  return <String, Object?>{
    'top': _side(border.top),
    'right': _side(border.right),
    'bottom': _side(border.bottom),
    'left': _side(border.left),
  };
}

Map<String, Object?>? _side(BorderSide side) => side.style == BorderStyle.none
    ? null
    : <String, Object?>{
        'color': _color(side.color),
        'width': side.width,
        if (side.strokeAlign != BorderSide.strokeAlignInside)
          'strokeAlign': side.strokeAlign,
      };

Map<String, Object?>? _radius(BorderRadiusGeometry? radius) {
  if (radius == null) return null;
  final r = radius.resolve(TextDirection.ltr);
  if (r == BorderRadius.zero) return null;
  return <String, Object?>{
    'topLeft': _round(r.topLeft.x),
    'topRight': _round(r.topRight.x),
    'bottomRight': _round(r.bottomRight.x),
    'bottomLeft': _round(r.bottomLeft.x),
  };
}

Map<String, Object?> _edges(EdgeInsetsGeometry padding) {
  final resolved = padding.resolve(TextDirection.ltr);
  return <String, Object?>{
    'left': _round(resolved.left),
    'top': _round(resolved.top),
    'right': _round(resolved.right),
    'bottom': _round(resolved.bottom),
  };
}

String? _color(Color? color) {
  if (color == null) return null;
  final value = color.toARGB32();
  return '#${value.toRadixString(16).padLeft(8, '0').toUpperCase()}';
}

double _round(double value) => (value * 100).roundToDouble() / 100;

Object? _finite(double value) => value.isFinite ? _round(value) : null;

// ---------------------------------------------------------------------------
// Snapshot
// ---------------------------------------------------------------------------

/// Compares [probe] with the JSON stored at [path]. Writes the file when it
/// does not exist or when `UPDATE_DESIGN_SNAPSHOTS=true`; otherwise throws on
/// any difference and leaves the new JSON at `<path>.actual` for inspection.
void expectDesignSnapshot(Map<String, Object?> probe, {required String path}) {
  const encoder = JsonEncoder.withIndent('  ');
  final actual = '${encoder.convert(probe)}\n';
  final file = File(path);
  final update = Platform.environment[updateSnapshotsFlag] == 'true';

  if (!file.existsSync() || update) {
    file.parent.createSync(recursive: true);
    file.writeAsStringSync(actual);
    return;
  }

  final expected = file.readAsStringSync();
  if (expected == actual) return;

  File('$path.actual').writeAsStringSync(actual);
  throw StateError(
    'design snapshot changed: $path\n'
    '${_diff(expected, actual)}\n'
    'new snapshot written to $path.actual — '
    'to accept it, run with $updateSnapshotsFlag=true',
  );
}

String _diff(String expected, String actual) {
  final left = const LineSplitter().convert(expected);
  final right = const LineSplitter().convert(actual);
  final lines = <String>[];
  for (var i = 0; i < left.length || i < right.length; i++) {
    final before = i < left.length ? left[i] : '';
    final after = i < right.length ? right[i] : '';
    if (before == after) continue;
    lines.add('line ${i + 1}\n  before: $before\n  after:  $after');
    if (lines.length == 10) break;
  }
  return lines.join('\n');
}

// ---------------------------------------------------------------------------
// Accessibility helpers
// ---------------------------------------------------------------------------

/// Throws when any recorded tap target is smaller than [minSize] logical
/// pixels on either axis (Material: 48, Apple HIG: 44).
void expectMinTapTargets(Map<String, Object?> probe, {double minSize = 48}) {
  final offenders = <String>[];
  void walk(Object? node) {
    if (node is! Map<String, Object?>) return;
    if (node['tapTarget'] == true && node['rect'] is Map) {
      final rect = node['rect'] as Map<String, Object?>;
      final w = rect['w'] as double;
      final h = rect['h'] as double;
      if (w < minSize || h < minSize) {
        offenders.add('${node['type']} ${node['key'] ?? ''} ${w}x$h');
      }
    }
    final children = node['children'];
    if (children is List) children.forEach(walk);
  }

  walk(probe['tree']);
  if (offenders.isNotEmpty) {
    throw StateError(
      'tap targets smaller than ${minSize}px:\n  ${offenders.join('\n  ')}',
    );
  }
}

// ---------------------------------------------------------------------------
// Fonts
// ---------------------------------------------------------------------------

bool _fontsLoaded = false;

/// Loads every font family declared in the app's `FontManifest.json` so the
/// probe measures text with the real family instead of the Ahem test font.
/// Call once in `setUpAll`. Fonts from `google_fonts` are not in the manifest;
/// bundle the TTFs in pubspec for tests that need them.
Future<void> loadAppFonts() async {
  if (_fontsLoaded) return;
  final manifest = await rootBundle.loadStructuredData<List<dynamic>>(
    'FontManifest.json',
    (source) async => json.decode(source) as List<dynamic>,
  );

  for (final entry in manifest.cast<Map<String, dynamic>>()) {
    final family = entry['family'] as String?;
    if (family == null) continue;
    final loader = FontLoader(family);
    for (final font in (entry['fonts'] as List<dynamic>?) ?? const []) {
      final asset = (font as Map<String, dynamic>)['asset'] as String?;
      if (asset == null) continue;
      loader.addFont(rootBundle.load(asset));
    }
    await loader.load();
  }
  _fontsLoaded = true;
}
