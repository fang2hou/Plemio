from __future__ import annotations

import math

from fontTools.misc.transform import Identity, Transform
from fontTools.ttLib import TTFont

from plemio.config import Config, Supplement, Variant
from plemio.jobs import BuildJob
from plemio.measure import (
    cap_height,
    cell_width,
    ink_box,
    italic_pivot,
    line_art_span,
    stem_width,
    vertical_stroke_band,
)
from plemio.outlines import SourceFont
from plemio.placement import AxisMap, Box, CjkFit, Knots, LatinFit, PointMap, SymbolLayout, slant
from plemio.providers import (
    CjkOffset,
    CjkProvider,
    Grid,
    LineArtProvider,
    NativeProvider,
    NerdFontsProvider,
    Provider,
    Restricted,
    SupplementProvider,
)
from plemio.sources import SourceCatalog
from plemio.styles import Style
from plemio.supplements import calibrate_weight, instantiate, load_static
from plemio.symbols import EmboldenedProvider, ProportionalSymbolProvider, SymbolFit
from plemio.synthetic import (
    BRAILLE_PATTERNS,
    IDEOGRAPHIC_SPACE,
    SHADES,
    BrailleSource,
    IdeographicSpaceSource,
    ShadeSource,
    SyntheticProvider,
)
from plemio.unicode import AmbiguousWidth, is_private_use_any_plane

BOX_DRAWING = range(0x2500, 0x2580)
SOLID_BLOCKS = (range(0x2580, 0x2591), range(0x2594, 0x25A0))


def without_private_use(provider: Provider) -> Provider:
    return Restricted(provider, lambda codepoint: not is_private_use_any_plane(codepoint))


