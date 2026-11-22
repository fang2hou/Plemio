from __future__ import annotations

import math
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, replace
from typing import Protocol

from fontTools.misc.transform import Identity, Transform

from plemio.config import NerdFonts, Nudge
from plemio.outlines import OutlineSource, SourceFont
from plemio.placement import (
    Box,
    CjkFit,
    LatinFit,
    PointMap,
    SymbolLayout,
    fit_cjk,
    fit_icon,
    fit_mark,
    fit_separator,
)
from plemio.unicode import (
    COMPATIBILITY_IDEOGRAPHS,
    AmbiguousWidth,
    CodepointSet,
    allowed_cells,
    canonical_ideograph,
    is_control,
    is_letter_script,
    is_private_use,
    is_wide,
    is_zero_width,
)

LATIN_BASELINE_LIMIT = 0x2000


@dataclass(frozen=True, slots=True)
class Native:
    name: str


@dataclass(frozen=True, slots=True)
class Drawn:
    source: OutlineSource
    name: str
    transform: PointMap
    advance: int

    @property
    def key(self) -> tuple[str, str, PointMap, int]:
        return (self.source.key, self.name, self.transform, self.advance)


type Resolved = Native | Drawn


class Provider(Protocol):
    def codepoints(self) -> Iterable[int]: ...

    def resolve(self, codepoint: int) -> Resolved | None: ...


@dataclass(frozen=True, slots=True)
class Grid:
    cell_width: int
    ambiguous: AmbiguousWidth
    line: Box

    def narrow_advances(self, codepoint: int) -> frozenset[int]:
        if is_wide(codepoint):
            return frozenset()
        if is_control(codepoint):
            return frozenset({0, self.cell_width})
        return frozenset({0 if is_zero_width(codepoint) else self.cell_width})

    def cells(self, codepoint: int) -> int:
        return 2 if is_wide(codepoint) else 1

    def cjk_cells(self, codepoint: int, design_advance: int, em: int) -> int:
        allowed = allowed_cells(codepoint, self.ambiguous)
        if len(allowed) == 1:
            return next(iter(allowed))
        if self.ambiguous is AmbiguousWidth.NARROW:
            return 2
        return 2 if design_advance > em / 2 else 1


class NativeProvider:
    def __init__(self, font: SourceFont, grid: Grid) -> None:
        self._font = font
        self._grid = grid

    def codepoints(self) -> Iterable[int]:
        return self._font.cmap

    def resolve(self, codepoint: int) -> Resolved | None:
        name = self._font.cmap.get(codepoint)
        if name is None or self._font.advance(name) not in self._grid.narrow_advances(codepoint):
            return None
        return Native(name)


class SupplementProvider:
    def __init__(
        self,
        font: SourceFont,
        grid: Grid,
        *,
        latin: LatinFit,
        layout: SymbolLayout,
        cap_ratio: float,
        slant: Transform = Identity,
    ) -> None:
        self._font = font
        self._grid = grid
        self._latin = latin
        self._layout = layout
        self._cap_ratio = cap_ratio
        self._slant = slant
        self._em_scale = 1000 / font.units_per_em

    def codepoints(self) -> Iterable[int]:
        return self._font.cmap

    def resolve(self, codepoint: int) -> Resolved | None:
        name = self._font.cmap.get(codepoint)
        if name is None:
            return None
        source_advance = self._font.advance(name) * self._em_scale
        advance = self._latin.advance(source_advance)
        if advance not in self._grid.narrow_advances(codepoint):
            return None
        center_x = self._font.advance(name) / 2
        normalize = Identity.translate(center_x, 0).scale(self._cap_ratio).translate(-center_x, 0)
        fit = self._latin.for_advance(source_advance).transform(
            Identity.scale(self._em_scale).transform(normalize)
        )
        ink = self._font.ink(name)
        if ink is not None and self._layout.is_symbol(codepoint):
            fit = self._layout.recenter(codepoint, fit, ink)
        return Drawn(self._font, name, self._slant.transform(fit), advance)


@dataclass(frozen=True, slots=True)
class CjkOffset:
    y_offset: float
    exempt: CodepointSet
    nudges: tuple[Nudge, ...] = ()

    def for_codepoint(self, codepoint: int, cells: int) -> float:
        on_latin_baseline = cells == 1 and codepoint < LATIN_BASELINE_LIMIT
        return 0 if on_latin_baseline or codepoint in self.exempt else self.y_offset

    def nudge(self, codepoint: int) -> Transform:
        for nudge in self.nudges:
            if codepoint in nudge.codepoints:
                return Identity.translate(nudge.x, nudge.y)
        return Identity


