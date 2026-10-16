"""lint.py's rules, offline: python checks/test_lint.py (or pytest). Each test changes one thing in a small ledger and
names the one rule that must catch it; two run on the real ledger and its archive."""
import re
import tempfile
from pathlib import Path

from lint import CANT, FAIL, ROOT, WARN, keeps, lint, read, sha256

TODAY = "2026-11-30"
NOWHERE = Path(__file__).parent / "no-such-archive"
NOBODY = "    SEEN      nobody yet"
WRONG_IF = "    WRONG IF  it is not there, or it moved; or it is gone.\n"
BASE = """TEST LEDGER (version 0)

STATUS
  {status}

WORDS USED HERE
  Member   Ann, Bo, Cy, Zed. Adding a member works like a rule change.

THE RULES
  1. The list holds promises and facts.
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
  The next entry is number {next}.

CHANGES TO THE RULES
  2026-10-15. Clean start.{changes}
"""
THIRD = "\n  FACT 3. (Bo, 2026-10-24)\n    SAYS      A third thing.\n    WRONG IF  it is not.\n    SEEN      nobody yet\n"


def make(status="Adopted on 2026-10-22 under rule 7.", seen1=NOBODY, seen2=NOBODY, more="", changes="", next=None):
    return BASE.format(status=status, seen1=seen1, seen2=seen2, more=more, changes=changes,
                       next=next or 3 + more.count("\n  FACT ") + more.count("\n  PROMISE "))


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


def with_archive(prev, test):
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "v0.txt").write_bytes(prev.encode())
        return test(Path(d))


def test_real_ledger_and_its_archive():
    real = read((ROOT / "ledger.txt").read_bytes())
    for prev in [real] + [read(p.read_bytes()) for p in sorted((ROOT / "archive").glob("*.txt"))]:
        rows = lint(real, prev, ROOT / "archive", TODAY)
        assert not codes(rows, FAIL) and not codes(rows, CANT), rows


def test_adoption_turn_rehearsed_on_the_real_ledger():
    """AFTER_VOTE_20261022.md in small: STATUS rewritten and the voted text archived; fact 1's LINK changed with its
    CHANGED line, then its first checks; two checks of fact 3; a new fact 10, and the next number raised."""
    real = read((ROOT / "ledger.txt").read_bytes())
    new = re.sub(r"(?m)^STATUS\n(?:  .*\n)+", "STATUS\n  Adopted on 2026-10-22 under rule 7. Posts made before "
                 "2026-10-23 were the dry run.\n", real, count=1)
    head, f1 = new.split("  FACT 1.", 1)
    f1, tail = f1.split("  FACT 2.", 1)
    f1 = re.sub(r"(?m)^(    LINK      ).*$", r"\1https://solscan.io/account/6PeGko4hvJn8EioYxKera24TrKMfkGUVM7egzrRwNVTo",
                f1, count=1)
    f1 = f1.replace(NOBODY, "    CHANGED   2026-10-23, before any check: the LINK names the $FEBU account.\n" +
                    seen(item("Laura", "2026-10-23"), item("Merc", "2026-10-25")), 1)
    head3, f3 = tail.split("  FACT 3.", 1)
    f3 = f3.replace(NOBODY, seen(item("Laura", "2026-10-23", lines="1, 2"), item("Ksizzle", "2026-10-24", lines="1, 2")), 1)
    new = head + "  FACT 1." + f1 + "  FACT 2." + head3 + "  FACT 3." + f3
    new = new.replace("  The next entry is number 10.", "  FACT 10. (Laura, 2026-10-24)\n    SAYS      A new thing.\n"
                      "    LINK      https://example.org\n    WRONG IF  it is not there.\n    SEEN      nobody yet\n\n"
                      "  The next entry is number 11.")
    new = new.rstrip("\n") + archived(real, "08_CLAIMS_LEDGER_v3-voted.txt") + "\n"
    with tempfile.TemporaryDirectory() as d:
        arch = Path(d)
        for p in (ROOT / "archive").glob("*.txt"):
            (arch / p.name).write_bytes(p.read_bytes())
        (arch / "08_CLAIMS_LEDGER_v3-voted.txt").write_bytes(real.encode())
        rows = lint(new, real, arch, TODAY)
        assert not codes(rows, FAIL) and not codes(rows, WARN), rows
        assert "2 first SEEN items" in row(rows, "I1") and "next is 11" in row(rows, "I2")
        (arch / "08_CLAIMS_LEDGER_v3-voted.txt").unlink()
        assert codes(lint(new, real, arch, TODAY), FAIL) == ["I1", "I9"]


