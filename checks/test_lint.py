"""lint.py's rules, offline: python checks/test_lint.py (or pytest). Each test changes one thing in a small ledger and
names the one rule that must catch it; two run on the real ledger and its archive."""
import re
import tempfile
from pathlib import Path

from lint import CANT, FAIL, OK, ROOT, WARN, lint, read, sha256

TODAY = "2026-11-30"
NOWHERE = Path(__file__).parent / "no-such-archive"
NOBODY = "    SEEN      nobody yet"
BASE = """TEST LEDGER (version 0)

STATUS
  {status}

WORDS USED HERE
  Member   Ann, Bo, Cy, Zed. Adding a member works like a rule change.

THE RULES
  2. Nothing is removed or rewritten.

THE ENTRIES

  FACT 1. (Zed, 2026-10-12)
    SAYS      One thing.
    WRONG IF  it is not there, or it moved; or it is gone.
{seen1}

  PROMISE 2. (Ann, 2026-10-12)
    WILL      Do a thing.
    BY        10 days after this version is adopted under rule 7.
    KNOWN BY  the file.
    IF BROKEN none.
{seen2}
{more}
CHANGES TO THE RULES
  2026-10-15. Clean start.{changes}
"""


def make(status="Adopted on 2026-10-22 under rule 7.", seen1=NOBODY, seen2=NOBODY, more="", changes=""):
    return BASE.format(status=status, seen1=seen1, seen2=seen2, more=more, changes=changes)


def item(name, date, word="HOLDS", lines="1, 2, 3"):
    return "- %s, %s: %s%s. Saw: it. New: a date. 3 minutes." % (name, date, word, " on lines " + lines if lines else "")


def seen(*items):
    return "    SEEN      " + "\n              ".join(items)


def codes(rows, status):
    return sorted({what.split()[0] for s, what in rows if s == status})


def row(rows, code):
    return next(what for _, what in rows if what.startswith(code + " "))


def archived(prev, name="v0.txt"):
    """A CHANGES TO THE RULES line that keeps prev as archive/name."""
    return "\n  2026-10-23. A change. The text before it is kept word for word in\n  archive/%s SHA-256\n  %s" % (
        name, sha256(prev))


def test_real_ledger_and_its_archive():
    real = read((ROOT / "ledger.txt").read_bytes())
    for prev in [real] + [read(p.read_bytes()) for p in sorted((ROOT / "archive").glob("*.txt"))]:
        rows = lint(real, prev, ROOT / "archive", TODAY)
        assert not codes(rows, FAIL) and not codes(rows, CANT), rows


def test_adoption_turn_rehearsed_on_the_real_ledger():
    """AFTER_VOTE_20261022.md in small: STATUS rewritten, the voted text archived, two checks of fact 3 copied in."""
    real = read((ROOT / "ledger.txt").read_bytes())
    new = re.sub(r"(?m)^STATUS\n(?:  .*\n)+", "STATUS\n  Adopted on 2026-10-22 under rule 7. Posts made before "
                 "2026-10-23 were the dry run.\n", real, count=1)
    head, tail = new.split("  FACT 3.", 1)
    new = head + "  FACT 3." + tail.replace(NOBODY, seen(item("Laura", "2026-10-23", lines="1, 2"),
                                                         item("Ksizzle", "2026-10-24", lines="1, 2")), 1)
    new = new.rstrip("\n") + archived(real, "08_CLAIMS_LEDGER_v3-voted.txt") + "\n"
    with tempfile.TemporaryDirectory() as d:
        arch = Path(d)
        for p in (ROOT / "archive").glob("*.txt"):
            (arch / p.name).write_bytes(p.read_bytes())
        (arch / "08_CLAIMS_LEDGER_v3-voted.txt").write_bytes(real.encode())
        rows = lint(new, real, arch, TODAY)
        assert not codes(rows, FAIL) and not codes(rows, WARN), rows
        assert "1 first SEEN item" in row(rows, "I1")
        (arch / "08_CLAIMS_LEDGER_v3-voted.txt").unlink()
        assert codes(lint(new, real, arch, TODAY), FAIL) == ["I1", "I9"]


def test_a_rewrite_needs_the_earlier_version_archived():
    prev = make()
    assert codes(lint(prev.replace("One thing.", "One other thing."), prev, NOWHERE, TODAY), FAIL) == ["I1"]
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "v0.txt").write_bytes(prev.encode())
        new = make(changes=archived(prev)).replace("One thing.", "One other thing.")
        rows = lint(new, prev, Path(d), TODAY)
        assert not codes(rows, FAIL) and "keeps it as archive/v0.txt" in row(rows, "I1")


def test_removed_personal_information_passes():
    prev = make(status="Adopted on 2026-10-22 under rule 7. Ann's phone is 555 0100.")
    rows = lint(prev.replace("555 0100", "[removed]"), prev, NOWHERE, TODAY)
    assert not codes(rows, FAIL) and "1 [removed]" in row(rows, "I1")


def test_the_first_seen_item_replaces_nobody_yet():
    prev = make()
    rows = lint(make(seen1=seen(item("Ann", "2026-10-23"), item("Bo", "2026-10-24"))), prev, NOWHERE, TODAY)
    assert not codes(rows, FAIL) and not codes(rows, WARN), rows
    assert "1 first SEEN item" in row(rows, "I1")


