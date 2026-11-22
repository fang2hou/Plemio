from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from plemio.config import Config
from plemio.styles import STYLES, Style


@dataclass(frozen=True, slots=True)
class BuildJob:
    variant: str
    region: str
    style: Style

    def family(self, config: Config) -> str:
        return config.variants[self.variant].family(config.family.name)

    def filename(self, config: Config) -> str:
        return f"{self.family(config).replace(' ', '-')}-{self.region}-{self.style.name}.ttf"


def plan_jobs(
    variants: Iterable[str], regions: Iterable[str], styles: Iterable[Style]
) -> list[BuildJob]:
    regions, styles = list(regions), list(styles)
    return [
        BuildJob(variant, region, style)
        for variant in variants
        for style in styles
        for region in regions
    ]


def job_for_filename(config: Config, filename: str) -> BuildJob | None:
    jobs = plan_jobs(config.variants, config.regions, STYLES)
    return next((job for job in jobs if job.filename(config) == filename), None)