class CjkProvider:
    def __init__(
        self,
        fonts: Sequence[SourceFont],
        grid: Grid,
        *,
        fit: CjkFit,
        offset: CjkOffset,
        layout: SymbolLayout,
        slant: Transform = Identity,
    ) -> None:
        self._layout = layout
        self._fonts = fonts
        self._grid = grid
        self._wide_fit = fit
        self._narrow_fit = replace(fit, scale=1.0)
        self._letter_fit = replace(fit, scale=1.0, squeeze_aspect=math.inf)
        self._offset = offset
        self._slant = slant

    def codepoints(self) -> Iterable[int]:
        covered = {codepoint for font in self._fonts for codepoint in font.cmap}
        aliases = {
            codepoint
            for block in COMPATIBILITY_IDEOGRAPHS
            for codepoint in block
            if canonical_ideograph(codepoint) in covered
        }
        return covered | aliases

    def resolve(self, codepoint: int) -> Resolved | None:
        found = self._lookup(codepoint)
        if found is None and (canonical := canonical_ideograph(codepoint)) is not None:
            found = self._lookup(canonical)
        if found is None:
            return None
        font, name = found
        if is_zero_width(codepoint):
            mark = fit_mark(self._offset.for_codepoint(codepoint, cells=2))
            return Drawn(font, name, self._slant.transform(mark), 0)
        design_advance = font.advance(name)
        cells = self._grid.cjk_cells(codepoint, design_advance, font.units_per_em)
        width = cells * self._grid.cell_width
        narrowed_symbol = (
            cells == 1
            and not is_letter_script(codepoint)
            and design_advance > font.units_per_em / 2
        )
        placement = fit_cjk(
            design_advance or width,
            font.ink(name),
            width,
            self._fit_for(codepoint, cells),
            pivot_y=font.em_center,
            y_offset=self._offset.for_codepoint(codepoint, cells),
            symbol_center_y=self._layout.center_y(codepoint) if narrowed_symbol else None,
        )
        placement = self._offset.nudge(codepoint).transform(placement)
        return Drawn(font, name, self._slant.transform(placement), width)

    def _fit_for(self, codepoint: int, cells: int) -> CjkFit:
        if cells > 1:
            return self._wide_fit
        return self._letter_fit if is_letter_script(codepoint) else self._narrow_fit

    def _lookup(self, codepoint: int) -> tuple[SourceFont, str] | None:
        for font in self._fonts:
            if name := font.cmap.get(codepoint):
                return font, name
        return None


class LineArtProvider:
    def __init__(self, font: SourceFont, maps: Sequence[tuple[range, PointMap, int]]) -> None:
        self._font = font
        self._maps = maps

    def codepoints(self) -> Iterable[int]:
        return (codepoint for block, _, _ in self._maps for codepoint in block)

    def resolve(self, codepoint: int) -> Resolved | None:
        name = self._font.cmap.get(codepoint)
        if name is None:
            return None
        for block, point_map, advance in self._maps:
            if codepoint in block:
                return Drawn(self._font, name, point_map, advance)
        return None


class NerdFontsProvider:
    def __init__(self, font: SourceFont, grid: Grid, config: NerdFonts) -> None:
        self._font = font
        self._grid = grid
        self._config = config
        self._em_scale = 1000 / font.units_per_em * config.icon_scale
        self._source_line = font.line()
        self._reference = font.ink(font.cmap[ord(config.cell_reference)])

    def codepoints(self) -> Iterable[int]:
        return self._font.cmap

    def resolve(self, codepoint: int) -> Resolved | None:
        name = self._font.cmap.get(codepoint)
        if name is None or self._reference is None:
            return None
        advance = self._font.advance(name)
        cell = self._grid.cell_width
        if codepoint in self._config.cell_ranges:
            transform = fit_separator(
                self._reference,
                advance=advance,
                cell_width=cell,
                em_scale=self._em_scale,
                line=self._grid.line,
            )
            return Drawn(self._font, name, transform, cell)
        cells = 1 if is_private_use(codepoint) else self._grid.cells(codepoint)
        transform = fit_icon(
            self._source_line,
            advance=advance,
            cell_width=cells * cell,
            em_scale=self._em_scale,
            center_y=self._config.icon_center_y,
        )
        return Drawn(self._font, name, transform, cells * cell)


class Restricted:
    def __init__(self, provider: Provider, accepts: Callable[[int], bool]) -> None:
        self._provider = provider
        self._accepts = accepts

    def codepoints(self) -> Iterable[int]:
        return filter(self._accepts, self._provider.codepoints())

    def resolve(self, codepoint: int) -> Resolved | None:
        return self._provider.resolve(codepoint) if self._accepts(codepoint) else None


def resolve_codepoints(
    providers: Sequence[Provider], excluded: Callable[[int], bool]
) -> dict[int, Resolved]:
    universe = {codepoint for provider in providers for codepoint in provider.codepoints()}
    resolved: dict[int, Resolved] = {}
    for codepoint in sorted(universe):
        if excluded(codepoint):
            continue
        for provider in providers:
            if (result := provider.resolve(codepoint)) is not None:
                resolved[codepoint] = result
                break
    return resolved
