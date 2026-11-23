<div align="center">

<img src="./docs/images/hero.png" width="448" alt="Plemio">

[English](./README.md) | [简体中文](./README.zh-CN.md) | [繁體中文](./README.zh-TW.md) | [日本語](./README.ja.md) | [한국어](./README.ko.md)

[![Font license: OFL-1.1](https://img.shields.io/badge/Font%20license-OFL--1.1-green?style=flat-square)](./OFL.txt)
[![Code license: MIT](https://img.shields.io/badge/Code%20license-MIT-blue?style=flat-square)](./LICENSE)

</div>

Plemio 是一款基于 IBM Plex 的等宽编程字体，适用于终端、代码编辑器和技术写作。中日韩（CJK）字符的宽度严格等于英文字符的两倍，中英混排的代码、注释和表格都能对齐。

<p align="center">
  <img src="./docs/images/sc/editor.png" width="560" alt="Plemio SC 在代码编辑器中的 2:1 混排对齐效果">
</p>

## ✨ 特性

### `1` 8 个字重与斜体

从 `Thin`（100）到 `Bold`（700）共 8 个字重，包含 IBM Plex 的 `Text`（450）。每个字重都有斜体，中日韩字形与 IBM Plex Mono Italic 倾斜角度一致。

<p align="center">
  <img src="./docs/images/sc/weights.png" width="640" alt="8 个字重的正体与斜体展示">
</p>

### `2` 编辑器与终端两个系列

- **Plemio**（编辑器与文档）：英文略微收窄，中文标点、箭头和制表符保持全角。
- **Plemio Nerd**（终端）：保留 IBM Plex Mono 原始字宽，模糊宽度符号按终端习惯取半角，并内置 Nerd Fonts 图标。

<p align="center">
  <img src="./docs/images/sc/families.png" width="600" alt="Plemio 与 Plemio Nerd 两个系列的排布对比">
</p>

### `3` 终端图标与符号

**Plemio Nerd** 内置 Nerd Fonts 图标、无缝 Powerline 分隔符、无断点制表符和盲文点阵，并用虚线标出全角空格（`U+3000`）。

<p align="center">
  <img src="./docs/images/sc/terminal.png" width="560" alt="Plemio Nerd SC 在终端中的 Nerd 图标、Powerline 与盲文显示效果">
</p>

### `4` 符号垂直居中

Plemio 保留 IBM Plex Mono 易于区分的 `0O` 和 `1lI`，并调整其他字形的高度，使其与英文代码对齐：

- 中日韩字符与英文的视觉中心对齐。
- `≠`、`≤`、`→`、`∑` 等数学符号取自 IBM Plex Math，与 `=`、`+` 位于同一轴线。
- 箭头、macOS 按键符号（`⌘`、`⌥`、`⇧`）和勾选标记对齐大写字母高度的中线。

<p align="center">
  <img src="./docs/images/sc/symbols.png" width="600" alt="IBM Plex 风格的数字、数学符号与界面图标">
</p>

## 📦 下载与安装

### Homebrew

在 macOS 或 Linux 上可通过 [Homebrew](https://brew.sh/) 直接安装（如需其他地区版本，将 `sc` 替换为 `tc`、`jp` 或 `kr`）：

```bash
brew install --cask fang2hou/tap/font-plemio-sc
brew install --cask fang2hou/tap/font-plemio-nerd-sc

# 或安装包含四地区的 TTC 合集
brew install --cask fang2hou/tap/font-plemio
brew install --cask fang2hou/tap/font-plemio-nerd
```

### 手动下载

下载下方的压缩包，解压后安装其中的 `.ttf` 文件。四个地区版本收录的字符相同，只有地区字形不同，选一个即可。

| 地区 | Plemio（编辑器） | Plemio Nerd（终端） |
| :--- | :--- | :--- |
| 简体中文（`SC`） | [Plemio-SC.zip](https://github.com/fang2hou/Plemio/releases/latest/download/Plemio-SC.zip) | [Plemio-Nerd-SC.zip](https://github.com/fang2hou/Plemio/releases/latest/download/Plemio-Nerd-SC.zip) |
| 繁体中文（`TC`） | [Plemio-TC.zip](https://github.com/fang2hou/Plemio/releases/latest/download/Plemio-TC.zip) | [Plemio-Nerd-TC.zip](https://github.com/fang2hou/Plemio/releases/latest/download/Plemio-Nerd-TC.zip) |
| 日文（`JP`） | [Plemio-JP.zip](https://github.com/fang2hou/Plemio/releases/latest/download/Plemio-JP.zip) | [Plemio-Nerd-JP.zip](https://github.com/fang2hou/Plemio/releases/latest/download/Plemio-Nerd-JP.zip) |
| 韩文（`KR`） | [Plemio-KR.zip](https://github.com/fang2hou/Plemio/releases/latest/download/Plemio-KR.zip) | [Plemio-Nerd-KR.zip](https://github.com/fang2hou/Plemio/releases/latest/download/Plemio-Nerd-KR.zip) |

`.ttc` 合集与历史版本见 [Releases](https://github.com/fang2hou/Plemio/releases) 页面。

## 🔤 字体构成

- **IBM Plex Mono**：英文、希腊字母、西里尔字母与制表符
- **IBM Plex Math**：数学运算符与箭头
- **IBM Plex Sans SC / TC / JP / KR**：中日韩字符
- **Nerd Fonts**：`Plemio Nerd` 中的图标
- **Noto Sans Mono 与 JetBrains Mono**：其余符号

## 🛠️ 本地构建

从源码构建需要在 macOS 或 Linux 上安装 [mise](https://mise.jdx.dev/)。

```bash
mise install          # 安装锁定版本的工具链
mise run setup        # 安装依赖与 git 钩子
mise run fetch        # 下载源字体
mise run build        # 在 build/fonts 生成全部字体
mise run verify-fonts # 校验生成的字体
mise run bundle       # 在 build/ttc 打包 TTC
```

详见 [DEVELOPMENT.md](./DEVELOPMENT.md) 与 [ARCHITECTURE.md](./ARCHITECTURE.md)。

## 🤝 参与贡献

欢迎提交 Issue 或 Pull Request，请先阅读 [CONTRIBUTING.md](./CONTRIBUTING.md)。

## 🙏 致谢

- [PlemoCJK](https://github.com/nexustar/PlemoCJK) 与 [PlemolJP](https://github.com/yuru7/PlemolJP)
- [IBM Plex](https://github.com/IBM/plex)
- [Nerd Fonts](https://github.com/ryanoasis/nerd-fonts)、[Noto](https://github.com/notofonts/latin-greek-cyrillic) 与 [JetBrains Mono](https://github.com/JetBrains/JetBrainsMono)

## 📄 开源许可

- 字体文件：[OFL-1.1](./OFL.txt)（Nerd Fonts 图标采用 MIT 许可）
- 构建代码：[MIT](./LICENSE)
