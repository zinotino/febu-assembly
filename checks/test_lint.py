"""lint.py's rules, offline: python checks/test_lint.py (or pytest). Each test changes one thing in the worked version-5
ledger (checks/fixtures/ledger_v5_worked.txt) and names the one rule that must catch it; one runs the day of adoption,
the frozen version-5 text against version 3's archive copy."""
import shutil
import tempfile
from pathlib import Path

from lint import CANT, FAIL, OK, ROOT, WARN, keeps, lint, read, sha256

FIXTURES = ROOT / "checks" / "fixtures"
ARCHIVE = ROOT / "archive"
FROZEN = read((FIXTURES / "ledger_v5.txt").read_bytes())
WORKED = read((FIXTURES / "ledger_v5_worked.txt").read_bytes())
V3 = read((ARCHIVE / "08_CLAIMS_LEDGER_v3.txt").read_bytes())
TODAY = "2026-11-08"
NOWHERE = Path(__file__).parent / "no-such-archive"


def swap(text, old, new=""):
    assert text.count(old) == 1, old
    return text.replace(old, new)


# The worked ledger a week earlier: before Q2's second answer, Ksizzle's SEEN item under its first, Crypto Fish's
# vote and the first LAST POSTS line.
ANSWER2 = WORKED[WORKED.index("    ANSWER 2.   (CrypticK"):WORKED.index("  The next question is Q3.")]
KSIZZLE = ('                - Ksizzle, 2026-11-07: HOLDS on lines 1, 2. Items: line 1, all 24; line 2, all\n'
           '                  1. Saw: "mockery" is not "mock". New: page 25 is in verse.\n')
VOTE = "    - Crypto Fish, 2026-11-08: YES.\n"
LAST = WORKED[WORKED.index("  - 2026-11-08: CrypticK"):WORKED.index("\nWHEN THIS HAS FAILED")]
EARLIER = swap(swap(swap(swap(WORKED, ANSWER2), KSIZZLE), VOTE), LAST, "  None yet.\n")


def codes(rows, status):
    return sorted({what.split()[0] for s, what in rows if s == status})


def row(rows, code):
    return next(what for _, what in rows if what.startswith(code + " "))


def run(new, prev=None, archive=ARCHIVE, today=TODAY):
    return lint(new, prev, archive, today)


def with_archive(prev, new):
    """new with a CHANGES TO THE RULES line that keeps prev as archive/v0.txt, linted against prev."""
    line = "\n  2026-11-08. A change. The text before it is kept word for word in\n  archive/v0.txt SHA-256\n  %s" % sha256(prev)
    with tempfile.TemporaryDirectory() as d:
        for f in ARCHIVE.glob("*.txt"):
            shutil.copy(f, d)
        (Path(d) / "v0.txt").write_bytes(prev.encode())
        return run(new.rstrip("\n") + line + "\n", prev, Path(d))


def test_the_fixture_is_the_frozen_text():
    assert sha256(FROZEN) == "6108f6e3140759b80f30b52c54c7214ea6641bb7423bb4fefd05e896141fd0a4"
    assert sha256(V3) == "d3e1765863039f24a8c38ddcdd72f1034cb0252b1302d2214e154eef002984f7"


def test_adoption_day_the_frozen_text_replaces_version_3():
    rows = run(FROZEN, V3, today="2026-10-30")
    assert not codes(rows, FAIL) and not codes(rows, CANT) and not codes(rows, WARN), rows
    assert "archive/08_CLAIMS_LEDGER_v3.txt" in row(rows, "I1") and "replaces it" in row(rows, "I1")


def test_adoption_day_needs_version_3_kept():
    with tempfile.TemporaryDirectory() as d:
        for f in ARCHIVE.glob("*.txt"):
            if f.name != "08_CLAIMS_LEDGER_v3.txt":
                shutil.copy(f, d)
        rows = run(FROZEN, V3, Path(d), "2026-10-30")
    assert codes(rows, FAIL) == ["I9"] and codes(rows, CANT) == ["I1"]


def test_a_week_of_growth_passes():
    rows = run(WORKED, EARLIER)
    assert not codes(rows, FAIL) and not codes(rows, CANT), rows
    assert "only grew" in row(rows, "I1")
    assert codes(rows, WARN) == ["I3"] and "Zurandol's script" in row(rows, "I3")   # Ksizzle ran a poster's script


def test_the_worked_ledger_against_itself():
    rows = run(WORKED, WORKED)
    assert not codes(rows, FAIL) and not codes(rows, CANT), rows
    assert "3 proposal(s), 2 question(s)" in row(rows, "I2")


