from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable

from plemio.config import Config
from plemio.factory import ProviderFactory
from plemio.jobs import BuildJob
from plemio.latin import prepare_latin
from plemio.measure import cell_width
from plemio.metadata import finalize
from plemio.outlines import SourceFont
from plemio.placement import LatinFit
from plemio.providers import Drawn, Native, Resolved, resolve_codepoints
from plemio.sources import SourceCatalog

MAX_GLYPHS = 0xFFFF


class GlyphOverflowError(RuntimeError):
    pass


class FontAssembler:
    def __init__(self, font: TTFont) -> None:
        self._font = font
        self._glyf = font["glyf"]
        self._hmtx = font["hmtx"]
        self._order = list(font.getGlyphOrder())
        self._taken = set(self._order)
        self._drawn: dict[tuple, str] = {}

    def glyph_name(self, codepoint: int, resolved: Resolved) -> str:
        match resolved:
            case Native(name):
                return name
            case Drawn() if resolved.key in self._drawn:
                return self._drawn[resolved.key]
            case Drawn():
                name = self._add(codepoint, resolved)
                self._drawn[resolved.key] = name
                return name

    def commit(self, cmap: Mapping[int, str]) -> None:
        if len(self._order) > MAX_GLYPHS:
            msg = f"{len(self._order)} glyphs exceed the TrueType limit of {MAX_GLYPHS}"
            raise GlyphOverflowError(msg)
        self._font.setGlyphOrder(self._order)
        self._glyf.glyphOrder = self._order
        write_cmap(self._font, cmap)

    def _add(self, codepoint: int, drawn: Drawn) -> str:
        name = self._unique_name(codepoint)
        glyph = drawn.source.outline(drawn.name).render(drawn.transform)
        glyph.recalcBounds(self._glyf)
        self._glyf.glyphs[name] = glyph
        self._hmtx.metrics[name] = (drawn.advance, getattr(glyph, "xMin", 0))
        self._order.append(name)
        self._taken.add(name)
        return name

    def _unique_name(self, codepoint: int) -> str:
        base = f"uni{codepoint:04X}" if codepoint <= 0xFFFF else f"u{codepoint:05X}"
        name, suffix = base, 0
        while name in self._taken:
            suffix += 1
            name = f"{base}.{suffix}"
        return name


def write_cmap(font: TTFont, mapping: Mapping[int, str]) -> None:
    bmp = {codepoint: name for codepoint, name in mapping.items() if codepoint <= 0xFFFF}
    layouts = [(4, 0, 3, bmp), (4, 3, 1, bmp)]
    if len(bmp) < len(mapping):
        layouts += [(12, 0, 4, mapping), (12, 3, 10, mapping)]
    subtables = []
    for fmt, platform_id, encoding_id, glyphs in layouts:
        subtable = CmapSubtable.newSubtable(fmt)
        subtable.platformID, subtable.platEncID, subtable.language = platform_id, encoding_id, 0
        subtable.cmap = dict(glyphs)
        subtables.append(subtable)
    cmap = font["cmap"]
    cmap.tableVersion = 0
    cmap.tables = subtables


def build_font(config: Config, catalog: SourceCatalog, job: BuildJob, output_dir: Path) -> Path:
    variant = config.variants[job.variant]
    mono = TTFont(catalog.font("plex-mono", style=job.style.name))
    mono.ensureDecompiled()
    fit = LatinFit(cell_width(mono), variant.half_width, *variant.latin_scale)
    base = prepare_latin(mono, fit)
    factory = ProviderFactory(config, catalog, job, SourceFont("latin", base))
    resolved = resolve_codepoints(factory.build(), config.exclude.__contains__)
    assembler = FontAssembler(base)
    cmap = {
        codepoint: assembler.glyph_name(codepoint, item) for codepoint, item in resolved.items()
    }
    assembler.commit(cmap)
    finalize(base, config, job, variant.half_width)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / job.filename(config)
    base.save(path)
    return path
