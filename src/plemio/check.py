from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from fontTools.ttLib import TTFont

from plemio.compose import MAX_GLYPHS
from plemio.config import Config
from plemio.jobs import BuildJob, job_for_filename
from plemio.measure import cell_width
from plemio.unicode import AmbiguousWidth, allowed_cells, is_control, is_zero_width

REQUIRED_TEXT = "Aa0|中文漢字かなカナ한글│█⣿→"
NERD_FONTS_TEXT = "\ue0b0\uf015\uf09b"


def check_font(config: Config, path: Path) -> list[str]:
    job = job_for_filename(config, path.name)
    if job is None:
        return [f"{path.name} does not match any planned build"]
    with TTFont(path) as font:
        return list(_problems(config, font, job))


def _problems(config: Config, font: TTFont, job: BuildJob) -> Iterator[str]:
    cmap = font.getBestCmap()
    advances = {name: advance for name, (advance, _) in font["hmtx"].metrics.items()}
    variant = config.variants[job.variant]
    cell = cell_width(font)
    if cell != variant.half_width:
        yield f"cell width {cell} is not {variant.half_width}"
    yield from _check_tables(config, font, job)
    yield from _check_widths(variant.ambiguous, cmap, advances, cell)
    yield from _check_extents(font)
    required = REQUIRED_TEXT + (NERD_FONTS_TEXT if variant.nerd_fonts else "")
    missing = [char for char in required if ord(char) not in cmap]
    if missing:
        yield f"missing required characters {missing}"


def _check_tables(config: Config, font: TTFont, job: BuildJob) -> Iterator[str]:
    if font["maxp"].numGlyphs > MAX_GLYPHS:
        yield f"{font['maxp'].numGlyphs} glyphs exceed {MAX_GLYPHS}"
    if font["post"].isFixedPitch != 1:
        yield "post.isFixedPitch is not set"
    expected = f"{job.family(config)} {job.region}"
    family = font["name"].getDebugName(16) or font["name"].getDebugName(1)
    if family is None or not family.startswith(expected):
        yield f"family name {family!r} does not start with {expected!r}"


def _check_widths(
    ambiguous: AmbiguousWidth, cmap: dict[int, str], advances: dict[str, int], cell: int
) -> Iterator[str]:
    allowed = {0, cell, 2 * cell}
    odd = sorted(set(advances.values()) - allowed)
    if odd:
        yield f"advances outside {sorted(allowed)}: {odd[:8]}"
    wrong = []
    for codepoint, name in cmap.items():
        advance = advances[name]
        if advance == 0:
            if not (is_zero_width(codepoint) or is_control(codepoint)):
                wrong.append(codepoint)
        elif advance not in {cells * cell for cells in allowed_cells(codepoint, ambiguous)}:
            wrong.append(codepoint)
    if wrong:
        sample = ", ".join(f"U+{codepoint:04X}" for codepoint in wrong[:8])
        yield f"{len(wrong)} codepoints break the width policy ({sample})"


def _check_extents(font: TTFont) -> Iterator[str]:
    glyf, os2 = font["glyf"], font["OS/2"]
    top, bottom = os2.usWinAscent, -os2.usWinDescent
    clipped = [
        name
        for name in font.getGlyphOrder()
        if glyf[name].numberOfContours and (glyf[name].yMax > top or glyf[name].yMin < bottom)
    ]
    if clipped:
        yield f"{len(clipped)} glyphs would be clipped by usWin metrics ({clipped[:6]})"
