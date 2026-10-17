"""The two copies of the rules (build.py and assets/claims.js) on made-up input neither author picked.
test_build.py and test_claims.js each run a few dozen hand-written cases; this runs both copies on thousands of
random ones and says where they differ. Run: python test_agree.py (needs node)"""
import datetime, json, random, shutil, subprocess, unittest
from pathlib import Path

import build

ROOT = Path(__file__).resolve().parent
BASE = datetime.date(2026, 10, 23)
MEMBERS = ["Ann", "Bo", "Cy", "Di", "Ed"]
WORDS = ["alpha", "beta", "-", "1.5", "line", "x,y", "said:", "(ok)", "2026-10-30", "of", "all", "Items:", "Script:"]

NODE = r"""
const c = require('./assets/claims.js'), job = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const pad = (n) => ' '.repeat(n);
console.log(JSON.stringify({
  standing: job.standing.map((x) => { const s = c.standing(x.results, x.writer, x.members, x.start); delete s.groups; return s; }),
  seen: job.seen.map((p) => c.wrap('    SEEN      ', c.seenText(p.post), pad(16))),
}));
"""


def day(rng, back=3, ahead=70):
    return (BASE + datetime.timedelta(days=rng.randint(-back, ahead))).isoformat()


def standing_case(rng):
    writer = rng.choice(MEMBERS + ["Zed"])
    who = MEMBERS[:4] + ["Out1", writer]
    results = []
    for _ in range(rng.randint(2, 10)):   # few names, lines and words, so that pairs form: closes, disputes, CAN'T TELL
        word = rng.choice(["HOLDS", "HOLDS", "DOESN'T HOLD"])
        sample = [rng.randint(0, 2)] if word == "HOLDS" and rng.random() < 0.1 else []
        results.append([rng.choice(who), day(rng, 2, 50), word, rng.choice([[1], [1], [1, 2]]), sample, None])
    members = rng.sample(MEMBERS, rng.randint(3, 5))
    if rng.random() < 0.3:   # a close, a dispute of it, then a post near day 30 of the dispute: the CAN'T TELL edge
        a, b, c, d = rng.sample(MEMBERS, 4)
        t0 = BASE + datetime.timedelta(days=rng.randint(0, 5))
        at = lambda n: (t0 + datetime.timedelta(days=n)).isoformat()
        results += [[a, at(0), "HOLDS", [1], [], None], [b, at(1), "HOLDS", [1], [], None],
                    [c, at(2), "DOESN'T HOLD", [1], [], None], [d, at(rng.randint(2, 3)), "DOESN'T HOLD", [1], [], None],
                    [rng.choice([a, b, c, d]), at(rng.randint(28, 36)), rng.choice(["HOLDS", "DOESN'T HOLD"]), [1], [], None]]
        members, writer = list(set(members) | {a, b, c, d}), "Zed"
    return {"results": results, "writer": writer, "members": members,
            "start": None if rng.random() < 0.1 else day(rng, 2, 2)}


def words(rng, lo, hi):
    return " ".join(rng.choice(WORDS) for _ in range(rng.randint(lo, hi)))


def seen_post(rng):
    lines = sorted(rng.sample([1, 2, 3, 4], rng.randint(1, 3)))
    items = []
    for ln in rng.sample(lines, rng.randint(0, min(2, len(lines)))):
        of = rng.randint(2, 200)
        items.append({"line": rng.choice([0, ln]), "n": rng.choice([of, of, rng.randint(1, of - 1)]), "of": of})
    script = rng.choice([None, {"name": "python checks/resolve.py " + rng.choice(["fact4", "fact6"]), "by": "Zed",
                                "via": rng.choice([None, "api.mainnet-beta.solana.com"])}])
    return {"who": rng.choice(MEMBERS + ["Ann Lee"]), "date": day(rng), "word": rng.choice(["HOLDS", "DOESN'T HOLD"]),
            "lines": lines, "items": items, "script": script, "minutes": rng.choice([0, 1, 30]),
            "saw": [{"line": ln, "text": words(rng, 1, 14)} for ln in lines], "fresh": words(rng, 1, 6)}