def test_a_rewrite_needs_the_earlier_version_archived_and_a_changed_line():
    prev = make()
    reworded = prev.replace("One thing.", "One other thing.")
    assert codes(lint(reworded, prev, NOWHERE, TODAY), FAIL) == ["I1", "I5"]

    def archived_only(arch):
        return codes(lint(make(changes=archived(prev)).replace("One thing.", "One other thing."), prev, arch, TODAY), FAIL)
    assert with_archive(prev, archived_only) == ["I5"]                            # no CHANGED line

    def both(arch):
        new = make(changes=archived(prev)).replace("One thing.", "One other thing.").replace(
            WRONG_IF, WRONG_IF + "    CHANGED   2026-10-23, before any check: reworded.\n")
        rows = lint(new, prev, arch, TODAY)
        return not codes(rows, FAIL) and "keeps it as archive/v0.txt" in row(rows, "I1")
    assert with_archive(prev, both)


def test_rule_text_gains_lines_only_in_changes_to_the_rules():
    prev = make()
    assert codes(lint(prev.replace("rewritten.\n", "rewritten.\n     Except by Zed.\n"), prev, NOWHERE, TODAY), FAIL) == ["I1"]
    assert not codes(lint(make(changes="\n  2026-10-30. A dated line."), prev, NOWHERE, TODAY), FAIL)


def test_removed_keeps_the_rest_of_its_line():
    prev = make(status="Adopted on 2026-10-22 under rule 7. Ann's phone is 555 0100.")
    rows = lint(prev.replace("555 0100", "[removed]"), prev, NOWHERE, TODAY)
    assert not codes(rows, FAIL) and "1 [removed]" in row(rows, "I1")
    rules = prev.replace("  1. The list holds promises and facts.\n  2. Nothing is removed or rewritten.\n", "  [removed]\n")
    assert codes(lint(rules, prev, NOWHERE, TODAY), FAIL) == ["I1"]                # a [removed] cannot stand for lines
    says = prev.replace("    SAYS      One thing.", "    SAYS      [removed]")
    assert "I1" in codes(lint(says, prev, NOWHERE, TODAY), FAIL)                   # nor for a whole field
    assert not keeps("[removed]", "anything") and keeps("a [removed] c", "a b c") and not keeps("a [removed] c", "a  c")


def test_removed_cannot_erase_a_check():
    prev = make(seen1=seen(item("Ann", "2026-10-23"), item("Bo", "2026-10-24")))
    wiped = make(seen1="    SEEN      [removed]\n              [removed]")
    assert "I5" in codes(lint(wiped, prev, NOWHERE, TODAY), FAIL)


def test_the_first_seen_item_replaces_nobody_yet():
    prev = make()
    for seen1 in (seen(item("Ann", "2026-10-23"), item("Bo", "2026-10-24")),
                  "    SEEN\n              " + item("Ann", "2026-10-23")):            # the label alone on its line
        rows = lint(make(seen1=seen1), prev, NOWHERE, TODAY)
        assert not codes(rows, FAIL) and not codes(rows, WARN), rows
        assert "1 first SEEN item," in row(rows, "I1")


def test_more_seen_items_on_a_checked_entry():
    prev = make(seen1=seen(item("Ann", "2026-10-23")))
    assert not codes(lint(make(seen1=seen(item("Ann", "2026-10-23"), item("Bo", "2026-10-24"))), prev, NOWHERE, TODAY),
                     FAIL)


def test_no_earlier_version_cannot_tell():
    assert codes(lint(make(), None, NOWHERE, TODAY), CANT) == ["I1"]


def test_numbering_and_the_next_number():
    new = make().replace("PROMISE 2.", "PROMISE 3.").replace("number 3.", "number 4.")
    assert codes(lint(new, new, NOWHERE, TODAY), FAIL) == ["I2"]
    stale = make(more=THIRD, next=3)                                               # an entry added, the number not raised
    assert codes(lint(stale, make(), NOWHERE, TODAY), FAIL) == ["I2"]
    rows = lint(make(more=THIRD), make(), NOWHERE, TODAY)                          # added and raised: nothing rewritten
    assert not codes(rows, FAIL) and "only grew" in row(rows, "I1")


