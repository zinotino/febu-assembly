"""python -m unittest test_build: build.py's reading of a version-5 ledger, on the fixtures in checks/fixtures/ (the
frozen text and a worked copy with known answers), each known answer with a one-change control."""
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

import build

FIXTURES = build.ROOT / "checks" / "fixtures"
FROZEN = (FIXTURES / "ledger_v5.txt").read_text(encoding="utf-8")
WORKED = (FIXTURES / "ledger_v5_worked.txt").read_text(encoding="utf-8")


def swap(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new)


def model(text):
    return build.model(build.sections(text)[1])


def answer(q, a, text=WORKED):
    return model(text)["questions"][q - 1]["answers"][a - 1]


class Seen(unittest.TestCase):
    """The SEEN item the weekly page writes (test_claims.js writes this same line) is read back with its slots."""

    def read(self, item):
        seen = ("\n" + " " * 18).join(textwrap.wrap(item, 76))   # wrapped as the ledger lays it out
        body = ("  Q1. (opened 2026-10-31, from P1)\n    ASKS        x\n    ANSWER 1.   (Zed, 2026-10-31)\n"
                "      WRONG IF  a page is off, or a page is missing.\n      SEEN      %s\n" % seen)
        return build.results(build.questions(body.split("\n"))[0]["answers"][0]["fields"])

    def test_read_back(self):
        self.assertEqual(self.read("- Ann, 2026-11-04: HOLDS on line 1. Items: line 1, 20 of 164. Script: python "
                                   "checks/resolve.py fact4 by Zurandol via api.mainnet-beta.solana.com. Saw: line 1, "
                                   "pages. New: page 7."),
                         [("Ann", "2026-11-04", "HOLDS", (1,), ((1, 20, 164),),
                           ("python checks/resolve.py fact4", "Zurandol", "api.mainnet-beta.solana.com"))])
        self.assertEqual(self.read("- Bo, 2026-11-04: HOLDS on lines 1, 2. Items: all 164. Script: mine.py by Bo. Saw: x."),
                         [("Bo", "2026-11-04", "HOLDS", (1, 2), ((0, 164, 164),), ("mine.py", "Bo", None))])
        self.assertEqual(self.read("- Bo, 2026-11-04: DOESN'T HOLD on line 2. Saw: x. New: y."),
                         [("Bo", "2026-11-04", "DOESN'T HOLD", (2,), (), None)])
        for odd in ("Items: twenty.", "Items: 20 of 164; most.", "Script: mine.py.", "Script: x by Bo, Cy.",
                    "items: 20 of 164.", "Item: 20 of 164.", "ITEMS : 20 of 164.", " Items: 20 of 164.", "Items 20 of 164.",
                    "Items: 20 of 164", "script: x by Bo.", "Scripts: x.py by Bo.", "Ran x.py.", "Items: all 1. Scripts: x by Bo.",
                    "Items: all 0.", "Items: line 0, all 1.", "Items: 0 of 0."):
            self.assertEqual(self.read("- Bo, 2026-11-04: HOLDS on line 1. %s Saw: x." % odd), [], odd)   # lint I6
        self.assertEqual(self.read("- Bo, 2026-11-04: HOLDS on line 1. Items: all 1."), [])   # no Saw: no check
        self.assertEqual(len(self.read("- Bo, 2026-11-04: HOLDS on line 1. Items: all 1. Saw: x.")), 1)   # the control

    def test_a_note_at_the_end_of_a_line_is_text(self):
        """A field's words are the file's: "(...)" set off at the end of a line is not a layout note the model drops."""
        body = ("  Q1. (opened 2026-10-31, from P1)\n    ANSWER 1.   (Zed, 2026-10-31)\n      SAYS      One thing,\n"
                "                and another.   (withdrawn: it moved)\n")
        fields = build.questions(body.split("\n"))[0]["answers"][0]["fields"]
        self.assertEqual(build.text_of(fields, "SAYS"), "One thing, and another.   (withdrawn: it moved)")

    def test_wrong_if_lines(self):
        fields = build.questions(("  Q1. (opened 2026-10-31, from P1)\n    ANSWER 1.   (Zed, 2026-10-31)\n"
                                  "      WRONG IF  it is not there, or it moved; or it is gone.\n").split("\n"))[0]["answers"][0]["fields"]
        self.assertEqual(build.wrong_if(fields), ["it is not there", "it moved", "it is gone"])


