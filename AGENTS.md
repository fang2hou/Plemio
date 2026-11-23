# AGENTS.md

Plemio is a Python font-composition pipeline that merges IBM Plex Mono, IBM Plex Sans SC/TC/JP/KR, IBM Plex Math, and Nerd Fonts into 2:1 monospaced CJK programming fonts.

## Commands

```bash
mise install                                # set up the toolchain
mise run setup                              # uv sync + prek git hooks
mise run fetch                              # download pinned sources, verify sources.lock
mise run build -- -v nerd -r SC -s Regular  # build one font (~10s)
mise run build                              # build all 128 fonts
mise run verify-fonts                       # validate invariants on fonts in build/fonts
mise run preview -- -v nerd -r SC           # render tuning sheets into build/preview
mise run specimen                           # regenerate docs/images via figcraft-cli (needs built fonts)
uv run pytest tests/test_placement.py       # run a single test file
mise run test                               # check, then run the full test suite
mise run lint                               # ruff check only
mise run fix                                # ruff format + ruff check --fix
mise run check                              # full validation — run before every commit
```

Run Python through `uv run`, never bare `python` or `pip`.

## Engineering Standards

This project follows the shared engineering guidelines:

> https://github.com/fang2hou/ai-coding-guidelines/blob/main/PORTAL.md

Read the portal's reading recipes for your task type before starting. Repository documentation takes precedence over remembered summaries.

Project-specific overrides:

- No Python type checker runs in `mise run check`; the guidelines name none for Python.
- TTC bundling runs `otb-ttc-bundle` through `pnpm dlx`; there is no `package.json`.
- `mise.toml` uses floating minor/major/LTS tool ranges (`python = "3.15"`, `uv = "latest"`, `node = "lts"`, `pnpm = "12"`, `prek = "0.5"`, `cocogitto = "7"`, `gitleaks = "8"`) instead of exact patch pins so local setups reuse installed versions and CI picks up security patches automatically.

## Layout

- `src/plemio/` — pipeline modules: `cli` and `pipeline` drive builds, `factory` assembles providers, `compose` writes each font, `placement` holds grid geometry, and `specimen` drives `figcraft-cli` for README previews.
- `tests/` — pytest suite; `test_build.py` builds real fonts and skips when `sources/` is absent.
- `docs/` — ADRs in `docs/adr/` and README specimen PNGs in `docs/images/`.
- `plemio.toml` — design and tuning values; `sources.toml` and `sources.lock` — pinned upstream fonts.

## Boundaries

Always:

- Run `mise run check` before every commit.
- Rebuild at least `-v nerd -r SC -s Regular` and run `mise run verify-fonts` after changing anything that affects glyph output.
- Regenerate `docs/images/` with `mise run specimen` when a change alters glyph appearance.
- Put design and tuning numbers in `plemio.toml`, not in Python code.

Never:

- Hand-edit `sources.lock` or `uv.lock`; use `uv run plemio fetch --mode update-lock` and `uv lock`.
- Commit `build/` or `sources/`.
- Add PlemolJP font data or any font name containing "Plex".

Ask first:

- Adding dependencies or upstream font sources.
- Changing `metrics`, `cjk.y-offset`, `symbols.*-center-y`, or `nerd-fonts.icon-center-y`, which are tuned visually.
- Changing invariants in `ARCHITECTURE.md` or decisions in `docs/adr/`.

## Confirmed Language Policy

| Item | Value |
| :--- | :--- |
| Conversation | Follows the user (currently Chinese) |
| Code / comments / commits | English |
| Product docs | English `README.md`, mirrored in `README.zh-CN.md`, `README.zh-TW.md`, `README.ja.md`, and `README.ko.md` |
| Font names | English family names, plus localized OpenType names for `zh-CN`, `zh-TW`, `ja`, and `ko` in `plemio.toml` |

Do not infer UI language from conversation language.

## Project Conventions

- Plex Mono glyphs are never redrawn in `Plemio Nerd`; every other glyph comes from a provider in `providers.py`, `symbols.py`, or `synthetic.py`.
- Glyph positions live in glyph space (`cjk.y-offset`, `symbols.*-center-y`, `nerd-fonts.icon-center-y`); `metrics` moves only the line box so line art, braille, and Powerline follow it automatically.
- Advances are 0, 1, or 2 cells, enforced by `plemio check` according to the variant's `ambiguous` width policy.
- Judge visual tuning at reading size (`14 px` in Orca), not only zoomed in.

Depth: see [DEVELOPMENT.md](./DEVELOPMENT.md) for workflow and tuning, [CONTRIBUTING.md](./CONTRIBUTING.md) for PR rules, and [ARCHITECTURE.md](./ARCHITECTURE.md) for invariants.
