import pytest
from pydantic import ValidationError

from plemio.config import Config
from plemio.jobs import BuildJob, job_for_filename, plan_jobs
from plemio.sources import SourceCatalog, SourceError, download
from plemio.styles import STYLES, STYLES_BY_NAME
from plemio.unicode import AmbiguousWidth


def test_repository_config_is_valid(config: Config) -> None:
    assert list(config.regions) == ["SC", "TC", "JP", "KR"]
    assert config.metrics.line_height == 1300
    assert config.metrics.cell_center_y == 360
    assert 0xE0B0 in config.nerd_fonts.cell_ranges


def test_variants_match_the_two_families(config: Config) -> None:
    plemio, nerd = config.variants["plemio"], config.variants["nerd"]
    assert (plemio.half_width, plemio.ambiguous, plemio.nerd_fonts) == (
        528,
        AmbiguousWidth.WIDE,
        False,
    )
    assert (nerd.half_width, nerd.ambiguous, nerd.nerd_fonts) == (600, AmbiguousWidth.NARROW, True)
    assert config.family_name("nerd", "SC") == "Plemio Nerd SC"
    assert config.family_name("plemio", "KR") == "Plemio KR"


def test_fallback_must_reference_known_regions(config: Config) -> None:
    data = config.model_dump(by_alias=True) | {"root": config.root}
    data["regions"]["SC"]["fallback"] = ["XX"]
    with pytest.raises(ValidationError, match="fallback"):
        Config.model_validate(data)


def test_jobs_round_trip_through_filenames(config: Config) -> None:
    job = BuildJob("nerd", "TC", STYLES_BY_NAME["LightItalic"])
    assert job.filename(config) == "Plemio-Nerd-TC-LightItalic.ttf"
    assert job_for_filename(config, job.filename(config)) == job
    assert len(plan_jobs(config.variants, config.regions, STYLES)) == 2 * 4 * 16


def test_catalog_expands_every_template(config: Config) -> None:
    files = list(SourceCatalog.from_config(config).files())
    fonts = [file for file in files if file.path.suffix == ".ttf"]
    assert len(fonts) == 16 + 4 * 8 + 1 + 1 + 2 + 1
    assert len({file.path for file in files}) == len(files)


def test_catalog_resolves_parameterized_paths(config: Config) -> None:
    catalog = SourceCatalog.from_config(config)
    assert catalog.font("plex-sans", region="TC", weight="Text").name == "IBMPlexSansTC-Text.ttf"
    assert catalog.italic_font("jetbrains-mono").name == "JetBrainsMono-Italic[wght].ttf"
    assert catalog.italic_font("noto-sans-mono").name == "NotoSansMono[wdth,wght].ttf"


def test_download_rejects_non_https_urls(tmp_path) -> None:
    with pytest.raises(SourceError, match="https"):
        download("http://example.com/font.ttf", tmp_path / "font.ttf")
    with pytest.raises(SourceError, match="https"):
        download("file:///etc/passwd", tmp_path / "passwd")
