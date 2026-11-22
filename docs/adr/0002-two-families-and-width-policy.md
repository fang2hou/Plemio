# ADR-0002: Ship Plemio and Plemio Nerd with different width policies

- **Status**: accepted
- **Date**: 2026-11-22

## Context

Code editors and document tools work well with full-width CJK punctuation, symbols, and box drawing, following PlemolJP's default variant. Terminal emulators instead compute cell widths with `wcwidth`, which treats East Asian Ambiguous characters as single-cell (`1`); drawing those glyphs two cells wide causes overlapping characters in terminal output.

## Decision

Ship exactly two families on a strict 2:1 grid:

- **Plemio**: `528 : 1056` cell grid, narrowed IBM Plex Mono Latin glyphs, full-width ambiguous characters (keeping CJK design widths), double-width box drawing, and no Nerd Fonts.
- **Plemio Nerd**: `600 : 1200` cell grid, untouched IBM Plex Mono glyphs, strict East Asian Width (`ambiguous = "narrow"`), Nerd Fonts icons, and a visible ideographic space (`U+3000`).

Both families share the same vertical design (line box, CJK vertical offset, and symbol/icon centers).

## Alternatives Considered

### One family with an OpenType width feature

- **Pros**: Fewer distributed font files.
- **Cons**: Terminal emulators cannot toggle OpenType features per Unicode character width.
- **Reason rejected**: Cannot prevent overlapping glyphs in terminals.

### Keep PlemoCJK's three variants, including the 3:5 Natural grid

- **Pros**: Continuity with PlemoCJK naming.
- **Cons**: A `3:5` ratio breaks the strict `2:1` column alignment required by this project.
- **Reason rejected**: Excluded by project scope.

## Consequences

- Each family behaves predictably in its target environment without manual width workarounds.
- `Plemio Nerd` intentionally diverges from PlemoCJK's `Term` build on roughly 370 codepoints where CJK fonts draw full-width glyphs but Unicode defines the width as narrow.

## Review Triggers

- Terminal emulators adopt a different default `wcwidth` convention for East Asian Ambiguous codepoints.
- Terminal users require an explicit ambiguous-wide build.