def test_the_first_seen_item_replaces_nobody_yet():
    first = swap(WORKED, "      SEEN      nobody yet", "      SEEN      - Merc, 2026-11-08: HOLDS on lines 1, 2. "
                 "Items: all 1. Saw: 40 pages.\n                  New: page 30.")
    rows = run(first, WORKED)
    assert not codes(rows, FAIL) and "1 first SEEN item," in row(rows, "I1")


def test_rewrites_fail_unless_the_earlier_text_is_archived():
    for old, new in (("Adopted on 2026-10-30, in place", "Adopted on 2026-10-29, in place"),           # STATUS
                     ("    - Merc, 2026-11-02: YES.", "    - Merc, 2026-11-02: OBJECT."),             # a vote
                     ("Merc 2026-10-29, Ksizzle", "Ksizzle"),                                          # a yes
                     ("P3. Ksizzle, 2026-11-01: In the scripture", "P3. Ksizzle, 2026-11-01: In the copy"),
                     ("Ksizzle 2026-11-07, Laura", "Ksizzle 2026-11-06, Laura"),                       # LAST POSTS
                     ("in one public place outside", "in two public places outside"),                 # a rule
                     ("    ASKS        In the scripture", "    ASKS        In the copy"),                # a question
                     ("       Opened as Q1.\n", "")):                                                  # an opening
        changed = swap(WORKED, old, new)
        rows = run(changed, WORKED)
        assert "I1" in codes(rows, FAIL), (old, rows)
        rows = with_archive(WORKED, changed)
        assert "I1" not in codes(rows, FAIL) and "keeps it as archive/v0.txt" in row(rows, "I1"), (old, rows)


def test_lines_may_be_added_where_the_file_grows():
    for old, new in (("  The next proposal is P4.", "  P4. Laura, 2026-11-08: Did it?\n  The next proposal is P5."),
                     (VOTE, VOTE + "    - Laura, 2026-11-08: YES.\n"),
                     ("  2026-10-30. Version 5.", "  2026-11-08. A dated line.\n  2026-10-30. Version 5.")):
        rows = run(swap(WORKED, old, new), WORKED)
        assert not codes(rows, FAIL), (old, rows)
    rows = run(swap(WORKED, "  Member   CrypticK", "  Member   Ann, CrypticK"), WORKED)
    assert "I1" in codes(rows, FAIL)                                                 # but not in the rules


def test_removed_keeps_the_rest_of_its_line():
    for old, new in (("23,843,803.61 tokens, in one", "[removed] tokens, in one"),            # a checked answer's SAYS
                     ('"mockery" on page 9. New: page 9 is the longest.',                     # a SEEN item past Saw:
                      '"mockery" on [removed]. New: page 9 is the longest.'),
                     ("change my mind: a week with two", "change my mind: [removed] with two")):   # an objection
        rows = run(swap(WORKED, old, new), WORKED)
        assert not codes(rows, FAIL), (new, rows)
    assert "1 [removed]" in row(run(swap(WORKED, "change my mind: a week", "change my mind: [removed]"), WORKED), "I1")
    for old, new in (("(Laura, 2026-10-31, version 3's fact 2)", "([removed], 2026-10-31, version 3's fact 2)"),
                     ("- CrypticK, 2026-11-05: HOLDS", "- [removed], 2026-11-05: HOLDS"),   # who closed it
                     ("      CHANGED   Laura, 2026-11-05:", "      CHANGED   [removed], 2026-11-05:"),
                     ("  P1. Laura, 2026-10-24:", "  P1. [removed], 2026-10-24:"),
                     ("Yes: Merc 2026-10-29,", "Yes: [removed] 2026-10-29,"),
                     ("    - Merc, 2026-11-02: YES.", "    - [removed], 2026-11-02: YES."),
                     ("three members other than its posters", "three members [removed] its posters"),   # a rule
                     ("in place of version 3, which", "in place of [removed], which")):                  # STATUS
        rows = run(swap(WORKED, old, new), WORKED)
        assert "I1" in codes(rows, FAIL), (new, rows)   # rule 4 counts by names and dates; the rules are no one's
    rows = run(swap(WORKED, "      SAYS      In the copy Z saved, none of the words jest, hollow, false, mock, laugh,\n"
                    "                theater, spectacle or debt is on scripture pages 1-24, and jest and hollow\n"
                    "                are both on page 25.\n", "      SAYS      [removed]\n"), WORKED)
    assert "I5" in codes(rows, FAIL)                                                 # not a whole field
    assert not keeps("[removed]", "anything") and keeps("a [removed] c", "a b c") and not keeps("a [removed] c", "a  c")


