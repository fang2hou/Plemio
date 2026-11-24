from __future__ import annotations

import bisect
import math
import unicodedata
from dataclasses import dataclass

from fontTools.misc.transform import Identity, Transform

from plemio.unicode import CodepointSet

EDGE = 1.0


@dataclass(frozen=True, slots=True)
class Box:
    x_min: float
    y_min: float
    x_max: float
    y_max: float

    @property
    def width(self) -> float:
        return self.x_max - self.x_min

    @property
    def height(self) -> float:
        return self.y_max - self.y_min

    @property
    def center_x(self) -> float:
        return (self.x_min + self.x_max) / 2

    @property
    def center_y(self) -> float:
        return (self.y_min + self.y_max) / 2


@dataclass(frozen=True, slots=True)
class Knots:
    points: tuple[tuple[float, float], ...]

    @classmethod
    def shift(cls, source: float, target: float) -> Knots:
        return cls(((source, target),))

    @classmethod
    def linear(cls, source: tuple[float, float], target: tuple[float, float]) -> Knots:
        return cls(tuple(zip(source, target, strict=True)))

    @classmethod
    def banded(
        cls, source: tuple[float, float], band: tuple[float, float], target: tuple[float, float]
    ) -> Knots:
        shift = sum(target) / 2 - sum(source) / 2
        return cls(
            (
                (source[0], target[0]),
                (band[0], band[0] + shift),
                (band[1], band[1] + shift),
                (source[1], target[1]),
            )
        )

    @classmethod
    def overhung(
        cls, source: tuple[float, float], target: tuple[float, float], overhang: float
    ) -> Knots:
        (s0, s1), (t0, t1) = source, target
        scale = (t1 - t0) / (s1 - s0)
        return cls(
            (
                (s0, t0 - overhang),
                (s0 + EDGE, t0 + EDGE * scale),
                (s1 - EDGE, t1 - EDGE * scale),
                (s1, t1 + overhang),
            )
        )

    def __call__(self, value: float) -> float:
        sources = [source for source, _ in self.points]
        if len(self.points) == 1 or value <= sources[0] or value >= sources[-1]:
            source, target = self.points[0 if value <= sources[0] else -1]
            return value + target - source
        index = bisect.bisect_right(sources, value)
        (s0, t0), (s1, t1) = self.points[index - 1], self.points[index]
        return t0 + (value - s0) * (t1 - t0) / (s1 - s0)


@dataclass(frozen=True, slots=True)
class AxisMap:
    x: Knots
    y: Knots

    def transformPoint(self, point: tuple[float, float]) -> tuple[float, float]:  # noqa: N802
        return self.x(point[0]), self.y(point[1])


type PointMap = Transform | AxisMap


@dataclass(frozen=True, slots=True)
class CjkFit:
    scale: float
    ink_margin: float
    squeeze_aspect: float


@dataclass(frozen=True, slots=True)
class LatinFit:
    source_width: int
    cell_width: int
    scale_x: float
    scale_y: float

    def for_advance(self, advance: float) -> Transform:
        if advance == 0:
            cell_dx = (self.cell_width - self.source_width * self.scale_x) / 2
            dx = self.source_width * self.scale_x + cell_dx - self.cell_width
        else:
            dx = (self.advance(advance) - advance * self.scale_x) / 2
        return Identity.translate(dx, 0).scale(self.scale_x, self.scale_y)

    def advance(self, advance: float) -> int:
        return round(advance / self.source_width) * self.cell_width

    @property
    def is_identity(self) -> bool:
        return (self.scale_x, self.scale_y) == (1, 1) and self.cell_width == self.source_width


def scale_about(sx: float, sy: float, pivot_y: float, dx: float = 0, dy: float = 0) -> Transform:
    return Identity.translate(dx, pivot_y + dy).scale(sx, sy).translate(0, -pivot_y)


def fit_cjk(
    advance: int,
    ink: Box | None,
    width: int,
    fit: CjkFit,
    *,
    pivot_y: float,
    y_offset: float = 0,
    symbol_center_y: float | None = None,
) -> Transform:
    if ink is None:
        return Identity
    budget = width - 2 * fit.ink_margin
    if ink.width * fit.scale > budget:
        sx = budget / ink.width
        sy = min(fit.scale, sx * fit.squeeze_aspect)
        dx = width / 2 - sx * ink.center_x
        if symbol_center_y is None:
            return scale_about(sx, sy, pivot_y, dx, y_offset)
        return Identity.translate(dx, symbol_center_y - sy * ink.center_y).scale(sx, sy)
    dx = (width - advance * fit.scale) / 2
    if dx + ink.x_min * fit.scale < 0 or dx + ink.x_max * fit.scale > width:
        dx = width / 2 - fit.scale * ink.center_x
    return scale_about(fit.scale, fit.scale, pivot_y, dx, y_offset)


def fit_mark(y_offset: float) -> Transform:
    return Identity.translate(0, y_offset)


def fit_icon(
    source_line: Box,
    *,
    advance: int,
    cell_width: int,
    em_scale: float,
    center_y: float,
) -> Transform:
    cells = 1 if advance * em_scale <= cell_width else 2
    dx = (cells * cell_width - advance * em_scale) / 2
    return Identity.translate(dx, center_y).scale(em_scale).translate(0, -source_line.center_y)


def fit_separator(
    reference_ink: Box, *, advance: int, cell_width: int, em_scale: float, line: Box
) -> Transform:
    sx = min(em_scale, cell_width / advance)
    sy = line.height / reference_ink.height
    dx = (cell_width - advance * sx) / 2
    return Identity.translate(dx, line.y_min).scale(sx, sy).translate(0, -reference_ink.y_min)


def slant(angle_degrees: float, pivot_y: float) -> Transform:
    shear = math.tan(math.radians(angle_degrees))
    return Transform(1, 0, shear, 1, -shear * pivot_y, 0)


SYMBOL_CATEGORIES = frozenset({"Sm", "So"})


@dataclass(frozen=True, slots=True)
class SymbolLayout:
    icon_center_y: float
    operator_center_y: float
    operators: CodepointSet
    fixed: CodepointSet

    def is_symbol(self, codepoint: int) -> bool:
        category = unicodedata.category(chr(codepoint))
        return category in SYMBOL_CATEGORIES and codepoint not in self.fixed

    def center_y(self, codepoint: int) -> float:
        return self.operator_center_y if codepoint in self.operators else self.icon_center_y

    def recenter(self, codepoint: int, transform: Transform, ink: Box) -> Transform:
        _, y = transform.transformPoint((ink.center_x, ink.center_y))
        return Identity.translate(0, self.center_y(codepoint) - y).transform(transform)
