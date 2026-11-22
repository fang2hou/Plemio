# Contributing

Follow these steps to propose changes, report glyph issues, and open pull requests in Plemio. Local setup and tuning details live in [DEVELOPMENT.md](./DEVELOPMENT.md); instructions for AI agents live in [AGENTS.md](./AGENTS.md).

## Ground Rules

- Keep every change as small and complete as the requirement allows.
- Avoid mixing unrelated refactoring or cleanup into feature or fix PRs.
- Obtain approval before adding runtime dependencies or upstream font sources.
- Include before-and-after images from `mise run preview` or `mise run specimen` whenever glyph rendering changes.

## Reporting a Bug

Open an issue before starting a pull request:

1. Search existing issues to avoid duplicates.
2. Specify the family, region, style, and codepoint (for example, `Plemio Nerd SC Regular, U+2318`), along with the application, font size, and a screenshot showing the issue.

## Proposing a Feature

Open an issue to align on the design before writing code, especially for changes that alter glyph positions, vertical metrics, or character widths.

## Pull Request Workflow

1. Branch from `main`.
2. Implement the change and verify `mise run check` and `mise run test` pass.
3. Format commit messages as Conventional Commits (enforced by Cocogitto via the `commit-msg` hook).
4. Open a pull request against `main` and wait for CI checks to pass.
5. Address review feedback before squash-merging.

## Review Expectations

Reviewers verify:

- Requested behavior, including rendered pixel checks for visual changes.
- Tight scope with no unintended files or unapproved dependencies.
- Alignment with the invariants in [ARCHITECTURE.md](./ARCHITECTURE.md) and decisions in [docs/adr/](./docs/adr/).
- Absence of secrets or local build artifacts.

## Commit Conventions

Commits follow Conventional Commits, validated locally by `prek` and in CI by Cocogitto:

```text
feat(symbols): fit IBM Plex Math glyphs into the cell
fix(metrics): balance hanzi in the line box
```

Because pull requests are squash-merged, PR titles must follow the same convention (checked by the **PR title** workflow).

## Pull Request Descriptions

Every pull request description must include these five sections, matching [.github/pull_request_template.md](./.github/pull_request_template.md):

- **Purpose**: what problem the change solves
- **Impact**: which families, regions, styles, or glyph ranges change
- **Context**: relevant background, linked issues, or ADRs
- **Risks**: potential regressions, such as altered widths or glyph clipping
- **Testing**: commands run, test results, and before/after previews when visual output changes
