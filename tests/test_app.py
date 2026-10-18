import shutil
from pathlib import Path

from explorer import app as app_mod
from explorer.app import ExplorerApp
from explorer.sorting import SortKey


def make_tree(root: Path):
    (root / "sub").mkdir()
    (root / "alpha.txt").write_text("small", encoding="utf-8")
    (root / "beta.txt").write_text("b" * 500, encoding="utf-8")
    (root / "sub" / "deep.log").write_text("deep", encoding="utf-8")


async def test_shows_entries(tmp_path):
    make_tree(tmp_path)
    app = ExplorerApp(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.cwd == tmp_path.resolve()
        assert app.query_one("#files").row_count == 3
        assert [e.name for e in app.shown][0] == "sub"


async def test_enter_dir_and_go_up(tmp_path):
    make_tree(tmp_path)
    app = ExplorerApp(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("enter")
        assert app.cwd == (tmp_path / "sub").resolve()
        await pilot.press("left")
        assert app.cwd == tmp_path.resolve()


async def test_enter_on_denied_dir_shows_status_error_and_stays(tmp_path, monkeypatch):
    make_tree(tmp_path)
    real = app_mod.list_dir

    def fake(p):
        if Path(p).name == "sub":
            return [], "Немає доступу до цієї папки"
        return real(p)

    monkeypatch.setattr(app_mod, "list_dir", fake)
    app = ExplorerApp(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("enter")
        assert app.cwd == tmp_path.resolve()
        assert "Немає доступу" in app.status_text


async def test_sort_key_changes_order(tmp_path):
    make_tree(tmp_path)
    app = ExplorerApp(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("s")
        assert app.sort_key is SortKey.SIZE
        files = [e.name for e in app.shown if not e.is_dir]
        assert files == ["alpha.txt", "beta.txt"]


async def test_live_filter(tmp_path):
    make_tree(tmp_path)
    app = ExplorerApp(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("/", "a", "l")
        assert [e.name for e in app.shown] == ["alpha.txt"]
        await pilot.press("escape")
        assert len(app.shown) == 3


async def test_recursive_search_lists_matches(tmp_path):
    make_tree(tmp_path)
    app = ExplorerApp(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("ctrl+f", "d", "e", "e", "p", "enter")
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert [e.path.name for e in app.shown] == ["deep.log"]
        await pilot.press("escape")
        assert len(app.shown) == 3


async def test_theme_toggle_changes_theme_name(tmp_path):
    app = ExplorerApp(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.theme_obj.name == "retro"
        await pilot.press("t")
        assert app.theme_obj.name == "modern"
        assert app.theme == "explorer-modern"


async def test_deleted_cwd_falls_back_to_parent(tmp_path):
    make_tree(tmp_path)
    app = ExplorerApp(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("enter")
        shutil.rmtree(tmp_path / "sub")
        await pilot.press("r")
        assert app.cwd == tmp_path.resolve()


async def test_preview_shown_for_text_file(tmp_path):
    (tmp_path / "a.txt").write_text("привіт, світе", encoding="utf-8")
    app = ExplorerApp(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert "привіт" in app.preview_text


async def test_invalid_start_path_falls_back_to_existing_parent(tmp_path):
    app = ExplorerApp(tmp_path / "nope" / "deeper")
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.cwd == tmp_path.resolve()


async def test_newline_and_unicode_names_do_not_crash(tmp_path):
    (tmp_path / "файл з пробілом.txt").write_text("x", encoding="utf-8")
    app = ExplorerApp(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.query_one("#files").row_count == 1
