import os
import sys
from pathlib import Path

import pytest

from explorer import fs
from explorer.fs import human_size, list_dir, nearest_existing


def _can_symlink(tmp: Path) -> bool:
    try:
        (tmp / "_probe").symlink_to(tmp)
        (tmp / "_probe").unlink()
        return True
    except (OSError, NotImplementedError):
        return False


def test_list_dir_basic(tmp_path):
    (tmp_path / "a.txt").write_text("hi", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    entries, error = list_dir(tmp_path)
    assert error is None
    by_name = {e.name: e for e in entries}
    assert by_name["sub"].is_dir is True
    assert by_name["a.txt"].is_dir is False
    assert by_name["a.txt"].size == 2
    assert by_name["a.txt"].kind == "txt"
    assert by_name["sub"].kind == "dir"


def test_list_dir_missing_returns_error(tmp_path):
    entries, error = list_dir(tmp_path / "немає")
    assert entries == []
    assert error is not None


def test_list_dir_not_a_directory(tmp_path):
    f = tmp_path / "f.txt"
    f.write_text("x", encoding="utf-8")
    entries, error = list_dir(f)
    assert entries == []
    assert error is not None


def test_unicode_and_spaces_names(tmp_path):
    (tmp_path / "файл з пробілом.txt").write_text("привіт", encoding="utf-8")
    entries, error = list_dir(tmp_path)
    assert error is None
    assert [e.name for e in entries] == ["файл з пробілом.txt"]


@pytest.mark.skipif(sys.platform == "win32", reason="newline in name not allowed on Windows")
def test_newline_in_name(tmp_path):
    (tmp_path / "a\nb.txt").write_text("x", encoding="utf-8")
    entries, error = list_dir(tmp_path)
    assert error is None
    assert entries[0].name == "a\nb.txt"


def test_broken_symlink(tmp_path):
    if not _can_symlink(tmp_path):
        pytest.skip("symlinks unavailable")
    (tmp_path / "bad").symlink_to(tmp_path / "nowhere")
    entries, error = list_dir(tmp_path)
    assert error is None
    assert entries[0].is_symlink is True
    assert entries[0].is_broken is True
    assert entries[0].kind == "link"


def test_permission_denied(tmp_path, monkeypatch):
    def boom(_):
        raise PermissionError("denied")

    monkeypatch.setattr(os, "scandir", boom)
    entries, error = list_dir(tmp_path)
    assert entries == []
    assert "доступ" in error.lower()


def test_human_size():
    assert human_size(0) == "0 B"
    assert human_size(1536) == "1.5 KB"
    assert human_size(None) == "-"


def test_nearest_existing(tmp_path):
    deep = tmp_path / "a" / "b"
    assert nearest_existing(deep) == tmp_path
    assert nearest_existing(tmp_path) == tmp_path


def test_entry_for_existing_and_missing(tmp_path):
    f = tmp_path / "x.txt"
    f.write_text("abc", encoding="utf-8")
    e = fs.entry_for(f)
    assert e is not None and e.size == 3 and e.name == "x.txt"
    assert fs.entry_for(tmp_path / "nope") is None
