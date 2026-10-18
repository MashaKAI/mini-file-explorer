"""Кольорові теми: retro (бурштин/зелений) та modern (темна з акцентом)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    name: str
    background: str
    foreground: str
    accent: str
    dir_color: str
    muted: str
    error: str
    selection: str
    dir_icon: str
    file_icon: str
    link_icon: str

    def to_textual(self):
        """Тема Textual із прив'язкою кольорів до CSS-змінних ($primary, $surface тощо)."""
        from textual.theme import Theme as TextualTheme

        return TextualTheme(
            name=f"explorer-{self.name}",
            primary=self.accent,
            secondary=self.dir_color,
            accent=self.accent,
            foreground=self.foreground,
            background=self.background,
            surface=self.selection,
            panel=self.selection,
            error=self.error,
            dark=True,
        )


RETRO = Theme(
    name="retro",
    background="#0a0a0a",
    foreground="#33ff66",
    accent="#ffb000",
    dir_color="#ffb000",
    muted="#1f9940",
    error="#ff5555",
    selection="#1a3d24",
    dir_icon="▸",
    file_icon="·",
    link_icon="↪",
)

MODERN = Theme(
    name="modern",
    background="#0f1117",
    foreground="#c0caf5",
    accent="#7aa2f7",
    dir_color="#7dcfff",
    muted="#565f89",
    error="#f7768e",
    selection="#292e42",
    dir_icon="▣",
    file_icon="▢",
    link_icon="⇢",
)

THEMES: tuple[Theme, ...] = (RETRO, MODERN)


def next_theme(current: Theme) -> Theme:
    return THEMES[(THEMES.index(current) + 1) % len(THEMES)]
