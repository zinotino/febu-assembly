"""What an AI helper runs on a member's own machine. It helps a person look. It never posts a result (ledger.txt, WORDS
USED HERE, Saw), so nothing here posts, signs or edits a file.

    python checks/agent.py status                  the ledger's and process.md's hashes, the members, each entry's state
    python checks/agent.py run 8                   fact 8's scripts from checks/, then one line saying what ran
    python checks/agent.py draft 8 --as Laura      run them, then print a CHECK post with Saw: and New: left empty
    python checks/agent.py lint post.txt           would the weekly page take this post? ("-" reads stdin)

draft never writes "I opened the link myself." and never fills Saw: or New:: only a person who opened the link can.
lint refuses the post until they are there, by the weekly page's own reading of it (assets/claims.js, needs node).
"""
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HERE = ROOT / "checks"
# Fact -> the scripts that read it. Fact 8 needs both reads (process.md, section 5). Fact 7 is a promise: no script.
SCRIPTS = {1: ["resolve.py fact1"], 2: ["fact2.py"], 3: ["resolve.py fact3"], 4: ["resolve.py fact4"], 5: ["fact5.py"],
           6: ["fact6.py"], 8: ["resolve.py fact8", "resolve.py door2"], 9: ["resolve.py test9"]}
VERDICT = re.compile(r"^verdict[^:\n]*:\s*(HOLDS|DOESN'T HOLD|CAN'T TELL)", re.M)
# Reads the weekly page's own parser on {text, data, now}. Prints what it would add, what it holds back and why.
NODE = r"""
const input = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const claims = require(input.claims), p = claims.parse(input.text), r = claims.review(p, input.data, input.now);
console.log(JSON.stringify({
  checks: p.checks.length,
  held: r.held.map(h => h.post.kind + ' ' + h.post.num + ': ' + h.why),
  blank: p.checks.filter(c => c.saw.some(s => !s.text)).map(c => c.kind + ' ' + c.num + ' has a Saw: line with nothing after it'),
  add: r.add.reduce((n, a) => n + a.posts.length, 0)
}));
"""


def sha8(name):
    return hashlib.sha256((ROOT / name).read_bytes()).hexdigest()[:8]


def ledger_data():
    """What the weekly page holds from ledger.txt: members, and per entry the writer, WRONG IF count and results."""
    page = (ROOT / "weekly.html").read_text(encoding="utf-8")
    m = re.search(r'<script type="application/json" id="ledger-data">(.*?)</script>', page, re.S)
    if not m:
        raise SystemExit("weekly.html has no ledger-data block: run python build.py")
    data = json.loads(m.group(1).replace("<\\/", "</"))
    nums = [int(n) for n in re.findall(r"^  (?:FACT|PROMISE) (\d+)\.", (ROOT / "ledger.txt").read_text(encoding="utf-8"), re.M)]
    # ponytail: entry numbers only; a SEEN line added since the last build.py shows late here. Run build.py first.
    if [e["num"] for e in data["entries"]] != nums:
        raise SystemExit("weekly.html is older than ledger.txt: run python build.py")
    return data


def verdict_of(outputs):
    """One word for the entry from its scripts' "verdict:" lines, or None if any script printed none."""
    words = [VERDICT.search(o) for o in outputs]
    if not words or not all(words):
        return None
    got = {w.group(1) for w in words}
    return next((w for w in ("DOESN'T HOLD", "CAN'T TELL") if w in got), "HOLDS")


