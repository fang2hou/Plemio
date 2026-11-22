# ADR-0001: Compose fonts with fontTools instead of FontForge

- **Status**: accepted
- **Date**: 2026-11-22

## Context

Plemio replaces PlemoCJK, which inherited PlemolJP's FontForge scripts and a Docker image to run them. Those scripts mixed glyph surgery, width conversion, and metadata generation inside a single 1,600-line file, requiring a container for every build.

## Decision

Compose every font in pure Python using `fontTools` inside a `uv`-managed environment. Use `skia-pathops` for outline offsets and `ttfautohint` (via `ttfautohint-py`) to re-hint narrowed Latin glyphs. Do not use FontForge.

## Alternatives Considered

### Keep FontForge scripts

- **Pros**: Proven on PlemolJP with built-in glyph transform utilities.
- **Cons**: Requires FontForge's bundled Python or Docker, offers no lockfile, and makes unit-testing geometry impractical.
- **Reason rejected**: Conflicts with the `uv` and `ruff` toolchain and prevents fast unit tests on grid placement.

### Run the official Nerd Fonts font-patcher

- **Pros**: Includes upstream scaling rules for every icon set.
- **Cons**: Depends on FontForge and patches existing fonts as a post-processing step rather than composing cleanly from sources.
- **Reason rejected**: Placing glyphs directly from `SymbolsNerdFont` provides identical icons with full control over grid alignment and vertical centering.

## Consequences

- `uv run plemio build` builds every variant locally and in CI with no external container; a single font builds in roughly 10s.
- Grid geometry stays in pure Python (`placement.py`) and is covered by unit tests.
- Outline transform and offset helpers that FontForge previously supplied are maintained directly in `placement.py` and `weights.py`.

## Review Triggers

- `fontTools` or `skia-pathops` drops support for a required outline or table operation.
- A future requirement demands interactive visual glyph editing inside the pipeline.
