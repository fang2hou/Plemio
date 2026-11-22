from __future__ import annotations

import math
from collections.abc import Callable, Iterable, Sequence

from fontTools.misc.transform import Identity

from plemio.outlines import Outline, OutlineSource
from plemio.placement import Box
from plemio.providers import Drawn, Resolved

type Command = tuple[str, tuple]
type Point = tuple[float, float]

BRAILLE_PATTERNS = range(0x2800, 0x2900)
BRAILLE_DOTS = ((0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2), (0, 3), (1, 3))
IDEOGRAPHIC_SPACE = 0x3000
CIRCLE_SEGMENTS = 8
EDGE_INSET = 1


def circle(cx: float, cy: float, radius: float) -> list[Command]:
    control_radius = radius / math.cos(math.pi / CIRCLE_SEGMENTS)
    controls = tuple(
        (cx + control_radius * math.cos(angle), cy + control_radius * math.sin(angle))
        for angle in (-2 * math.pi * i / CIRCLE_SEGMENTS for i in range(CIRCLE_SEGMENTS))
    )
    return [("qCurveTo", (*controls, None)), ("closePath", ())]


def polygon(points: Sequence[Point], curves: frozenset[int] = frozenset()) -> list[Command]:
    commands: list[Command] = [("moveTo", (points[0],))]
    index = 1
    while index < len(points):
        if index in curves:
            commands.append(("qCurveTo", (points[index], points[index + 1])))
            index += 2
        else:
            commands.append(("lineTo", (points[index],)))
            index += 1
    commands.append(("closePath", ()))
    return commands


def rectangle(x0: float, y0: float, x1: float, y1: float) -> list[Command]:
    return polygon([(x0, y0), (x0, y1), (x1, y1), (x1, y0)])


def hole(x0: float, y0: float, x1: float, y1: float) -> list[Command]:
    return polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])


def rotate(points: Sequence[Point], center: Point, quarter_turns: int) -> list[Point]:
    cx, cy = center
    rotated = list(points)
    for _ in range(quarter_turns % 4):
        rotated = [(cx + (y - cy), cy - (x - cx)) for x, y in rotated]
    return rotated


class BrailleSource:
    def __init__(self, cell: Box, dot_size: float) -> None:
        self.key = f"braille:{cell}:{dot_size}"
        self._cell = cell
        self._pitch_x = cell.width / 2
        self._pitch_y = cell.height / 4
        self._radius = self._pitch_x * dot_size / 2

    def outline(self, name: str) -> Outline:
        pattern = int(name.removeprefix("uni"), 16) - BRAILLE_PATTERNS.start
        commands: list[Command] = []
        for bit, (column, row) in enumerate(BRAILLE_DOTS):
            if pattern & (1 << bit):
                cx = self._cell.x_min + (column + 0.5) * self._pitch_x
                cy = self._cell.y_max - (row + 0.5) * self._pitch_y
                commands += circle(cx, cy, self._radius)
        return Outline(tuple(commands))


class IdeographicSpaceSource:
    def __init__(self, square: Box, stroke: float, dash_ratio: float) -> None:
        self.key = f"ideographic-space:{square}:{stroke}:{dash_ratio}"
        self._square = square
        self._stroke = stroke
        self._dash = square.width * dash_ratio
        self._arm = square.width * (1 - dash_ratio) / 4

    def outline(self, name: str) -> Outline:  # noqa: ARG002
        center = (self._square.center_x, self._square.center_y)
        commands: list[Command] = []
        for turn in range(4):
            commands += polygon(rotate(self._corner(), center, turn), curves=frozenset({2}))
            commands += polygon(rotate(self._dash_points(), center, turn))
        return Outline(tuple(commands))

    def _corner(self) -> list[Point]:
        x0, y1, t, arm = self._square.x_min, self._square.y_max, self._stroke, self._arm
        return [
            (x0, y1 - arm),
            (x0, y1 - t),
            (x0, y1),
            (x0 + t, y1),
            (x0 + arm, y1),
            (x0 + arm, y1 - t),
            (x0 + t, y1 - t),
            (x0 + t, y1 - arm),
        ]

    def _dash_points(self) -> list[Point]:
        cx, y1, t, half = self._square.center_x, self._square.y_max, self._stroke, self._dash / 2
        return [(cx - half, y1 - t), (cx - half, y1), (cx + half, y1), (cx + half, y1 - t)]


SHADES = range(0x2591, 0x2594)
LIGHT_SHADE, MEDIUM_SHADE, DARK_SHADE = SHADES
SHADE_COLUMNS_PER_CELL = 8
SHADE_ROWS_PER_LINE = 8


def light_shade_cell(row: int, column: int) -> bool:
    return column % 4 == 2 * (row % 2)


def medium_shade_cell(row: int, column: int) -> bool:
    return (row + column // 2) % 2 == 0


class ShadeSource:
    def __init__(self, line: Box, cells: int, overhang: float) -> None:
        self.key = f"shade:{line}:{cells}:{overhang}"
        self._line = line
        self._columns = SHADE_COLUMNS_PER_CELL * cells
        self._width = line.width * cells
        self._column_width = self._width / self._columns
        self._row_height = line.height / SHADE_ROWS_PER_LINE
        self._overhang = overhang

    def outline(self, name: str) -> Outline:
        codepoint = int(name.removeprefix("uni"), 16)
        if codepoint == DARK_SHADE:
            return Outline(tuple(self._dark()))
        pattern = light_shade_cell if codepoint == LIGHT_SHADE else medium_shade_cell
        return Outline(tuple(self._pattern(pattern)))

    def _pattern(self, dark: Callable[[int, int], bool]) -> list[Command]:
        commands: list[Command] = []
        for row in range(SHADE_ROWS_PER_LINE):
            y0 = self._line.y_min + row * self._row_height
            column = 0
            while column < self._columns:
                if not dark(row, column):
                    column += 1
                    continue
                start = column
                while column < self._columns and dark(row, column):
                    column += 1
                x0, x1 = start * self._column_width, column * self._column_width
                commands += rectangle(x0, y0, x1, y0 + self._row_height)
        return commands

    def _dark(self) -> list[Command]:
        over, line = self._overhang, self._line
        left, right = -over, self._width + over
        bottom, top = line.y_min - over, line.y_max + over
        commands = rectangle(left, bottom, right, top)
        first_row = math.floor((bottom - line.y_min) / self._row_height)
        last_row = math.ceil((top - line.y_min) / self._row_height)
        first_column = math.floor(left / self._column_width)
        last_column = math.ceil(right / self._column_width)
        for row in range(first_row, last_row):
            y0 = max(line.y_min + row * self._row_height, bottom + EDGE_INSET)
            y1 = min(line.y_min + (row + 1) * self._row_height, top - EDGE_INSET)
            for column in range(first_column, last_column):
                if y1 <= y0 or not light_shade_cell(row, column % self._columns):
                    continue
                x0 = max(column * self._column_width, left + EDGE_INSET)
                x1 = min((column + 1) * self._column_width, right - EDGE_INSET)
                if x1 > x0:
                    commands += hole(x0, y0, x1, y1)
        return commands


class SyntheticProvider:
    def __init__(self, source: OutlineSource, codepoints: range, advance: int) -> None:
        self._source = source
        self._codepoints = codepoints
        self._advance = advance

    def codepoints(self) -> Iterable[int]:
        return self._codepoints

    def resolve(self, codepoint: int) -> Resolved | None:
        if codepoint not in self._codepoints:
            return None
        return Drawn(self._source, f"uni{codepoint:04X}", Identity, self._advance)