def test_a_checked_answer_never_changes():
    for old, new in (("are both on page 25.", "are both on page 26."),                              # its SAYS
                     ("                it through 2026-10-14.\n",                                    # a note set off
                      "                it through 2026-10-14.   (withdrawn: it bought again)\n"),
                     ('"mockery" on page 9. New: page 9 is the longest.', '"mockery" on page 8. New: x.'),  # a SEEN item
                     (KSIZZLE, "")):                                                                 # one is gone
        rows = run(swap(WORKED, old, new), WORKED)
        assert "I5" in codes(rows, FAIL), (old, rows)
    late = swap(WORKED, "      CHANGED   Laura, 2026-11-05: WRONG IF now names page 25.\n",
                "      CHANGED   Laura, 2026-11-05: WRONG IF now names page 25.\n"
                "      CHANGED   Laura, 2026-11-08: a second change.\n")
    assert "I5" in codes(run(late, WORKED), FAIL)


def test_an_unchecked_answer_changes_with_a_changed_line():
    says = swap(WORKED, "and laugh each appear on at least 40", "and laugh each appear on at least 30")
    assert "I5" in codes(run(says, WORKED), FAIL)
    said = swap(says, "      SEEN      nobody yet", "      CHANGED   Laura, 2026-11-08: 40 was 30.\n      SEEN      nobody yet")
    assert codes(run(said, WORKED), FAIL) == ["I1"]                    # a rewrite: the earlier text must be kept too
    assert not codes(with_archive(WORKED, said), FAIL)


def test_changed_lines_name_who_and_when():
    rows = run(swap(WORKED, "CHANGED   Laura, 2026-11-05:", "CHANGED   2026-11-05:"))
    assert codes(rows, FAIL) == ["I5"] and "Name, YYYY-MM-DD" in row(rows, "I5")
    rows = run(swap(WORKED, "CHANGED   Laura, 2026-11-05:", "CHANGED   Laura, 2026-11-07:"))
    assert codes(rows, FAIL) == ["I5"] and "after its first SEEN item" in row(rows, "I5")


def test_numbering():
    for old, new in (("  The next proposal is P4.", "  The next proposal is P5."),
                     ("  The next question is Q3.", "  The next question is Q4."),
                     ("    ANSWER 2.   (CrypticK", "    ANSWER 3.   (CrypticK"),
                     ("  Q2. (opened 2026-11-05, from P3)", "  Q3. (opened 2026-11-05, from P3)"),
                     ("       Opened as Q2.\n", ""),
                     ("  Q2. (opened 2026-11-05, from P3)", "  Q2. (opened 2026-11-05)")):
        rows = run(swap(WORKED, old, new))
        assert "I2" in codes(rows, FAIL), (old, rows)


def test_rule_2_opens_on_the_day_of_the_third_yes():
    late = swap(WORKED, "  Q2. (opened 2026-11-05, from P3)", "  Q2. (opened 2026-11-06, from P3)")
    rows = run(late)
    assert "I2" in codes(rows, FAIL) and "rule 2 opens P3 on 2026-11-05" in row(rows, "I2")
    for old, new in (("Laura 2026-11-03, Crypto Fish 2026-11-03.", "Laura 2026-11-03, Crypto Fish 2026-11-06."),):
        assert "I2" in codes(run(swap(WORKED, old, new)), FAIL)                      # the file's 11-05 is now early
        assert not codes(run(swap(late, old, new)), FAIL)                            # and 11-06 is right
    wrong = swap(swap(WORKED, "from P3)", "from P2)"), "       Opened as Q2.\n", "")
    wrong = swap(wrong, "       Yes: Laura 2026-11-01, CrypticK 2026-11-02.\n",
                 "       Yes: Laura 2026-11-01, CrypticK 2026-11-02.\n       Opened as Q2.\n")
    assert "rule 2 opens P3 on 2026-11-05" in row(run(wrong), "I2")                  # P2 never had three yeses


def test_an_opening_the_file_lacks_is_flagged():
    q2 = WORKED[WORKED.index("\n  Q2. (opened"):WORKED.index("  The next question is Q3.")]
    lacks = swap(swap(swap(WORKED, q2, "\n"), "       Opened as Q2.\n"), "The next question is Q3.", "The next question is Q2.")
    rows = run(lacks)
    assert not codes(rows, FAIL), rows
    assert codes(rows, WARN) == ["I2", "I3"] and "rule 2 opens P3 as Q2 on 2026-11-05" in row(rows, "I2")


def test_nothing_opens_before_adoption():
    proposed = swap(WORKED, "  Adopted on 2026-10-30,", "  Proposed on 2026-10-30,")
    rows = run(proposed)
    assert codes(rows, FAIL) == ["I2", "I4"], rows


def test_a_posters_result_counts_for_nothing():
    rows = run(swap(WORKED, "- Crypto Fish, 2026-11-06: HOLDS", "- Merc, 2026-11-06: HOLDS"))
    assert "I3" in codes(rows, WARN) and "Merc's SEEN item of 2026-11-06 is by one of its posters" in "".join(
        w for _, w in rows)
    rows = run(swap(WORKED, "checks/resolve.py fact2 by Ksizzle via laptop", "checks/resolve.py fact2 by Laura via laptop"))
    assert "Laura's script" in "".join(w for _, w in rows)


