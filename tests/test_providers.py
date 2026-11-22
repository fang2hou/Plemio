from collections.abc import Iterable

from fontTools.misc.transform import Identity

from plemio.config import Nudge
from plemio.placement import Box
from plemio.providers import CjkOffset, Grid, Native, Resolved, Restricted, resolve_codepoints
from plemio.synthetic import (
    BRAILLE_PATTERNS,
    BrailleSource,
    IdeographicSpaceSource,
    ShadeSource,
    SyntheticProvider,
)
from plemio.unicode import AmbiguousWidth, CodepointSet

LINE = Box(0, -303, 600, 947)


class FakeProvider:
    def __init__(self, label: str, codepoints: set[int]) -> None:
        self._label = label
        self._codepoints = codepoints

    def codepoints(self) -> Iterable[int]:
        return self._codepoints

    def resolve(self, codepoint: int) -> Resolved | None:
        return Native(self._label) if codepoint in self._codepoints else None


def test_first_provider_wins_and_exclusions_apply() -> None:
    first = FakeProvider("first", {1, 2})
    second = FakeProvider("second", {2, 3, 4})
    resolved = resolve_codepoints([first, second], lambda codepoint: codepoint == 4)
    assert resolved == {1: Native("first"), 2: Native("first"), 3: Native("second")}


def test_restricted_provider_filters_both_ways() -> None:
    restricted = Restricted(FakeProvider("odd", {1, 2, 3}), lambda codepoint: codepoint % 2 == 1)
    assert set(restricted.codepoints()) == {1, 3}
    assert restricted.resolve(2) is None


def test_cjk_offset_keeps_latin_range_and_exempt_codepoints() -> None:
    offset = CjkOffset(-20, CodepointSet.parse(["AC00-D7A3"]))
    assert offset.for_codepoint(0x4E2D, cells=2) == -20
    assert offset.for_codepoint(0xFF71, cells=1) == -20
    assert offset.for_codepoint(0xD55C, cells=2) == 0
    assert offset.for_codepoint(0x03B1, cells=1) == 0


def test_cjk_offset_nudges_listed_codepoints() -> None:
    nudge = Nudge(codepoints=CodepointSet.parse(["FF08"]), x=-180)
    offset = CjkOffset(-20, CodepointSet(), (nudge,))
    assert offset.nudge(0xFF08).transformPoint((500, 0)) == (320, 0)
    assert offset.nudge(0xFF09) == Identity


def test_grid_cjk_cells_follow_the_ambiguous_policy() -> None:
    narrow = Grid(600, AmbiguousWidth.NARROW, LINE)
    wide = Grid(528, AmbiguousWidth.WIDE, LINE)
    assert narrow.cjk_cells(0x2460, 1000, 1000) == 1
    assert wide.cjk_cells(0x2460, 1000, 1000) == 2
    assert wide.cjk_cells(0x03B1, 1000, 1000) == 1
    assert narrow.cjk_cells(0xE000, 1000, 1000) == 2
    assert narrow.narrow_advances(0x000D) == {0, 600}
    assert narrow.narrow_advances(0x4E00) == frozenset()


def test_braille_dots_follow_bit_order() -> None:
    source = BrailleSource(LINE, dot_size=0.4)
    assert source.outline("uni2800").commands == ()
    assert len(source.outline("uni28FF").commands) == 16
    dot1 = source.outline("uni2801").render(Identity)
    dot8 = source.outline("uni2880").render(Identity)
    dot1.recalcBounds(None)
    dot8.recalcBounds(None)
    assert dot1.xMax < 300 < dot8.xMin
    assert dot1.yMin > dot8.yMax


def test_synthetic_provider_covers_its_range() -> None:
    provider = SyntheticProvider(BrailleSource(LINE, 0.4), BRAILLE_PATTERNS, 600)
    assert len(list(provider.codepoints())) == 256
    assert provider.resolve(0x41) is None


def test_ideographic_space_draws_eight_dashes_inside_its_square() -> None:
    square = Box(255, 44, 945, 734)
    glyph = IdeographicSpaceSource(square, stroke=44, dash_ratio=0.3).outline("uni3000")
    rendered = glyph.render(Identity)
    rendered.recalcBounds(None)
    assert rendered.numberOfContours == 8
    assert (rendered.xMin, rendered.yMin, rendered.xMax, rendered.yMax) == (255, 44, 945, 734)


def test_shades_tile_the_line_and_dark_shade_overhangs() -> None:
    source = ShadeSource(LINE, cells=1, overhang=50)
    light = source.outline("uni2591").render(Identity)
    dark = source.outline("uni2593").render(Identity)
    light.recalcBounds(None)
    dark.recalcBounds(None)
    assert (light.yMin, light.yMax) == (-303, 947)
    assert (dark.xMin, dark.yMin, dark.xMax, dark.yMax) == (-50, -353, 650, 997)


def test_braille_field_can_center_on_the_symbol_line() -> None:
    field = Box(0, 349 - 500, 600, 349 + 500)
    glyph = BrailleSource(field, dot_size=0.4).outline("uni28FF").render(Identity)
    glyph.recalcBounds(None)
    assert (glyph.yMin + glyph.yMax) / 2 == 349
