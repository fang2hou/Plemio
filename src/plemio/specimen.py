from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from plemio.config import Config
from plemio.jobs import BuildJob
from plemio.styles import STYLES_BY_NAME, WEIGHTS
from plemio.unicode import is_wide, is_zero_width

DEFAULT_FONT_SIZE = 13.5
SCALE = 2
NERD_SPECIMEN_STYLES = ("Regular", "Medium", "SemiBold")

_EDITOR_COMMENTS: dict[str, str] = {
    "SC": "# 2:1 CJK alignment: 中文, 日本語, 한국어",
    "TC": "# 2:1 CJK alignment: 繁體中文, 日本語, 한국어",
    "JP": "# 2:1 CJK alignment: 日本語, 中文, 한국어",
    "KR": "# 2:1 CJK alignment: 한국어, 中文, 日本語",
}

_EDITOR_LABELS: dict[str, str] = {
    "SC": '"中文「混排」テスト / 한국어"',
    "TC": '"繁體中文「混排」測試 / 한국어"',
    "JP": '"日本語「混植」テスト / 한국어"',
    "KR": '"한국어 「혼용」 테스트 / 日本語"',
}

_WEIGHT_SAMPLES: dict[str, str] = {
    "SC": "Plemio 永和九年 あいう 한글 0O1lI ⌘⇧",
    "TC": "Plemio 繁體字型 あいう 한글 0O1lI ⌘⇧",
    "JP": "Plemio 漢字仮名 あいう 한글 0O1lI ⌘⇧",
    "KR": "Plemio 한글글꼴 永和九 あい 0O1lI ⌘⇧",
}

_TERMINAL_PAIR: dict[str, str] = {
    "SC": "JP",
    "TC": "SC",
    "JP": "KR",
    "KR": "JP",
}


@dataclass(frozen=True, slots=True)
class Theme:
    window: str
    chrome: str
    border: str
    text: str
    muted: str
    badge_bg: str
    badge_fg: str
    keyword: str
    func: str
    type_name: str
    string: str
    green: str
    prompt_a: tuple[str, str]
    prompt_b: tuple[str, str]
    prompt_c: tuple[str, str]


LIGHT = Theme(
    window="#FFFFFF",
    chrome="#F8FAFC",
    border="#E2E8F0",
    text="#0F172A",
    muted="#64748B",
    badge_bg="#EFF6FF",
    badge_fg="#1D4ED8",
    keyword="#2563EB",
    func="#7C3AED",
    type_name="#B45309",
    string="#047857",
    green="#15803D",
    prompt_a=("#C2410C", "#FFFFFF"),
    prompt_b=("#B45309", "#FFFFFF"),
    prompt_c=("#15803D", "#FFFFFF"),
)

DARK = Theme(
    window="#141720",
    chrome="#1B1F2B",
    border="#2A3042",
    text="#E2E8F0",
    muted="#94A3B8",
    badge_bg="#1E293B",
    badge_fg="#7DD3FC",
    keyword="#7DD3FC",
    func="#C4B5FD",
    type_name="#FCD34D",
    string="#86EFAC",
    green="#86EFAC",
    prompt_a=("#C45C28", "#FAF6EC"),
    prompt_b=("#BE8C32", "#FAF6EC"),
    prompt_c=("#4B7F47", "#FAF6EC"),
)


def find_figcraft_cli() -> str:
    candidate = shutil.which("figcraft-cli") or str(Path.home() / ".local" / "bin" / "figcraft-cli")
    if Path(candidate).is_file():
        return candidate
    msg = "figcraft-cli is required to render specimen images"
    raise RuntimeError(msg)


def display_cells(text: str) -> int:
    return sum(0 if is_zero_width(ord(c)) else 2 if is_wide(ord(c)) else 1 for c in text)


def boxed(title: str, rows: list[str], inner_width: int) -> list[str]:
    top = f"╭─ {title} " + "─" * (inner_width - display_cells(title) - 3) + "╮"
    body = [f"│ {row}" + " " * (inner_width - display_cells(row) - 1) + "│" for row in rows]
    return [top, *body, "╰" + "─" * inner_width + "╯"]