def test_dates():
    rows = run(swap(WORKED, "- Ksizzle, 2026-11-02: HOLDS", "- Ksizzle, 2026-10-30: HOLDS"))   # one that closed nothing
    assert codes(rows, FAIL) == ["I4"] and "dated before 2026-10-31" in row(rows, "I4")
    rows = run(swap(WORKED, "- Merc, 2026-11-01: HOLDS", "- Merc, 2026-10-30: HOLDS"))
    assert codes(rows, FAIL) == ["I2", "I4"]                       # one that did: Q1 stays open, so Q2 cannot open
    rows = run(swap(WORKED, "- Crypto Fish, 2026-11-06: HOLDS", "- Crypto Fish, 2026-11-31: HOLDS"))
    assert "I4" in codes(rows, FAIL) and "not a date on the calendar" in row(rows, "I4")
    rows = run(WORKED, today="2026-11-07")
    said = "".join(w for _, w in rows)
    assert codes(rows, FAIL) == ["I4"] and "Crypto Fish's vote is dated 2026-11-08, after today" in said
    assert "LAST POSTS: the line is dated 2026-11-08" in said and "Q2 answer 2: its header is dated 2026-11-08" in said
    assert not codes(run(WORKED, today="2026-11-08"), FAIL)                         # the control: the file's own last day
    late = swap(WORKED, "  - 2026-11-08: CrypticK 2026-11-08,", "  - 2027-06-01: CrypticK 2026-11-08,")
    assert "LAST POSTS: the line is dated 2027-06-01" in row(run(late), "I4")      # it would make Q2 CAN'T TELL
    for old, new in (("  P1. Laura, 2026-10-24:", "  P1. Laura, 2026-10-34:"),
                     ("posted 2026-11-01, SHA-256", "posted 2026-02-30, SHA-256")):
        assert "is not a date on the calendar" in row(run(swap(WORKED, old, new)), "I4"), new
    no_day = swap(WORKED, "  Adopted on 2026-10-30,", "  Taken up on 2026-10-30,")
    assert "I4" in codes(run(no_day), CANT)


def test_unreadable_items_are_left_to_a_person():
    rows = run(swap(WORKED, "                - Zurandol, 2026-11-06: DOESN'T HOLD on line 1. Items: line 1, all 24. Saw:",
                    "                - Zurandol said it does not hold. Items: line 1, all 24. Saw:"))
    assert codes(rows, WARN) == ["I3", "I6"] and not codes(rows, FAIL)
    rows = run(swap(WORKED, "Yes: Laura 2026-11-01, CrypticK", "Yes: Laura said yes, CrypticK"))
    assert "I6" in codes(rows, WARN) and "Laura said yes" in row(rows, "I6")


def test_results_and_lines():
    for old, new in (("- Crypto Fish, 2026-11-06: HOLDS on lines 1, 2.", "- Crypto Fish, 2026-11-06: KEPT on lines 1, 2."),
                     ("- Zurandol, 2026-11-06: DOESN'T HOLD on line 1.", "- Zurandol, 2026-11-06: DOESN'T HOLD on line 3."),
                     ("- Zurandol, 2026-11-06: DOESN'T HOLD on line 1.", "- Zurandol, 2026-11-06: DOESN'T HOLD.")):
        assert "I7" in codes(run(swap(WORKED, old, new)), FAIL), old


def test_archive_copies_must_be_there_and_match():
    rows = run(WORKED, WORKED, NOWHERE)
    assert "I9" in codes(rows, FAIL)
    with tempfile.TemporaryDirectory() as d:
        for f in ARCHIVE.glob("*.txt"):
            shutil.copy(f, d)
        (Path(d) / "08_CLAIMS_LEDGER_v3.txt").write_bytes(b"something else\n")
        rows = run(WORKED, WORKED, Path(d))
    assert codes(rows, FAIL) == ["I9"]


def test_no_earlier_version_cannot_tell():
    rows = run(WORKED)
    assert codes(rows, CANT) == ["I1"] and not codes(rows, FAIL)


def test_an_unreadable_file_fails_without_a_crash():
    for bad in (WORKED.replace("STATUS", "STATE", 1), WORKED.replace("THE QUESTIONS\n", "QUESTIONS\n", 1),
                swap(WORKED, "version 3's fact 5)\n", "version 3's fact 5)\n     stray\n")):
        rows = run(bad)
        assert rows[0][0] == FAIL and "cannot read" in rows[0][1], rows
    rows = run(WORKED, V3)                                                          # version 3, not archived as such
    assert codes(rows, OK) and "I1" in codes(rows, OK)                             # it is: v5 names it


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
