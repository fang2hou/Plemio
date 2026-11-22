from __future__ import annotations

from collections.abc import Collection

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

from plemio.measure import STEM_PROBE, stem_width

CALIBRATION_STEPS = 16


def subset_font(font: TTFont, codepoints: Collection[int]) -> TTFont:
    options = subset.Options()
    options.layout_features = []
    options.notdef_outline = True
    options.name_IDs = ["*"]
    options.glyph_names = True
    options.recalc_timestamp = False
    subsetter = subset.Subsetter(options)
    subsetter.populate(unicodes=codepoints)
    subsetter.subset(font)
    return font


def weight_range(font: TTFont) -> tuple[float, float]:
    axis = next(axis for axis in font["fvar"].axes if axis.axisTag == "wght")
    return axis.minValue, axis.maxValue


def calibrate_weight(path: str, target_stem: float, axes: dict[str, float]) -> float:
    with TTFont(path) as font:
        probe = subset_font(font, [ord(STEM_PROBE)])
        low, high = weight_range(probe)
        for _ in range(CALIBRATION_STEPS):
            middle = (low + high) / 2
            instance = instantiateVariableFont(probe, {"wght": middle, **axes}, inplace=False)
            if stem_width(instance) < target_stem:
                low = middle
            else:
                high = middle
    return round((low + high) / 2, 1)


def instantiate(
    path: str, weight: float, axes: dict[str, float], covered: Collection[int]
) -> TTFont:
    font = TTFont(path)
    font = subset_font(font, set(font.getBestCmap()) - set(covered))
    return instantiateVariableFont(font, {"wght": weight, **axes}, inplace=True)


def load_static(path: str, covered: Collection[int]) -> TTFont:
    font = TTFont(path)
    return subset_font(font, set(font.getBestCmap()) - set(covered))
