"""Textual-інтерфейс: breadcrumb, таблиця файлів, прев'ю, фільтр і статус-бар."""
from __future__ import annotations

import threading
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import DataTable, Input, Static

from .fs import Entry, entry_for, human_size, list_dir, nearest_existing
from .preview import read_preview
from .search import search
from .sorting import SortKey, filter_entries, sort_entries
from .themes import MODERN, RETRO, THEMES, Theme, next_theme

HINTS = "Enter відкрити · ← нагору · / фільтр · Ctrl+F пошук · s сорт. · t тема · q вихід"


def printable_name(name: str) -> str:
    """Імена з керуючими символами (напр. новий рядок) показуємо безпечно."""
    return "".join(ch if ch.isprintable() else ("⏎" if ch == "\n" else "�") for ch in name)


def format_date(ts: float | None) -> str:
    if ts is None:
        return "-"
    try:
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
    except (OSError, OverflowError, ValueError):
        return "-"


class FileTable(DataTable):
    """Таблиця, у якої ←/→/Backspace керують навігацією, а не колонками."""

    BINDINGS = [
        Binding("right", "app.open_selected", "Увійти", show=False),
        Binding("left", "app.go_up", "Нагору", show=False),
        Binding("backspace", "app.go_up", "Нагору", show=False),
    ]


