from __future__ import annotations

import math

from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont

from plemio.placement import Box

STEM_PROBE = "|"
CELL_PROBE = "0"
LINE_PROBE = "█"
VERTICAL_STROKE_PROBES = "┃║"


def ink_box(font: TTFont, char: str) -> Box:
    glyph_set = font.getGlyphSet()
    pen = BoundsPen(glyph_set)
    glyph_set[font.getBestCmap()[ord(char)]].draw(pen)
    return Box(*pen.bounds)


def stem_width(font: TTFont) -> float:
    return ink_box(font, STEM_PROBE).width


def italic_pivot(upright: TTFont, italic: TTFont) -> float:
    straight, slanted = ink_box(upright, STEM_PROBE), ink_box(italic, STEM_PROBE)
    shear = math.tan(math.radians(-italic["post"].italicAngle))
    return slanted.center_y - (slanted.center_x - straight.center_x) / shear


def line_art_span(font: TTFont) -> tuple[float, float]:
    box = ink_box(font, LINE_PROBE)
    return box.y_min, box.y_max


def vertical_stroke_band(font: TTFont) -> tuple[float, float]:
    boxes = [ink_box(font, char) for char in VERTICAL_STROKE_PROBES]
    return min(box.x_min for box in boxes), max(box.x_max for box in boxes)


def cap_height(font: TTFont) -> float:
    return font["OS/2"].sCapHeight / font["head"].unitsPerEm


def cell_width(font: TTFont) -> int:
    return font["hmtx"][font.getBestCmap()[ord(CELL_PROBE)]][0]
