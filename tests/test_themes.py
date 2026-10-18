import re
from dataclasses import fields

from explorer.themes import MODERN, RETRO, THEMES, next_theme


def test_next_theme_cycles():
    assert next_theme(RETRO) is MODERN
    assert next_theme(MODERN) is RETRO


def test_themes_have_valid_hex_colors():
    color_fields = ["background", "foreground", "accent", "dir_color", "muted", "error", "selection"]
    for theme in THEMES:
        for name in color_fields:
            assert re.fullmatch(r"#[0-9a-fA-F]{6}", getattr(theme, name)), (theme.name, name)


def test_theme_names_unique():
    assert len({t.name for t in THEMES}) == len(THEMES)


def test_all_fields_filled():
    for theme in THEMES:
        for f in fields(theme):
            assert getattr(theme, f.name)


def test_to_textual_registers_prefixed_name():
    t = RETRO.to_textual()
    assert t.name == "explorer-retro"
    assert t.background.lower() == RETRO.background
