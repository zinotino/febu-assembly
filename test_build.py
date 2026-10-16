"""python -m unittest test_build: the people page puts writers, checkers and predictions under the right names."""
import re
import unittest

import build

LEDGER = """TEST LEDGER (version 0)

STATUS
  Proposed by Zed.

WORDS USED HERE
  Member   Ann, Bo Cat, Zed. Adding a member works like a rule change.

THE ENTRIES

  FACT 1. (Zed, 2026-10-12)
    SAYS      One thing.
    SEEN      Ann, 2026-10-20: saw it. HOLDS.

  FACT 2. (Outsider, 2026-10-13)
    SAYS      Another thing.
    SEEN      nobody yet

Z'S PREDICTIONS THAT FAILED (carried over)
  Zed's word only.
  W1. Something would happen. FAILED. It did not.
"""


def window(out, pid):
    """(entries written, checks posted, the rest) in one person's window."""
    win = re.search(r'<section class="win person" id="%s".*?</section>' % pid, out, re.S).group()
    return re.split(r"<h3>Checks posted</h3>|<h3>Z&#x27;s predictions", win.split("<h3>Entries written</h3>")[1]) + [win]


class PeoplePage(unittest.TestCase):
    def test_names(self):
        out = build.people_page(build.sections(LEDGER)[1])
        self.assertLess(out.index('id="ann"'), out.index('id="zed"'))   # the Member line's order, members first
        self.assertLess(out.index('id="zed"'), out.index('id="outsider"'))
        wrote, saw, win = window(out, "ann")
        self.assertNotIn("fact-", wrote)
        self.assertIn("ledger.html#fact-1", saw)
        wrote, saw, preds, win = window(out, "zed")
        self.assertIn("ledger.html#fact-1", wrote)
        self.assertNotIn("fact-", saw)
        self.assertIn('href="ledger.html#W1"', preds)
        wrote, saw, win = window(out, "outsider")
        self.assertIn("ledger.html#fact-2", wrote)
        self.assertIn("not on the Member line", win)
        self.assertIn("Nothing stands under these names yet: Bo Cat.", out)


CHECKED = """  FACT 3. (Zed, 2026-10-12)
    SAYS      One thing.
    WRONG IF  it is not there, or it moved; or it is gone.
    SEEN      - Ann, 2026-10-20: HOLDS on lines 1, 2. Saw: line 1, it; line 2, that. New: a date. 1 minute.
              - Zed, 2026-10-20: HOLDS on lines 1, 2. Saw: x. New: y.
              - Bo Cat, 2026-10-21: HOLDS on lines 1, 2, 3. Saw: all of
                it, on two lines. New: z.
"""


class CheckedEntry(unittest.TestCase):
    """The SEEN line the weekly page writes (test_claims.js checks this same line) is read back, and rule 3 closes an
    entry only on two members other than the writer with the same result on the same WRONG IF lines."""

    def test_rule_3(self):
        _, kind, num, who, fields = build.entries(CHECKED.split("\n"))[0]
        members = ["Ann", "Bo Cat", "Zed"]
        found = build.results(fields)
        self.assertEqual(build.wrong_if(fields), ["it is not there", "it moved", "it is gone"])
        self.assertEqual([f[0] for f in found], ["Ann", "Zed", "Bo Cat"])
        self.assertEqual(found[0], ("Ann", "2026-10-20", "HOLDS", (1, 2), (), None))
        self.assertTrue(build.checked(fields))
        self.assertEqual(build.standing(found, "Zed", members, "2026-10-01")["state"], "OPEN")   # Zed wrote it; Bo Cat
        found.append(("Bo Cat", "2026-10-22", "HOLDS", (1, 2)))                                    # tested other lines
        st = build.standing(found, "Zed", members, "2026-10-01")
        self.assertEqual((st["state"], st["lines"], st["since"]), ("HOLDS", [1, 2], "2026-10-22"))



SLOTS = ("- Ann, 2026-10-24: HOLDS on line 1. Items: line 1, 20 of 164. Script: python checks/resolve.py fact4 by "
         "Zurandol via api.mainnet-beta.solana.com. Saw: line 1, pages 1-20 as predicted. New: page 7 is short. 30 minutes.")