class States(unittest.TestCase):
    """Rules 2, 4, 5 and 8 on the cases test_claims.js runs through claims.js too (checks/states.json)."""

    fx = json.loads((build.ROOT / "checks" / "states.json").read_text(encoding="utf-8"))

    def test_standing(self):
        st = self.fx["standing"]
        for c in st["cases"]:
            found = [tuple(r[:4]) + (tuple(map(tuple, r[4])), r[5] and tuple(r[5])) for r in c["results"]]
            got = build.standing(found, set(c.get("posters", st["posters"])), st["members"], c.get("start", st["start"]),
                                 c.get("n", st["n"]), c.get("posts", st["posts"]))
            self.assertEqual(got, c["want"], c["why"])

    def test_questions(self):
        qs = self.fx["questions"]
        for c in qs["cases"]:
            got = build.question_state(qs["opened"], [{"num": n, "state": {"held": h}} for n, h in c["answers"]], c["as_of"])
            self.assertEqual(got, c["want"], c["why"])

    def test_slot(self):
        sl = self.fx["slot"]
        for c in sl["cases"]:
            on = c.get("adopted", sl["adopted"])
            props = [{"num": n, "who": w, "date": d, "yes": [tuple(y) for y in ys]} for n, w, d, ys in c["proposals"]]
            for p in props:
                p["reach"] = build.reach(p, sl["members"], on)
            self.assertEqual([list(x) for x in build.slot(props, c["frees"], on)], c["want"], c["why"])

    def test_votes(self):
        vt = self.fx["votes"]
        for c in vt["cases"]:
            got = build.vote_state({"posted": vt["posted"], "votes": [tuple(v) for v in c["votes"]]}, vt["members"],
                                   c.get("posts", vt["posts"]), c["as_of"])
            self.assertEqual(got, c["want"], c["why"])

    def test_odd_dates_do_not_stop_the_build(self):
        self.assertEqual(build.days_after("9999-12-31", 30), "9999-12-31")
        self.assertIsNone(build.a_day("2026-13-45"))
        found = [("Ann", "2026-13-45", "HOLDS", (1,), (), None), ("Bo", "9999-12-20", "HOLDS", (1,), (), None)]
        self.assertEqual(build.standing(found, {"Zed"}, ["Ann", "Bo", "Cy"], "2026-10-23", 1)["state"], "OPEN")


