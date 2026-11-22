from fontTools.misc.transform import Identity

from plemio.outlines import Outline
from plemio.synthetic import hole, rectangle
from plemio.weights import adjust_weight, contour_count, to_outline, to_path


def double_bar() -> Outline:
    return Outline(tuple(rectangle(0, 0, 400, 40) + rectangle(0, 100, 400, 140)))


def bounds(path) -> tuple[float, ...]:
    return tuple(round(value) for value in path.bounds)


def test_emboldening_grows_each_side() -> None:
    path = adjust_weight(to_path(Outline(tuple(rectangle(0, 0, 400, 40))), Identity), 10)
    assert bounds(path) == (-10, -10, 410, 50)


def test_emboldening_never_merges_separate_strokes() -> None:
    path = adjust_weight(to_path(double_bar(), Identity), 60)
    assert contour_count(path) == 2
    assert path.bounds[3] - path.bounds[1] > 140


def test_thinning_never_erases_a_stroke() -> None:
    ring = Outline(tuple(rectangle(0, 0, 300, 300) + hole(20, 20, 280, 280)))
    path = adjust_weight(to_path(ring, Identity), -30)
    assert contour_count(path) == 2


def test_round_trip_produces_quadratic_outline() -> None:
    outline = to_outline(to_path(double_bar(), Identity))
    assert {operator for operator, _ in outline.commands} <= {
        "moveTo",
        "lineTo",
        "qCurveTo",
        "closePath",
    }
