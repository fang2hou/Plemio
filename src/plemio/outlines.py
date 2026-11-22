from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from fontTools.misc.transform import Transform
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import Glyph

from plemio.placement import Box


@dataclass(frozen=True, slots=True)
class Outline:
    commands: tuple[tuple[str, tuple], ...]

    def render(self, transform: Transform) -> Glyph:
        pen = TTGlyphPen(None)
        transform_pen = TransformPen(pen, transform)
        for operator, operands in self.commands:
            getattr(transform_pen, operator)(*operands)
        return pen.glyph()


class OutlineSource(Protocol):
    key: str

    def outline(self, name: str) -> Outline: ...


class SourceFont:
    def __init__(self, key: str, font: TTFont) -> None:
        self.key = key
        self.font = font
        self.cmap: dict[int, str] = font.getBestCmap()
        self._glyph_set = font.getGlyphSet()
        self._metrics = font["hmtx"].metrics
        self._glyf = font["glyf"]

    @classmethod
    def open(cls, key: str, path: Path) -> SourceFont:
        return cls(key, TTFont(path, lazy=True))

    @property
    def em_center(self) -> float:
        os2 = self.font["OS/2"]
        return (os2.sTypoAscender + os2.sTypoDescender) / 2

    def advance(self, name: str) -> int:
        return self._metrics[name][0]

    def outline(self, name: str) -> Outline:
        recording = DecomposingRecordingPen(self._glyph_set, skipMissingComponents=True)
        self._glyph_set[name].draw(recording)
        return Outline(tuple(recording.value))

    def ink(self, name: str) -> Box | None:
        glyph = self._glyf[name]
        if glyph.numberOfContours == 0:
            return None
        return Box(glyph.xMin, glyph.yMin, glyph.xMax, glyph.yMax)

    @property
    def units_per_em(self) -> int:
        return self.font["head"].unitsPerEm

    def line(self) -> Box:
        hhea = self.font["hhea"]
        return Box(0, hhea.descent, 0, hhea.ascent)