def _load_font_cmd(config: Config, font_dir: Path, variant: str, region: str, style: str) -> dict:
    job = BuildJob(variant, region, STYLES_BY_NAME[style])
    path = font_dir / job.filename(config)
    if not path.is_file():
        msg = f"missing built font {path}; run `plemio build` first"
        raise FileNotFoundError(msg)
    return {"command": "text.loadFont", "params": {"path": str(path)}}


def _window_shell(
    frame_as: str,
    title: str,
    badge: str,
    theme: Theme,
    *,
    width: int,
    status_left: str,
    status_right: str,
    font_family: str,
) -> tuple[list[dict], str]:
    body_as = f"{frame_as}_body"
    commands: list[dict] = [
        {
            "command": "frame.create",
            "as": frame_as,
            "params": {
                "x": 0,
                "y": 0,
                "width": width,
                "name": frame_as,
                "props": {
                    "fill": theme.window,
                    "stroke": theme.border,
                    "strokeWeight": 1,
                    "cornerRadius": 12,
                    "layout": "vertical",
                    "sizingV": "hug",
                    "padding": 0,
                    "gap": 0,
                },
            },
        },
        {
            "command": "frame.create",
            "as": f"{frame_as}_bar",
            "params": {
                "parent": {"$ref": frame_as},
                "name": "titlebar",
                "props": {
                    "fill": theme.chrome,
                    "stroke": theme.border,
                    "strokeWeight": 1,
                    "strokeSides": [False, False, True, False],
                    "layout": "horizontal",
                    "sizingH": "fill",
                    "sizingV": "hug",
                    "padding": [9, 14, 9, 14],
                    "mainAlign": "spaceBetween",
                    "crossAlign": "center",
                },
            },
        },
        {
            "command": "frame.create",
            "as": f"{frame_as}_left",
            "params": {
                "parent": {"$ref": f"{frame_as}_bar"},
                "props": {
                    "fill": "none",
                    "layout": "horizontal",
                    "sizingH": "hug",
                    "sizingV": "hug",
                    "gap": 10,
                    "crossAlign": "center",
                },
            },
        },
        {
            "command": "frame.create",
            "as": f"{frame_as}_dots",
            "params": {
                "parent": {"$ref": f"{frame_as}_left"},
                "props": {
                    "fill": "none",
                    "layout": "horizontal",
                    "sizingH": "hug",
                    "sizingV": "hug",
                    "gap": 6,
                    "crossAlign": "center",
                },
            },
        },
    ]
    commands.extend(
        {
            "command": "shape.ellipse",
            "params": {
                "parent": {"$ref": f"{frame_as}_dots"},
                "x": 0,
                "y": 0,
                "width": 9,
                "height": 9,
                "props": {"fill": dot_color},
            },
        }
        for dot_color in ("#FF5F56", "#FFBD2E", "#27C93F")
    )
    commands.extend(
        [
            {
                "command": "node.create",
                "params": {
                    "type": "text",
                    "parent": {"$ref": f"{frame_as}_left"},
                    "text": title,
                    "props": {
                        "fontFamily": font_family,
                        "fontStyle": "Medium",
                        "fontSize": 11.5,
                        "fill": theme.text,
                    },
                },
            },
            {
                "command": "frame.create",
                "as": f"{frame_as}_badge",
                "params": {
                    "parent": {"$ref": f"{frame_as}_bar"},
                    "props": {
                        "fill": theme.badge_bg,
                        "cornerRadius": 5,
                        "layout": "horizontal",
                        "sizingH": "hug",
                        "sizingV": "hug",
                        "padding": [2, 8, 2, 8],
                    },
                },
            },
            {
                "command": "node.create",
                "params": {
                    "type": "text",
                    "parent": {"$ref": f"{frame_as}_badge"},
                    "text": badge,
                    "props": {
                        "fontFamily": font_family,
                        "fontStyle": "SemiBold",
                        "fontSize": 10.5,
                        "fill": theme.badge_fg,
                    },
                },
            },
            {
                "command": "frame.create",
                "as": body_as,
                "params": {
                    "parent": {"$ref": frame_as},
                    "name": "body",
                    "props": {
                        "fill": "none",
                        "layout": "vertical",
                        "sizingH": "fill",
                        "sizingV": "hug",
                        "padding": [16, 18, 16, 16],
                        "gap": 8,
                    },
                },
            },
            {
                "command": "frame.create",
                "as": f"{frame_as}_status",
                "params": {
                    "parent": {"$ref": frame_as},
                    "name": "statusbar",
                    "props": {
                        "fill": theme.chrome,
                        "stroke": theme.border,
                        "strokeWeight": 1,
                        "strokeSides": [True, False, False, False],
                        "layout": "horizontal",
                        "sizingH": "fill",
                        "sizingV": "hug",
                        "padding": [7, 14, 7, 14],
                        "mainAlign": "spaceBetween",
                        "crossAlign": "center",
                    },
                },
            },
            {
                "command": "node.create",
                "params": {
                    "type": "text",
                    "parent": {"$ref": f"{frame_as}_status"},
                    "text": status_left,
                    "props": {
                        "fontFamily": font_family,
                        "fontStyle": "Regular",
                        "fontSize": 10.5,
                        "fill": theme.muted,
                    },
                },
            },
            {
                "command": "node.create",
                "params": {
                    "type": "text",
                    "parent": {"$ref": f"{frame_as}_status"},
                    "text": status_right,
                    "props": {
                        "fontFamily": font_family,
                        "fontStyle": "Regular",
                        "fontSize": 10.5,
                        "fill": theme.muted,
                    },
                },
            },
        ]
    )
    return commands, body_as


