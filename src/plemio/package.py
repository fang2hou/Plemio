from __future__ import annotations

import zipfile
from collections.abc import Iterable
from pathlib import Path

from plemio.config import Config, Variant
from plemio.jobs import BuildJob
from plemio.styles import STYLES


class PackageError(RuntimeError):
    pass


def _license_entries(config: Config, variant: Variant) -> list[tuple[Path, str]]:
    project_license = config.root / "OFL.txt"
    if not project_license.is_file():
        msg = f"missing project license {project_license}"
        raise PackageError(msg)
    entries: list[tuple[Path, str]] = [(project_license, "licenses/OFL-Plemio.txt")]
    for source_dir in sorted(config.sources_dir.iterdir()):
        if not source_dir.is_dir():
            continue
        if source_dir.name == "nerd-fonts" and not variant.nerd_fonts:
            continue
        entries.extend(
            (candidate, f"licenses/{source_dir.name}-{candidate.name}")
            for candidate in sorted(source_dir.iterdir())
            if candidate.is_file()
            and (candidate.name.startswith("LICENSE") or candidate.name == "OFL.txt")
        )
    return entries


def _write_zip(output: Path, files: Iterable[tuple[Path, str]]) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for source, arcname in files:
            archive.write(source, arcname)
    return output


def package_releases(
    config: Config,
    font_dir: Path,
    ttc_dir: Path,
    dist_dir: Path,
    variants: Iterable[str] | None = None,
) -> list[Path]:
    selected = list(variants) if variants is not None else list(config.variants)
    archives: list[Path] = []
    for variant_name in selected:
        variant = config.variants[variant_name]
        prefix = variant.family(config.family.name).replace(" ", "-")
        licenses = _license_entries(config, variant)
        for region in config.regions:
            ttfs = [
                font_dir / BuildJob(variant_name, region, style).filename(config)
                for style in STYLES
            ]
            missing = [path.name for path in ttfs if not path.is_file()]
            if missing:
                msg = f"cannot package {prefix}-{region}.zip: missing {missing}"
                raise PackageError(msg)
            entries = [(path, path.name) for path in ttfs] + licenses
            archives.append(_write_zip(dist_dir / f"{prefix}-{region}.zip", entries))
        ttcs = [ttc_dir / f"{prefix}-{style.name}.ttc" for style in STYLES]
        missing_ttcs = [path.name for path in ttcs if not path.is_file()]
        if missing_ttcs:
            msg = f"cannot package {prefix}-TTC.zip: missing {missing_ttcs}"
            raise PackageError(msg)
        entries = [(path, path.name) for path in ttcs] + licenses
        archives.append(_write_zip(dist_dir / f"{prefix}-TTC.zip", entries))
    return archives
