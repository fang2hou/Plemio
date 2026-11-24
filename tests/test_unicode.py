from plemio.unicode import (
    AmbiguousWidth,
    CodepointRange,
    CodepointSet,
    allowed_cells,
    canonical_ideograph,
    is_private_use,
    is_private_use_any_plane,
    is_zero_width,
)


def test_range_parses_single_and_span() -> None:
    assert CodepointRange.parse("274C") == CodepointRange(0x274C, 0x274C)
    assert CodepointRange.parse(" E0B0-E0D7 ") == CodepointRange(0xE0B0, 0xE0D7)


def test_set_membership() -> None:
    codepoints = CodepointSet.parse(["0370-03FF", "274C"])
    assert 0x03B1 in codepoints
    assert 0x274C in codepoints
    assert 0x0041 not in codepoints


def test_compatibility_ideograph_maps_to_unified() -> None:
    assert canonical_ideograph(0xF900) == 0x8C48
    assert canonical_ideograph(0x4E00) is None


def test_zero_width_is_category_based() -> None:
    assert is_zero_width(0x0301)
    assert is_zero_width(0x200B)
    assert not is_zero_width(0x000D)
    assert not is_zero_width(0xE000)


def test_set_round_trips_to_strings() -> None:
    items = ["0370-03FF", "274C"]
    assert CodepointSet.parse(items).to_strings() == items


def test_allowed_cells_by_policy() -> None:
    assert allowed_cells(0x4E00, AmbiguousWidth.NARROW) == {2}
    assert allowed_cells(0x2460, AmbiguousWidth.NARROW) == {1}
    assert allowed_cells(0x2460, AmbiguousWidth.WIDE) == {1, 2}
    assert allowed_cells(0x03B1, AmbiguousWidth.WIDE) == {1}
    assert allowed_cells(0xE000, AmbiguousWidth.NARROW) == {1, 2}


def test_private_use_any_plane_covers_all_three_areas() -> None:
    private = (0xE000, 0xF8FF, 0xF0000, 0xFFFFD, 0x100000, 0x10FFFD)
    public = (0xDFFF, 0xF900, 0xEFFFF, 0xFFFFE, 0x10FFFE)
    assert all(is_private_use_any_plane(codepoint) for codepoint in private)
    assert not any(is_private_use_any_plane(codepoint) for codepoint in public)
    assert is_private_use(0xE000)
    assert not is_private_use(0xF0000)