def test_the_writer_cannot_check():
    for name in ("Zed", "zed"):
        new = make(seen1=seen(item(name, "2026-10-23")))
        assert codes(lint(new, new, NOWHERE, TODAY), FAIL) == ["I3"], name


def test_dates():
    for status, date in (("Proposed by Zed.", "2026-10-16"),                     # the vote week: the dry run
                         ("Adopted on 2026-10-22 under rule 7.", "2026-11-00"),  # no such day: state() skips it
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
    for status in ("Adopted on 2026-13-45 under rule 7.", "Adopted on 9999-12-31 under rule 7."):   # no crash
        odd = make(status=status, seen2=seen(item("Bo", "2026-11-01", "KEPT", None)))
        assert "I4" in codes(lint(odd, odd, NOWHERE, TODAY), FAIL) + codes(lint(odd, odd, NOWHERE, TODAY), CANT)


def test_a_checked_entry_never_changes():
    prev = make(seen1=seen(item("Ann", "2026-10-23")))
    late = prev.replace(WRONG_IF, WRONG_IF + "    CHANGED   2026-10-24, before any check: it.\n")
    assert codes(lint(late, prev, NOWHERE, TODAY), FAIL) == ["I5"]               # added, and dated after the item
    backdated = prev.replace(WRONG_IF, WRONG_IF + "    CHANGED   2026-10-20, before any check: it.\n")
    assert codes(lint(backdated, prev, NOWHERE, TODAY), FAIL) == ["I5"]          # the date says before; the file says after
    widened = prev.replace(WRONG_IF, WRONG_IF + "              ; or it was never there.\n")
    assert "I5" in codes(lint(widened, prev, NOWHERE, TODAY), FAIL)              # a line slipped into WRONG IF

    def rewritten(arch):                                                         # an archived copy does not license it
        new = make(seen1=seen(item("Ann", "2026-10-23")), changes=archived(prev)).replace("One thing.", "Two things.")
        rows = lint(new, prev, arch, TODAY)
        return codes(rows, FAIL) == ["I5"] and "its SAYS changed" in row(rows, "I5")
    assert with_archive(prev, rewritten)

    both = make(seen1=seen(item("Ann", "2026-10-23")), seen2=seen(item("Bo", "2026-11-01", "KEPT", None)))

    def gone(arch):                                                              # nor does it license deleting it
        new = make(seen1=seen(item("Ann", "2026-10-23")), changes=archived(both))
        new = new.replace(new[new.index("  PROMISE 2."):new.index("\n\n  The next")], "").replace("number 3.", "number 2.")
        rows = lint(new, both, arch, TODAY)
        return codes(rows, FAIL) == ["I5"] and "PROMISE 2 had a SEEN item" in row(rows, "I5")
    assert with_archive(both, gone)


def test_changed_after_the_first_check_in_one_version():
    new = make(seen1=seen(item("Ann", "2026-10-23"))).replace(
        WRONG_IF, WRONG_IF + "    CHANGED   2026-10-25, before any check: reworded.\n")
    assert codes(lint(new, None, NOWHERE, TODAY), FAIL) == ["I5"]


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


def test_archive_copies_must_be_there_and_match():
    prev = make()
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "v0.txt").write_bytes(b"something else\n")
        new = make(changes=archived(prev))
        assert codes(lint(new, new, Path(d), TODAY), FAIL) == ["I9"]
        assert codes(lint(new, new, NOWHERE, TODAY), FAIL) == ["I9"]
    loose = make(status="Adopted on 2026-10-22 under rule 7. See archive/gone.txt.")   # named anywhere, no hash
    assert codes(lint(loose, loose, NOWHERE, TODAY), FAIL) == ["I9"]


def test_an_unreadable_file_fails_without_a_crash():
    for bad in (make().replace("STATUS", "STATE", 1),
                make(seen1=seen(item("Ann", "2026-10-23", lines="1" * 5000)))):
        rows = lint(bad, None, NOWHERE, TODAY)
        assert rows[0][0] == FAIL and "cannot read" in rows[0][1], rows


def test_slow_removed_patterns_stay_fast():
    import time
    t = time.time()
    keeps(" ".join(["[removed]"] * 12), " " * 400)
    assert time.time() - t < 0.5


if __name__ == "__main__":
    for name, f in list(globals().items()):
        if name.startswith("test_"):
            f()
    print("ok")
