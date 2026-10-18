import os

from explorer import preview as preview_mod
from explorer.preview import read_preview


def test_text_file(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("рядок 1\nline 2\n", encoding="utf-8")
    p = read_preview(f)
    assert p.text == "рядок 1\nline 2\n"
    assert p.note is None


def test_large_file_truncated_with_note(tmp_path):
    f = tmp_path / "big.txt"
    f.write_text("x" * 100_000, encoding="utf-8")
    p = read_preview(f, max_bytes=1000)
    assert len(p.text) <= 1000
    assert p.note is not None


def test_binary_detected_by_nul_byte(tmp_path):
    f = tmp_path / "b.bin"
    f.write_bytes(b"\x00\x01\x02abc")
    p = read_preview(f)
    assert p.text is None
    assert "бінар" in p.note.lower()


def test_invalid_utf8_replaced(tmp_path):
    f = tmp_path / "bad.txt"
    f.write_bytes(b"ok \xff\xfe end")
    p = read_preview(f)
    assert p.text is not None and "ok" in p.text


def test_missing_file_note(tmp_path):
    p = read_preview(tmp_path / "nope.txt")
    assert p.text is None and p.note


def test_permission_error_note(tmp_path, monkeypatch):
    f = tmp_path / "x.txt"
    f.write_text("x", encoding="utf-8")

    def boom(*a, **k):
        raise PermissionError("denied")

    monkeypatch.setattr(preview_mod.Path, "open", boom)
    p = read_preview(f)
    assert p.text is None and "доступ" in p.note


def test_utf8_cyrillic_not_split(tmp_path):
    f = tmp_path / "c.txt"
    f.write_text("я" * 100, encoding="utf-8")  # 2 байти на символ
    p = read_preview(f, max_bytes=51)  # різати посеред символу
    assert "\ufffd" not in p.text


def test_directory_note(tmp_path):
    p = read_preview(tmp_path)
    assert p.text is None and p.note
