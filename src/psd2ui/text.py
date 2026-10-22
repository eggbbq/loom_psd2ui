"""Extract styles, never rasterize ordinary text or invent missing styles."""
import math


def text_bounds(layer, diagnostics, path):
    """Map Photoshop's text layout rectangle to document pixels.

    layer.bbox is the *ink* rectangle. A Laya Text positions its layout box;
    using the ink origin would apply font bearings/ascenders a second time.
    Do not use boundingBox here: that descriptor also describes glyph ink.
    """
    try:
        bounds = layer._data.text_data.get(b"bounds")
        if bounds is None:
            raise ValueError("PSD text layout 'bounds' descriptor is missing")
        left, top, right, bottom = (float(bounds[k]) for k in (b"Left", b"Top ", b"Rght", b"Btom"))
        a, b, c, d, tx, ty = map(float, layer.transform)
        if (not all(math.isfinite(v) for v in (left, top, right, bottom, a, b, c, d, tx, ty)) or
                right <= left or bottom <= top or abs(a * d - b * c) < 1e-12):
            raise ValueError("PSD text layout bounds/transform are invalid")
        points = [(a * x + c * y + tx, b * x + d * y + ty)
                  for x, y in ((left, top), (right, top), (left, bottom), (right, bottom))]
        box = tuple(round(v, 4) for v in (
            min(p[0] for p in points), min(p[1] for p in points),
            max(p[0] for p in points), max(p[1] for p in points)))
        if box[2] <= box[0] or box[3] <= box[1]:
            raise ValueError("Transformed text layout rectangle is empty")
        return box
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        diagnostics.warn("UNREADABLE_TEXT_BOUNDS", path,
                         f"{exc}; using cached glyph bounds as an approximate fallback")
        return layer.bbox


def rgba(values):
    a, r, g, b = (max(0, min(255, round(float(v) * 255))) for v in values)
    return f"#{r:02X}{g:02X}{b:02X}" + (f"{a:02X}" if a != 255 else "")


def effect_color(effect):
    d = effect.color
    if d is None or any(k not in d for k in (b"Rd  ", b"Grn ", b"Bl  ")):
        raise ValueError("Only RGB effect colors are supported")
    return rgba([effect.opacity / 100, *(float(d[k]) / 255 for k in (b"Rd  ", b"Grn ", b"Bl  "))])


def text_properties(layer, diagnostics, path):
    result = {"text": layer.text.replace("\r\n", "\n").replace("\r", "\n"),
              "align": "left", "outline": 0}
    if layer.opacity != 255:
        result["opacity"] = layer.opacity / 255
    try:
        ts = layer.typesetting
        runs = [r for r in ts.runs if r.text.strip("\r\n\x00")]
        if not runs:
            raise ValueError("No readable text style runs")
        style = runs[0].style
        # Unlike the convenience accessor's fallback, require a real FontSize.
        if style._get("FontSize") is None or not style.font_name or style.fill_color is None:
            raise ValueError("Missing font, FontSize, or FillColor")
        a, b, c, d, _, _ = layer.transform
        sx, sy = math.hypot(a, b), math.hypot(c, d)
        if sy <= 0 or not math.isfinite(sy * style.font_size):
            raise ValueError("Invalid text transform/font size")
        # EngineData FontSize is the text-space size; transform maps it to PSD pixels.
        result.update(font=style.font_name, fontSize=round(style.font_size * sy, 4),
                      color=rgba(style.fill_color))
        if abs(b) > 1e-5 or abs(c) > 1e-5 or abs(sx - sy) > 1e-4 or a < 0 or d < 0:
            diagnostics.warn("UNSUPPORTED_VISUAL_EFFECT", path,
                             "Rotated, mirrored, skewed or nonuniformly scaled text is approximated")
        signatures = {(r.style.font_name, r.style.font_size, r.style.fill_color,
                       r.style.faux_bold, r.style.faux_italic,
                       r.style._get("Tracking"), r.style._get("BaselineShift")) for r in runs}
        justifications = {int(p.style.justification) for p in ts.paragraphs}
        if len(signatures) > 1 or len(justifications) > 1:
            diagnostics.warn("UNSUPPORTED_RICH_TEXT", path, "Multiple text styles; using first readable run/paragraph")
        if ts.paragraphs:
            result["align"] = {0: "left", 1: "right", 2: "center"}.get(int(ts.paragraphs[0].style.justification), "left")
            if any(j not in (0, 1, 2) for j in justifications):
                diagnostics.warn("UNSUPPORTED_VISUAL_EFFECT", path, "Justified text is approximated as left aligned")
        if (style.faux_bold or style.faux_italic or style.stroke_flag or
                style._get("Tracking", 0) or style._get("BaselineShift", 0) or
                int(ts.writing_direction or 0) != 0):
            diagnostics.warn("UNSUPPORTED_VISUAL_EFFECT", path,
                             "Character decorations, tracking, baseline shift or vertical writing are not mapped in V1")
    except Exception as exc:
        diagnostics.warn("UNREADABLE_TEXT_STYLE", path, str(exc))

    seen = set()
    for effect in layer.effects:
        if not layer.effects.enabled or not effect.enabled:
            continue
        try:
            if effect.name in seen:
                diagnostics.warn("UNSUPPORTED_VISUAL_EFFECT", path, f"Multiple {effect.name} effects; last style wins")
            seen.add(effect.name)
            if effect.name == "Stroke":
                result.update(outline=float(effect.size), outlineColor=effect_color(effect))
            elif effect.name == "DropShadow":
                angle = math.radians(float(effect.angle))
                result.update(shadow=[round(-math.cos(angle) * effect.distance, 4),
                                      round(math.sin(angle) * effect.distance, 4)],
                              shadowColor=effect_color(effect), shadowBlur=float(effect.size))
            else:
                continue  # The shared visual inspection reports unsupported effects.
        except Exception as exc:
            diagnostics.warn("UNREADABLE_TEXT_STYLE", path, f"Cannot read {effect.name}: {exc}")
    return result

