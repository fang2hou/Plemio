import pytest
from fontTools.ttLib import TTFont

from plemio.check import check_font
from plemio.compose import build_font
from plemio.config import Config
from plemio.jobs import BuildJob
from plemio.measure import italic_pivot
from plemio.sources import SourceCatalog
from plemio.styles import STYLES_BY_NAME


@pytest.fixture(scope="module")
def catalog(config: Config) -> SourceCatalog:
    catalog = SourceCatalog.from_config(config)
    if not all(file.path.is_file() for file in catalog.files()):
        pytest.skip("sources not fetched; run `plemio fetch`")
    return catalog


CASES = [("plemio", "Regular", 528), ("nerd", "SemiBoldItalic", 600)]


@pytest.mark.parametrize("case", CASES, ids=[f"{variant}-{style}" for variant, style, _ in CASES])
def test_built_font_passes_checks(
    config: Config, catalog: SourceCatalog, tmp_path, case: tuple[str, str, int]
) -> None:
    variant, style, cell = case
    path = build_font(config, catalog, BuildJob(variant, "JP", STYLES_BY_NAME[style]), tmp_path)
    assert check_font(config, path) == []
    font = TTFont(path)
    assert font["hmtx"][font.getBestCmap()[ord("0")]][0] == cell
    cmap, glyf = font.getBestCmap(), font["glyf"]
    scale_y = config.variants[variant].latin_scale[1]
    expected_y = config.symbols.operator_center_y * scale_y
    for codepoint in (0x2211, 0x222B):
        glyph = glyf[cmap[codepoint]]
        assert abs((glyph.yMin + glyph.yMax) / 2 - expected_y) < 5


def test_italic_pivot_matches_plex_mono(catalog: SourceCatalog) -> None:
    upright = TTFont(catalog.font("plex-mono", style="Regular"))
    italic = TTFont(catalog.font("plex-mono", style="Italic"))
    assert 230 < italic_pivot(upright, italic) < 280
