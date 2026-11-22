from __future__ import annotations

import hashlib
import itertools
import json
import string
import tomllib
import urllib.request
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from urllib.parse import unquote, urlsplit

from plemio.config import LOCK_FILE, SOURCES_FILE, Config, Model
from plemio.styles import STYLES, WEIGHTS

CHUNK_SIZE = 1 << 16
RELOCK_HINT = "run `plemio fetch --mode update-lock`"
USER_AGENT = "plemio-build"


class SourceSpec(Model):
    revision: str
    url: str
    italic_url: str | None = None
    license: str


@dataclass(frozen=True, slots=True)
class SourceFile:
    url: str
    path: Path


@dataclass(frozen=True, slots=True)
class LockEntry:
    url: str
    sha256: str


class SourceError(RuntimeError):
    pass


class SourceCatalog:
    def __init__(self, specs: dict[str, SourceSpec], directory: Path, regions: list[str]) -> None:
        self._specs = specs
        self._directory = directory
        self._choices = {
            "style": [style.name for style in STYLES],
            "weight": [weight.name for weight in WEIGHTS],
            "region": regions,
        }

    @classmethod
    def from_config(cls, config: Config) -> SourceCatalog:
        data = tomllib.loads((config.root / SOURCES_FILE).read_text(encoding="utf-8"))
        specs = {key: SourceSpec.model_validate(value) for key, value in data.items()}
        return cls(specs, config.sources_dir, list(config.regions))

    def font(self, source_id: str, **params: str) -> Path:
        return self._file(source_id, self._spec(source_id).url, params).path

    def italic_font(self, source_id: str, **params: str) -> Path:
        spec = self._spec(source_id)
        return self._file(source_id, spec.italic_url or spec.url, params).path

    def has_italic(self, source_id: str) -> bool:
        return self._spec(source_id).italic_url is not None

    def license(self, source_id: str) -> Path:
        return self._file(source_id, self._spec(source_id).license, {}).path

    def files(self) -> Iterator[SourceFile]:
        for source_id, spec in self._specs.items():
            for template in filter(None, (spec.url, spec.italic_url, spec.license)):
                for params in self._expansions(template):
                    yield self._file(source_id, template, params)

    def _spec(self, source_id: str) -> SourceSpec:
        try:
            return self._specs[source_id]
        except KeyError:
            msg = f"unknown source {source_id!r}; known: {sorted(self._specs)}"
            raise SourceError(msg) from None

    def _expansions(self, template: str) -> Iterator[dict[str, str]]:
        choices = self._choices
        fields = {name for _, name, _, _ in string.Formatter().parse(template) if name}
        keys = [key for key in choices if key in fields or f"{key}_lower" in fields]
        for values in itertools.product(*(choices[key] for key in keys)):
            yield dict(zip(keys, values, strict=True))

    def _file(self, source_id: str, template: str, params: dict[str, str]) -> SourceFile:
        spec = self._spec(source_id)
        lowered = {f"{key}_lower": value.lower() for key, value in params.items()}
        url = template.format(revision=spec.revision, **params, **lowered)
        name = unquote(Path(urlsplit(url).path).name)
        return SourceFile(url, self._directory / source_id / name)


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, destination: Path) -> None:
    if urlsplit(url).scheme != "https":
        msg = f"refusing non-https source URL: {url}"
        raise SourceError(msg)
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})  # noqa: S310
    try:
        with urllib.request.urlopen(request, timeout=120) as response, partial.open("wb") as out:  # noqa: S310
            while chunk := response.read(CHUNK_SIZE):
                out.write(chunk)
        partial.replace(destination)
    except Exception:
        partial.unlink(missing_ok=True)
        raise


class Lockfile:
    def __init__(self, path: Path, root: Path) -> None:
        self.path = path
        self._root = root
        raw = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
        self.entries = {key: LockEntry(**value) for key, value in raw.items()}

    @classmethod
    def for_config(cls, config: Config) -> Lockfile:
        return cls(config.root / LOCK_FILE, config.root)

    def key(self, file: SourceFile) -> str:
        return file.path.relative_to(self._root).as_posix()

    def save(self) -> None:
        payload = {
            key: {"url": entry.url, "sha256": entry.sha256}
            for key, entry in sorted(self.entries.items())
        }
        self.path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


@dataclass(slots=True)
class FetchReport:
    downloaded: int = 0
    verified: int = 0
    errors: list[str] = field(default_factory=list)


class SyncMode(StrEnum):
    DOWNLOAD = "download"
    UPDATE_LOCK = "update-lock"
    OFFLINE = "offline"


def sync_sources(
    catalog: SourceCatalog,
    lockfile: Lockfile,
    mode: SyncMode = SyncMode.DOWNLOAD,
    log: Callable[[str], None] = lambda _: None,
) -> FetchReport:
    update_lock = mode is SyncMode.UPDATE_LOCK
    report = FetchReport()
    files = list(catalog.files())
    for file in files:
        key = lockfile.key(file)
        locked = lockfile.entries.get(key)
        stale = locked is not None and locked.url != file.url
        if stale and not update_lock:
            report.errors.append(f"{key}: url changed since locking; {RELOCK_HINT}")
            continue
        if not file.path.is_file() or stale:
            if mode is SyncMode.OFFLINE:
                report.errors.append(f"{key}: missing")
                continue
            log(f"download {key}")
            download(file.url, file.path)
            report.downloaded += 1
        digest = sha256_of(file.path)
        if locked is None or update_lock:
            lockfile.entries[key] = LockEntry(file.url, digest)
        elif locked.sha256 != digest:
            report.errors.append(f"{key}: sha256 {digest} does not match lock {locked.sha256}")
            continue
        report.verified += 1
    if not report.errors:
        wanted = {lockfile.key(file) for file in files}
        lockfile.entries = {key: entry for key, entry in lockfile.entries.items() if key in wanted}
        lockfile.save()
    return report
