"""Сортування та фільтрація записів каталогу."""
from __future__ import annotations

from enum import Enum

from .fs import Entry


class SortKey(Enum):
    NAME = "ім'я"
    SIZE = "розмір"
    DATE = "дата"

    def next(self) -> "SortKey":
        members = list(SortKey)
        return members[(members.index(self) + 1) % len(members)]


def sort_entries(entries: list[Entry], key: SortKey, reverse: bool = False) -> list[Entry]:
    """Папки завжди першими; reverse застосовується лише всередині груп."""

    def value(e: Entry):
        if key is SortKey.SIZE:
            return (e.size or 0, e.name.casefold())
        if key is SortKey.DATE:
            return (e.modified or 0.0, e.name.casefold())
        return e.name.casefold()

    dirs = sorted((e for e in entries if e.is_dir), key=value, reverse=reverse)
    files = sorted((e for e in entries if not e.is_dir), key=value, reverse=reverse)
    return dirs + files


def filter_entries(entries: list[Entry], text: str) -> list[Entry]:
    needle = text.casefold()
    if not needle:
        return entries
    return [e for e in entries if needle in e.name.casefold()]
