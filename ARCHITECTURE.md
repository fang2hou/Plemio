# Architecture

## Overview

Plemio is a batch font-composition pipeline. For each variant, region, and style, it starts from the matching IBM Plex Mono TTF, resolves every Unicode codepoint through an ordered stack of glyph providers, transforms or generates outlines onto the target grid, and writes one TrueType font. All outline, metrics, and table operations run in `fontTools` alongside `skia-pathops` and `ttfautohint`, without FontForge.

## Codebase Map

- **cli, pipeline, jobs**: command-line entry points, parallel worker orchestration, and the `variant × region × style` build matrix.
- **config, sources**: typed `plemio.toml` schema (`Pydantic`) and HTTPS source downloads verified by SHA-256 against `sources.lock`.
- **factory**: builds the ordered provider stack for one build job from configuration.
- **providers**: codepoint resolution for native Plex Mono glyphs, CJK fonts with regional fallback, monospaced supplements, line art, and Nerd Fonts.
- **symbols, weights**: proportional IBM Plex Math fitting with topology-preserving `skia-pathops` outline offsets and emboldened derived glyphs.
- **synthetic**: generated braille patterns, shade blocks, and the visible ideographic space marker (`U+3000`).
- **placement, measure**: pure 2D grid geometry and reference glyph measurements.
- **latin**: uniform horizontal narrowing, GPOS anchor scaling, and `ttfautohint` re-hinting of Plex Mono for the `528 : 1056` grid.
- **compose, metadata**: glyph assembly into the base font and writing of `name`, `OS/2`, `post`, `head`, and `meta` tables.
- **check, bundle, preview, specimen**: font invariant validation, `otb-ttc-bundle` TTC packing, Pillow tuning sheets, and `figcraft-cli` README specimen exports.

## Invariants

- **Single resolution path**: after `latin` prepares the base font, each codepoint resolves through the first matching provider in `factory`. Providers return immutable plans (`Native` or `Drawn`); only `FontAssembler` mutates the output font.
- **Unmodified Plex Mono in `Plemio Nerd`**: `Plemio Nerd` copies Plex Mono glyphs, hinting, and OpenType features intact, except for line art and the explicitly configured `symbols.override` math operators fitted from IBM Plex Math. `Plemio` narrows Latin glyphs uniformly and re-hints them with `ttfautohint`, never redrawing glyphs by hand.
- **Two coordinate systems**: `metrics` controls only the line box (`ascender` / `descender`). Text, symbols, and icons are positioned in glyph space (`cjk.y-offset`, `symbols.*-center-y`, `nerd-fonts.icon-center-y`), whereas line art, braille, and Powerline glyphs are anchored to the line box so moving one never silently shifts the other.
- **Strict cell width policy**: every glyph advance is `0`, `1`, or `2` cells, governed by the variant's `ambiguous` policy. `plemio check` rejects any font that violates this rule.
- **Configuration owns design numbers**: all visual tuning constants live in `plemio.toml`; Python modules hold only structural constants.
- **Reproducible inputs**: builds read exclusively from `sources/`, verified by URL and SHA-256 in `sources.lock`. Only `plemio fetch` downloads upstream fonts, and `plemio bundle` invokes `otb-ttc-bundle` via `pnpm dlx`.
- **Unidirectional dependencies**: `cli → pipeline → compose → factory → providers / symbols / synthetic → placement / outlines / unicode`. Pure geometry modules never import providers or configuration.

## Decisions

Key architectural decisions are recorded as ADRs in [docs/adr/](./docs/adr/). When a requirement conflicts with an existing ADR, do not bypass it silently; evaluate the impact and update or supersede the ADR explicitly.