def _styled_text_commands(
    node_as: str,
    parent_ref: str,
    lines: list[list[tuple[str, str, str]]],
    *,
    font_family: str,
    font_size: float,
    line_height: float,
    default_color: str,
) -> list[dict]:
    full_text = "\n".join("".join(seg for seg, _, _ in line) for line in lines)
    commands: list[dict] = [
        {
            "command": "node.create",
            "as": node_as,
            "params": {
                "type": "text",
                "parent": {"$ref": parent_ref},
                "text": full_text,
                "props": {
                    "fontFamily": font_family,
                    "fontStyle": "Regular",
                    "fontSize": font_size,
                    "lineHeight": line_height,
                    "fill": default_color,
                },
            },
        }
    ]
    offset = 0
    for row_index, line in enumerate(lines):
        for seg, color, style in line:
            end = offset + len(seg)
            if color != default_color or style != "Regular":
                commands.append(
                    {
                        "command": "text.style",
                        "params": {
                            "id": {"$ref": node_as},
                            "start": offset,
                            "end": end,
                            "fontStyle": style,
                            "textFills": [color],
                        },
                    }
                )
            offset = end
        if row_index + 1 < len(lines):
            offset += 1
    return commands


def _editor_commands(region: str, output_path: Path) -> list[dict]:
    theme = DARK
    name = "editor"
    family = f"Plemio {region}"
    commands, body_as = _window_shell(
        name,
        "format_grid.py",
        family,
        theme,
        width=540,
        status_left=f"{family} / Regular",
        status_right="2:1 CJK / UTF-8",
        font_family=family,
    )
    row_as = f"{name}_row"
    commands.insert(
        -3,
        {
            "command": "frame.create",
            "as": row_as,
            "params": {
                "parent": {"$ref": body_as},
                "props": {
                    "fill": "none",
                    "layout": "horizontal",
                    "sizingH": "fill",
                    "sizingV": "hug",
                    "gap": 14,
                    "crossAlign": "min",
                },
            },
        },
    )
    code_lines: list[list[tuple[str, str, str]]] = [
        [(_EDITOR_COMMENTS.get(region, _EDITOR_COMMENTS["SC"]), theme.muted, "Italic")],
        [
            ("def ", theme.keyword, "Regular"),
            ("format_row", theme.func, "Regular"),
            ("(name: ", theme.text, "Regular"),
            ("str", theme.type_name, "Regular"),
            (") -> ", theme.text, "Regular"),
            ("list", theme.type_name, "Regular"),
            ("[", theme.text, "Regular"),
            ("str", theme.type_name, "Regular"),
            ("]:", theme.text, "Regular"),
        ],
        [
            ("    label = ", theme.text, "Regular"),
            (_EDITOR_LABELS.get(region, _EDITOR_LABELS["SC"]), theme.string, "Regular"),
        ],
        [
            ("    marks = (", theme.text, "Regular"),
            ('"→"', theme.string, "Regular"),
            (", ", theme.text, "Regular"),
            ('"⇒"', theme.string, "Regular"),
            (", ", theme.text, "Regular"),
            ('"≠"', theme.string, "Regular"),
            (", ", theme.text, "Regular"),
            ('"≤"', theme.string, "Regular"),
            (", ", theme.text, "Regular"),
            ('"⌘"', theme.string, "Regular"),
            (")", theme.text, "Regular"),
        ],
        [("    grid = [", theme.text, "Regular")],
        [
            ("        ", theme.text, "Regular"),
            ('"| 简体 | 繁體 | 日本語 | 한국어 |"', theme.string, "Regular"),
            (",", theme.text, "Regular"),
        ],
        [
            ("        ", theme.text, "Regular"),
            ('"| 0O1l | I|[] | ⌘⌥⌃⇧ | ★※… |"', theme.string, "Regular"),
            (",", theme.text, "Regular"),
        ],
        [("    ]", theme.text, "Regular")],
        [
            ("    ", theme.text, "Regular"),
            ("return ", theme.keyword, "Regular"),
            ("[f", theme.string, "Regular"),
            ('"{label} {marks[0]} {r}"', theme.string, "Regular"),
            (" for ", theme.keyword, "Regular"),
            ("r ", theme.text, "Regular"),
            ("in ", theme.keyword, "Regular"),
            ("grid]", theme.text, "Regular"),
        ],
    ]
    gutter_text = "\n".join(f"{i:2}" for i in range(1, len(code_lines) + 1))
    gutter_cmd = {
        "command": "node.create",
        "params": {
            "type": "text",
            "parent": {"$ref": row_as},
            "text": gutter_text,
            "props": {
                "fontFamily": family,
                "fontStyle": "Regular",
                "fontSize": DEFAULT_FONT_SIZE,
                "lineHeight": 20,
                "fill": theme.muted,
            },
        },
    }
    code_cmds = _styled_text_commands(
        f"{name}_code",
        row_as,
        code_lines,
        font_family=family,
        font_size=DEFAULT_FONT_SIZE,
        line_height=20,
        default_color=theme.text,
    )
    commands = [*commands[:-3], gutter_cmd, *code_cmds, *commands[-3:]]
    commands.append(
        {
            "command": "file.export",
            "params": {
                "ids": [{"$ref": name}],
                "format": "png",
                "scale": SCALE,
                "path": str(output_path),
            },
        }
    )
    return commands


