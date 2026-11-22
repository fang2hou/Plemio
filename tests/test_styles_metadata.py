import pytest
from fontTools.ttLib import TTFont

from plemio.config import Config
from plemio.jobs import BuildJob
from plemio.metadata import FontNames, font_revision, write_names
from plemio.styles import STYLES, STYLES_BY_NAME, parse_styles


def test_sixteen_styles_with_plex_names() -> None:
    assert len(STYLES) == 16
    assert {"Regular", "Italic", "Text", "TextItalic", "BoldItalic"} <= set(STYLES_BY_NAME)


def test_parse_styles_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="Heavy"):
        parse_styles(["Heavy"])


def test_ribbi_names() -> None:
    names = FontNames("Plemio SC", STYLES_BY_NAME["BoldItalic"])
    assert names.family_records() == {1: "Plemio SC", 2: "Bold Italic"}
    assert names.postscript_name == "PlemioSC-BoldItalic"


def test_extended_weight_names_use_typographic_family() -> None:
    names = FontNames("Plemio JP", STYLES_BY_NAME["LightItalic"])
    assert names.family_records() == {
        1: "Plemio JP Light",
        2: "Italic",
        16: "Plemio JP",
        17: "Light Italic",
    }
    assert names.full_name == "Plemio JP Light Italic"


@pytest.mark.parametrize(("version", "revision"), [("0.1.0", 0.1), ("1.2.3", 1.203)])
def test_font_revision(version: str, revision: float) -> None:
    assert font_revision(version) == revision


def test_write_names_sets_designer_and_variant_copyrights(config: Config) -> None:
    regular = STYLES_BY_NAME["Regular"]
    plemio_font = TTFont()
    write_names(plemio_font, config, BuildJob("plemio", "SC", regular))
    assert plemio_font["name"].getDebugName(9) == "Zhou Fang"
    assert "Copyright 2026 Zhou Fang" in plemio_font["name"].getDebugName(0)
    assert "Ryan L McIntyre" not in plemio_font["name"].getDebugName(0)

    nerd_font = TTFont()
    write_names(nerd_font, config, BuildJob("nerd", "SC", regular))
    assert nerd_font["name"].getDebugName(9) == "Zhou Fang"
    assert "Ryan L McIntyre" in nerd_font["name"].getDebugName(0)
