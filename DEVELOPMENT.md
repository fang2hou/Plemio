# Development

Set up the local toolchain, build and validate fonts, and tune glyph placement in Plemio. End-user installation and usage live in [README.md](./README.md).

## Setup

[mise](https://mise.jdx.dev/) manages runtimes and CLI tools, while `uv` manages Python packages and virtual environments:

```bash
mise install     # install pinned tools from mise.toml
mise run setup   # run uv sync --locked and install prek git hooks
mise run fetch   # download 59 upstream files into sources/ and verify sources.lock
```

| Tool | Purpose | Managed via |
| :--- | :--- | :--- |
| Python 3.15 | Runtime | `mise.toml` |
| uv | Environments and dependencies (`uv.lock`) | `mise.toml` |
| ruff | Linting and formatting | `pyproject.toml` (`dev` group) |
| prek | Git hooks for `mise run check` and commit messages | `mise.toml`, `prek.toml` |
| cocogitto | Conventional Commits validation | `mise.toml`, `cog.toml` |
| gitleaks | Secret scanning | `mise.toml`, `.gitleaks.toml` |
| Node LTS + pnpm | Runs `otb-ttc-bundle` via `pnpm dlx` for TTC bundling | `mise.toml` |

Do not substitute standardized tools without explicit approval. Generating README specimen images (`mise run specimen`) additionally requires `figcraft-cli` on `PATH` or at `~/.local/bin/figcraft-cli`.

## Commands

```bash
mise run check                               # lint, format check, and secret scan (mirrors CI)
mise run test                                # run check, then pytest
uv run pytest tests/test_weights.py          # run a single test file
mise run build                               # build all variants, regions, and styles
mise run build -- -v nerd -r SC -s Regular   # build a subset; pass -j to set worker count
mise run verify-fonts                        # validate invariants across built fonts
mise run bundle                              # pack regional fonts into TTCs in build/ttc
mise run preview -- -v nerd -r SC -s Regular # render tuning sheets into build/preview
mise run specimen                            # regenerate README specimen PNGs in docs/images
```

Run `mise run` with no arguments to list every task.

## Workflow

1. Branch from `main`.
2. Make the smallest complete change that solves the task.
3. If glyph output changes, rebuild a representative subset and run `mise run verify-fonts`. Regenerate `docs/images` with `mise run specimen` whenever glyph rendering changes.
4. Confirm `mise run check` passes (`prek` runs it automatically on every commit).
5. Write commit messages using Conventional Commits (validated by Cocogitto).
6. Open a pull request following [CONTRIBUTING.md](./CONTRIBUTING.md).

## Layout

- `src/plemio/` holds the composition pipeline: `cli` and `pipeline` orchestrate builds, `factory` assembles the provider stack per variant, region, and style, `providers`, `symbols`, and `synthetic` supply glyphs, `placement` and `weights` handle geometry and outline offsetting, `compose` and `metadata` write fonts, `check` enforces invariants, and `specimen` exports README images via `figcraft-cli`.
- `tests/` contains the pytest suite, from unit tests on geometry to real font builds in `test_build.py`.
- `docs/adr/` stores architectural decision records, and `docs/images/` stores generated README specimen images.
- `plemio.toml` defines design and tuning values; `sources.toml` and `sources.lock` pin upstream font revisions and SHA-256 digests.

## Coding Standards

Follow the shared engineering coding standards along with these project rules:

- Keep design numbers in `plemio.toml` and read them through `config.py`.
- Keep geometry calculations as pure functions in `placement.py` so unit tests run without font files.
- Return `Drawn` or `Native` plans from providers rather than mutating the base font; only `FontAssembler` writes glyphs.

## Testing

- `mise run test` runs the full suite. `test_build.py` builds one `Plemio` font and one `Plemio Nerd` font, skipping automatically if `sources/` has not been fetched.
- Geometry, width policies, outline offsetting, URL validation, and config parsing are covered by fast unit tests that need no font files.
- For visual changes, compare `mise run preview` sheets before and after editing because automated tests cannot judge typographic appearance.

## Tuning

Every design parameter below lives in [`plemio.toml`](./plemio.toml). Rebuild and inspect `mise run preview` sheets (which draw line boxes and midlines) at normal reading size (`14 px` in Orca).

| Key | Effect |
| :--- | :--- |
| `metrics.ascender` / `descender` | Line-box bounds (`1010` / `-290`, line height `1.3`). Shifting both equally moves all text inside the line while line art, braille, and Powerline track the box |
| `[variants.*]` | Per-family cell width (`half-width`), `latin-scale`, `ambiguous` width policy (`narrow` or `wide`), `nerd-fonts`, `full-width-line-art`, and `visible-ideographic-space` |
| `variants.*.cjk-over-latin` | Codepoints where the CJK glyph overrides Plex Mono (full-width arrows and marks in `Plemio`) |
| `cjk.scale`, `cjk.y-offset` | Scale and vertical shift applied to 2-cell CJK glyphs |
| `cjk.y-offset-exempt` | Codepoint ranges that keep their native vertical position (Hangul) |
| `cjk.ink-margin`, `cjk.squeeze-aspect` | Horizontal margin and maximum aspect squeeze when fitting full-width glyphs into one cell |
| `cjk.preferred` | Codepoint ranges where Plex Sans overrides monospaced supplements (Greek) |
| `cjk.nudges` | Per-codepoint horizontal or vertical offsets, such as widened full-width brackets |
| `symbols.icon-center-y`, `operator-center-y` | Vertical centers for icon-like symbols and mathematical operators |
| `symbols.operators`, `symbols.fixed`, `symbols.override` | Ranges centered on the operator axis, ranges kept at their source position, and Plex Mono operators overridden with centered Plex Math glyphs (`∑`, `∫`) |
| `symbols.ink-margin`, `max-height` | Horizontal padding and height cap when fitting IBM Plex Math symbols |
| `symbols.emboldened` | Glyphs derived by emboldening another glyph (`✔` from `✓`) |
| `nerd-fonts.icon-scale`, `icon-center-y` | Scale and vertical center for Nerd Fonts icons |
| `nerd-fonts.cell-ranges` | Glyphs stretched to fill the line box, such as Powerline separators |
| `line-art.block-overhang` | Bleed distance past cell edges for solid block elements |
| `ideographic-space.*` | Center, box size, stroke width, and dash ratio for the visible `U+3000` marker |
| `braille.height`, `braille.dot-size` | Braille field height and dot diameter |
| `[[supplements]]` | Symbol supplement fonts in priority order; `fit = "proportional"` fits and re-weights single-weight fonts |
| `[regions.*]` | Fallback order, OpenType script tag, code pages, and localized family names |

## Updating Sources

Upstream revisions are pinned in [`sources.toml`](./sources.toml). After updating a revision, re-lock digests and rebuild:

```bash
uv run plemio fetch --mode update-lock   # download updated files and rewrite sources.lock
mise run build && mise run verify-fonts
```

Run `uv run plemio fetch --mode offline` to verify local files against `sources.lock` without network access.

## Validation

`mise run check` is the primary validation entry point and runs the same checks locally and in CI. `mise run verify-fonts` (`plemio check`) validates font invariants across `build/fonts`: glyph advances (`0`, `1`, or `2` cells), ambiguous-width rules, family names, glyph count limits, and required character coverage.

## Deployment

- The **Fonts** workflow (`workflow_dispatch`) fetches pinned sources, builds all 128 TTFs, validates them with `plemio check`, bundles regional TTCs, and uploads the `plemio-fonts` artifact.
- The **Release** workflow (triggered by a `v*` tag) runs the same build and verification steps, packages each series and region into a standalone `.zip` archive (`Plemio-{SC,TC,JP,KR}.zip`, `Plemio-Nerd-{SC,TC,JP,KR}.zip`, and TTC bundles) with license files, and publishes them to GitHub Releases.