def _terminal_commands(region: str, output_path: Path) -> list[dict]:
    theme = DARK
    name = "terminal"
    family = f"Plemio Nerd {region}"
    font_size = 14
    line_height = 18.2
    commands, body_as = _window_shell(
        name,
        "zsh",
        family,
        theme,
        width=540,
        status_left=f"{family} / Regular",
        status_right="Nerd Fonts 3.5.1 / U+3000",
        font_family=family,
    )
    prompt_as = f"{name}_prompt"
    prompt_cmds: list[dict] = [
        {
            "command": "frame.create",
            "as": prompt_as,
            "params": {
                "parent": {"$ref": body_as},
                "props": {
                    "fill": "none",
                    "layout": "horizontal",
                    "sizingH": "hug",
                    "sizingV": "hug",
                    "gap": 0,
                    "crossAlign": "center",
                },
            },
        }
    ]
    segments = [
        (" \uf179 Plemio ", theme.prompt_a),
        (" \uf07c ~/src ", theme.prompt_b),
        (" \ue0a0 main ", theme.prompt_c),
    ]
    for idx, (label, (bg, fg)) in enumerate(segments):
        seg_as = f"{name}_seg{idx}"
        next_bg = segments[idx + 1][1][0] if idx + 1 < len(segments) else "none"
        prompt_cmds.extend(
            [
                {
                    "command": "frame.create",
                    "as": seg_as,
                    "params": {
                        "parent": {"$ref": prompt_as},
                        "props": {
                            "fill": bg,
                            "layout": "horizontal",
                            "sizingH": "hug",
                            "sizingV": "hug",
                            "padding": 0,
                        },
                    },
                },
                {
                    "command": "node.create",
                    "params": {
                        "type": "text",
                        "parent": {"$ref": seg_as},
                        "text": label,
                        "props": {
                            "fontFamily": family,
                            "fontStyle": "Regular",
                            "fontSize": font_size,
                            "lineHeight": line_height,
                            "fill": fg,
                        },
                    },
                },
                {
                    "command": "frame.create",
                    "as": f"{seg_as}_tip",
                    "params": {
                        "parent": {"$ref": prompt_as},
                        "props": {
                            "fill": next_bg,
                            "layout": "horizontal",
                            "sizingH": "hug",
                            "sizingV": "hug",
                            "padding": 0,
                        },
                    },
                },
                {
                    "command": "node.create",
                    "params": {
                        "type": "text",
                        "parent": {"$ref": f"{seg_as}_tip"},
                        "text": "\ue0b0",
                        "props": {
                            "fontFamily": family,
                            "fontStyle": "Regular",
                            "fontSize": font_size,
                            "lineHeight": line_height,
                            "fill": bg,
                        },
                    },
                },
            ]
        )

    other_region = _TERMINAL_PAIR.get(region, "JP")
    box_rows = boxed(
        "Build",
        [
            f"{region}  ████████████░░░░  75%  ⣿⡇",
            f"{other_region}  ██████▓▓▒▒░░░░░░  40%  ⠹ ",
            'ID  "full\u3000width"     U+3000  ',
        ],
        34,
    )
    term_lines: list[list[tuple[str, str, str]]] = [
        [("❯ ", theme.keyword, "Regular"), ("ls -F", theme.text, "Regular")],
        [
            ("  \uf07b ", theme.keyword, "Regular"),
            ("src/   ", theme.text, "Regular"),
            ("\uf07b ", theme.keyword, "Regular"),
            ("tests/   ", theme.text, "Regular"),
            ("\ue615 ", theme.type_name, "Regular"),
            ("plemio.toml   ", theme.text, "Regular"),
            ("\uf48a ", theme.func, "Regular"),
            ("README.md", theme.text, "Regular"),
        ],
        [("❯ ", theme.keyword, "Regular"), ("plemio check --summary", theme.text, "Regular")],
        [
            ("  \uf00c ", theme.green, "Regular"),
            ("128 fonts ok  ", theme.text, "Regular"),
            ("0O1lI  → ≠ ★ ※ …", theme.muted, "Regular"),
        ],
        [],
        *[[(row, theme.text, "Regular")] for row in box_rows],
    ]
    term_cmds = _styled_text_commands(
        f"{name}_lines",
        body_as,
        term_lines,
        font_family=family,
        font_size=font_size,
        line_height=line_height,
        default_color=theme.text,
    )
    commands = [*commands[:-3], *prompt_cmds, *term_cmds, *commands[-3:]]
    commands.append(
        {
            "command": "file.export",
            "params": {
                "ids": [{"$ref": name}],
                "format": "png",
                "scale": SCALE,
                "path": str(output_path),
            },
        }
    )
    return commands


