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


if __name__ == "__main__":
    unittest.main()