class Slots(unittest.TestCase):
    """Items: and Script: (ASSEMBLY_SPEC section 4) read back from the SEEN item the weekly page writes (test_claims.js
    writes this same line), and two samples of fact 4 closing nothing on the real ledger."""

    def read(self, item):
        import textwrap
        seen = "\n                ".join(textwrap.wrap(item, 76))   # wrapped as the ledger lays it out
        return build.results(build.entries(("  FACT 4. (Zed, 2026-10-12)\n    WRONG IF  a page is off.\n"
                                            "    SEEN      %s\n" % seen).split("\n"))[0][4])

    def test_read_back(self):
        self.assertEqual(self.read(SLOTS), [("Ann", "2026-10-24", "HOLDS", (1,), (1,), (
            "python checks/resolve.py fact4", "Zurandol", "api.mainnet-beta.solana.com"))])
        self.assertEqual(self.read("- Bo, 2026-10-24: HOLDS on line 1. Items: all 164. Script: mine.py by Bo. Saw: x."),
                         [("Bo", "2026-10-24", "HOLDS", (1,), (), ("mine.py", "Bo", None))])
        self.assertEqual(self.read("- Bo, 2026-10-24: HOLDS. Items: 20 of 164; line 2, all 44. Saw: x."),
                         [("Bo", "2026-10-24", "HOLDS", (), (0,), None)])
        self.assertEqual(self.read("- Bo, 2026-10-24: HOLDS on line 1. Saw: x. New: y."),   # an item from before the slots
                         [("Bo", "2026-10-24", "HOLDS", (1,), (), None)])
        for odd in ("Items: twenty.", "Items: 20 of 164; most.", "Script: mine.py.", "Script: x by Bo, Cy."):
            self.assertEqual(self.read("- Bo, 2026-10-24: HOLDS on line 1. %s Saw: x." % odd), [], odd)   # lint I6

    def test_two_samples_of_fact_4_close_nothing(self):
        real = re.sub(r"(?ms)^STATUS\n.*?(?=^\S)", "STATUS\n  Adopted on 2026-10-22 under rule 7.\n\n",
                      build.LEDGER.read_text(encoding="utf-8"), count=1)
        two = [m for m in build.member_names(build.sections(real)[1]) if m != "Zurandol"][:2]

        def fact4(items):
            seen = "\n              ".join("- %s, 2026-10-2%d: HOLDS on line 1.%s Saw: line 1, as predicted. New: page %d."
                                           % (who, 4 + i, items, i) for i, who in enumerate(two))
            text = real.replace("    SEEN      nobody yet\n\n  FACT 5.", "    SEEN      %s\n\n  FACT 5." % seen)
            self.assertNotEqual(text, real)
            return build.entry_states(build.sections(text)[1])["4"]["state"]

        self.assertEqual(fact4(" Items: line 1, 20 of 164."), "OPEN")
        self.assertEqual(fact4(" Items: line 1, all 164."), "HOLDS")
        self.assertEqual(fact4(""), "HOLDS")   # nothing says it was a sample: the text trusts the post


class Votes(unittest.TestCase):
    def test_status_subjects(self):
        secs = build.sections(LEDGER.replace("  Proposed by Zed.", '  Proposed by Zed. "yes" or "object" by 2026-10-22.\n'
                                             "  Also up for the vote by 2026-10-22: the Saw line; the stop rule."))[1]
        self.assertEqual(build.open_votes("TEST LEDGER (version 0)", secs),
                         [("version 0", "2026-10-22"), ("the Saw line", "2026-10-22"), ("the stop rule", "2026-10-22")])

    def test_no_subjects_line(self):
        secs = build.sections(LEDGER)[1]
        self.assertEqual(build.open_votes("TEST LEDGER (version 0)", secs), [("version 0", None)])


