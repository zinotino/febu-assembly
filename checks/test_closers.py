"""closers.py on small ledgers with known answers, offline: python checks/test_closers.py (or pytest). Each control
changes one thing and names what must move; one runs on the real ledger."""
import contextlib
import io
import tempfile
from pathlib import Path

from closers import ROOT, main, report, tally

ADOPTED = "Adopted on 2026-10-22 under rule 7."
D1, D2 = "2026-10-24", "2026-10-25"
LEDGER = """TEST LEDGER (version 0)

STATUS
  {status}

WORDS USED HERE
  Member   Ann, Bo, Cy, Di, Zed. Adding a member works like a rule change.

THE ENTRIES
{entries}
  The next entry is number 9.
"""


def post(name, date, word="HOLDS", items=""):
    lines = " on line 1" if word in ("HOLDS", "DOESN'T HOLD") else ""
    return "- %s, %s: %s%s.%s Saw: it. New: a date. 3 minutes." % (
        name, date, word, lines, " Items: %s." % items if items else "")


def seen(posts):
    return "    SEEN      " + ("\n              ".join(posts) or "nobody yet")


def fact(num, who, *posts):
    return "\n  FACT %d. (%s, 2026-10-12)\n    SAYS      A thing.\n    WRONG IF  it is not there.\n%s\n" % (
        num, who, seen(posts))


def promise(num, who, *posts, withdrawn=None):
    return ("\n  PROMISE %d. (%s, 2026-10-12)\n    WILL      Do a thing.\n    BY        2026-11-20.\n"
            "    KNOWN BY  the file.\n    IF BROKEN none.\n%s%s\n"
            % (num, who, "    WITHDRAWN %s\n" % withdrawn if withdrawn else "", seen(posts)))


def ledger(*entries, status=ADOPTED):
    return LEDGER.format(status=status, entries="".join(entries))


F1 = fact(1, "Zed", post("Ann", D1), post("Bo", D2))
F4 = fact(4, "Bo", post("Cy", D1))                                          # one post: open


def base(other="Bo", last=post("Cy", D2)):
    """Three closes: Ann and Bo on facts 1 and 2 (both by Zed), Bo and `last` on fact 3 (by Ann); fact 4 (by Bo) open.
    On fact 2 `other` posts before Ann, so a pair is the same pair whoever posts first."""
    return ledger(F1, fact(2, "Zed", post(other, D1, "DOESN'T HOLD"), post("Ann", D2, "DOESN'T HOLD")),
                  fact(3, "Ann", post("Bo", D1), last), F4)