class ExplorerApp(App):
    TITLE = "Mini File Explorer"

    CSS = """
    Screen { background: $background; color: $foreground; }
    #breadcrumb { height: 1; padding: 0 1; background: $panel; color: $accent; text-style: bold; }
    #main { height: 1fr; }
    #files { width: 62%; background: $background; scrollbar-size-vertical: 1; scrollbar-background: $background; scrollbar-color: $primary; }
    #preview { width: 38%; padding: 0 1; border-left: tall $primary; background: $surface; }
    #filter { display: none; height: 3; border: tall $primary; background: $background; }
    #filter.active { display: block; }
    #status { height: 1; padding: 0 1; background: $panel; }
    """

    BINDINGS = [
        Binding("s", "cycle_sort", "Сортування"),
        Binding("slash", "start_filter", "Фільтр"),
        Binding("ctrl+f", "start_search", "Пошук"),
        Binding("t", "cycle_theme", "Тема"),
        Binding("r", "refresh_dir", "Оновити"),
        Binding("escape", "cancel", "Скасувати", show=False),
        Binding("q", "quit", "Вийти"),
    ]

    def __init__(self, start: Path | str | None = None, theme: str = "retro") -> None:
        super().__init__()
        self.theme_obj: Theme = MODERN if theme == "modern" else RETRO
        self.sort_key = SortKey.NAME
        self.entries: list[Entry] = []
        self.shown: list[Entry] = []
        self.filter_text = ""
        self.search_results: list[Entry] | None = None
        self.search_query = ""
        self.status_text = ""
        self.preview_text = ""
        self._input_mode = "filter"
        self._cancel_search = threading.Event()
        self.cwd = self._initial_dir(start)

    @staticmethod
    def _initial_dir(start: Path | str | None) -> Path:
        try:
            path = Path(start if start is not None else ".").expanduser().resolve()
        except (OSError, RuntimeError):
            path = Path.cwd()
        if path.is_file():
            path = path.parent
        return nearest_existing(path)

    # ---------- побудова ----------
    def compose(self) -> ComposeResult:
        yield Static(id="breadcrumb")
        with Horizontal(id="main"):
            yield FileTable(id="files", cursor_type="row", zebra_stripes=True)
            with VerticalScroll(id="preview"):
                yield Static(id="preview-text")
        yield Input(id="filter")
        yield Static(id="status")

    def on_mount(self) -> None:
        for theme in THEMES:
            self.register_theme(theme.to_textual())
        self.theme = f"explorer-{self.theme_obj.name}"
        table = self.query_one("#files", DataTable)
        table.add_column("Ім'я", key="name")
        table.add_column("Розмір", key="size")
        table.add_column("Змінено", key="date")
        table.add_column("Тип", key="kind")
        self._load(self.cwd)
        table.focus()

    # ---------- завантаження і відображення ----------
    def _load(self, path: Path) -> bool:
        entries, error = list_dir(path)
        if error:
            self.set_status(error, error=True)
            return False
        self.cwd = path
        self.entries = entries
        self.refresh_table()
        return True

    def _base(self) -> list[Entry]:
        return self.entries if self.search_results is None else self.search_results

    def refresh_table(self) -> None:
        self.shown = sort_entries(filter_entries(self._base(), self.filter_text), self.sort_key)
        table = self.query_one("#files", DataTable)
        table.clear()
        theme = self.theme_obj
        for i, e in enumerate(self.shown):
            if e.is_broken:
                icon, color = theme.link_icon, theme.error
            elif e.is_dir:
                icon, color = theme.dir_icon, theme.dir_color
            elif e.is_symlink:
                icon, color = theme.link_icon, theme.muted
            else:
                icon, color = theme.file_icon, theme.foreground
            table.add_row(
                Text(f"{icon} {printable_name(e.name)}", style=color),
                Text(human_size(e.size), style=theme.muted, justify="right"),
                Text(format_date(e.modified), style=theme.muted),
                Text(e.kind, style=theme.muted),
                key=str(i),
            )
        if self.shown:
            table.move_cursor(row=0)
        self._update_breadcrumb()
        self._update_preview()
        self._default_status()

    def _update_breadcrumb(self) -> None:
        parts = self.cwd.parts or (str(self.cwd),)
        crumb = Text(" › ".join(p.strip("\\/") or p for p in parts))
        if self.search_results is not None:
            crumb.append(f"   🔍 «{self.search_query}»: {len(self.search_results)}", style=self.theme_obj.foreground)
        elif self.filter_text:
            crumb.append(f"   ⌕ «{self.filter_text}»", style=self.theme_obj.foreground)
        self.query_one("#breadcrumb", Static).update(crumb)

    def selected(self) -> Entry | None:
        table = self.query_one("#files", DataTable)
        row = table.cursor_row
        if table.row_count and 0 <= row < len(self.shown):
            return self.shown[row]
        return None

    def _update_preview(self) -> None:
        e = self.selected()
        if e is None:
            self.preview_text = ""
        elif e.is_dir:
            self.preview_text = f"Папка\n{printable_name(e.name)}"
        elif e.is_broken:
            self.preview_text = "Бите посилання — цільовий файл не існує"
        else:
            p = read_preview(e.path)
            self.preview_text = p.text if p.text is not None else (p.note or "")
            if p.text is not None and p.note:
                self.preview_text += f"\n\n… {p.note}"
        self.query_one("#preview-text", Static).update(Text(self.preview_text, style=self.theme_obj.foreground))

    def set_status(self, message: str, error: bool = False) -> None:
        self.status_text = message
        style = self.theme_obj.error if error else self.theme_obj.muted
        self.query_one("#status", Static).update(Text(message, style=style))

    def _default_status(self) -> None:
        info = f"{len(self.shown)} елем. · сорт.: {self.sort_key.value} · {HINTS}"
        self.set_status(info)

    # ---------- події ----------
    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self._update_preview()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self.action_open_selected()

    def on_input_changed(self, event: Input.Changed) -> None:
        if self._input_mode == "filter":
            self.filter_text = event.value
            self.refresh_table()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if self._input_mode == "search":
            self._start_search(event.value.strip())
        else:
            self._hide_input()

    # ---------- навігація ----------
    def _navigate(self, path: Path, select: str | None = None) -> None:
        old = (self.filter_text, self.search_results)
        self.filter_text, self.search_results = "", None
        if not self._load(path):
            self.filter_text, self.search_results = old
            return
        self._hide_input()
        if select is not None:
            for i, e in enumerate(self.shown):
                if e.name == select:
                    self.query_one("#files", DataTable).move_cursor(row=i)
                    self._update_preview()
                    break

    def action_open_selected(self) -> None:
        e = self.selected()
        if e is None:
            return
        if e.is_dir:
            self._navigate(e.path)
        elif self.search_results is not None:
            self._navigate(e.path.parent, select=e.path.name)
        else:
            self.set_status(f"{printable_name(e.name)} — {human_size(e.size)}, змінено {format_date(e.modified)}")

    def action_go_up(self) -> None:
        if self.search_results is not None or self.filter_text:
            self.action_cancel()
            return
        parent = self.cwd.parent
        if parent == self.cwd:
            self.set_status("Це корінь — вище підніматися нікуди")
            return
        self._navigate(parent, select=self.cwd.name)

    def action_refresh_dir(self) -> None:
        if not self.cwd.is_dir():
            fallback = nearest_existing(self.cwd)
            self.search_results, self.filter_text = None, ""
            if self._load(fallback):
                self.set_status(f"Папку видалено — перейшли до {fallback}", error=True)
            return
        self._load(self.cwd)

    # ---------- сортування, тема ----------
    def action_cycle_sort(self) -> None:
        self.sort_key = self.sort_key.next()
        self.refresh_table()

    def action_cycle_theme(self) -> None:
        self.theme_obj = next_theme(self.theme_obj)
        self.theme = f"explorer-{self.theme_obj.name}"
        self.refresh_table()

    # ---------- фільтр і пошук ----------
    def _show_input(self, mode: str, placeholder: str, value: str) -> None:
        self._input_mode = mode
        box = self.query_one("#filter", Input)
        box.placeholder = placeholder
        box.add_class("active")
        box.value = value
        box.focus()

    def _hide_input(self) -> None:
        self.query_one("#filter", Input).remove_class("active")
        self.query_one("#files", DataTable).focus()

    def action_start_filter(self) -> None:
        self._show_input("filter", "Фільтр за назвою…", self.filter_text)

    def action_start_search(self) -> None:
        self._show_input("search", "Рекурсивний пошук (Enter — почати, Esc — скасувати)…", "")

    def action_cancel(self) -> None:
        self._cancel_search.set()
        self.filter_text, self.search_results = "", None
        self._hide_input()
        self.refresh_table()

    def _start_search(self, query: str) -> None:
        if not query:
            return
        self._cancel_search.set()
        cancel = threading.Event()
        self._cancel_search = cancel
        root = self.cwd
        self.search_query = query
        self._hide_input()
        self.set_status(f"Пошук «{query}»… (Esc — скасувати)")

        def work() -> None:
            result = search(root, query, cancel=cancel.is_set)
            if not cancel.is_set():
                self.call_from_thread(self._finish_search, query, root, result)

        self.run_worker(work, thread=True, group="search", exclusive=True)

    def _finish_search(self, query: str, root: Path, result) -> None:
        found: list[Entry] = []
        for p in result.matches:
            e = entry_for(p)
            if e is None:
                continue
            try:
                rel = str(p.relative_to(root))
            except ValueError:
                rel = str(p)
            found.append(replace(e, name=rel))
        self.filter_text = ""
        self.search_results = found
        self.refresh_table()
        note = f"Знайдено {len(found)}"
        if result.truncated:
            note += " (показано лише перші — звузьте запит)"
        if result.errors:
            note += f" · недоступних папок: {result.errors}"
        self.set_status(note + " · Esc — повернутися", error=bool(result.errors))
