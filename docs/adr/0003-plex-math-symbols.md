# ADR-0003: Take missing symbols from IBM Plex Math with outline offsets

- **Status**: accepted
- **Date**: 2026-11-22

## Context

IBM Plex Mono lacks many arrows, mathematical operators, technical symbols, and macOS key glyphs. Filling all missing symbols from Noto Sans Mono and JetBrains Mono mixed incompatible stroke designs and vertical centers (`⌘` sat too high while Noto arrows sat low), and Hack only supplied two static weights.

## Decision

Use IBM Plex Math as the primary symbol supplement. Scale each glyph to fit the cell, center it using Plex Mono's vertical conventions (operators on the math axis; icon-like symbols at half cap height), and offset outlines with `skia-pathops` to match each style's stroke weight without changing contour counts. Also override the overly low native Plex Mono display operators listed in `symbols.override` (`∑`, `∫`) with fitted, math-axis-centered Plex Math glyphs so they align with surrounding operators. Keep Noto Sans Mono and JetBrains Mono as secondary supplements, scaled to Plex Mono's cap height and aligned with the same rule. Drop Hack entirely.

## Alternatives Considered

### Re-align the existing supplements without adding IBM Plex Math

- **Pros**: No extra upstream source and native variable weights from Noto and JetBrains Mono.
- **Cons**: Visual design stays inconsistent against IBM Plex glyphs.
- **Reason rejected**: Re-centering alone did not resolve the visual mismatch observed during design review.

### Keep Hack as a fallback font

- **Pros**: Covers Armenian, Georgian, and rare arrows.
- **Cons**: Only ships two static weights, belongs to a different typeface family, and adds another upstream license.
- **Reason rejected**: Removed during design review; OS font fallback already handles rare scripts.

## Consequences

- Symbols match IBM Plex proportions and aesthetics across all eight weights.
- `skia-pathops` is a required runtime dependency, and synthetic outline-offsetting at `Thin` can appear slightly softer than hand-drawn masters.

## Review Triggers

- IBM releases IBM Plex Math in multiple weights.
- Outline offsetting introduces visible artifacts on a symbol at any weight.