def execute(num):
    """Run the entry's scripts: (the commands as typed, their outputs). A script that fails stops everything."""
    if num not in SCRIPTS:
        raise SystemExit("entry %d has no script in checks/: open its link and look" % num)
    cmds, outs = [], []
    for spec in SCRIPTS[num]:
        name, *args = spec.split()
        print("running python checks/%s ..." % spec, file=sys.stderr)
        done = subprocess.run([sys.executable, str(HERE / name), *args], cwd=ROOT, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        if done.returncode:
            raise SystemExit("python checks/%s failed:\n%s%s" % (spec, done.stdout, done.stderr))
        cmds.append("python checks/" + spec)
        outs.append(done.stdout)
    return cmds, outs


def script_line(cmds, word, when):
    return "Script: %s said %s on ledger %s at %s" % (" and ".join(cmds), word or "no verdict", sha8("ledger.txt"), when)


def draft_post(entry, who, date, word, script):
    """The CHECK post for a person to finish. It leaves out "I opened the link myself." on purpose."""
    n = entry["lines"]
    head = "CHECK %s %d | %s | lines %s | %s | %s" % (entry["kind"], entry["num"], word or "RESULT", ",".join(map(str, range(1, n + 1))), who, date)
    return "\n".join([head] + ["Line %d:\nSaw:" % i for i in range(1, n + 1)] + ["New:", script]) + "\n"


def lint(text, data, now=None):
    """The reasons the weekly page would not take this post as it stands. An empty list means it would."""
    if not shutil.which("node"):
        raise SystemExit("lint needs node (test_claims.js does too)")
    payload = {"text": text, "data": data, "now": now or dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d"),
               "claims": str(ROOT / "assets" / "claims.js")}
    done = subprocess.run(["node", "-e", NODE], input=json.dumps(payload), capture_output=True, text=True, encoding="utf-8")
    if done.returncode:
        raise SystemExit("node failed:\n" + done.stderr)
    out = json.loads(done.stdout)
    if not out["checks"]:
        return ["no CHECK line found: the first line is CHECK FACT n | HOLDS or DOESN'T HOLD | lines 1,2 | Name | YYYY-MM-DD"]
    return out["held"] + out["blank"]


def main(argv):
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "status":
        d = ledger_data()
        print("ledger.txt %s | process.md %s" % (sha8("ledger.txt"), sha8("process.md")))
        print("members: " + ", ".join(d["members"]))
        print("open votes: " + ("; ".join("%s by %s" % (v["subject"], v["by"]) for v in d["votes"]) or "none"))
        for e in d["entries"]:
            print("%-8s %-3d writer %-14s %d WRONG IF line%s, %d check%s, script %s" % (
                e["kind"], e["num"], e["writer"], e["lines"], "" if e["lines"] == 1 else "s", len(e["results"]),
                "" if len(e["results"]) == 1 else "s", "yes" if e["num"] in SCRIPTS else "no"))
    elif cmd in ("run", "draft") and len(argv) > 2 and argv[2].isdigit():
        num = int(argv[2])
        if cmd == "draft":   # check these before a script that can take minutes
            who = argv[argv.index("--as") + 1] if "--as" in argv[:-1] else sys.exit("draft needs --as <your name in the chat>")
            data = ledger_data()
            entry = next((e for e in data["entries"] if e["num"] == num), None) or sys.exit("the ledger has no entry %d" % num)
        cmds, outs = execute(num)
        word = verdict_of(outs)
        when = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")   # the ledger's dates are UTC
        if cmd == "run":
            print("\n".join(outs) + "\n" + script_line(cmds, word, when))
            return
        if word == "CAN'T TELL":
            raise SystemExit("the script says CAN'T TELL: that is not a result, so there is nothing to post")
        if who not in data["members"]:
            print("note: %s is not on the Member line, so a post by them is an outsider's (rule 3)" % who, file=sys.stderr)
        print(draft_post(entry, who, when[:10], word, script_line(cmds, word, when)), end="")
        print("Not posted. Open the link yourself, fill every Saw: and New:, add 'Minutes: n' and the line\n"
              "'I opened the link myself.' once it is true, then: python checks/agent.py lint post.txt", file=sys.stderr)
    elif cmd == "lint" and len(argv) > 2:
        text = sys.stdin.read() if argv[2] == "-" else Path(argv[2]).read_text(encoding="utf-8")
        why = lint(text, ledger_data())
        print("\n".join(why) if why else "ok: the weekly page would take this post")
        sys.exit(1 if why else 0)
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main(sys.argv)