class LedgerJson(unittest.TestCase):
    """ledger.json is an index of ledger.txt for an agent: the text's hash, the entries' state, no address in full."""

    def test_index(self):
        import hashlib, json
        raw = LEDGER.encode("utf-8")
        title, secs = build.sections(LEDGER)
        out = json.loads(build.ledger_json(title, secs, raw))
        self.assertEqual(out["ledger"], {"url": build.SITE + "/ledger.txt", "sha256": hashlib.sha256(raw).hexdigest(),
                                         "bytes": len(raw)})
        self.assertTrue(out["proposed"])
        self.assertEqual(out["members"], ["Ann", "Bo Cat", "Zed"])
        one, two = out["entries"]
        self.assertEqual((one["kind"], one["num"], one["writer"], one["says"]), ("FACT", 1, "Zed", "One thing."))
        self.assertEqual(one["url"], build.SITE + "/ledger.html#fact-1")
        self.assertEqual((one["results"], one["empty"]), ([], False))   # a SEEN line in another form is a person's to read
        self.assertEqual((two["writer"], two["empty"]), ("Outsider", True))

    def test_an_address_is_cut(self):
        wallet = "ApWpkd8tpPTdTFNihoYuF5en8Y27TQn4LAQTvvmf8faG"
        self.assertEqual(build.clip("signed by %s and by ApWpkd8" % wallet), "signed by ApWpkd8… and by ApWpkd8")

    def test_a_hash_with_no_zero_is_not_an_address(self):
        import hashlib, json
        title, secs = build.sections(LEDGER)
        for i in range(5000):   # about 1 hash in 60 has no 0 in it, and then reads as a 64-character base58 address
            raw = (LEDGER + "x" * i).encode("utf-8")
            if "0" not in hashlib.sha256(raw).hexdigest():
                break
        else:
            self.fail("no zero-free hash in 5000 tries")
        out = json.loads(build.ledger_json(title, secs, raw))   # exits if the hash is vetted as an address
        self.assertEqual(out["ledger"]["sha256"], hashlib.sha256(raw).hexdigest())

    def test_the_committed_file_is_what_build_writes(self):
        raw = build.raw_text(build.LEDGER)
        title, secs = build.sections(raw.decode("utf-8").rstrip("\n"))
        self.assertEqual(build.ledger_json(title, secs, raw), (build.ROOT / "ledger.json").read_text(encoding="utf-8"))


class ProcessTables(unittest.TestCase):
    def test_data_th(self):
        out = build.md_tables("<table><thead><tr><th>A</th><th>B</th></tr></thead><tbody><tr><td>1</td><td>2</td></tr>"
                              "</tbody></table>")
        self.assertIn('<td data-th="A">1</td><td data-th="B">2</td>', out)
        self.assertTrue(out.startswith('<div class="tbl stack"><table>'))


class ArchiveOrder(unittest.TestCase):
    def test_ties_break_on_path(self):
        import pathlib, tempfile
        a, b = "archive/ledger-1.1.txt", "archive/ledger-1.1-final.txt"
        with tempfile.TemporaryDirectory() as d:   # archive/ is empty at the clean start, so the test makes its own
            (pathlib.Path(d) / "archive").mkdir()
            for p in (a, b):
                (pathlib.Path(d) / p).write_text("x\n", encoding="utf-8")
            real, build.ROOT = build.ROOT, pathlib.Path(d)
            try:
                order = lambda text: [p for p, _, _ in build.archived(text)]
                self.assertEqual(order(a + " " + b), order(b + " " + a))   # the page must not depend on the hash seed
                self.assertEqual(order(a + " " + b), [b, a])
            finally:
                build.ROOT = real

class Calendar(unittest.TestCase):
    def test_events(self):
        secs = build.sections(LEDGER + "\nKNOWN BUGS (rule 8)\n  1. One thing, no date yet.\n"
                              "  2. Another. Fix by: 2026-11-14.\n")[1]
        ics = build.calendar_ics([("version 0", "2026-10-22"), ("the Saw line", "2026-10-22")],
                                 ["Ann", "Bo Cat", "Zed"], "2026-10-14", secs)
        self.assertIn("SUMMARY:Assembly vote closes: version 0\\; the Saw line", ics)
        self.assertEqual(ics.count("SUMMARY:Assembly vote closes"), 1)
        self.assertIn("DTSTART;VALUE=DATE:20261021\r\nDTEND;VALUE=DATE:20261028\r\nSUMMARY:Assembly weekly turn: Bo Cat",
                      ics)
        self.assertIn("SUMMARY:Assembly: known bug 2\\, fix by", ics)
        self.assertNotIn("known bug 1", ics)
        self.assertEqual(ics.count("BEGIN:VEVENT"), 1 + 12 + 1)


class AfterAdoption(unittest.TestCase):
    """The vote-week wording and the fact 1 note clear themselves: no page edit is needed once the ledger changes."""
    def test_freeze_wording_only_while_proposed(self):
        real = build.LEDGER.read_text(encoding="utf-8")
        status = lambda s: re.sub(r"(?ms)^STATUS\n.*?(?=^\S)", "STATUS\n  %s\n\n" % s, real, count=1)
        for text, frozen in ((status("Proposed by Z."), True), (status("Adopted 2026-10-22 under rule 7."), False)):
            title, secs = build.sections(text)
            for page in (build.weekly_page(title, secs), build.write_page(secs)):
                self.assertEqual("Not during a vote" in page, frozen)

    def test_fact1_note_until_link_names_the_account(self):
        from types import SimpleNamespace as L
        account = build.FACT1_ACCOUNT.rsplit("/", 1)[1]
        old = [("LINK", [L(txt="https://solscan.io/account/ApWpkd8#transfers")])]
        new = [("LINK", [L(txt="https://solscan.io/account/" + account)])]
        self.assertTrue(build.site_note(build.SITE_NOTES, "FACT", "1", old))
        self.assertEqual(build.site_note(build.SITE_NOTES, "FACT", "1", new), "")
        self.assertEqual(build.site_note(build.SITE_NOTES, "FACT", "3", old), "")


