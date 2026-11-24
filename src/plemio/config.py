from __future__ import annotations

import tomllib
from functools import cached_property
from pathlib import Path
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    PlainSerializer,
    model_validator,
)
from pydantic.alias_generators import to_snake

from plemio.unicode import AmbiguousWidth, CodepointSet

CONFIG_FILE = "plemio.toml"
SOURCES_FILE = "sources.toml"
LOCK_FILE = "sources.lock"


def _kebab(name: str) -> str:
    return to_snake(name).replace("_", "-")


def _codepoints(value: object) -> CodepointSet:
    if isinstance(value, CodepointSet):
        return value
    if not isinstance(value, list):
        msg = "expected a list of codepoint ranges such as ['E0B0-E0D7']"
        raise TypeError(msg)
    return CodepointSet.parse(value)


def _codepoint(value: object) -> int:
    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        msg = "expected a hexadecimal codepoint such as '2714'"
        raise TypeError(msg)
    return int(value, 16)


Codepoint = Annotated[
    int, BeforeValidator(_codepoint), PlainSerializer(lambda value: f"{value:04X}")
]
Codepoints = Annotated[
    CodepointSet, BeforeValidator(_codepoints), PlainSerializer(CodepointSet.to_strings)
]


class Model(BaseModel):
    model_config = ConfigDict(
        alias_generator=_kebab,
        populate_by_name=True,
        frozen=True,
        extra="forbid",
        arbitrary_types_allowed=True,
    )


class Family(Model):
    name: str
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    vendor_id: str = Field(min_length=4, max_length=4)
    copyright: str
    designer: str
    url: str = ""


class Metrics(Model):
    ascender: int = Field(gt=0)
    descender: int = Field(lt=0)

    @property
    def line_height(self) -> int:
        return self.ascender - self.descender

    @property
    def cell_center_y(self) -> float:
        return (self.ascender + self.descender) / 2


class Variant(Model):
    label: str = ""
    half_width: int = Field(gt=0)
    latin_scale: tuple[float, float] = (1.0, 1.0)
    ambiguous: AmbiguousWidth
    nerd_fonts: bool = False
    visible_ideographic_space: bool = False
    full_width_line_art: bool = False
    cjk_over_latin: Codepoints = CodepointSet()

    def family(self, base: str) -> str:
        return f"{base} {self.label}".strip()


class Nudge(Model):
    codepoints: Codepoints
    x: float = 0
    y: float = 0


class Cjk(Model):
    scale: float = Field(gt=0.5, le=1.2)
    y_offset: float = 0
    y_offset_exempt: Codepoints = CodepointSet()
    nudges: tuple[Nudge, ...] = ()
    ink_margin: float = Field(ge=0)
    squeeze_aspect: float = Field(ge=1)
    preferred: Codepoints = CodepointSet()


class NerdFonts(Model):
    source: str
    icon_scale: float = Field(gt=0)
    icon_center_y: float
    cell_ranges: Codepoints = CodepointSet()
    cell_reference: str = Field(min_length=1, max_length=1)


class LineArt(Model):
    block_overhang: float = Field(ge=0)


class IdeographicSpace(Model):
    center_y: float
    size: float = Field(gt=0, lt=1)
    stroke: float = Field(gt=0)
    dash_ratio: float = Field(gt=0, lt=1)


class Braille(Model):
    enabled: bool = True
    height: float = Field(gt=0)
    dot_size: float = Field(gt=0, lt=1)


class Emboldened(Model):
    codepoint: Codepoint
    source: Codepoint
    stroke_ratio: float = Field(gt=1)


class Symbols(Model):
    icon_center_y: float
    operator_center_y: float
    operators: Codepoints = CodepointSet()
    fixed: Codepoints = CodepointSet()
    override: Codepoints = CodepointSet()
    ink_margin: float = Field(ge=0)
    max_height: float = Field(gt=0)
    stroke_probe: str = Field(min_length=1, max_length=1)
    emboldened: tuple[Emboldened, ...] = ()


class Supplement(Model):
    source: str
    fit: Literal["monospaced", "proportional"] = "monospaced"
    axes: dict[str, float] = Field(default_factory=dict)


class Region(Model):
    fallback: tuple[str, ...]
    script: str
    code_pages: tuple[int, ...]
    localized: dict[str, str] = Field(default_factory=dict)


class Config(Model):
    root: Path = Field(exclude=True)
    exclude: Codepoints = CodepointSet()
    family: Family
    metrics: Metrics
    variants: dict[str, Variant]
    cjk: Cjk
    line_art: LineArt
    nerd_fonts: NerdFonts
    braille: Braille
    symbols: Symbols
    ideographic_space: IdeographicSpace
    supplements: tuple[Supplement, ...] = ()
    regions: dict[str, Region]

    @model_validator(mode="after")
    def _check_fallbacks(self) -> Config:
        for name, region in self.regions.items():
            unknown = set(region.fallback) - set(self.regions)
            if unknown or name in region.fallback:
                msg = f"region {name} has an invalid fallback list {region.fallback}"
                raise ValueError(msg)
        return self

    @cached_property
    def sources_dir(self) -> Path:
        return self.root / "sources"

    @cached_property
    def build_dir(self) -> Path:
        return self.root / "build"

    def family_name(self, variant: str, region: str) -> str:
        return f"{self.variants[variant].family(self.family.name)} {region}"


def find_root(start: Path | None = None) -> Path:
    here = (start or Path.cwd()).resolve()
    for candidate in (here, *here.parents):
        if (candidate / CONFIG_FILE).is_file():
            return candidate
    msg = f"{CONFIG_FILE} not found in {here} or any parent directory"
    raise FileNotFoundError(msg)


def load_config(root: Path | None = None) -> Config:
    root = root or find_root()
    data = tomllib.loads((root / CONFIG_FILE).read_text(encoding="utf-8"))
    return Config.model_validate({**data, "root": root})