def _families_commands(config: Config, region: str, output_path: Path) -> list[dict]:
    theme = LIGHT
    font_size = 15
    line_height = 22
    samples = [
        "|中文|English|日本語|한국어|",
        "→ ⇒ ① ★ ※ … “quote” §×÷",
        "┌──┬──┐ ░▒▓█ ⣿⠿ ⌘⌥⇧⏎",
    ]
    panels = [
        (
            f"Plemio {region}",
            "Editors & Prose | Full-width symbols & box drawing",
            "plemio",
            [*samples],
        ),
        (
            f"Plemio Nerd {region}",
            "Terminals & Prompts | Strict wcwidth + Nerd icons",
            "nerd",
            [*samples[:-1], f"{samples[-1]}  \uf07b \ue0a0 \uf09b \u3000"],
        ),
    ]
    card_w = 600
    grid_w = card_w - 44
    commands: list[dict] = [
        {
            "command": "frame.create",
            "as": "families",
            "params": {
                "x": 0,
                "y": 0,
                "width": card_w,
                "name": "families",
                "props": {
                    "fill": theme.window,
                    "stroke": theme.border,
                    "strokeWeight": 1,
                    "cornerRadius": 12,
                    "layout": "vertical",
                    "sizingV": "hug",
                    "padding": 22,
                    "gap": 18,
                },
            },
        }
    ]
    for family, meta, variant_key, lines in panels:
        panel_as = f"panel_{variant_key}"
        box_as = f"gridbox_{variant_key}"
        cell_px = font_size * config.variants[variant_key].half_width / 1000
        box_h = len(lines) * line_height
        commands.extend(
            [
                {
                    "command": "frame.create",
                    "as": panel_as,
                    "params": {
                        "parent": {"$ref": "families"},
                        "props": {
                            "fill": "none",
                            "layout": "vertical",
                            "sizingH": "fill",
                            "sizingV": "hug",
                            "gap": 8,
                        },
                    },
                },
                {
                    "command": "frame.create",
                    "as": f"{panel_as}_head",
                    "params": {
                        "parent": {"$ref": panel_as},
                        "props": {
                            "fill": "none",
                            "layout": "horizontal",
                            "sizingH": "fill",
                            "sizingV": "hug",
                            "mainAlign": "spaceBetween",
                            "crossAlign": "center",
                        },
                    },
                },
                {
                    "command": "node.create",
                    "params": {
                        "type": "text",
                        "parent": {"$ref": f"{panel_as}_head"},
                        "text": family,
                        "props": {
                            "fontFamily": family,
                            "fontStyle": "SemiBold",
                            "fontSize": 13,
                            "fill": theme.keyword,
                        },
                    },
                },
                {
                    "command": "node.create",
                    "params": {
                        "type": "text",
                        "parent": {"$ref": f"{panel_as}_head"},
                        "text": meta,
                        "props": {
                            "fontFamily": family,
                            "fontStyle": "Regular",
                            "fontSize": 11,
                            "fill": theme.muted,
                        },
                    },
                },
                {
                    "command": "frame.create",
                    "as": box_as,
                    "params": {
                        "parent": {"$ref": panel_as},
                        "width": grid_w,
                        "height": box_h + 12,
                        "props": {
                            "fill": theme.chrome,
                            "stroke": theme.border,
                            "strokeWeight": 1,
                            "cornerRadius": 8,
                            "clip": True,
                        },
                    },
                },
            ]
        )
        max_cols = int((grid_w - 16) / cell_px)
        commands.extend(
            {
                "command": "shape.rectangle",
                "params": {
                    "parent": {"$ref": box_as},
                    "x": 10 + col * cell_px,
                    "y": 6,
                    "width": 1,
                    "height": box_h,
                    "props": {"fill": "#E2E8F0"},
                },
            }
            for col in range(max_cols + 1)
        )
        commands.append(
            {
                "command": "node.create",
                "params": {
                    "type": "text",
                    "parent": {"$ref": box_as},
                    "x": 10,
                    "y": 6,
                    "text": "\n".join(lines),
                    "props": {
                        "fontFamily": family,
                        "fontStyle": "Regular",
                        "fontSize": font_size,
                        "lineHeight": line_height,
                        "fill": theme.text,
                    },
                },
            }
        )
    commands.append(
        {
            "command": "file.export",
            "params": {
                "ids": [{"$ref": "families"}],
                "format": "png",
                "scale": SCALE,
                "path": str(output_path),
            },
        }
    )
    return commands