class Worked(unittest.TestCase):
    """The worked ledger's known answers, each with the one change that moves it."""

    def test_known_answers(self):
        m = model(WORKED)
        self.assertEqual((m["adopted"], m["as_of"], m["next"]), ("2026-10-30", "2026-11-08", {"proposal": 4, "question": 3}))
        self.assertEqual(m["slot"], [(1, "2026-10-31"), (3, "2026-11-05")])   # rule 2: P3 opens the day Q1 closes
        q1, q2 = m["questions"]
        self.assertEqual(q1["state"], {"state": "CLOSED", "since": "2026-11-05", "until": "2026-11-30", "answer": 1})
        a = q1["answers"][0]
        self.assertEqual((sorted(a["posters"]), a["state"]["state"], a["state"]["by"]),
                         (["Laura", "Zurandol"], "HOLDS", ["CrypticK", "Merc", "WitnesstoFebu"]))
        self.assertEqual((q2["state"]["state"], q2["state"]["until"]), ("OPEN", "2026-12-05"))
        kept = q2["answers"][0]["state"]   # rule 5: two full HOLDS and two DOESN'T HOLD on line 1, four people
        self.assertEqual((kept["state"], kept["both"], kept["since"]), ("OPEN", ["DOESN'T HOLD", "HOLDS"], "2026-11-07"))
        self.assertEqual(sorted(q2["answers"][0]["posters"]), ["Laura", "Merc"])   # Laura's CHANGED line makes her one
        self.assertEqual(sorted(q2["answers"][1]["posters"]), ["CrypticK", "Zurandol"])   # Zurandol wrote fact 5
        self.assertEqual([(v["subject"], v["passed"]) for v in m["votes"]], [("Rule 4 floor wording", "2026-11-08")])

    def test_the_writer_of_a_copied_entry(self):
        members = model(WORKED)["members"]
        self.assertEqual(build.v3_writer("FACT", "2", members), "Zurandol")
        self.assertEqual(build.v3_writer("PROMISE", "7", members), "Zurandol")   # the group's: "Zurandol proposed it"
        no_copy = swap(WORKED, "(CrypticK, 2026-11-08, version 3's fact 5)", "(CrypticK, 2026-11-08)")
        self.assertEqual(sorted(answer(2, 2, no_copy)["posters"]), ["CrypticK"])
        two = swap(WORKED, "(CrypticK, 2026-11-08, version 3's fact 5)", "(CrypticK, 2026-11-08, version 3's facts 2 and 5)")
        self.assertEqual(sorted(answer(2, 2, two)["posters"]), ["CrypticK", "Zurandol"])
        with self.assertRaises(SystemExit):   # every number is read: version 3 has no fact 99
            model(swap(WORKED, "(CrypticK, 2026-11-08, version 3's fact 5)", "(CrypticK, 2026-11-08, version 3's facts 5 and 99)"))

    def test_odd_input_does_not_stop_the_build_with_a_traceback(self):
        """An address in a question, "<!--" in the data, a date off the calendar in VOTES or STATUS: every page is still
        written. A section the model reads, written twice, stops with a message, not a traceback."""
        wallet = "ApWpkd8tpPTdTFNihoYuF5en8Y27TQn4LAQTvvmf8faG"
        text = swap(WORKED, "Did the wallet that created $FEBU sell all of its $FEBU on 2026-09-22 and\n",
                    "Did the wallet %s <!-- <script> sell all of its $FEBU on 2026-09-22 and\n" % wallet)
        text = swap(text, "posted 2026-11-01, SHA-256", "posted 2026-02-30, SHA-256")
        title, secs = build.sections(swap(text, "  Adopted on 2026-10-30,", "  Adopted on 2026-10-30 (not 2026-13-01),"))
        m = build.model(secs)
        front = build.assembly_page(title, secs, build.sections(build.raw_text(build.HOW).decode("utf-8"))[1], m)
        self.assertIn("ApWpkd8t...", front)
        weekly = build.weekly_page(title, secs, m)
        data = re.search(r'id="ledger-data">(.*?)</script>', weekly, re.S).group(1)
        self.assertNotIn("<", data)
        self.assertIn("ApWpkd8… <!-- <script>", json.loads(data)["questions"][0]["asks"])
        self.assertEqual(build.open_votes(title, secs, m), [])
        build.calendar_ics(build.open_votes(title, secs, m), m["members"], build.turn_start(secs), secs)
        twice = WORKED + "\nLAST POSTS\n  - 2026-11-09: Merc 2026-11-09.\n"
        with self.assertRaises(SystemExit) as e:
            model(twice)
        self.assertIn("2 LAST POSTS sections", str(e.exception))

    def test_by_hand(self):
        """Rule 4: one of the three closers opened every link with no script. Merc and CrypticK were by hand; with a
        script on both, WitnesstoFebu's is by script too, and nothing closes. With one of them by hand, it closes."""
        script = "Items: all 1. Script: python checks/resolve.py fact2 by Ksizzle via laptop. Saw:"
        one = swap(WORKED, "2026-11-01: HOLDS on lines 1, 2, 3. Items: all 1. Saw:", "2026-11-01: HOLDS on lines 1, 2, 3. "
                   + script)
        self.assertEqual(answer(1, 1, one)["state"]["state"], "HOLDS")
        both = swap(one, "2026-11-05: HOLDS on lines 1, 2, 3. Items: all 1. Saw:", "2026-11-05: HOLDS on lines 1, 2, 3. "
                    + script)
        self.assertEqual(answer(1, 1, both)["state"]["state"], "OPEN")

    def test_a_poster_closes_nothing(self):
        """CrypticK's full check on 2026-11-05 is Laura's instead: Laura posted the answer, so it does not close."""
        self.assertEqual(answer(1, 1, swap(WORKED, "- CrypticK, 2026-11-05:", "- Laura, 2026-11-05:"))["state"]["state"],
                         "OPEN")

    def test_day_30(self):
        """Q2 opened 2026-11-05: a file whose last date is 2026-12-05 has it OPEN, one day later CAN'T TELL."""
        def q2(day):
            text = swap(WORKED, "  - 2026-11-08: CrypticK 2026-11-08,", "  - %s: CrypticK 2026-11-08," % day)
            return model(text)["questions"][1]["state"]
        self.assertEqual(q2("2026-12-05")["state"], "OPEN")
        self.assertEqual((q2("2026-12-06")["state"], q2("2026-12-06")["since"]), ("CAN'T TELL", "2026-12-06"))

    def test_frozen(self):
        m = model(FROZEN)
        self.assertEqual((m["adopted"], m["questions"], m["next"]), (None, [], {"proposal": 1, "question": 1}))


