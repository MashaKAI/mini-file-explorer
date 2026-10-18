from pathlib import Path

from explorer.fs import Entry
from explorer.sorting import SortKey, filter_entries, sort_entries


def e(name, is_dir=False, size=0, modified=0.0):
    return Entry(name, Path(name), is_dir, None if is_dir else size, modified)


def names(entries):
    return [x.name for x in entries]


def test_dirs_always_first():
    out = sort_entries([e("a.txt"), e("zdir", True)], SortKey.NAME)
    assert names(out) == ["zdir", "a.txt"]


def test_sort_by_name_case_insensitive():
    out = sort_entries([e("b"), e("A"), e("c")], SortKey.NAME)
    assert names(out) == ["A", "b", "c"]


def test_sort_by_size_desc():
    out = sort_entries([e("s", size=1), e("l", size=9)], SortKey.SIZE, reverse=True)
    assert names(out) == ["l", "s"]


def test_sort_by_date():
    out = sort_entries([e("new", modified=5), e("old", modified=1)], SortKey.DATE)
    assert names(out) == ["old", "new"]


def test_none_size_does_not_crash():
    broken = Entry("x", Path("x"), False, None, None)
    out = sort_entries([e("a", size=3), broken], SortKey.SIZE)
    assert len(out) == 2
    out = sort_entries([e("a", modified=3), broken], SortKey.DATE)
    assert len(out) == 2


def test_sortkey_cycle():
    assert SortKey.NAME.next() is SortKey.SIZE
    assert SortKey.SIZE.next() is SortKey.DATE
    assert SortKey.DATE.next() is SortKey.NAME


def test_filter_case_insensitive_unicode():
    out = filter_entries([e("привіт.txt"), e("other")], "ПРИВІТ")
    assert names(out) == ["привіт.txt"]


def test_filter_empty_returns_all():
    items = [e("a"), e("b")]
    assert filter_entries(items, "") == items
