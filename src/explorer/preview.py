"""Прев'ю невеликих текстових файлів."""
from __future__ import annotations

import codecs
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Preview:
    text: str | None
    note: str | None = None


def read_preview(path: Path, max_bytes: int = 8192, max_lines: int = 60) -> Preview:
    try:
        if path.is_dir():
            return Preview(None, "Це папка")
        with path.open("rb") as fh:
            raw = fh.read(max_bytes + 1)
    except PermissionError:
        return Preview(None, "Немає доступу до файлу")
    except FileNotFoundError:
        return Preview(None, "Файл не знайдено")
    except OSError as exc:
        return Preview(None, f"Не вдалося прочитати: {exc.strerror or exc}")

    truncated = len(raw) > max_bytes
    raw = raw[:max_bytes]
    if b"\x00" in raw:
        return Preview(None, "Бінарний файл — прев'ю недоступне")

    # інкрементальний декодер відкидає обірваний наприкінці багатобайтовий символ
    decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
    text = decoder.decode(raw, final=not truncated).replace("\r\n", "\n")

    lines = text.splitlines(keepends=True)
    note = None
    if len(lines) > max_lines:
        text = "".join(lines[:max_lines])
        truncated = True
    if truncated:
        note = "Показано лише початок файлу"
    return Preview(text, note)
