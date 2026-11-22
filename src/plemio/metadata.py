from __future__ import annotations

from dataclasses import dataclass

from fontTools.ttLib import TTFont, newTable

from plemio.config import Config
from plemio.jobs import BuildJob
from plemio.styles import Style

WINDOWS = (3, 1)
LANGUAGE_IDS = {"en": 0x0409, "zh-CN": 0x0804, "zh-TW": 0x0404, "ja": 0x0411, "ko": 0x0412}
UPSTREAM_COPYRIGHTS = (
    'Copyright © 2017 IBM Corp. with Reserved Font Name "Plex"',
    "Copyright 2020 The JetBrains Mono Project Authors (https://github.com/JetBrains/JetBrainsMono)",
    "Copyright 2022 The Noto Project Authors (https://github.com/notofonts/latin-greek-cyrillic)",
)
NERD_FONTS_COPYRIGHT = "Copyright (c) 2014 Ryan L McIntyre (Nerd Fonts)"
LICENSE_DESCRIPTION = (
    "This Font Software is licensed under the SIL Open Font License, Version 1.1. "
    "This license is available with a FAQ at: https://openfontlicense.org"
)
LICENSE_URL = "https://openfontlicense.org"
SUPPORTED_SCRIPTS = ("Latn", "Cyrl", "Grek", "Hans", "Hant", "Jpan", "Kore")
DROPPED_TABLES = ("DSIG", "hdmx", "LTSH", "VDMX")

FS_ITALIC = 1 << 0
FS_BOLD = 1 << 5
FS_REGULAR = 1 << 6
FS_USE_TYPO_METRICS = 1 << 7
MAC_BOLD = 1 << 0
MAC_ITALIC = 1 << 1
PANOSE_MONOSPACED = 9


@dataclass(frozen=True, slots=True)
class FontNames:
    family: str
    style: Style

    @property
    def legacy_family(self) -> str:
        return self.family if self.style.is_ribbi else f"{self.family} {self.style.weight.name}"

    @property
    def legacy_subfamily(self) -> str:
        if self.style.is_ribbi:
            return self.style.display_name
        return "Italic" if self.style.italic else "Regular"

    @property
    def full_name(self) -> str:
        return f"{self.family} {self.style.display_name}"

    @property
    def postscript_name(self) -> str:
        return f"{self.family.replace(' ', '')}-{self.style.name}"

    def family_records(self) -> dict[int, str]:
        records = {1: self.legacy_family, 2: self.legacy_subfamily}
        if not self.style.is_ribbi:
            records |= {16: self.family, 17: self.style.display_name}
        return records


def font_revision(version: str) -> float:
    major, minor, patch = (int(part) for part in version.split("."))
    return round(major + minor / 10 + patch / 1000, 3)


def write_names(font: TTFont, config: Config, job: BuildJob) -> None:
    style, region = job.style, job.region
    variant = config.variants[job.variant]
    family = variant.family(config.family.name)
    names = FontNames(f"{family} {region}", style)
    revision = f"{font_revision(config.family.version):.3f}"
    notices = (config.family.copyright, *UPSTREAM_COPYRIGHTS)
    if variant.nerd_fonts:
        notices = (*notices, NERD_FONTS_COPYRIGHT)
    english = names.family_records() | {
        0: ". ".join(notices) + ".",
        3: f"{revision};{config.family.vendor_id};{names.postscript_name}",
        4: names.full_name,
        5: f"Version {revision}",
        6: names.postscript_name,
        8: config.family.designer,
        9: config.family.designer,
        13: LICENSE_DESCRIPTION,
        14: LICENSE_URL,
    }
    if config.family.url:
        english |= {11: config.family.url, 12: config.family.url}
    table = newTable("name")
    table.names = []
    for name_id, text in english.items():
        table.setName(text, name_id, *WINDOWS, LANGUAGE_IDS["en"])
    for locale, label in config.regions[region].localized.items():
        localized = FontNames(f"{family} {label}", style).family_records()
        for name_id in (1, 16):
            if name_id in localized:
                table.setName(localized[name_id], name_id, *WINDOWS, LANGUAGE_IDS[locale])
    font["name"] = table


def ink_extent(font: TTFont) -> tuple[int, int]:
    glyf = font["glyf"]
    inked = [glyf[name] for name in font.getGlyphOrder() if glyf[name].numberOfContours]
    return max(glyph.yMax for glyph in inked), min(glyph.yMin for glyph in inked)


def write_vertical_metrics(font: TTFont, config: Config) -> None:
    ascender, descender = config.metrics.ascender, config.metrics.descender
    os2, hhea = font["OS/2"], font["hhea"]
    os2.sTypoAscender, os2.sTypoDescender, os2.sTypoLineGap = ascender, descender, 0
    top, bottom = ink_extent(font)
    os2.usWinAscent, os2.usWinDescent = max(ascender, top), max(-descender, -bottom)
    hhea.ascent, hhea.descent, hhea.lineGap = ascender, descender, 0


def write_style_flags(font: TTFont, style: Style) -> None:
    os2, head = font["OS/2"], font["head"]
    os2.usWeightClass = style.weight.value
    selection = FS_USE_TYPO_METRICS
    selection |= FS_ITALIC if style.italic else 0
    selection |= FS_BOLD if style.is_bold else 0
    selection |= FS_REGULAR if not (style.italic or style.is_bold) else 0
    os2.fsSelection = selection
    head.macStyle = (MAC_BOLD if style.is_bold else 0) | (MAC_ITALIC if style.italic else 0)


def write_classification(font: TTFont, config: Config, region: str, cell_width: int) -> None:
    os2 = font["OS/2"]
    os2.version = max(os2.version, 4)
    os2.achVendID = config.family.vendor_id
    os2.xAvgCharWidth = cell_width
    os2.panose.bProportion = PANOSE_MONOSPACED
    pages = config.regions[region].code_pages
    os2.ulCodePageRange1 = sum(1 << bit for bit in pages if bit < 32)
    os2.ulCodePageRange2 = sum(1 << (bit - 32) for bit in pages if bit >= 32)
    os2.recalcUnicodeRanges(font)
    post = font["post"]
    post.isFixedPitch = 1
    post.formatType = 3.0
    font["head"].fontRevision = font_revision(config.family.version)


def write_language_tags(font: TTFont, config: Config, region: str) -> None:
    meta = newTable("meta")
    meta.data = {"dlng": config.regions[region].script, "slng": ",".join(SUPPORTED_SCRIPTS)}
    font["meta"] = meta


def finalize(font: TTFont, config: Config, job: BuildJob, cell_width: int) -> None:
    for tag in DROPPED_TABLES:
        if tag in font:
            del font[tag]
    write_names(font, config, job)
    write_vertical_metrics(font, config)
    write_style_flags(font, job.style)
    write_classification(font, config, job.region, cell_width)
    write_language_tags(font, config, job.region)
