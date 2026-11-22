from __future__ import annotations

import math

import pathops
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.transformPen import TransformPen

from plemio.outlines import Outline
from plemio.placement import PointMap

CURVE_TOLERANCE = 1.0
MITER_LIMIT = 4.0
SEARCH_STEPS = 6


def to_path(outline: Outline, transform: PointMap) -> pathops.Path:
    path = pathops.Path()
    pen = TransformPen(path.getPen(), transform)
    for operator, operands in outline.commands:
        getattr(pen, operator)(*operands)
    path.simplify(clockwise=True)
    return path


def to_outline(path: pathops.Path) -> Outline:
    recording = RecordingPen()
    path.draw(Cu2QuPen(recording, CURVE_TOLERANCE, reverse_direction=False))
    return Outline(tuple(recording.value))


def offset(path: pathops.Path, delta: float) -> pathops.Path:
    if not delta:
        return path
    ring = pathops.Path(path)
    ring.stroke(2 * abs(delta), pathops.LineCap.BUTT_CAP, pathops.LineJoin.MITER_JOIN, MITER_LIMIT)
    operator = pathops.PathOp.UNION if delta > 0 else pathops.PathOp.DIFFERENCE
    return pathops.op(path, ring, operator, clockwise=True)


def contour_count(path: pathops.Path) -> int:
    return sum(1 for _ in path.contours)


def adjust_weight(path: pathops.Path, delta: float) -> pathops.Path:
    contours = contour_count(path)
    result = offset(path, delta)
    if contour_count(result) == contours:
        return result
    low, high, best = 0.0, abs(delta), path
    for _ in range(SEARCH_STEPS):
        middle = (low + high) / 2
        candidate = offset(path, math.copysign(middle, delta))
        if contour_count(candidate) == contours:
            low, best = middle, candidate
        else:
            high = middle
    return best
