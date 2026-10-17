"""closers.py, offline: python checks/test_closers.py (or pytest). Known answers on the worked version-5 ledger
(checks/fixtures/ledger_v5_worked.txt), each with a one-change control."""
import contextlib
import io
import tempfile
from pathlib import Path

from closers import ROOT, main, report, tally

FIXTURES = ROOT / "checks" / "fixtures"
WORKED = (FIXTURES / "ledger_v5_worked.txt").read_bytes().replace(b"\r\n", b"\n").decode("utf-8")
FROZEN = (FIXTURES / "ledger_v5.txt").read_bytes().replace(b"\r\n", b"\n").decode("utf-8")
Q1 = ("Q1 answer 1", "HOLDS", ("Laura", "Zurandol"), ("CrypticK", "Merc", "WitnesstoFebu"), "2026-11-05")
# Q2's copied answer closed by three more members on 2026-11-08: two closes by two sets, Zurandol a poster on both
CLOSE2 = WORKED.replace("      SEEN      nobody yet\n",
                        "      SEEN      - Merc, 2026-11-08: HOLDS on lines 1, 2. Items: all 1. Saw: x. New: y.\n"
                        "                - Ksizzle, 2026-11-08: HOLDS on lines 1, 2. Items: all 1. Saw: x. New: y.\n"
                        "                - Laura, 2026-11-08: HOLDS on lines 1, 2. Items: all 1. Saw: x. New: y.\n")


def swap(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new)


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
    t = tally(WORKED)
    assert t["rows"] == [Q1], t["rows"]
    assert t["posted"] == {"Laura": 2, "Zurandol": 2, "Merc": 1, "CrypticK": 1}   # Laura changed Q2's first answer
    assert t["closed"] == {"Laura": 1, "Zurandol": 1}
    assert t["closers"] == {"CrypticK": 1, "Merc": 1, "WitnesstoFebu": 1}
    text = report(t, "ledger.txt", "0" * 64)
    for line in ("- Q1 answer 1, HOLDS: posted by Laura and Zurandol, closed by CrypticK, Merc and WitnesstoFebu on "
                 "2026-11-05.",
                 "Closes per set of closers: CrypticK, Merc, WitnesstoFebu 1.",
                 "Busiest set: CrypticK, Merc, WitnesstoFebu, 1 of the 1 closes (100%)."):
        assert line in text.split("\n"), (line, text)


def test_moving_one_closer_moves_the_set():
    """CrypticK's full check on 2026-11-05 is Crypto Fish's instead: a different set closes, on the same day."""
    t = tally(swap(WORKED, "- CrypticK, 2026-11-05: HOLDS", "- Crypto Fish, 2026-11-05: HOLDS"))
    assert t["rows"] == [Q1[:3] + (("Crypto Fish", "Merc", "WitnesstoFebu"), "2026-11-05")], t["rows"]


def test_a_sampled_holds_closes_nothing():
    """CrypticK's second check names a sample: it stays a SEEN item, and nothing closes."""
    sample = swap(WORKED, "- CrypticK, 2026-11-05: HOLDS on lines 1, 2, 3. Items: all 1.",
                  "- CrypticK, 2026-11-05: HOLDS on lines 1, 2, 3. Items: line 1, all 1; line 2, all 1; line 3, 20 of 164.")
    assert tally(sample)["rows"] == []
    full = swap(WORKED, "- CrypticK, 2026-11-05: HOLDS on lines 1, 2, 3. Items: all 1.",
                "- CrypticK, 2026-11-05: HOLDS on lines 1, 2, 3. Items: line 1, all 1; line 2, all 1; line 3, all 164.")
    assert tally(full)["rows"] == [Q1]                                       # the control: every item closes it


def test_exactly_half_is_flagged():
    """Two closes by two sets: each set is at 1 of 2, and at least half means flagged; Zurandol is a poster on both."""
    t = tally(CLOSE2)
    assert [r[0] for r in t["rows"]] == ["Q1 answer 1", "Q2 answer 2"], t["rows"]
    assert t["rows"][1][2:] == (("CrypticK", "Zurandol"), ("Ksizzle", "Laura", "Merc"), "2026-11-08")
    for who in ("CrypticK, Merc, WitnesstoFebu made 1 of the 2 ", "Ksizzle, Laura, Merc made 1 of the 2 ",
                "Zurandol posted 2 of the 2 ", "Laura posted 1 of the 2 ", "CrypticK posted 1 of the 2 "):
        assert any(f.startswith("FLAG: " + who) for f in t["flags"]), (who, t["flags"])
    assert "Busiest closer: Merc, one of the closers on 2 of the 2 closes (100%)." in report(t, "x", "0" * 64)


def test_exit_codes():
    code, out = on_file(WORKED, lambda p: run([p]))
    assert code == 0 and "Closed under rule 4: 1 answer." in out, out
    code, out = on_file(FROZEN, lambda p: run([p]))
    assert code == 2 and "Nothing has closed under rule 4 yet." in out and "Busiest" not in out, out
    code, out = on_file("TEST LEDGER\n\nNO STATUS\n  here\n", lambda p: run([p]))
    assert code == 1 and "cannot be read" in out, out
    assert run([str(ROOT / "no-such-ledger.txt")])[0] == 1


if __name__ == "__main__":
    for name in sorted(n for n in dir() if n.startswith("test_")):
        globals()[name]()
        print("ok", name)
