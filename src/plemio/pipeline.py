from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from plemio.compose import build_font
from plemio.config import Config, load_config
from plemio.jobs import BuildJob
from plemio.sources import SourceCatalog


def fonts_dir(config: Config) -> Path:
    return config.build_dir / "fonts"


def _build_one(root: Path, job: BuildJob) -> tuple[Path, float]:
    started = time.perf_counter()
    config = load_config(root)
    path = build_font(config, SourceCatalog.from_config(config), job, fonts_dir(config))
    return path, time.perf_counter() - started


def build_fonts(
    config: Config, jobs: list[BuildJob], workers: int, log: Callable[[str], None]
) -> Iterator[Path]:
    if workers <= 1:
        for job in jobs:
            path, seconds = _build_one(config.root, job)
            log(f"built {path.name} in {seconds:.0f}s")
            yield path
        return
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_build_one, config.root, job) for job in jobs]
        for future in as_completed(futures):
            path, seconds = future.result()
            log(f"built {path.name} in {seconds:.0f}s")
            yield path
