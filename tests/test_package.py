from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

import pytest

from plemio.config import Config, load_config
from plemio.jobs import BuildJob
from plemio.package import PackageError, package_releases
from plemio.styles import STYLES


def _seed_build_tree(config: Config, tmp_path: Path) -> Config:
    shutil.copy(config.root / "plemio.toml", tmp_path / "plemio.toml")
    sources_dir = tmp_path / "sources"
    for name, license_name in (
        ("plex-mono", "LICENSE.txt"),
        ("plex-sans", "LICENSE.txt"),
        ("nerd-fonts", "LICENSE"),
    ):
        (sources_dir / name).mkdir(parents=True)
        (sources_dir / name / license_name).write_text(f"{name} license\n", encoding="utf-8")
    (tmp_path / "OFL.txt").write_text("Plemio OFL\n", encoding="utf-8")
    test_config = load_config(tmp_path)
    font_dir = test_config.build_dir / "fonts"
    ttc_dir = test_config.build_dir / "ttc"
    font_dir.mkdir(parents=True)
    ttc_dir.mkdir(parents=True)
    for variant_name, variant in test_config.variants.items():
        prefix = variant.family(test_config.family.name).replace(" ", "-")
        for style in STYLES:
            (ttc_dir / f"{prefix}-{style.name}.ttc").write_bytes(b"ttc")
            for region in test_config.regions:
                job = BuildJob(variant_name, region, style)
                (font_dir / job.filename(test_config)).write_bytes(b"ttf")
    return test_config


def test_package_releases_creates_archives_with_scoped_licenses(
    config: Config, tmp_path: Path
) -> None:
    test_config = _seed_build_tree(config, tmp_path)
    archives = package_releases(
        test_config,
        test_config.build_dir / "fonts",
        test_config.build_dir / "ttc",
        test_config.build_dir / "dist",
    )
    names = sorted(path.name for path in archives)
    assert names == [
        "Plemio-JP.zip",
        "Plemio-KR.zip",
        "Plemio-Nerd-JP.zip",
        "Plemio-Nerd-KR.zip",
        "Plemio-Nerd-SC.zip",
        "Plemio-Nerd-TC.zip",
        "Plemio-Nerd-TTC.zip",
        "Plemio-SC.zip",
        "Plemio-TC.zip",
        "Plemio-TTC.zip",
    ]
    with zipfile.ZipFile(test_config.build_dir / "dist" / "Plemio-SC.zip") as plemio_zip:
        members = set(plemio_zip.namelist())
        assert "Plemio-SC-Regular.ttf" in members
        assert "licenses/OFL-Plemio.txt" in members
        assert "licenses/plex-mono-LICENSE.txt" in members
        assert "licenses/nerd-fonts-LICENSE" not in members
    with zipfile.ZipFile(test_config.build_dir / "dist" / "Plemio-Nerd-SC.zip") as nerd_zip:
        members = set(nerd_zip.namelist())
        assert "Plemio-Nerd-SC-Regular.ttf" in members
        assert "licenses/nerd-fonts-LICENSE" in members


def test_package_releases_fails_when_font_is_missing(config: Config, tmp_path: Path) -> None:
    test_config = _seed_build_tree(config, tmp_path)
    (test_config.build_dir / "fonts" / "Plemio-SC-Regular.ttf").unlink()
    with pytest.raises(PackageError, match=r"Plemio-SC-Regular\.ttf"):
        package_releases(
            test_config,
            test_config.build_dir / "fonts",
            test_config.build_dir / "ttc",
            test_config.build_dir / "dist",
            ["plemio"],
        )
