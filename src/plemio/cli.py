from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

import typer

from plemio.config import Config, load_config
from plemio.jobs import plan_jobs
from plemio.pipeline import build_fonts, fonts_dir
from plemio.sources import Lockfile, SourceCatalog, SyncMode, sync_sources
from plemio.styles import parse_styles

app = typer.Typer(no_args_is_help=True, add_completion=False, help="Build the Plemio fonts.")

VariantOption = Annotated[
    list[str] | None, typer.Option("--variant", "-v", help="Variant such as nerd; repeatable.")
]
RegionOption = Annotated[
    list[str] | None, typer.Option("--region", "-r", help="Region to build; repeatable.")
]
StyleOption = Annotated[
    list[str] | None, typer.Option("--style", "-s", help="Style such as Regular; repeatable.")
]


def _config() -> Config:
    return load_config()


def _choose(kind: str, requested: list[str] | None, known: list[str]) -> list[str]:
    chosen = requested or known
    unknown = sorted(set(chosen) - set(known))
    if unknown:
        raise typer.BadParameter(f"unknown {kind}(s) {unknown}; choose from {known}")
    return chosen


def _regions(config: Config, requested: list[str] | None) -> list[str]:
    return _choose("region", requested, list(config.regions))


def _variants(config: Config, requested: list[str] | None) -> list[str]:
    return _choose("variant", requested, list(config.variants))


def _fail(message: str) -> None:
    typer.secho(message, fg=typer.colors.RED, err=True)
    raise typer.Exit(1)


@app.command()
def fetch(
    mode: Annotated[
        SyncMode, typer.Option(help="download, update-lock after a revision bump, or offline.")
    ] = SyncMode.DOWNLOAD,
) -> None:
    """Download the pinned upstream fonts and verify them against sources.lock."""
    config = _config()
    report = sync_sources(
        SourceCatalog.from_config(config), Lockfile.for_config(config), mode, log=typer.echo
    )
    typer.echo(f"downloaded={report.downloaded} verified={report.verified}")
    if report.errors:
        _fail("\n".join(report.errors))


@app.command()
def build(
    variant: VariantOption = None,
    region: RegionOption = None,
    style: StyleOption = None,
    jobs: Annotated[int, typer.Option("--jobs", "-j", min=1)] = max(1, (os.cpu_count() or 2) // 2),
) -> None:
    """Compose one TTF per region and style into build/fonts."""
    config = _config()
    planned = plan_jobs(_variants(config, variant), _regions(config, region), parse_styles(style))
    typer.echo(f"building {len(planned)} font(s) with {jobs} worker(s)")
    for _ in build_fonts(config, planned, jobs, typer.echo):
        pass


@app.command()
def check(
    paths: Annotated[list[Path] | None, typer.Argument(help="Fonts to check.")] = None,
) -> None:
    """Verify width, metadata and coverage invariants of built fonts."""
    from plemio.check import check_font  # noqa: PLC0415

    config = _config()
    targets = paths or sorted(fonts_dir(config).glob("*.ttf"))
    if not targets:
        _fail("no fonts to check; run `plemio build` first")
    failures = 0
    for path in targets:
        problems = check_font(config, path)
        failures += bool(problems)
        status = "FAIL" if problems else "ok"
        typer.echo(f"{status:4} {path.name}")
        for problem in problems:
            typer.echo(f"     - {problem}")
    if failures:
        _fail(f"{failures} font(s) failed")


@app.command()
def bundle(variant: VariantOption = None, style: StyleOption = None) -> None:
    """Pack the regional fonts of each variant and style into one TTC with shared glyphs."""
    from plemio.bundle import BundleError, bundle_style  # noqa: PLC0415

    config = _config()
    for name in _variants(config, variant):
        for selected in parse_styles(style):
            try:
                path = bundle_style(config, fonts_dir(config), name, selected)
            except BundleError as err:
                _fail(str(err))
            typer.echo(f"bundled {path.relative_to(config.root)}")


@app.command()
def package(variant: VariantOption = None) -> None:
    """Package built TTFs, TTCs, and licenses into release ZIPs under build/dist."""
    from plemio.package import PackageError, package_releases  # noqa: PLC0415

    config = _config()
    try:
        archives = package_releases(
            config,
            fonts_dir(config),
            config.build_dir / "ttc",
            config.build_dir / "dist",
            _variants(config, variant),
        )
    except PackageError as err:
        _fail(str(err))
    for path in archives:
        typer.echo(f"packaged {path.relative_to(config.root)}")


@app.command()
def preview(
    variant: VariantOption = None,
    region: RegionOption = None,
    style: StyleOption = None,
    size: Annotated[int, typer.Option(min=8)] = 28,
) -> None:
    """Render sample text from built fonts into build/preview."""
    from plemio.preview import render_preview  # noqa: PLC0415

    config = _config()
    jobs = plan_jobs(
        _variants(config, variant), _regions(config, region), parse_styles(style or ["Regular"])
    )
    for job in jobs:
        try:
            path = render_preview(config, fonts_dir(config), job, size)
        except OSError as err:
            _fail(f"cannot render preview for {job.filename(config)}: {err}")
        typer.echo(f"rendered {path.relative_to(config.root)}")


@app.command()
def specimen(region: RegionOption = None) -> None:
    """Regenerate the README specimen images in docs/images from built fonts."""
    from plemio.specimen import render_specimens  # noqa: PLC0415

    config = _config()
    try:
        paths = render_specimens(
            config,
            fonts_dir(config),
            config.root / "docs" / "images",
            _regions(config, region),
        )
    except (FileNotFoundError, RuntimeError) as err:
        _fail(str(err))
    for path in paths:
        typer.echo(f"rendered {path.relative_to(config.root)}")
