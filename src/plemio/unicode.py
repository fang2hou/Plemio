from __future__ import annotations

import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

PRIVATE_USE_AREA = range(0xE000, 0xF900)
COMPATIBILITY_IDEOGRAPHS = (range(0xF900, 0xFB00), range(0x2F800, 0x2FA20))
LETTER_SCRIPTS = (
    range(0x0250, 0x02B0),
    range(0x0370, 0x0530),
    range(0x1F00, 0x2000),
)


class AmbiguousWidth(StrEnum):
    NARROW = "narrow"
    WIDE = "wide"


@dataclass(frozen=True, slots=True)
class CodepointRange:
    first: int
    last: int

    @classmethod
    def parse(cls, text: str) -> CodepointRange:
        first, _, last = text.strip().partition("-")
        return cls(int(first, 16), int(last or first, 16))

    def __contains__(self, codepoint: object) -> bool:
        return isinstance(codepoint, int) and self.first <= codepoint <= self.last

    def __str__(self) -> str:
        if self.first == self.last:
            return f"{self.first:04X}"
        return f"{self.first:04X}-{self.last:04X}"


@dataclass(frozen=True, slots=True)
class CodepointSet:
    ranges: tuple[CodepointRange, ...] = ()

    @classmethod
    def parse(cls, items: Iterable[str]) -> CodepointSet:
        return cls(tuple(CodepointRange.parse(item) for item in items))

    def __contains__(self, codepoint: object) -> bool:
        return any(codepoint in r for r in self.ranges)

    def to_strings(self) -> list[str]:
        return [str(r) for r in self.ranges]


ZERO_WIDTH_CATEGORIES = frozenset({"Mn", "Me", "Cf", "Zl", "Zp"})


def is_zero_width(codepoint: int) -> bool:
    return unicodedata.category(chr(codepoint)) in ZERO_WIDTH_CATEGORIES


def is_control(codepoint: int) -> bool:
    return unicodedata.category(chr(codepoint)) == "Cc"


def is_private_use(codepoint: int) -> bool:
    return codepoint in PRIVATE_USE_AREA


def east_asian_width(codepoint: int) -> str:
    return unicodedata.east_asian_width(chr(codepoint))


def is_wide(codepoint: int) -> bool:
    return east_asian_width(codepoint) in {"W", "F"}


def is_letter_script(codepoint: int) -> bool:
    return any(codepoint in block for block in LETTER_SCRIPTS)


def allowed_cells(codepoint: int, ambiguous: AmbiguousWidth) -> frozenset[int]:
    if is_wide(codepoint):
        return frozenset({2})
    if ambiguous is AmbiguousWidth.NARROW:
        return frozenset({1, 2}) if is_private_use(codepoint) else frozenset({1})
    if east_asian_width(codepoint) in {"Na", "H"} or is_letter_script(codepoint):
        return frozenset({1})
    return frozenset({1, 2})


def canonical_ideograph(codepoint: int) -> int | None:
    if not any(codepoint in block for block in COMPATIBILITY_IDEOGRAPHS):
        return None
    parts = unicodedata.decomposition(chr(codepoint)).split()
    if len(parts) != 1 or parts[0].startswith("<"):
        return None
    return int(parts[0], 16)
