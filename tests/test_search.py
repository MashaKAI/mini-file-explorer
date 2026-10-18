import os
import threading

import pytest

from explorer import search as search_mod
from explorer.search import search


def test_finds_nested_match(tmp_path):
    (tmp_path / "a" / "b").mkdir(parents=True)
    target = tmp_path / "a" / "b" / "звіт.txt"
    target.write_text("x", encoding="utf-8")
    res = search(tmp_path, "звіт")
    assert res.matches == [target]
    assert res.truncated is False


def test_case_insensitive(tmp_path):
    (tmp_path / "README.md").write_text("x", encoding="utf-8")
    assert len(search(tmp_path, "readme").matches) == 1


def test_limit_sets_truncated(tmp_path):
    for i in range(10):
        (tmp_path / f"f{i}.txt").write_text("x", encoding="utf-8")
    res = search(tmp_path, "f", limit=3)
    assert len(res.matches) == 3
    assert res.truncated is True


def test_symlink_loop_terminates(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "hit.txt").write_text("x", encoding="utf-8")
    try:
        (tmp_path / "a" / "loop").symlink_to(tmp_path / "a", target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")
    res = search(tmp_path, "hit")
    assert len(res.matches) == 1


def test_unreadable_dir_counted_in_errors(tmp_path, monkeypatch):
    (tmp_path / "locked").mkdir()
    real = os.scandir

    def fake(path):
        if str(path).endswith("locked"):
            raise PermissionError("denied")
        return real(path)

    monkeypatch.setattr(search_mod.os, "scandir", fake)
    res = search(tmp_path, "x")
    assert res.errors == 1


def test_cancel_stops_early(tmp_path):
    for i in range(5):
        (tmp_path / f"d{i}").mkdir()
    res = search(tmp_path, "zzz", cancel=lambda: True)
    assert res.matches == []


def test_deep_tree_no_recursion_error(tmp_path, monkeypatch):
    # імітуємо дуже глибоке дерево без створення 1200 реальних папок
    class FakeEntry:
        def __init__(self, name, path):
            self.name, self.path = name, path

        def is_dir(self, follow_symlinks=True):
            return True

        def is_symlink(self):
            return False

    class FakeScan:
        def __init__(self, entries):
            self.entries = entries

        def __enter__(self):
            return iter(self.entries)

        def __exit__(self, *a):
            return False

    def fake_scandir(path):
        depth = int(str(path).rsplit("/", 1)[-1].replace("d", "") or 0) if "/d" in str(path) else 0
        if depth >= 1200:
            return FakeScan([])
        nxt = f"/d{depth + 1}" if depth else "/d1"
        base = str(path).rsplit("/", 1)[0] if depth else str(path)
        return FakeScan([FakeEntry(f"d{depth + 1}", base + nxt)])

    monkeypatch.setattr(search_mod.os, "scandir", fake_scandir)
    monkeypatch.setattr(search_mod.os.path, "realpath", lambda p: str(p))
    res = search(tmp_path.__class__("/root"), "nomatch")
    assert res.matches == []
    assert res.errors == 0
