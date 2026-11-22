from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from plemio.config import Config
from plemio.jobs import BuildJob

SAMPLES = (
    "The quick brown fox jumps over the lazy dog. 0O 1lI |!",
    'fn main() { let s = "混排テスト 한국어"; } // → ⇒ ≠ ≤ ≥',
    "|漢字かな|ABCD|全角　空白|1234|",
    "|永和九年|abcdefgh|〇一二三|wxyz|",
    "简体 繁體 日本語 한국어 ，。、！？「」【】",
    "┌──┬──┐ ╔══╗ ░▒▓█ ▁▂▃▄▅▆▇█ ⣿⠿",
    "│ab│中│ ║  ║ ⌘⌥⌃⇧⏎⌫⎋ ❯ ➜ ✗ ⚠",
    "\ue0b0\ue0b1\ue0b2\ue0b3 \uf015 \ue7a8 \uf09b \uf113 \ue606 \uf120 \U000f0219 \ue0a0 \uf418",
    "①②③ ★☆ ※ §×÷ αβγδ АБВГ “quote” … ½ ℃",
)
INK = (24, 24, 27)
GUIDE = (228, 228, 235)
PAPER = (255, 255, 255)
BANDS = ((246, 246, 250), (236, 238, 246))
MIDLINE = (232, 120, 120)


def render_preview(config: Config, font_dir: Path, job: BuildJob, size: int) -> Path:
    font_path = font_dir / job.filename(config)
    font = ImageFont.truetype(font_path, size)
    cell = size * config.variants[job.variant].half_width / 1000
    line = size * config.metrics.line_height / 1000
    columns = max(len(sample) * 2 for sample in SAMPLES)
    margin = int(cell * 2)
    width = int(margin * 2 + cell * columns)
    height = int(margin * 2 + line * (len(SAMPLES) + 1))
    image = Image.new("RGB", (width, height), PAPER)
    draw = ImageDraw.Draw(image)
    rows = (f"{job.family(config)} {job.region} {job.style.display_name}", *SAMPLES)
    midline = size * (config.metrics.ascender - config.metrics.cell_center_y) / 1000
    for row in range(len(rows)):
        top = margin + row * line
        draw.rectangle([(margin, top), (width - margin, top + line - 1)], fill=BANDS[row % 2])
        draw.line([(margin, top + midline), (width - margin, top + midline)], fill=MIDLINE)
    for column in range(columns + 1):
        x = margin + column * cell
        draw.line([(x, margin), (x, height - margin)], fill=GUIDE)
    for row, text in enumerate(rows):
        draw.text((margin, margin + row * line), text, font=font, fill=INK)
    output = config.build_dir / "preview" / f"{font_path.stem}.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)
    return output