def _weights_commands(region: str, output_path: Path) -> list[dict]:
    theme = LIGHT
    family = f"Plemio {region}"
    sample = _WEIGHT_SAMPLES.get(region, _WEIGHT_SAMPLES["SC"])
    commands: list[dict] = [
        {
            "command": "frame.create",
            "as": "weights",
            "params": {
                "x": 0,
                "y": 0,
                "width": 692,
                "name": "weights",
                "props": {
                    "fill": theme.window,
                    "stroke": theme.border,
                    "strokeWeight": 1,
                    "cornerRadius": 12,
                    "layout": "vertical",
                    "sizingV": "hug",
                    "padding": 22,
                    "gap": 8,
                },
            },
        },
        {
            "command": "frame.create",
            "as": "weights_head",
            "params": {
                "parent": {"$ref": "weights"},
                "props": {
                    "fill": "none",
                    "layout": "horizontal",
                    "sizingH": "fill",
                    "sizingV": "hug",
                    "padding": [0, 0, 6, 0],
                    "stroke": theme.border,
                    "strokeWeight": 1,
                    "strokeSides": [False, False, True, False],
                    "mainAlign": "spaceBetween",
                },
            },
        },
        {
            "command": "node.create",
            "params": {
                "type": "text",
                "parent": {"$ref": "weights_head"},
                "text": f"{family}: 8 Weights × Upright & Italic",
                "props": {
                    "fontFamily": family,
                    "fontStyle": "SemiBold",
                    "fontSize": 12.5,
                    "fill": theme.text,
                },
            },
        },
        {
            "command": "node.create",
            "params": {
                "type": "text",
                "parent": {"$ref": "weights_head"},
                "text": "100 – 700 (incl. Text 450)",
                "props": {
                    "fontFamily": family,
                    "fontStyle": "Regular",
                    "fontSize": 11.5,
                    "fill": theme.muted,
                },
            },
        },
    ]
    for weight in WEIGHTS:
        row_as = f"w_{weight.name}"
        upright = STYLES_BY_NAME[weight.name].display_name
        italic_name = "Italic" if weight.name == "Regular" else f"{weight.name}Italic"
        italic = STYLES_BY_NAME[italic_name].display_name
        commands.extend(
            [
                {
                    "command": "frame.create",
                    "as": row_as,
                    "params": {
                        "parent": {"$ref": "weights"},
                        "props": {
                            "fill": "none",
                            "layout": "horizontal",
                            "sizingH": "fill",
                            "sizingV": "hug",
                            "gap": 12,
                            "crossAlign": "center",
                        },
                    },
                },
                {
                    "command": "node.create",
                    "params": {
                        "type": "text",
                        "parent": {"$ref": row_as},
                        "width": 100,
                        "text": f"{weight.name:<10} {weight.value}",
                        "props": {
                            "fontFamily": family,
                            "fontStyle": "Regular",
                            "fontSize": 11,
                            "fill": theme.muted,
                            "textAutoResize": "none",
                        },
                    },
                },
                {
                    "command": "node.create",
                    "params": {
                        "type": "text",
                        "parent": {"$ref": row_as},
                        "text": sample,
                        "props": {
                            "fontFamily": family,
                            "fontStyle": upright,
                            "fontSize": 12.5,
                            "fill": theme.text,
                        },
                    },
                },
                {
                    "command": "node.create",
                    "params": {
                        "type": "text",
                        "parent": {"$ref": row_as},
                        "text": sample,
                        "props": {
                            "fontFamily": family,
                            "fontStyle": italic,
                            "fontSize": 12.5,
                            "fill": theme.keyword,
                        },
                    },
                },
            ]
        )
    commands.append(
        {
            "command": "file.export",
            "params": {
                "ids": [{"$ref": "weights"}],
                "format": "png",
                "scale": SCALE,
                "path": str(output_path),
            },
        }
    )
    return commands