PROMISE = """  PROMISE 4. (Ann, 2026-10-24)
    WILL      Do it.
    BY        2026-12-01
    KNOWN BY  a link
    IF BROKEN none
    WITHDRAWN %s: we stop.
    SEEN      nobody yet
"""


class States(unittest.TestCase):
    """Rules 3 and 4 in one place, build.standing, on the cases test_claims.js runs through claims.js too."""

    def test_shared_cases(self):
        import json
        fx = json.loads((build.ROOT / "checks" / "states.json").read_text(encoding="utf-8"))
        for c in fx["cases"]:
            got = build.standing([tuple(r) for r in c["results"]], fx["writer"], fx["members"], c["start"])
            self.assertEqual(got, c["want"], c["why"])

    def test_the_real_ledger_before_and_after_adoption(self):
        real = build.LEDGER.read_text(encoding="utf-8")
        status = lambda s: re.sub(r"(?ms)^STATUS\n.*?(?=^\S)", "STATUS\n  %s\n\n" % s, real, count=1)
        self.assertEqual({s["start"] for s in build.entry_states(build.sections(real)[1]).values()}, {None})
        st = build.entry_states(build.sections(status("Adopted on 2026-10-22 under rule 7."))[1])
        self.assertEqual(st["1"]["start"], "2026-10-23")   # posts count from the day after adoption
        self.assertEqual(st["7"]["start"], "2026-11-21")   # PROMISE 7: BY is 30 days after adoption
        self.assertEqual({s["state"] for s in st.values()}, {"OPEN"})
        self.assertIsNone(build.adopted(build.sections(status("Adopted 2026-10-22, in other words."))[1]))

    def test_withdrawn(self):
        for day, word in (("2026-11-24", "WITHDRAWN"), ("2026-11-25", "BROKEN")):   # up to 7 days before BY
            fields = build.entries((PROMISE % day).split("\n"))[0][4]
            self.assertEqual(build.text_of(fields, "IF BROKEN"), "none")   # "WITHDRAWN 2026-..." is its own field
            st = build.entry_state("PROMISE", "Ann, 2026-10-24", fields, ["Ann", "Bo"], "2026-10-22")
            self.assertEqual((st["state"], st["since"], st["start"]), (word, day, "2026-12-01"))
            self.assertEqual(build.entry_state("PROMISE", "Ann, 2026-10-24", fields, ["Ann"], None)["state"], "OPEN")

    def test_text(self):
        fields = build.entries(CHECKED.split("\n"))[0][4]   # three WRONG IF lines
        st = lambda **k: dict(build.standing([], "", [], None), **k)
        self.assertIsNone(build.state_text(st(), "FACT", fields))
        self.assertEqual(build.state_text(st(state="HOLDS", lines=[1, 2, 3]), "FACT", fields), "HOLDS")
        self.assertEqual(build.state_text(st(state="HOLDS", lines=[2]), "FACT", fields), "HOLDS on line 2 only, of 3")
        self.assertEqual(build.state_text(st(both=["DOESN'T HOLD", "HOLDS"], until="2026-11-27"), "FACT", fields),
                         "disputed, DOESN'T HOLD and HOLDS: CAN'T TELL after 2026-11-27 unless it closes")
        self.assertEqual(build.state_text(st(state="KEPT"), "PROMISE", fields), "KEPT")

    def test_odd_dates_do_not_stop_the_build(self):
        self.assertEqual(build.days_after("9999-12-31", 30), "9999-12-31")
        self.assertIsNone(build.a_day("2026-13-45"))
        found = [("Ann", "2026-13-45", "HOLDS", (1,)), ("Bo", "9999-12-20", "HOLDS", (1,)),
                 ("Pat", "9999-12-21", "DOESN'T HOLD", (1,)), ("Quin", "9999-12-22", "DOESN'T HOLD", (1,)),
                 ("Cy", "9999-12-23", "HOLDS", (1,))]
        self.assertEqual(build.standing(found, "Zed", ["Ann", "Bo", "Cy"], "2026-10-23")["until"], "9999-12-31")


if __name__ == "__main__":
    unittest.main()