class ProviderFactory:
    def __init__(
        self, config: Config, catalog: SourceCatalog, job: BuildJob, latin: SourceFont
    ) -> None:
        self._config = config
        self._catalog = catalog
        self._job = job
        self._variant: Variant = config.variants[job.variant]
        self._latin = latin
        self._mono = SourceFont.open(
            f"plex-mono:{job.style.name}", catalog.font("plex-mono", style=job.style.name)
        )
        self._upright = TTFont(catalog.font("plex-mono", style=Style(job.style.weight).name))
        metrics = config.metrics
        self.grid = Grid(
            self._variant.half_width,
            self._variant.ambiguous,
            Box(0, metrics.descender, self._variant.half_width, metrics.ascender),
        )
        self.latin_fit = LatinFit(
            cell_width(self._mono.font), self._variant.half_width, *self._variant.latin_scale
        )
        self._slant = self._italic_slant()
        self._cjk_sources = self._cjk_fonts()
        symbols, scale_y = config.symbols, self.latin_fit.scale_y
        self.layout = SymbolLayout(
            symbols.icon_center_y * scale_y,
            symbols.operator_center_y * scale_y,
            symbols.operators,
            symbols.fixed,
        )

    def build(self) -> list[Provider]:
        cjk = self._cjk()
        nerd_fonts = self._nerd_fonts()
        supplements = self._supplements()
        fallbacks: list[Provider] = (
            [cjk, *supplements]
            if self._variant.ambiguous is AmbiguousWidth.WIDE
            else [*supplements, cjk]
        )
        return [
            *self._ideographic_space(),
            *(Restricted(provider, is_private_use_any_plane) for provider in nerd_fonts),
            Restricted(cjk, self._variant.cjk_over_latin.__contains__),
            *self._line_art(),
            *(
                Restricted(provider, self._config.symbols.override.__contains__)
                for provider in supplements
            ),
            NativeProvider(self._latin, self.grid),
            *self._braille(),
            *self._emboldened(),
            Restricted(cjk, self._config.cjk.preferred.__contains__),
            *fallbacks,
            *nerd_fonts,
        ]

    def _italic_slant(self) -> Transform:
        if not self._job.style.italic:
            return Identity
        sx, sy = self._variant.latin_scale
        shear = math.tan(math.radians(-self._mono.font["post"].italicAngle)) * sx / sy
        pivot = italic_pivot(self._upright, self._mono.font) * sy
        return slant(math.degrees(math.atan(shear)), pivot)

    def _cjk_fonts(self) -> list[SourceFont]:
        region = self._config.regions[self._job.region]
        weight = self._job.style.weight.name
        return [
            SourceFont.open(
                f"cjk:{name}:{weight}", self._catalog.font("plex-sans", region=name, weight=weight)
            )
            for name in (self._job.region, *region.fallback)
        ]

    def _cjk(self) -> Provider:
        cjk = self._config.cjk
        return without_private_use(
            CjkProvider(
                self._cjk_sources,
                self.grid,
                fit=CjkFit(cjk.scale, cjk.ink_margin, cjk.squeeze_aspect),
                offset=CjkOffset(cjk.y_offset, cjk.y_offset_exempt, cjk.nudges),
                layout=self.layout,
                slant=self._slant,
            )
        )

    def _line_art(self) -> list[Provider]:
        font = self._mono.font
        source_x = (0.0, float(self.latin_fit.source_width))
        span = line_art_span(font)
        line = (self.grid.line.y_min, self.grid.line.y_max)
        cells = 2 if self._variant.full_width_line_art else 1
        width = cells * self.grid.cell_width
        target_x = (0.0, float(width))
        overhang = self._config.line_art.block_overhang
        box_x = (
            Knots.banded(source_x, vertical_stroke_band(font), target_x)
            if cells == 2
            else Knots.linear(source_x, target_x)
        )
        box: PointMap = AxisMap(box_x, Knots.shift(sum(span) / 2, self.grid.line.center_y))
        solid = AxisMap(
            Knots.overhung(source_x, target_x, overhang), Knots.overhung(span, line, overhang)
        )
        maps = [(BOX_DRAWING, box, width), *((block, solid, width) for block in SOLID_BLOCKS)]
        shades = ShadeSource(self.grid.line, cells, overhang)
        return [LineArtProvider(self._mono, maps), SyntheticProvider(shades, SHADES, width)]

    def _supplements(self) -> list[Provider]:
        providers: list[Provider] = []
        for supplement in self._config.supplements:
            if supplement.fit == "proportional":
                providers.append(self._proportional_supplement(supplement))
            else:
                providers.append(self._monospaced_supplement(supplement))
        return [without_private_use(provider) for provider in providers]

    def _monospaced_supplement(self, supplement: Supplement) -> Provider:
        source_id = supplement.source
        target_stem = stem_width(self._upright)
        weight = calibrate_weight(str(self._catalog.font(source_id)), target_stem, supplement.axes)
        native_italic = self._job.style.italic and self._catalog.has_italic(source_id)
        catalog = self._catalog
        path = catalog.italic_font(source_id) if native_italic else catalog.font(source_id)
        font = instantiate(str(path), weight, supplement.axes, self._mono.cmap.keys())
        cap_ratio = cap_height(self._mono.font) / cap_height(font)
        return SupplementProvider(
            SourceFont(f"{source_id}:{weight}:{native_italic}", font),
            self.grid,
            latin=self.latin_fit,
            layout=self.layout,
            cap_ratio=cap_ratio,
            slant=self._slant if not native_italic else Identity,
        )

    def _proportional_supplement(self, supplement: Supplement) -> Provider:
        source_id = supplement.source
        path = str(self._catalog.font(source_id))
        symbols = self._config.symbols
        with TTFont(path) as source:
            source_stroke = ink_box(source, symbols.stroke_probe).height
        covered = [cp for cp in self._mono.cmap if cp not in symbols.override]
        font = load_static(path, covered)
        scale_y = self.latin_fit.scale_y
        fit = SymbolFit(
            ink_margin=symbols.ink_margin,
            max_height=symbols.max_height * scale_y,
            target_stroke=ink_box(self._mono.font, symbols.stroke_probe).height * scale_y,
            source_stroke=source_stroke,
        )
        return ProportionalSymbolProvider(
            SourceFont(source_id, font), self.grid, layout=self.layout, fit=fit, slant=self._slant
        )

    def _emboldened(self) -> list[Provider]:
        symbols = self._config.symbols
        stroke = ink_box(self._mono.font, symbols.stroke_probe).height * self.latin_fit.scale_y
        derived = {
            item.codepoint: (item.source, stroke * (item.stroke_ratio - 1) / 2)
            for item in symbols.emboldened
        }
        return [EmboldenedProvider(self._latin, derived)] if derived else []

    def _braille(self) -> list[Provider]:
        settings = self._config.braille
        if not settings.enabled:
            return []
        center = self.layout.icon_center_y
        field = Box(
            0, center - settings.height / 2, self.grid.cell_width, center + settings.height / 2
        )
        source = BrailleSource(field, settings.dot_size)
        return [SyntheticProvider(source, BRAILLE_PATTERNS, self.grid.cell_width)]

    def _ideographic_space(self) -> list[Provider]:
        if not self._variant.visible_ideographic_space:
            return []
        settings = self._config.ideographic_space
        side = settings.size * 1000
        center_x = self.grid.cell_width
        center_y = settings.center_y
        square = Box(
            center_x - side / 2, center_y - side / 2, center_x + side / 2, center_y + side / 2
        )
        source = IdeographicSpaceSource(square, settings.stroke, settings.dash_ratio)
        space = range(IDEOGRAPHIC_SPACE, IDEOGRAPHIC_SPACE + 1)
        return [SyntheticProvider(source, space, 2 * self.grid.cell_width)]

    def _nerd_fonts(self) -> list[Provider]:
        if not self._variant.nerd_fonts:
            return []
        settings = self._config.nerd_fonts
        font = SourceFont.open("nerd-fonts", self._catalog.font(settings.source))
        return [NerdFontsProvider(font, self.grid, settings)]
