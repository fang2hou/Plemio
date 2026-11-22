<div align="center">

<img src="./docs/images/hero.png" width="448" alt="Plemio">

[English](./README.md) | [简体中文](./README.zh-CN.md) | [繁體中文](./README.zh-TW.md) | [日本語](./README.ja.md) | [한국어](./README.ko.md)

[![Font license: OFL-1.1](https://img.shields.io/badge/Font%20license-OFL--1.1-green?style=flat-square)](./OFL.txt)
[![Code license: MIT](https://img.shields.io/badge/Code%20license-MIT-blue?style=flat-square)](./LICENSE)

</div>

Plemio is a monospaced typeface built from IBM Plex for terminal emulators, code editors, and technical writing. Chinese, Japanese, and Korean (CJK) glyphs align strictly at a 2:1 width ratio against Latin characters, keeping mixed-language code, comments, and tables lined up.

<p align="center">
  <img src="./docs/images/sc/editor.png" width="560" alt="Plemio SC in a code editor showing 2:1 CJK alignment">
</p>

## ✨ Features

### `1` Eight weights with italics

Plemio covers eight weights from `Thin` (100) to `Bold` (700), including IBM Plex's `Text` (450) weight for comfortable body reading. Every weight pairs with an italic face whose CJK glyphs slant at the same angle as IBM Plex Mono Italic.

<p align="center">
  <img src="./docs/images/sc/weights.png" width="640" alt="Eight weights in upright and italic">
</p>

### `2` Two series for different environments

Plemio ships two series because editors and terminals handle ambiguous-width symbols differently. The **Plemio** series narrows Latin glyphs slightly and keeps CJK punctuation, arrows, and box drawing full-width for editors and prose; the **Plemio Nerd** series keeps IBM Plex Mono unchanged, enforces narrow ambiguous widths to match terminal `wcwidth`, and bundles Nerd Fonts icons.

<p align="center">
  <img src="./docs/images/sc/families.png" width="600" alt="Comparison between the Plemio and Plemio Nerd series">
</p>

### `3` Terminal icons, Powerline, and box drawing

For terminal prompts and TUI tools, **Plemio Nerd** includes Nerd Fonts icons, seamless Powerline separators, gap-free box drawing and shade blocks, generated braille patterns, and a visible dashed marker for ideographic spaces (`U+3000`).

<p align="center">
  <img src="./docs/images/sc/terminal.png" width="560" alt="Plemio Nerd SC in a terminal with Powerline prompt and Nerd Fonts icons">
</p>

### `4` Optical centering and legible symbols for coding

Naive font merges often leave arrows, icons, and CJK characters sitting too high or too low beside Latin code. Plemio keeps IBM Plex Mono's distinctive `0O` and `1lI` shapes and tunes vertical baselines and optical centers across every script and symbol group so lines stay visually level at reading size:

- **CJK and Latin balance**: Chinese and Japanese glyphs are subtly shifted to align optically with Latin text, while Hangul keeps its native height so syllable blocks stay centered. Full-width brackets and parentheses are nudged closer to adjacent characters to avoid awkward gaps.
- **Math operators on the math axis**: comparison and logic symbols (`≠`, `≤`, `≥`, `→`, `⇒`, `∈`, `∑`) come from IBM Plex Math, match each weight's stroke thickness, and center on the same axis as `=`, `+`, and `-`.
- **Programming and UI marks at cap-height center**: arrows, macOS key symbols (`⌘`, `⌥`, `⌃`, `⇧`, `⏎`), checkmarks, and bullets center at half cap height so they line up with surrounding identifiers.
- **Terminal-ready Nerd Fonts**: icons, Powerline separators, braille spinners, and visible `U+3000` markers are centered against the line box so prompt segments and status indicators stay aligned across terminal emulators.

<p align="center">
  <img src="./docs/images/sc/symbols.png" width="600" alt="Plex numerals, math operators, and UI symbols">
</p>

## 📦 Download & Install

Download the standalone archive for the series and region you want directly from the latest release, unzip it, and install the `.ttf` files. All four regional builds (`SC`, `TC`, `JP`, `KR`) share the same character coverage and differ only in regional glyph forms and punctuation placement.

| Region | Plemio (Editors) | Plemio Nerd (Terminals) |
| :--- | :--- | :--- |
| Simplified Chinese (`SC`) | [Plemio-SC.zip](https://github.com/fang2hou/Plemio/releases/latest/download/Plemio-SC.zip) | [Plemio-Nerd-SC.zip](https://github.com/fang2hou/Plemio/releases/latest/download/Plemio-Nerd-SC.zip) |
| Traditional Chinese (`TC`) | [Plemio-TC.zip](https://github.com/fang2hou/Plemio/releases/latest/download/Plemio-TC.zip) | [Plemio-Nerd-TC.zip](https://github.com/fang2hou/Plemio/releases/latest/download/Plemio-Nerd-TC.zip) |
| Japanese (`JP`) | [Plemio-JP.zip](https://github.com/fang2hou/Plemio/releases/latest/download/Plemio-JP.zip) | [Plemio-Nerd-JP.zip](https://github.com/fang2hou/Plemio/releases/latest/download/Plemio-Nerd-JP.zip) |
| Korean (`KR`) | [Plemio-KR.zip](https://github.com/fang2hou/Plemio/releases/latest/download/Plemio-KR.zip) | [Plemio-Nerd-KR.zip](https://github.com/fang2hou/Plemio/releases/latest/download/Plemio-Nerd-KR.zip) |

Multi-region `.ttc` bundles and earlier versions are available on the [Releases](https://github.com/fang2hou/Plemio/releases) page.

## 🚀 Usage

- **Code editors and prose**: select `Plemio SC` (or `TC`, `JP`, `KR`) for full-width CJK punctuation and compact Latin rhythm.
- **Terminals and prompts**: select `Plemio Nerd SC` (or `TC`, `JP`, `KR`) for Nerd Fonts icons, Powerline separators, visible `U+3000` markers, and clean `wcwidth` alignment.

<details>
<summary>Terminal line height in xterm.js</summary>

Plemio preserves IBM Plex Mono's `1.3` line height. Terminals built on `xterm.js` (such as VS Code and Orca) multiply their own `lineHeight` setting on top of the font metrics: `1.0` keeps the font's built-in spacing, while `1.335` opens up extra line room with balanced padding at `14 px` on 2x displays.

</details>

## 🔤 Source Typefaces

Plemio composes each font from multiple IBM Plex families and symbol supplements:

- **IBM Plex Mono**: Latin, Greek, Cyrillic, numerals, punctuation, box drawing, and block elements
- **IBM Plex Math**: mathematical operators, arrows, and technical symbols fitted and stroke-matched to each weight
- **IBM Plex Sans SC / TC / JP / KR**: Simplified Chinese, Traditional Chinese, Japanese, and Korean glyphs
- **Nerd Fonts**: developer icons and Powerline glyphs (included in the `Plemio Nerd` series)
- **Noto Sans Mono & JetBrains Mono**: fallback coverage for remaining symbols

## 🛠️ Development

Building from source requires [mise](https://mise.jdx.dev/) on macOS or Linux. Tool versions are pinned in `mise.toml`, and `mise run bundle` needs network access for `pnpm dlx`.

```bash
mise install          # Python 3.12, uv, Node LTS, pnpm, prek, cocogitto, gitleaks
mise run setup        # install Python dependencies and git hooks
mise run fetch        # download pinned upstream fonts and verify sources.lock
mise run build        # build all 128 TTFs into build/fonts
mise run verify-fonts # check width, metadata, and coverage invariants
mise run bundle       # pack regional TTFs into TTCs under build/ttc
```

See [DEVELOPMENT.md](./DEVELOPMENT.md) for tuning options and specimen generation, and [ARCHITECTURE.md](./ARCHITECTURE.md) for pipeline invariants.

## 🤝 Contributing

Contributions are welcome. Read [CONTRIBUTING.md](./CONTRIBUTING.md) for the pull request workflow, Conventional Commits rules, and visual verification expectations.

## 🙏 Acknowledgments

- **PlemoCJK and PlemolJP**: inspired the two-series design and four-region CJK coverage ([PlemoCJK](https://github.com/nexustar/PlemoCJK), [PlemolJP](https://github.com/yuru7/PlemolJP); Plemio uses a clean-room Python pipeline and contains no PlemolJP font data).
- **IBM Plex**: provides the core Mono, Math, and Sans SC/TC/JP/KR typefaces ([IBM/plex](https://github.com/IBM/plex)).
- **Nerd Fonts, Noto Sans Mono, and JetBrains Mono**: supply terminal icons and fallback symbol coverage ([nerd-fonts](https://github.com/ryanoasis/nerd-fonts), [Noto](https://github.com/notofonts/latin-greek-cyrillic), [JetBrainsMono](https://github.com/JetBrains/JetBrainsMono)).
- **fontTools, skia-pathops, ttfautohint, and otb-ttc-bundle**: power glyph composition, outline offsetting, Latin re-hinting, and TTC packaging.

## 📄 License

- Fonts: [OFL-1.1](./OFL.txt) (IBM Plex reserves the name "Plex", so derived fonts must not use it; Nerd Fonts icons are MIT-licensed)
- Build code: [MIT](./LICENSE)
