from pathlib import Path

import pytest
from fontTools.ttLib import TTFont

from plemio.check import check_font
from plemio.compose import build_font
from plemio.config import Config
from plemio.jobs import BuildJob
from plemio.measure import italic_pivot
from plemio.sources import SourceCatalog
from plemio.styles import STYLES_BY_NAME
from plemio.unicode import is_private_use_any_plane


@pytest.fixture(scope="module")
def catalog(config: Config) -> SourceCatalog:
    catalog = SourceCatalog.from_config(config)
    if not all(file.path.is_file() for file in catalog.files()):
        pytest.skip("sources not fetched; run `plemio fetch`")
    return catalog


CASES = [("plemio", "Regular", 528), ("nerd", "SemiBoldItalic", 600)]


@pytest.fixture(scope="module")
def built_case_fonts(
    config: Config, catalog: SourceCatalog, tmp_path_factory: pytest.TempPathFactory
) -> dict[tuple[str, str], Path]:
    return {
        (variant, style): build_font(
            config,
            catalog,
            BuildJob(variant, "JP", STYLES_BY_NAME[style]),
            tmp_path_factory.mktemp(f"{variant}-{style}"),
        )
        for variant, style, _ in CASES
    }


@pytest.mark.parametrize("case", CASES, ids=[f"{variant}-{style}" for variant, style, _ in CASES])
def test_built_font_passes_checks(
    config: Config, built_case_fonts: dict[tuple[str, str], Path], case: tuple[str, str, int]
) -> None:
    variant, style, cell = case
    path = built_case_fonts[variant, style]
    assert check_font(config, path) == []
    with TTFont(path) as font:
        assert font["hmtx"][font.getBestCmap()[ord("0")]][0] == cell
        cmap, glyf = font.getBestCmap(), font["glyf"]
        scale_y = config.variants[variant].latin_scale[1]
        expected_y = config.symbols.operator_center_y * scale_y
        for codepoint in (0x2211, 0x222B):
            glyph = glyf[cmap[codepoint]]
            assert abs((glyph.yMin + glyph.yMax) / 2 - expected_y) < 5


def test_private_use_glyphs_stay_inside_their_advance(
    config: Config, built_case_fonts: dict[tuple[str, str], Path]
) -> None:
    with TTFont(built_case_fonts["nerd", "SemiBoldItalic"]) as font:
        cmap, glyf, hmtx = font.getBestCmap(), font["glyf"], font["hmtx"]
        private_use = [codepoint for codepoint in cmap if is_private_use_any_plane(codepoint)]
        outside = [
            codepoint
            for codepoint in private_use
            if codepoint not in config.nerd_fonts.cell_ranges
            and (glyph := glyf[cmap[codepoint]]).numberOfContours
            and (glyph.xMin < 0 or glyph.xMax > hmtx[cmap[codepoint]][0])
        ]
    assert not outside


def test_italic_pivot_matches_plex_mono(catalog: SourceCatalog) -> None:
    upright = TTFont(catalog.font("plex-mono", style="Regular"))
    italic = TTFont(catalog.font("plex-mono", style="Italic"))
    assert 230 < italic_pivot(upright, italic) < 280


@pytest.mark.parametrize("case", CASES, ids=[f"{variant}-{style}" for variant, style, _ in CASES])
def test_built_fonts_map_private_use_from_nerd_fonts_only(
    config: Config,
    catalog: SourceCatalog,
    built_case_fonts: dict[tuple[str, str], Path],
    case: tuple[str, str, int],
) -> None:
    variant, style, _ = case
    with TTFont(catalog.font(config.nerd_fonts.source)) as icons:
        expected = {cp for cp in icons.getBestCmap() if is_private_use_any_plane(cp)}
    with TTFont(built_case_fonts[variant, style]) as font:
        private = {cp for cp in font.getBestCmap() if is_private_use_any_plane(cp)}
    assert private == (expected if variant == "nerd" else set())
