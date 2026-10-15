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
        self.assertEqual(found[0], ("Ann", "2026-10-20", "HOLDS", (1, 2)))
        self.assertTrue(build.checked(fields))
        self.assertIsNone(build.closed(found, "Zed", members))   # Zed is the writer; Bo Cat tested other lines
        found.append(("Bo Cat", "2026-10-22", "HOLDS", (1, 2)))
        self.assertEqual(build.closed(found, "Zed", members), ("HOLDS", (1, 2)))



class Votes(unittest.TestCase):
    def test_status_subjects(self):
        secs = build.sections(LEDGER.replace("  Proposed by Zed.", '  Proposed by Zed. "yes" or "object" by 2026-10-22.\n'
                                             "  Also up for the vote by 2026-10-22: the Saw line; the stop rule."))[1]
        self.assertEqual(build.open_votes("TEST LEDGER (version 0)", secs),
                         [("version 0", "2026-10-22"), ("the Saw line", "2026-10-22"), ("the stop rule", "2026-10-22")])

    def test_no_subjects_line(self):
        secs = build.sections(LEDGER)[1]
        self.assertEqual(build.open_votes("TEST LEDGER (version 0)", secs), [("version 0", None)])


class ProcessTables(unittest.TestCase):
    def test_data_th(self):
        out = build.md_tables("<table><thead><tr><th>A</th><th>B</th></tr></thead><tbody><tr><td>1</td><td>2</td></tr>"
                              "</tbody></table>")
        self.assertIn('<td data-th="A">1</td><td data-th="B">2</td>', out)
        self.assertTrue(out.startswith('<div class="tbl stack"><table>'))


class Calendar(unittest.TestCase):
    def test_events(self):
        secs = build.sections(LEDGER + "\nKNOWN BUGS (rule 8)\n  1. One thing. Fix by: 2026-11-14.\n")[1]
        ics = build.calendar_ics([("version 0", "2026-10-22"), ("the Saw line", "2026-10-22")],
                                 ["Ann", "Bo Cat", "Zed"], "2026-10-14", secs)
        self.assertIn("SUMMARY:Assembly vote closes: version 0\\; the Saw line", ics)
        self.assertEqual(ics.count("SUMMARY:Assembly vote closes"), 1)
        self.assertIn("DTSTART;VALUE=DATE:20261021\r\nDTEND;VALUE=DATE:20261028\r\nSUMMARY:Assembly weekly turn: Bo Cat",
                      ics)
        self.assertIn("SUMMARY:Assembly: known bug 1\\, fix by", ics)
        self.assertEqual(ics.count("BEGIN:VEVENT"), 1 + 12 + 1)


if __name__ == "__main__":
    unittest.main()
