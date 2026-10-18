"""Рекурсивний пошук за назвою: обхід у ширину через чергу (без рекурсії)."""
from __future__ import annotations

import os
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


@dataclass
class SearchResult:
    matches: list[Path] = field(default_factory=list)
    errors: int = 0
    truncated: bool = False


def search(
    root: Path,
    query: str,
    limit: int = 500,
    cancel: Callable[[], bool] | None = None,
) -> SearchResult:
    result = SearchResult()
    needle = query.casefold()
    if not needle:
        return result
    queue: deque[str] = deque([str(root)])
    visited: set[str] = set()
    while queue:
        if cancel is not None and cancel():
            return result
        current = queue.popleft()
        try:
            real = os.path.realpath(current)
        except OSError:
            result.errors += 1
            continue
        if real in visited:
            continue  # цикл symlink або повторний вхід
        visited.add(real)
        try:
            with os.scandir(current) as it:
                for de in it:
                    if needle in de.name.casefold():
                        result.matches.append(Path(de.path))
                        if len(result.matches) >= limit:
                            result.truncated = True
                            return result
                    try:
                        if de.is_dir(follow_symlinks=True):
                            queue.append(de.path)
                    except OSError:
                        result.errors += 1
        except OSError:
            result.errors += 1
    return result