def run_node(job):
    node = shutil.which("node")
    if not node:
        raise unittest.SkipTest("node is not installed")
    out = subprocess.run([node, "-e", NODE], input=json.dumps(job), cwd=ROOT, capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


class Agree(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng = random.Random(1069)
        cls.cases = [standing_case(rng) for _ in range(4000)]
        cls.posts = [seen_post(rng) for _ in range(1500)]
        cls._js = None

    @classmethod
    def js(cls):
        """claims.js on the same input, run once; skips the test that asks for it when node is missing."""
        if cls._js is None:
            cls._js = run_node({"standing": cls.cases, "seen": [{"post": p} for p in cls.posts]})
        return cls._js

    def test_standing_matches_claims_js(self):
        """build.standing and claims.js standing say the same about every random entry."""
        off = []
        for case, got in zip(self.cases, self.js()["standing"]):
            want = build.standing([tuple(r) for r in case["results"]], case["writer"], case["members"], case["start"])
            if want != got:
                off.append((case, want, got))
        self.assertEqual(off[:2], [], "%d of %d differ; first two shown" % (len(off), len(self.cases)))

    def test_seen_line_round_trips(self):
        """What the weekly page writes into SEEN, build.py reads back as the same result (build.results)."""
        off = []
        for post, lines in zip(self.posts, self.js()["seen"]):
            body = ["  FACT 1. (Zed, 2026-10-12)", "    SAYS      x", "    WRONG IF  y"] + lines
            fields = build.entries(body)[0][4]
            sample = tuple(sorted({it["line"] for it in post["items"] if it["n"] != it["of"]}))
            sc = post["script"] and (post["script"]["name"], post["script"]["by"], post["script"]["via"])
            want = [(post["who"], post["date"], post["word"], tuple(post["lines"]), sample, sc)]
            if build.results(fields) != want:
                off.append((post, lines, build.results(fields)))
        self.assertEqual(off[:2], [], "%d of %d differ; first two shown" % (len(off), len(self.posts)))

    def test_standing_keeps_to_the_rules_as_written(self):
        """Agreeing is not being right: two copies can share a misreading. These are the rules themselves, each a
        change to an entry that must change nothing (process.md rules 3 and 4), run through build.standing."""
        def stand(case, results=None, members=None):
            r = case["results"] if results is None else results
            return build.standing([tuple(x) for x in r], case["writer"], members or case["members"], case["start"])

        def same_but_the_clock(case, kept, what):
            """A line that counts for nothing changes nothing, except that its date can show the 30 days ran out: standing()
            reads that off any dated line, as the file has no other clock (so the state is CAN'T TELL, not OPEN until)."""
            full, less = stand(case), stand(case, kept)
            if full != less:
                late = less["until"] and any(r[1] > less["until"] for r in case["results"] if r not in kept)
                self.assertTrue(late and full["state"] == "CAN'T TELL" and less["state"] == "OPEN"
                                and full["since"] == build.days_after(less["until"], 1), what)

        for case in self.cases:
            same_but_the_clock(case, [r for r in case["results"] if r[0] != case["writer"]], "the writer's own result counts for nothing")
            same_but_the_clock(case, [r for r in case["results"] if not (r[2] == "HOLDS" and r[4])], "a sampled HOLDS counts for nothing")
            before = [r for r in case["results"] if not (case["start"] and r[1] < case["start"])]
            self.assertEqual(stand(case, before), stand(case), "a result dated before the first day counts for nothing")
            self.assertEqual(stand(case, members=case["members"][::-1]), stand(case), "the Member line's order does not matter")

    def test_rules_at_their_edges(self):
        """Rules 3 and 4 at the numbers they name, written out, so a misreading both copies share still fails."""
        ms, w = ["Ann", "Bo", "Cy", "Di"], "Zed"
        st = lambda *rs: build.standing(list(rs), w, ms, "2026-10-23")
        one = ("Ann", "2026-10-24", "HOLDS", (1,), (), None)
        two = ("Bo", "2026-10-25", "HOLDS", (1,), (), None)
        self.assertEqual(st(one)["state"], "OPEN")
        self.assertEqual(st(one, two)["state"], "HOLDS")
        self.assertEqual(st(one, ("Out", "2026-10-25", "HOLDS", (1,), (), None))["state"], "OPEN")   # not on the Member line
        self.assertEqual(st(one, ("Bo", "2026-10-25", "HOLDS", (2,), (), None))["state"], "OPEN")    # other WRONG IF lines
        self.assertEqual(st(one, (w, "2026-10-25", "HOLDS", (1,), (), None))["state"], "OPEN")       # the writer
        self.assertEqual(st(("Ann", "2026-10-24", "DOESN'T HOLD", (1,), (1,), None),
                            ("Bo", "2026-10-25", "DOESN'T HOLD", (1,), (1,), None))["state"], "DOESN'T HOLD")   # a sample finding a wrong item counts
        dispute = [("Cy", "2026-10-26", "DOESN'T HOLD", (1,), (), None), ("Di", "2026-10-27", "DOESN'T HOLD", (1,), (), None)]
        held = st(one, two, *dispute)
        self.assertEqual((held["state"], held["until"]), ("OPEN", "2026-11-26"))   # 30 days from the post that made it two words
        late = lambda d: st(one, two, *dispute, ("Ann", d, "HOLDS", (1,), (), None))["state"]
        self.assertEqual(late("2026-11-26"), "OPEN")        # day 30 can still close it: not yet CAN'T TELL
        self.assertEqual(late("2026-11-27"), "CAN'T TELL")  # day 31

    def test_real_ledger_loses_no_line(self):
        """build.sections and build.entries hand back every non-blank line of ledger.txt, whole and in order: a line the parser
        drops or moves would change what an entry says without anyone seeing it."""
        text = build.LEDGER.read_text(encoding="utf-8")
        title, secs = build.sections(text)
        kept = [title] + [l for h, b in secs for l in [h] + b]
        self.assertEqual([l for l in kept if l.strip()], [l.rstrip() for l in text.splitlines() if l.strip()])
        body = build.entries_section(secs)[1]
        got = []
        for it in build.entries(body):
            if it[0] == "text":
                got += [("", l.rstrip()) for l in it[1] if l.strip()]
                continue
            got.append(("", "  %s %s." % (it[1], it[2]) + (" (%s)" % it[3] if it[3] else "")))
            got += [(ln.raw, ln.raw + ("   (%s)" % ln.tag if ln.tag else "")) for _, lines in it[4] for ln in lines if ln.txt]
        want = [l.rstrip() for l in body if l.strip()]
        self.assertEqual(len(got), len(want))
        for (raw, rebuilt), w in zip(got, want):
            self.assertTrue(w == rebuilt or (w.startswith(raw) and build.TAG.fullmatch(w[len(raw):])), (rebuilt, w))   # a note set off to the right (Ln.tag) is cut from raw


if __name__ == "__main__":
    unittest.main()
