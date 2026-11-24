import math

import pytest
from fontTools.misc.transform import Identity

from plemio.placement import (
    AxisMap,
    Box,
    CjkFit,
    Knots,
    LatinFit,
    SymbolLayout,
    fit_cjk,
    fit_icon,
    fit_separator,
    slant,
)
from plemio.unicode import CodepointSet

FIT = CjkFit(scale=1.0, ink_margin=40, squeeze_aspect=1.35)
PIVOT = 380
ICON_LINE = Box(0, -410, 0, 1638)
ICON_SCALE = 1000 / 2048 * 0.6


def test_full_width_glyph_is_centered_in_two_cells() -> None:
    transform = fit_cjk(1000, Box(50, -100, 950, 860), 1200, FIT, pivot_y=PIVOT)
    assert transform.transformPoint((0, 380)) == pytest.approx((100, 380))


def test_cjk_offset_shifts_vertically_only() -> None:
    plain = fit_cjk(1000, Box(50, -100, 950, 860), 1200, FIT, pivot_y=PIVOT)
    dropped = fit_cjk(1000, Box(50, -100, 950, 860), 1200, FIT, pivot_y=PIVOT, y_offset=-20)
    x, y = plain.transformPoint((500, 500))
    assert dropped.transformPoint((500, 500)) == pytest.approx((x, y - 20))


def test_overwide_glyph_is_squeezed_into_budget() -> None:
    ink = Box(40, 0, 960, 760)
    transform = fit_cjk(1000, ink, 600, FIT, pivot_y=PIVOT)
    assert transform.transformPoint((ink.x_min, 380))[0] == pytest.approx(40)
    assert transform.transformPoint((ink.x_max, 380))[0] == pytest.approx(560)


def test_squeezed_symbol_can_be_recentered_on_the_line() -> None:
    ink = Box(40, -60, 960, 820)
    transform = fit_cjk(1000, ink, 600, FIT, pivot_y=PIVOT, symbol_center_y=322)
    _, y = transform.transformPoint((ink.center_x, ink.center_y))
    assert y == pytest.approx(322)


def test_letter_fit_keeps_full_height() -> None:
    letters = CjkFit(scale=1.0, ink_margin=60, squeeze_aspect=math.inf)
    transform = fit_cjk(1000, Box(100, 0, 900, 700), 600, letters, pivot_y=PIVOT)
    assert transform.transformPoint((0, 700))[1] - transform.transformPoint((0, 0))[1] == (
        pytest.approx(700)
    )


def test_blank_glyph_keeps_identity() -> None:
    assert fit_cjk(1000, None, 1200, FIT, pivot_y=PIVOT) == Identity


def test_latin_fit_centers_scaled_cells_and_hangs_marks_back() -> None:
    fit = LatinFit(source_width=600, cell_width=528, scale_x=0.91, scale_y=0.97)
    assert fit.advance(600) == 528
    assert fit.for_advance(600).transformPoint((300, 100)) == pytest.approx((264, 97))
    assert fit.for_advance(0).transformPoint((-300, 0)) == pytest.approx((-264, 0))
    assert LatinFit(600, 600, 1.0, 1.0).is_identity


def test_knots_translate_beyond_their_ends() -> None:
    knots = Knots.banded((0, 600), (198, 402), (0, 1200))
    assert knots(198) == pytest.approx(498)
    assert knots(402) - knots(198) == pytest.approx(204)
    assert knots(600) == pytest.approx(1200)
    assert knots(634) == pytest.approx(1234)
    assert Knots.shift(300, 322)(-350) == pytest.approx(-328)


def test_overhung_knots_push_only_the_edges() -> None:
    knots = Knots.overhung((-350, 950), (-303, 947), 50)
    assert knots(-350) == pytest.approx(-353)
    assert knots(950) == pytest.approx(997)
    assert knots(300) == pytest.approx(322)


def test_axis_map_combines_both_axes() -> None:
    mapping = AxisMap(Knots.linear((0, 600), (0, 1200)), Knots.shift(300, 322))
    assert mapping.transformPoint((300, 300)) == pytest.approx((600, 322))


def test_icon_is_centered_by_ink_inside_one_cell() -> None:
    ink = Box(400, -410, 1936, 1638)
    transform = fit_icon(
        ICON_LINE, ink, cell_width=600, em_scale=ICON_SCALE, ink_margin=20, center_y=342
    )
    assert transform.transformPoint((ink.center_x, ink.center_y)) == pytest.approx((300, 342))
    assert transform.transformPoint((ink.x_min, 0))[0] == pytest.approx(75)
    assert transform.transformPoint((ink.x_max, 0))[0] == pytest.approx(525)


def test_overwide_icon_is_scaled_down_to_the_cell_budget() -> None:
    ink = Box(0, -410, 4096, 1638)
    transform = fit_icon(
        ICON_LINE, ink, cell_width=600, em_scale=ICON_SCALE, ink_margin=20, center_y=342
    )
    assert transform.transformPoint((ink.x_min, ink.y_min)) == pytest.approx((20, 202))
    assert transform.transformPoint((ink.x_max, ink.y_max)) == pytest.approx((580, 482))


def test_narrow_icon_keeps_the_base_scale() -> None:
    ink = Box(512, -410, 1536, 1638)
    transform = fit_icon(
        ICON_LINE, ink, cell_width=600, em_scale=ICON_SCALE, ink_margin=20, center_y=342
    )
    assert transform.transformPoint((ink.x_min, ink.y_min)) == pytest.approx((150, 42))
    assert transform.transformPoint((ink.x_max, ink.y_max)) == pytest.approx((450, 642))


def test_blank_icon_keeps_identity() -> None:
    transform = fit_icon(
        ICON_LINE, None, cell_width=600, em_scale=ICON_SCALE, ink_margin=20, center_y=342
    )
    assert transform == Identity


def test_separator_fills_the_line_box() -> None:
    reference = Box(0, -400, 1300, 1700)
    line = Box(0, -303, 600, 947)
    transform = fit_separator(reference, advance=1300, cell_width=600, em_scale=0.5, line=line)
    assert transform.transformPoint((0, -400))[1] == pytest.approx(-303)
    assert transform.transformPoint((1300, 1700)) == pytest.approx((600, 947))


def test_slant_keeps_pivot_and_shears_above() -> None:
    transform = slant(9, 380)
    assert transform.transformPoint((100, 380)) == pytest.approx((100, 380))
    x, _ = transform.transformPoint((100, 480))
    assert x == pytest.approx(100 + 100 * math.tan(math.radians(9)))


def test_slant_applies_after_placement() -> None:
    combined = slant(9, 0).transform(Identity.translate(50, 0))
    assert combined.transformPoint((0, 100)) == pytest.approx(
        (50 + 100 * math.tan(math.radians(9)), 100)
    )


def test_symbol_layout_follows_plex_conventions() -> None:
    layout = SymbolLayout(
        349, 305, CodepointSet.parse(["2200-22FF"]), CodepointSet.parse(["239B-23B7"])
    )
    assert layout.is_symbol(0x2318)
    assert not layout.is_symbol(0x239B)
    assert not layout.is_symbol(0x0041)
    assert layout.center_y(0x2260) == 305
    assert layout.center_y(0x2318) == 349
    moved = layout.recenter(0x2318, Identity, Box(0, 100, 500, 700))
    assert moved.transformPoint((250, 400)) == pytest.approx((250, 349))