def test_no_earlier_version_cannot_tell():
    assert codes(lint(make(), None, NOWHERE, TODAY), CANT) == ["I1"]


def test_numbering():
    new = make().replace("PROMISE 2.", "PROMISE 3.")
    assert codes(lint(new, new, NOWHERE, TODAY), FAIL) == ["I2"]


def test_the_writer_cannot_check():
    new = make(seen1=seen(item("Zed", "2026-10-23")))
    assert codes(lint(new, new, NOWHERE, TODAY), FAIL) == ["I3"]


def test_dates():
    for status, date in (("Proposed by Zed.", "2026-10-16"),                     # the vote week: the dry run
                         ("Adopted on 2026-10-22 under rule 7.", "2026-10-22"),  # the day of adoption itself
                         ("Adopted on 2026-10-22 under rule 7.", "2026-12-01")):  # after today
        new = make(status=status, seen1=seen(item("Ann", date)))
        assert codes(lint(new, new, NOWHERE, TODAY), FAIL) == ["I4"], (status, date)
    early = make(seen2=seen(item("Bo", "2026-10-31", "KEPT", None)))             # BY is 2026-11-01
    assert codes(lint(early, early, NOWHERE, TODAY), FAIL) == ["I4"]
    on_time = make(seen2=seen(item("Bo", "2026-11-01", "KEPT", None)))
    assert not codes(lint(on_time, on_time, NOWHERE, TODAY), FAIL)
    undated = make(status="Adopted under rule 7.", seen1=seen(item("Ann", "2026-10-23")))
    assert codes(lint(undated, undated, NOWHERE, TODAY), CANT) == ["I4"]


def test_a_checked_entry_never_changes():
    wrong_if = "    WRONG IF  it is not there, or it moved; or it is gone.\n"
    prev = make(seen1=seen(item("Ann", "2026-10-23")))
    late = prev.replace(wrong_if, wrong_if + "    CHANGED   2026-10-24, before any check: it.\n")
    assert codes(lint(late, prev, NOWHERE, TODAY), FAIL) == ["I5"]               # added, and dated after the item
    backdated = prev.replace(wrong_if, wrong_if + "    CHANGED   2026-10-20, before any check: it.\n")
    assert codes(lint(backdated, prev, NOWHERE, TODAY), FAIL) == ["I5"]          # the date says before; the diff says after
    with tempfile.TemporaryDirectory() as d:                                     # an archived copy does not license it
        (Path(d) / "v0.txt").write_bytes(prev.encode())
        new = make(seen1=seen(item("Ann", "2026-10-23")), changes=archived(prev)).replace("One thing.", "Two things.")
        rows = lint(new, prev, Path(d), TODAY)
        assert codes(rows, FAIL) == ["I5"] and "line 15 changed" in row(rows, "I5"), rows


def test_unreadable_seen_item_is_left_to_a_person():
    new = make(seen1="    SEEN      Ann, 2026-10-23: saw it. HOLDS.")
    rows = lint(new, new, NOWHERE, TODAY)
    assert codes(rows, WARN) == ["I6"] and not codes(rows, FAIL)


def test_results_and_lines():
    for seen1, seen2 in ((seen(item("Ann", "2026-10-23", lines="4")), NOBODY),           # fact 1 has three lines
                         (seen(item("Ann", "2026-10-23", lines=None)), NOBODY),          # a fact's check names lines
                         (seen(item("Ann", "2026-10-23", "KEPT")), NOBODY),              # a fact's result is HOLDS
                         (NOBODY, seen(item("Bo", "2026-11-02", "KEPT", lines="1")))):   # a promise has no lines
        new = make(seen1=seen1, seen2=seen2)
        assert codes(lint(new, new, NOWHERE, TODAY), FAIL) == ["I7"], (seen1, seen2)


def test_unpaid_bond_then_a_new_promise():
    more = "\n  PROMISE 3. (Ann, 2026-11-20)\n    WILL      Another.\n    BY        2026-12-20\n    SEEN      nobody yet\n"
    new = make(seen2=seen(item("Bo", "2026-11-02", "BROKEN", None)) + "\n    UNPAID    2026-11-09: not burned.",
               more=more)
    rows = lint(new, new, NOWHERE, TODAY)
    assert codes(rows, CANT) == ["I8"] and "PROMISE 3" in row(rows, "I8") and not codes(rows, FAIL), rows
    assert row(lint(make(more=more), None, NOWHERE, TODAY), "I8").startswith("I8 nobody")


def test_archive_copies_must_match():
    prev = make()
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "v0.txt").write_bytes(b"something else\n")
        new = make(changes=archived(prev))
        assert codes(lint(new, new, Path(d), TODAY), FAIL) == ["I9"]
        assert codes(lint(new, new, NOWHERE, TODAY), FAIL) == ["I9"]


def test_an_unreadable_file_fails_without_a_crash():
    rows = lint(make().replace("STATUS", "STATE", 1), None, NOWHERE, TODAY)
    assert rows[0][0] == FAIL and "cannot read" in rows[0][1]


if __name__ == "__main__":
    for name, f in list(globals().items()):
        if name.startswith("test_"):
            f()
    print("ok")
