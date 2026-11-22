from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from fontTools.misc.transform import Identity, Transform

from plemio.outlines import Outline, OutlineSource, SourceFont
from plemio.placement import PointMap, SymbolLayout
from plemio.providers import Drawn, Grid, Resolved
from plemio.weights import adjust_weight, to_outline, to_path


@dataclass(frozen=True, slots=True)
class Plan:
    glyph: str
    transform: PointMap
    delta: float


class AdjustedSource:
    def __init__(self, key: str, source: OutlineSource) -> None:
        self.key = key
        self._source = source
        self._plans: dict[str, Plan] = {}

    def plan(self, plan: Plan) -> str:
        name = f"{plan.glyph}@{plan.transform}@{plan.delta:.2f}"
        self._plans[name] = plan
        return name

    def outline(self, name: str) -> Outline:
        plan = self._plans[name]
        path = to_path(self._source.outline(plan.glyph), plan.transform)
        return to_outline(adjust_weight(path, plan.delta))


@dataclass(frozen=True, slots=True)
class SymbolFit:
    ink_margin: float
    max_height: float
    target_stroke: float
    source_stroke: float


class ProportionalSymbolProvider:
    def __init__(
        self,
        font: SourceFont,
        grid: Grid,
        *,
        layout: SymbolLayout,
        fit: SymbolFit,
        slant: Transform = Identity,
    ) -> None:
        self._font = font
        self._grid = grid
        self._layout = layout
        self._fit = fit
        self._slant = slant
        self._source = AdjustedSource(f"fitted:{font.key}", font)
        self._em_scale = 1000 / font.units_per_em

    def codepoints(self) -> Iterable[int]:
        return (codepoint for codepoint in self._font.cmap if self._layout.is_symbol(codepoint))

    def resolve(self, codepoint: int) -> Resolved | None:
        name = self._font.cmap.get(codepoint)
        cell = self._grid.cell_width
        if name is None or not self._layout.is_symbol(codepoint):
            return None
        if cell not in self._grid.narrow_advances(codepoint):
            return None
        ink = self._font.ink(name)
        if ink is None:
            return None
        budget = cell - 2 * self._fit.ink_margin
        scale = self._em_scale * min(
            1.0,
            budget / (ink.width * self._em_scale),
            self._fit.max_height / (ink.height * self._em_scale),
        )
        transform = Identity.translate(
            cell / 2 - scale * ink.center_x, self._layout.center_y(codepoint) - scale * ink.center_y
        ).scale(scale)
        delta = (self._fit.target_stroke - self._fit.source_stroke * scale) / 2
        planned = self._source.plan(Plan(name, transform, delta))
        return Drawn(self._source, planned, self._slant, cell)


class EmboldenedProvider:
    def __init__(self, font: SourceFont, derived: Mapping[int, tuple[int, float]]) -> None:
        self._font = font
        self._derived = derived
        self._source = AdjustedSource(f"emboldened:{font.key}", font)

    def codepoints(self) -> Iterable[int]:
        return self._derived

    def resolve(self, codepoint: int) -> Resolved | None:
        if codepoint not in self._derived:
            return None
        base, delta = self._derived[codepoint]
        name = self._font.cmap.get(base)
        if name is None:
            return None
        planned = self._source.plan(Plan(name, Identity, delta))
        return Drawn(self._source, planned, Identity, self._font.advance(name))
