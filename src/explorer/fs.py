"""Шар файлової системи: читання каталогів без викидання винятків."""
from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Entry:
    name: str
    path: Path
    is_dir: bool
    size: int | None
    modified: float | None
    is_symlink: bool = False
    is_broken: bool = False

    @property
    def kind(self) -> str:
        if self.is_broken or (self.is_symlink and not self.is_dir):
            return "link"
        if self.is_dir:
            return "dir"
        suffix = Path(self.name).suffix.lstrip(".").lower()
        return suffix or "file"


def human_size(n: int | None) -> str:
    if n is None:
        return "-"
    size = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{int(size)} B" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"  # pragma: no cover


def _describe_error(exc: OSError) -> str:
    if isinstance(exc, PermissionError):
        return "Немає доступу до цієї папки"
    if isinstance(exc, FileNotFoundError):
        return "Шлях не існує"
    if isinstance(exc, NotADirectoryError):
        return "Це не папка"
    return f"Помилка файлової системи: {exc.strerror or exc}"


def _make_entry(de: os.DirEntry) -> Entry:
    path = Path(de.path)
    try:
        is_symlink = de.is_symlink()
    except OSError:
        is_symlink = False
    try:
        is_dir = de.is_dir()
    except OSError:
        is_dir = False
    size: int | None = None
    modified: float | None = None
    broken = False
    try:
        st = de.stat()
        modified = st.st_mtime
        size = None if is_dir else st.st_size
    except OSError:
        # битий symlink або файл, який зник / недоступний
        broken = is_symlink
        if is_symlink:
            try:
                modified = de.stat(follow_symlinks=False).st_mtime
            except OSError:
                modified = None
    return Entry(de.name, path, is_dir, size, modified, is_symlink, broken)


def list_dir(path: Path) -> tuple[list[Entry], str | None]:
    """Повертає (записи, повідомлення про помилку). Ніколи не кидає виняток."""
    entries: list[Entry] = []
    try:
        with os.scandir(path) as it:
            for de in it:
                try:
                    entries.append(_make_entry(de))
                except OSError:
                    continue
    except OSError as exc:
        return [], _describe_error(exc)
    return entries, None


def nearest_existing(path: Path) -> Path:
    """Найближчий існуючий каталог серед path та його батьків."""
    current = path
    while True:
        try:
            if current.is_dir():
                return current
        except OSError:
            pass
        parent = current.parent
        if parent == current:
            return current
        current = parent


def entry_for(path: Path) -> Entry | None:
    """Entry для одного шляху (None, якщо шлях недоступний)."""
    try:
        lst = path.lstat()
    except OSError:
        return None
    is_symlink = stat.S_ISLNK(lst.st_mode)
    try:
        st = path.stat()
        is_dir = stat.S_ISDIR(st.st_mode)
        broken = False
    except OSError:
        st, is_dir, broken = lst, False, is_symlink
    return Entry(
        path.name or str(path),
        path,
        is_dir,
        None if is_dir else st.st_size,
        st.st_mtime,
        is_symlink,
        broken,
    )
