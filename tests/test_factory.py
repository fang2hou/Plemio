import pytest
from fontTools.ttLib import TTFont

from plemio.config import Config
from plemio.factory import ProviderFactory
from plemio.jobs import BuildJob
from plemio.outlines import SourceFont
from plemio.providers import Drawn, Resolved, resolve_codepoints
from plemio.sources import SourceCatalog
from plemio.styles import STYLES_BY_NAME
from plemio.unicode import is_private_use_any_plane

VARIANTS = ("plemio", "nerd")


@pytest.fixture(scope="module")
def catalog(config: Config) -> SourceCatalog:
    catalog = SourceCatalog.from_config(config)
    if not all(file.path.is_file() for file in catalog.files()):
        pytest.skip("sources not fetched; run `plemio fetch`")
    return catalog


@pytest.fixture(scope="module", params=VARIANTS)
def stack(
    request: pytest.FixtureRequest, config: Config, catalog: SourceCatalog
) -> tuple[str, dict[int, Resolved]]:
    job = BuildJob(request.param, "SC", STYLES_BY_NAME["Regular"])
    latin = SourceFont("latin", TTFont(catalog.font("plex-mono", style="Regular")))
    factory = ProviderFactory(config, catalog, job, latin)
    return request.param, resolve_codepoints(factory.build(), config.exclude.__contains__)


def test_private_use_comes_from_nerd_fonts_only(
    config: Config, catalog: SourceCatalog, stack: tuple[str, dict[int, Resolved]]
) -> None:
    variant, resolved = stack
    private = {codepoint for codepoint in resolved if is_private_use_any_plane(codepoint)}
    with TTFont(catalog.font(config.nerd_fonts.source)) as icons:
        expected = {cp for cp in icons.getBestCmap() if is_private_use_any_plane(cp)}
    assert private == (expected if variant == "nerd" else set())
    assert all(
        isinstance(resolved[codepoint], Drawn) and resolved[codepoint].source.key == "nerd-fonts"
        for codepoint in private
    )


def test_restriction_spares_ordinary_codepoints(stack: tuple[str, dict[int, Resolved]]) -> None:
    _, resolved = stack
    for codepoint, source in ((0x4E2D, "cjk"), (0x218A, "jetbrains-mono")):
        plan = resolved[codepoint]
        assert isinstance(plan, Drawn)
        assert plan.source.key.startswith(source)
