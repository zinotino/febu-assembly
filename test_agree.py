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
        cls.js = run_node({"standing": cls.cases, "seen": [{"post": p} for p in cls.posts]})

    def test_standing_matches_claims_js(self):
        """build.standing and claims.js standing say the same about every random entry."""
        off = []
        for case, got in zip(self.cases, self.js["standing"]):
            want = build.standing([tuple(r) for r in case["results"]], case["writer"], case["members"], case["start"])
            if want != got:
                off.append((case, want, got))
        self.assertEqual(off[:2], [], "%d of %d differ; first two shown" % (len(off), len(self.cases)))

    def test_seen_line_round_trips(self):
        """What the weekly page writes into SEEN, build.py reads back as the same result (build.results)."""
        off = []
        for post, lines in zip(self.posts, self.js["seen"]):
            body = ["  FACT 1. (Zed, 2026-10-12)", "    SAYS      x", "    WRONG IF  y"] + lines
            fields = build.entries(body)[0][4]
            sample = tuple(sorted({it["line"] for it in post["items"] if it["n"] != it["of"]}))
            sc = post["script"] and (post["script"]["name"], post["script"]["by"], post["script"]["via"])
            want = [(post["who"], post["date"], post["word"], tuple(post["lines"]), sample, sc)]
            if build.results(fields) != want:
                off.append((post, lines, build.results(fields)))
        self.assertEqual(off[:2], [], "%d of %d differ; first two shown" % (len(off), len(self.posts)))

    def test_real_ledger_loses_no_line(self):
        """build.sections and build.entries hand back every non-blank line of ledger.txt, in order: a line the parser
        drops or moves would change what an entry says without anyone seeing it."""
        text = build.LEDGER.read_text(encoding="utf-8")
        title, secs = build.sections(text)
        kept = [title] + [l for h, b in secs for l in [h] + b]
        self.assertEqual([l for l in kept if l.strip()], [l.rstrip() for l in text.splitlines() if l.strip()])
        body = build.entries_section(secs)[1]
        got = []
        for it in build.entries(body):
            if it[0] == "text":
                got += [l.rstrip() for l in it[1]]
                continue
            got.append("  %s %s." % (it[1], it[2]))
            got += [ln.raw for _, lines in it[4] for ln in lines if ln.txt]
        want = [l.rstrip() for l in body if l.strip()]
        self.assertEqual(len(got), len(want))
        for g, w in zip(got, want):
            self.assertTrue(w.startswith(g.split(" (")[0]), (g, w))   # the header's (writer, date) and a note set off to the right (Ln.tag) are not in g


if __name__ == "__main__":
    unittest.main()