class LedgerJson(unittest.TestCase):
    """ledger.json is an index of ledger.txt for an agent: the text's hash, the questions' state, no address in full."""

    def json_of(self, text, raw=None):
        raw = raw or text.encode("utf-8")
        title, secs = build.sections(text)
        return json.loads(build.ledger_json(title, secs, raw, build.model(secs)))

    def test_index(self):
        raw = WORKED.encode("utf-8")
        out = self.json_of(WORKED)
        self.assertEqual(out["ledger"], {"url": build.SITE + "/ledger.txt", "sha256": hashlib.sha256(raw).hexdigest(),
                                         "bytes": len(raw)})
        self.assertFalse(out["proposed"])
        self.assertEqual([q["num"] for q in out["questions"]], [1, 2])
        a = out["questions"][0]["answers"][0]
        self.assertEqual((a["posters"], a["lines"], a["copies"], a["url"]),
                         (["Laura", "Zurandol"], 3, ["FACT", 2], build.SITE + "/ledger.html#q-1-answer-1"))
        self.assertIsNone(out["questions"][1]["answers"][0]["copies"])
        self.assertNotIn("ApWpkd8tpPTdTFNihoYuF5en8Y27TQn4LAQTvvmf8faG", json.dumps(out))

    def test_an_address_is_cut(self):
        wallet = "ApWpkd8tpPTdTFNihoYuF5en8Y27TQn4LAQTvvmf8faG"
        self.assertEqual(build.clip("signed by %s and by ApWpkd8" % wallet), "signed by ApWpkd8… and by ApWpkd8")

    def test_a_hash_with_no_zero_is_not_an_address(self):
        for i in range(5000):   # about 1 hash in 60 has no 0 in it, and then reads as a 64-character base58 address
            raw = (WORKED + "x" * i).encode("utf-8")
            if "0" not in hashlib.sha256(raw).hexdigest():
                break
        else:
            self.fail("no zero-free hash in 5000 tries")
        out = self.json_of(WORKED, raw)   # exits if the hash is vetted as an address
        self.assertEqual(out["ledger"]["sha256"], hashlib.sha256(raw).hexdigest())

    def test_the_committed_file_is_what_build_writes(self):
        raw = build.raw_text(build.LEDGER)
        text = raw.decode("utf-8").rstrip("\n")
        if "(version 5)" not in text.split("\n", 1)[0]:
            self.skipTest("ledger.txt is still version 3: Adoption below builds the version-5 fixture instead")
        title, secs = build.sections(text)
        self.assertEqual(build.ledger_json(title, secs, raw, build.model(secs)),
                         (build.ROOT / "ledger.json").read_text(encoding="utf-8"))