def run(argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = main(argv)
    return code, out.getvalue()


def on_file(text, test):
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "ledger.txt"
        p.write_bytes(text.encode("utf-8"))
        return test(str(p))


def test_known_answers():
    t = tally(base())
    assert [(r[0], r[1], r[2], r[3], r[4]) for r in t["rows"]] == [
        ("fact 1", "HOLDS", "Zed", ("Ann", "Bo"), D2),
        ("fact 2", "DOESN'T HOLD", "Zed", ("Ann", "Bo"), D2),
        ("fact 3", "HOLDS", "Ann", ("Bo", "Cy"), D2)], t["rows"]
    assert t["written"] == {"Zed": 2, "Ann": 1, "Bo": 1}
    assert t["closed"] == {"Zed": 2, "Ann": 1}
    assert t["closers"] == {"Bo": 3, "Ann": 2, "Cy": 1}
    assert t["pairs"] == {"Ann and Bo": 2, "Bo and Cy": 1}
    assert len(t["flags"]) == 2 and "Ann and Bo made 2 of the 3 closes (67%)" in t["flags"][0], t["flags"]
    assert "Zed wrote 2 of the 3 closed entries (67%)" in t["flags"][1], t["flags"]
    text = report(t, "ledger.txt", "0" * 64)
    for line in ("- fact 3, HOLDS: written by Ann, closed by Bo and Cy on 2026-10-25.",
                 "Entries written: Zed 2 (2 closed), Ann 1 (1 closed), Bo 1 (0 closed).",
                 "Closes per closer: Bo 3, Ann 2, Cy 1.",
                 "Closes per pair: Ann and Bo 2, Bo and Cy 1.",
                 "Busiest pair: Ann and Bo, 2 of the 3 closes (67%).",
                 "Busiest closer: Bo, one of the two on 3 of the 3 closes (100%)."):
        assert line in text.split("\n"), (line, text)


def test_moving_one_closer_moves_the_pair_count():
    """Fact 2's other closer is Cy, not Bo: three pairs of one, no pair at half, a three-way tie at the top."""
    t = tally(base(other="Cy"))
    assert t["pairs"] == {"Ann and Bo": 1, "Ann and Cy": 1, "Bo and Cy": 1}
    assert t["closers"] == {"Ann": 2, "Bo": 2, "Cy": 2}
    assert len(t["flags"]) == 1 and "Zed wrote" in t["flags"][0], t["flags"]
    assert "Busiest pair: Ann and Bo; Ann and Cy; Bo and Cy, 1 of the 3 closes (33%)." in report(t, "x", "0" * 64)


def test_a_sampled_holds_closes_nothing():
    """Fact 3's second HOLDS names a sample (Items: 20 of 164): it stays a SEEN line, and counts nowhere."""
    t = tally(base(last=post("Cy", D2, items="20 of 164")))
    assert [r[0] for r in t["rows"]] == ["fact 1", "fact 2"]
    assert t["closed"] == {"Zed": 2} and t["written"]["Ann"] == 1
    assert t["closers"] == {"Ann": 2, "Bo": 2} and "Cy" not in t["closers"]
    assert t["pairs"] == {"Ann and Bo": 2}
    t = tally(base(last=post("Cy", D2, items="all 164")))                    # the control: a full check closes
    assert [r[0] for r in t["rows"]] == ["fact 1", "fact 2", "fact 3"] and t["pairs"]["Bo and Cy"] == 1


def test_exactly_half_is_flagged():
    """Two closes by two pairs, of entries by two writers: each is at 1 of 2, and at least half means flagged."""
    t = tally(ledger(F1, fact(2, "Ann", post("Bo", D1), post("Cy", D2))))
    assert len(t["flags"]) == 4, t["flags"]
    for who in ("Ann and Bo made", "Bo and Cy made", "Ann wrote", "Zed wrote"):
        assert any(f.startswith("FLAG: %s 1 of the 2 " % who) and "(50%)" in f for f in t["flags"]), (who, t["flags"])


def test_a_withdrawn_promise_counts_nowhere():
    kept = (post("Ann", "2026-11-21", "KEPT"), post("Bo", "2026-11-22", "KEPT"))
    t = tally(ledger(F1, promise(2, "Cy", *kept)))                              # the control: it closes
    assert [r[0] for r in t["rows"]] == ["fact 1", "promise 2"] and t["written"]["Cy"] == 1
    t = tally(ledger(F1, promise(2, "Cy", *kept, withdrawn="2026-11-01")))      # withdrawn in time
    assert [r[0] for r in t["rows"]] == ["fact 1"] and "Cy" not in t["written"]
    assert t["pairs"] == {"Ann and Bo": 1}
    t = tally(ledger(F1, promise(2, "Cy", *kept, withdrawn="2026-11-18")))      # too late: BROKEN, but no close
    assert [r[0] for r in t["rows"]] == ["fact 1"] and t["written"]["Cy"] == 1 and t["closed"]["Cy"] == 0


def test_exit_codes():
    code, out = on_file(base(), lambda p: run([p]))
    assert code == 0 and "Closed under rule 3: 3 entries." in out, out
    code, out = on_file(base().replace(ADOPTED, "Proposed by Zed on 2026-10-14."), lambda p: run([p]))
    assert code == 2 and "Nothing has closed under rule 3 yet." in out and "Busiest" not in out, out
    code, out = on_file("TEST LEDGER\n\nNO STATUS\n  here\n", lambda p: run([p]))
    assert code == 1 and "cannot be read" in out, out
    assert run([str(ROOT / "no-such-ledger.txt")])[0] == 1


def test_real_ledger():
    code, out = run([str(ROOT / "ledger.txt")])
    assert code in (0, 2) and out.startswith("Who closed what: ledger.txt "), out
    for e, _, writer, by, _ in tally((ROOT / "ledger.txt").read_bytes().replace(b"\r\n", b"\n").decode())["rows"]:
        assert len(set(by)) == 2 and writer not in by, (e, writer, by)


if __name__ == "__main__":
    for name in sorted(n for n in dir() if n.startswith("test_")):
        globals()[name]()
        print("ok", name)
