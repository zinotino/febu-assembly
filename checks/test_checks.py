"""The checks' own logic, offline: python checks/test_checks.py (or pytest). The chain reads need a node and are not
tested here."""
from decimal import Decimal

from common import B58, entry, find, text
from fact5 import on_page
from fact6 import rows


def test_word_rule():
    page = {"title": "The Jester", "ascii_art": None, "body": "majesty, slaughter and onslaught, indebted, mocking"}
    assert on_page("jest", page) and on_page("mock", page)
    assert not on_page("laugh", page) and not on_page("debt", page)
    assert not on_page("jest", {"title": "", "body": "majesty"})


def test_steps_rows_add_up():
    got, total = rows(text("fact-6-steps.txt"))
    assert [n for n, *_ in got] == list(range(1, 45))
    assert sum(sol for _, _, sol, _ in got).quantize(total) == total == Decimal("2939.095965")


def test_ledger_links_found():
    assert find(r"solscan\.io/tx/(%s)" % B58, entry(2), "sale").startswith("51ekPPgz")
    assert find(r"other than (%s)" % B58, entry(6), "wallet").startswith("ApWpkd8t")
    assert find(r"\$FEBU token,\s+(%s)" % B58, entry(1), "mint").endswith("pump")


if __name__ == "__main__":
    for name, f in list(globals().items()):
        if name.startswith("test_"):
            f()
    print("ok")
