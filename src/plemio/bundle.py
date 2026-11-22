from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from plemio.config import Config
from plemio.jobs import BuildJob
from plemio.styles import Style

BUNDLER = "otb-ttc-bundle@1.8.1"
NODE_HEAP_MB = 8192


class BundleError(RuntimeError):
    pass


def bundle_style(config: Config, font_dir: Path, variant: str, style: Style) -> Path:
    jobs = [BuildJob(variant, region, style) for region in config.regions]
    inputs = [font_dir / job.filename(config) for job in jobs]
    missing = [path.name for path in inputs if not path.is_file()]
    if missing:
        msg = f"cannot bundle {style.name}: missing {missing}"
        raise BundleError(msg)
    pnpm = shutil.which("pnpm")
    if pnpm is None:
        msg = "pnpm is required for TTC bundling"
        raise BundleError(msg)
    family = jobs[0].family(config).replace(" ", "-")
    output = config.build_dir / "ttc" / f"{family}-{style.name}.ttc"
    output.parent.mkdir(parents=True, exist_ok=True)
    environment = os.environ | {"NODE_OPTIONS": f"--max-old-space-size={NODE_HEAP_MB}"}
    command = [pnpm, "dlx", BUNDLER, "-x", "-Oz", "-o", str(output), *map(str, inputs)]
    subprocess.run(command, check=True, env=environment, capture_output=True)  # noqa: S603
    return output