class Adoption(unittest.TestCase):
    """Adoption day in a copy of the repo: the frozen text goes in as ledger.txt (version 3 is already in archive/),
    build.py writes every page, lint passes it against version 3, and no people page is written. The worked copy
    builds too."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "repo"
        shutil.copytree(build.ROOT, self.root, ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache",
                                                                              "node_modules"))
        (self.root / "people.html").unlink(missing_ok=True)

    def tearDown(self):
        self.tmp.cleanup()

    def run_py(self, *args):
        return subprocess.run([sys.executable, *args], cwd=self.root, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})

    def test_frozen_text_builds_and_lints(self):
        shutil.copyfile(FIXTURES / "ledger_v5.txt", self.root / "ledger.txt")
        done = self.run_py("build.py")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        lint = self.run_py("checks/lint.py", "--prev", "archive/08_CLAIMS_LEDGER_v3.txt")
        self.assertEqual(lint.returncode, 0, lint.stdout + lint.stderr)
        self.assertFalse((self.root / "people.html").exists())
        index = json.loads((self.root / "ledger.json").read_text(encoding="utf-8"))
        self.assertEqual(index["ledger"]["sha256"], hashlib.sha256((FIXTURES / "ledger_v5.txt").read_bytes()).hexdigest())
        self.assertEqual(index["questions"], [])

    def test_worked_text_builds(self):
        shutil.copyfile(FIXTURES / "ledger_v5_worked.txt", self.root / "ledger.txt")
        done = self.run_py("build.py")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        index = json.loads((self.root / "ledger.json").read_text(encoding="utf-8"))
        heads = [int(n) for n in re.findall(r"^  Q(\d+)\. ", WORKED, re.M)]
        self.assertEqual([q["num"] for q in index["questions"]], heads)
        page = (self.root / "ledger.html").read_text(encoding="utf-8")
        self.assertIn('id="q-2-answer-2"', page)


class ProcessTables(unittest.TestCase):
    def test_data_th(self):
        out = build.md_tables("<table><thead><tr><th>A</th><th>B</th></tr></thead><tbody><tr><td>1</td><td>2</td></tr>"
                              "</tbody></table>")
        self.assertIn('<td data-th="A">1</td><td data-th="B">2</td>', out)
        self.assertTrue(out.startswith('<div class="tbl stack"><table>'))


class ArchiveOrder(unittest.TestCase):
    def test_ties_break_on_path(self):
        a, b = "archive/ledger-1.1.txt", "archive/ledger-1.1-final.txt"
        with tempfile.TemporaryDirectory() as d:   # the test makes its own archive/
            (Path(d) / "archive").mkdir()
            for p in (a, b):
                (Path(d) / p).write_text("x\n", encoding="utf-8")
            real, build.ROOT = build.ROOT, Path(d)
            try:
                order = lambda text: [p for p, _, _ in build.archived(text)]   # noqa: E731
                self.assertEqual(order(a + " " + b), order(b + " " + a))   # the page must not depend on the hash seed
                self.assertEqual(order(a + " " + b), [b, a])
            finally:
                build.ROOT = real


class Calendar(unittest.TestCase):
    def test_events(self):
        secs = build.sections(WORKED)[1]
        members = model(WORKED)["members"]
        ics = build.calendar_ics([("Rule 4 floor wording", "2026-11-08", "counted from")], members, "2026-10-30", secs)
        self.assertIn("SUMMARY:Assembly vote: Rule 4 floor wording (counted from 2026-11-08)", ics)
        self.assertIn("DTSTART;VALUE=DATE:20261106\r\nDTEND;VALUE=DATE:20261113\r\nSUMMARY:Assembly weekly turn: %s"
                      % members[1], ics)
        self.assertIn("SUMMARY:Assembly: known bug 1\\, fix by", ics)
        self.assertNotIn("known bug 8", ics)   # "Fix by: the 60th day from adoption" names no date
        bugs = len(re.findall(r"SUMMARY:Assembly: known bug", ics))
        self.assertEqual(ics.count("BEGIN:VEVENT"), 1 + 12 + bugs)


class AfterAdoption(unittest.TestCase):
    """The vote-week wording clears itself: no page edit is needed once STATUS says Adopted."""

    def test_freeze_wording_only_while_proposed(self):
        for text, frozen in ((FROZEN, True), (WORKED, False)):
            title, secs = build.sections(text)
            m = build.model(secs)
            for page in (build.weekly_page(title, secs, m), build.write_page(secs, m)):
                self.assertEqual("Not during a vote" in page, frozen)


if __name__ == "__main__":
    unittest.main()