def _symbols_commands(region: str, output_path: Path) -> list[dict]:
    theme = LIGHT
    plemio_family = f"Plemio {region}"
    nerd_family = f"Plemio Nerd {region}"
    rows = [
        ("Numerals & Lookalikes", "0123456789   0O 1lI |!   != === <= >= => ->"),
        ("IBM Plex Math", "∑ ∏ ∫ ∂ ∇ √ ∞ ≈ ≠ ≡ ≤ ≥ ∈ ∉ ∪ ∩ → ⇒ ↔ ⇔"),
        ("Keys & UI Symbols", "⌘ ⌥ ⌃ ⇧ ⏎ ⌫ ⎋   ✓ ✔ ✗ ⚠ ★ ☆ ※ § × ÷"),
    ]
    commands: list[dict] = [
        {
            "command": "frame.create",
            "as": "symbols",
            "params": {
                "x": 0,
                "y": 0,
                "width": 600,
                "name": "symbols",
                "props": {
                    "fill": theme.window,
                    "stroke": theme.border,
                    "strokeWeight": 1,
                    "cornerRadius": 12,
                    "layout": "vertical",
                    "sizingV": "hug",
                    "padding": 22,
                    "gap": 12,
                },
            },
        },
        {
            "command": "frame.create",
            "as": "symbols_head",
            "params": {
                "parent": {"$ref": "symbols"},
                "props": {
                    "fill": "none",
                    "layout": "horizontal",
                    "sizingH": "fill",
                    "sizingV": "hug",
                    "padding": [0, 0, 6, 0],
                    "stroke": theme.border,
                    "strokeWeight": 1,
                    "strokeSides": [False, False, True, False],
                    "mainAlign": "spaceBetween",
                },
            },
        },
        {
            "command": "node.create",
            "params": {
                "type": "text",
                "parent": {"$ref": "symbols_head"},
                "text": "Plex Numerals, Math Operators & UI Symbols",
                "props": {
                    "fontFamily": plemio_family,
                    "fontStyle": "SemiBold",
                    "fontSize": 12.5,
                    "fill": theme.text,
                },
            },
        },
        {
            "command": "node.create",
            "params": {
                "type": "text",
                "parent": {"$ref": "symbols_head"},
                "text": nerd_family,
                "props": {
                    "fontFamily": nerd_family,
                    "fontStyle": "Regular",
                    "fontSize": 11.5,
                    "fill": theme.muted,
                },
            },
        },
    ]
    for idx, (label, glyphs) in enumerate(rows):
        row_as = f"sym_{idx}"
        commands.extend(
            [
                {
                    "command": "frame.create",
                    "as": row_as,
                    "params": {
                        "parent": {"$ref": "symbols"},
                        "props": {
                            "fill": theme.chrome,
                            "stroke": theme.border,
                            "strokeWeight": 1,
                            "cornerRadius": 8,
                            "layout": "vertical",
                            "sizingH": "fill",
                            "sizingV": "hug",
                            "padding": [10, 14, 10, 14],
                            "gap": 4,
                        },
                    },
                },
                {
                    "command": "node.create",
                    "params": {
                        "type": "text",
                        "parent": {"$ref": row_as},
                        "text": label,
                        "props": {
                            "fontFamily": plemio_family,
                            "fontStyle": "SemiBold",
                            "fontSize": 10.5,
                            "fill": theme.keyword,
                        },
                    },
                },
                {
                    "command": "node.create",
                    "params": {
                        "type": "text",
                        "parent": {"$ref": row_as},
                        "text": glyphs,
                        "props": {
                            "fontFamily": nerd_family,
                            "fontStyle": "Regular",
                            "fontSize": 15,
                            "fill": theme.text,
                        },
                    },
                },
            ]
        )
    commands.append(
        {
            "command": "file.export",
            "params": {
                "ids": [{"$ref": "symbols"}],
                "format": "png",
                "scale": SCALE,
                "path": str(output_path),
            },
        }
    )
    return commands


