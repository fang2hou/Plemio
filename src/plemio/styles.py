from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Weight:
    name: str
    value: int


WEIGHTS = (
    Weight("Thin", 100),
    Weight("ExtraLight", 200),
    Weight("Light", 300),
    Weight("Regular", 400),
    Weight("Text", 450),
    Weight("Medium", 500),
    Weight("SemiBold", 600),
    Weight("Bold", 700),
)


@dataclass(frozen=True, slots=True)
class Style:
    weight: Weight
    italic: bool = False

    @property
    def name(self) -> str:
        if not self.italic:
            return self.weight.name
        return "Italic" if self.weight.name == "Regular" else f"{self.weight.name}Italic"

    @property
    def display_name(self) -> str:
        if not self.italic or self.weight.name == "Regular":
            return self.name
        return f"{self.weight.name} Italic"

    @property
    def is_ribbi(self) -> bool:
        return self.weight.name in {"Regular", "Bold"}

    @property
    def is_bold(self) -> bool:
        return self.weight.name == "Bold"


STYLES = tuple(Style(weight, italic) for italic in (False, True) for weight in WEIGHTS)
STYLES_BY_NAME = {style.name: style for style in STYLES}


def parse_styles(names: list[str] | None) -> tuple[Style, ...]:
    if not names:
        return STYLES
    unknown = [name for name in names if name not in STYLES_BY_NAME]
    if unknown:
        msg = f"unknown style(s) {unknown}; choose from {list(STYLES_BY_NAME)}"
        raise ValueError(msg)
    return tuple(STYLES_BY_NAME[name] for name in names)
