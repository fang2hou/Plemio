from __future__ import annotations

import io
from collections.abc import Iterator

from fontTools.misc.transform import Transform
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables
from ttfautohint import ttfautohint

from plemio.outlines import Outline
from plemio.placement import LatinFit

HINTING_TABLES = ("fpgm", "prep", "cvt ", "gasp", "hdmx", "LTSH", "VDMX", "DSIG")
EXTENSION_LOOKUP = 9


def prepare_latin(font: TTFont, fit: LatinFit) -> TTFont:
    if fit.is_identity:
        return font
    transforms = {
        name: fit.for_advance(advance) for name, (advance, _) in font["hmtx"].metrics.items()
    }
    _redraw_glyphs(font, fit, transforms)
    _move_anchors(font, transforms)
    for tag in HINTING_TABLES:
        if tag in font:
            del font[tag]
    return autohint(font)


def autohint(font: TTFont) -> TTFont:
    buffer = io.BytesIO()
    font.save(buffer)
    hinted = ttfautohint(
        in_buffer=buffer.getvalue(),
        default_script="latn",
        fallback_script="none",
        hinting_range_min=6,
        hinting_range_max=45,
        fallback_scaling=True,
        windows_compatibility=True,
        x_height_snapping_exceptions="13-",
        no_info=True,
    )
    result = TTFont(io.BytesIO(hinted))
    result.ensureDecompiled()
    return result


def _redraw_glyphs(font: TTFont, fit: LatinFit, transforms: dict[str, Transform]) -> None:
    glyph_set = font.getGlyphSet()
    outlines = {}
    for name in font.getGlyphOrder():
        pen = DecomposingRecordingPen(glyph_set, skipMissingComponents=True)
        glyph_set[name].draw(pen)
        outlines[name] = Outline(tuple(pen.value))
    glyf, hmtx = font["glyf"], font["hmtx"]
    for name, outline in outlines.items():
        glyph = outline.render(transforms[name])
        glyph.recalcBounds(glyf)
        glyf.glyphs[name] = glyph
        advance = fit.advance(hmtx.metrics[name][0])
        hmtx.metrics[name] = (advance, getattr(glyph, "xMin", 0))


def _move_anchors(font: TTFont, transforms: dict[str, Transform]) -> None:
    if "GPOS" not in font:
        return
    moved: set[int] = set()
    for glyph, anchor in _mark_anchors(font["GPOS"].table):
        if anchor is None or id(anchor) in moved:
            continue
        moved.add(id(anchor))
        x, y = transforms[glyph].transformPoint((anchor.XCoordinate, anchor.YCoordinate))
        anchor.XCoordinate, anchor.YCoordinate = round(x), round(y)


def _mark_anchors(gpos: otTables.GPOS) -> Iterator[tuple[str, otTables.Anchor | None]]:
    for lookup in gpos.LookupList.Lookup:
        for subtable in lookup.SubTable:
            table = subtable.ExtSubTable if lookup.LookupType == EXTENSION_LOOKUP else subtable
            yield from _subtable_anchors(table)


def _subtable_anchors(table: object) -> Iterator[tuple[str, otTables.Anchor | None]]:
    match table:
        case otTables.MarkBasePos():
            yield from _mark_array(table.MarkCoverage, table.MarkArray)
            for glyph, record in zip(
                table.BaseCoverage.glyphs, table.BaseArray.BaseRecord, strict=True
            ):
                for anchor in record.BaseAnchor:
                    yield glyph, anchor
        case otTables.MarkMarkPos():
            yield from _mark_array(table.Mark1Coverage, table.Mark1Array)
            for glyph, record in zip(
                table.Mark2Coverage.glyphs, table.Mark2Array.Mark2Record, strict=True
            ):
                for anchor in record.Mark2Anchor:
                    yield glyph, anchor
        case otTables.MarkLigPos():
            yield from _mark_array(table.MarkCoverage, table.MarkArray)
            ligatures = table.LigatureArray.LigatureAttach
            for glyph, attach in zip(table.LigatureCoverage.glyphs, ligatures, strict=True):
                for component in attach.ComponentRecord:
                    for anchor in component.LigatureAnchor:
                        yield glyph, anchor


def _mark_array(
    coverage: otTables.Coverage, marks: otTables.MarkArray
) -> Iterator[tuple[str, otTables.Anchor]]:
    for glyph, record in zip(coverage.glyphs, marks.MarkRecord, strict=True):
        yield glyph, record.MarkAnchor