def _render_region_specimens(
    figcraft: str,
    config: Config,
    font_dir: Path,
    region: str,
    region_dir: Path,
) -> list[Path]:
    region_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "editor": region_dir / "editor.png",
        "weights": region_dir / "weights.png",
        "families": region_dir / "families.png",
        "terminal": region_dir / "terminal.png",
        "symbols": region_dir / "symbols.png",
    }
    commands: list[dict] = [
        _load_font_cmd(config, font_dir, "plemio", region, style) for style in STYLES_BY_NAME
    ]
    commands.extend(
        _load_font_cmd(config, font_dir, "nerd", region, style) for style in NERD_SPECIMEN_STYLES
    )
    commands.extend(_editor_commands(region, outputs["editor"]))
    commands.extend(_weights_commands(region, outputs["weights"]))
    commands.extend(_families_commands(config, region, outputs["families"]))
    commands.extend(_terminal_commands(region, outputs["terminal"]))
    commands.extend(_symbols_commands(region, outputs["symbols"]))

    with tempfile.TemporaryDirectory() as tmp:
        script_path = Path(tmp) / f"specimens-{region.lower()}.json"
        script_path.write_text(json.dumps(commands, indent=2), encoding="utf-8")
        subprocess.run(  # noqa: S603
            [figcraft, "--no-system-fonts", "run", str(script_path)],
            check=True,
            capture_output=True,
            text=True,
        )
    return list(outputs.values())


def render_specimens(
    config: Config,
    font_dir: Path,
    output_dir: Path,
    regions: Sequence[str] | None = None,
) -> list[Path]:
    figcraft = find_figcraft_cli()
    selected = list(regions) if regions is not None else list(config.regions)
    rendered: list[Path] = []
    for region in selected:
        rendered.extend(
            _render_region_specimens(
                figcraft, config, font_dir, region, output_dir / region.lower()
            )
        )
    return rendered
