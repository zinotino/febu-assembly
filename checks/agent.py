"""What an AI helper runs on a member's own machine. It helps a person look. It never posts a result (ledger.txt, WORDS
USED HERE, Saw), so nothing here posts, signs or edits a file.

    python checks/agent.py status                  the ledger's and process.md's hashes, the members, each answer's state
    python checks/agent.py run 8                   version 3's fact 8's scripts from checks/, then one line saying what
                                                   ran and where
    python checks/agent.py draft 1 2 --as Laura    Q1 answer 2: run the scripts of the version 3 fact it copies, then
                                                   print a CHECK post with Saw: and New: left empty
    python checks/agent.py lint post.txt           would the weekly page take this post? ("-" reads stdin)

The scripts in checks/ re-read version 3's facts, so an answer has a script only when it copies one (its header says
"version 3's fact 8"). run and draft take --rpc https://your-node to read through another Solana node than the default.
The Script: line ends in "via <host>" (the host only: a path or query can hold an API key, and it is cut from the output
too). lint takes several posts, the week's chat for example, and notes where two members' results on one answer name the
same source.

draft never writes "I opened the link myself." and never fills Saw: or New:: only a person who opened the link can.
lint refuses the post until they are there, by the weekly page's own reading of it (assets/claims.js, needs node), and
refuses a Saw: or New: with nothing in it ("." is not an answer) or a named line with no Saw: of its own.
The questions and answers come from ledger.json, which build.py writes from ledger.txt. checks/mcp_server.py offers the same four
commands to an agent that has no shell.
"""
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HERE = ROOT / "checks"
sys.path.insert(0, str(HERE))   # common.py sits beside this file
import common  # noqa: E402
from common import host_of, redact  # noqa: E402  (the node's key is cut by the same code in every check)
# Fact -> the scripts that read it. Fact 8 needs both reads (process.md, section 5). Fact 7 is a promise: no script.
SCRIPTS = {1: ["resolve.py fact1"], 2: ["fact2.py"], 3: ["resolve.py fact3"], 4: ["resolve.py fact4"], 5: ["fact5.py"],
           6: ["fact6.py"], 8: ["resolve.py fact8", "resolve.py door2"], 9: ["resolve.py test9"]}
AUTHOR = "Zurandol"   # wrote every script in checks/ (process.md section 5); the Script: line names them (rule 3)
# Where an entry's scripts read from, named on the Script: line so two results can be told apart by it. These facts read the
# Solana node (SOLANA_RPC, or --rpc, or common.py's default); these read the link the entry itself carries, found with the
# same patterns resolve.py and fact5.py use.
RPC_FACTS = {1, 2, 6, 8, 9}
LINK_FACTS = {3: r"https://web\.archive\.org/web/\d{14}if_/\S+", 4: r"https://\S+/scripture\.html", 5: r"LINK\s+(https://\S+)"}
LOOPBACK = {"127.0.0.1", "localhost", "::1"}
SCRIPT_TIMEOUT = 600   # seconds per script; fact 8's door 2 takes about three minutes
VERDICT = re.compile(r"^verdict[^:\n]*:\s*(HOLDS|DOESN'T HOLD|CAN'T TELL)", re.M)
NAME = re.compile(r"[^\W_][\w .'-]{0,39}")   # a name as it is written in the chat: one line, nothing the post's format reads
POST_LINE = re.compile(r"CHECK [^\n]*|Line \d+:|Saw:|New:|Script: [^\n]*")
NEXT_STEP = ("Not posted. Open the link yourself, fill every Saw: and New:, and add the line\n"
             "'I opened the link myself.' once it is true. Under each Line n:, add how many items you opened:\n"
             "'Items: all 164' or 'Items: 20 of 164' (a HOLDS counts only with 'all' on every line, rule 4). Then:\n"
             "python checks/agent.py lint post.txt")
_busy = threading.Lock()   # one script run at a time: they all read the same public node
# Reads the weekly page's own parser on {text, data, now}, then asks more of a post than it does: a Saw: with something in
# it for every line the post names, a New: with something in it, and the attestation line inside the post itself.
NODE = r"""
const input = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const claims = require(input.claims), p = claims.parse(input.text), r = claims.review(p, input.data, input.now);
const lines = input.text.replace(/\r\n?/g, '\n').split('\n');
const solid = s => /[A-Za-z0-9]/.test(s);   // "." and "?" are not an answer; "none" is
const extra = [], posts = [];
[].concat(p.proposals, p.yeses, p.votes, p.answers).forEach(x => extra.push('line ' + x.at + ': a ' + x.type +
  ' post is not a check, and lint reads check posts only'));
p.checks.forEach(c => {
  const name = 'Q' + c.q + ' answer ' + c.a, block = [];
  for (let i = c.at - 1; i < lines.length && lines[i].trim(); i++) block.push(lines[i].trim());
  const via = (block.map(l => l.match(/^Script: .* via (\S+)$/i)).find(Boolean) || [])[1] || null;
  posts.push({q: c.q, a: c.a, who: c.who, via});
  if (!block.some(l => /^I opened the link myself\b/i.test(l))) extra.push(name + ': the line "I opened the link myself." is missing from the post');
  if (c.saw.some(s => !solid(s.text))) extra.push(name + ' has a Saw: line with nothing in it (a dot or a question mark is not an answer)');
  if (c.fresh && !solid(c.fresh)) extra.push(name + ' has a New: line with nothing in it');
  const general = c.saw.some(s => !s.line && solid(s.text));
  c.lines.forEach(n => { if (!general && !c.saw.some(s => s.line === n && solid(s.text))) extra.push(name + ': no Saw: for line ' + n); });
});
console.log(JSON.stringify({
  checks: p.checks.length,
  held: r.held.filter(h => h.post.type === 'check').map(h => 'Q' + h.post.q + ' answer ' + h.post.a + ': ' + h.why)
    .concat(extra),
  add: r.add.reduce((n, a) => n + a.posts.length, 0),
  posts
}));
"""


class Refused(Exception):
    """Something the person has to fix or know (bad input, a stale file, a script that failed), not a crash."""


def sha8(name):
    return hashlib.sha256((ROOT / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()[:8]


def ledger_data():
    """ledger.json, if build.py wrote it from the ledger.txt that is on disk."""
    path = ROOT / "ledger.json"
    if not path.exists():
        raise Refused("no ledger.json: ask the person to run python build.py (it rewrites the pages, so not in a vote week)")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data["ledger"]["sha256"] != hashlib.sha256((ROOT / "ledger.txt").read_bytes().replace(b"\r\n", b"\n")).hexdigest():
        raise Refused("ledger.json was not written from this ledger.txt: stop and tell the person. python build.py "
                      "rewrites it (and the pages), so it is theirs to run, and not in a vote week")
    return data


# --rpc: http(s), a plain host or an IPv6 literal, a port, then anything printable. No user:password@, no space, no
# non-ASCII, no control character: an error from the HTTP library echoes parts of the address, and the host goes into a post.
RPC_URL = re.compile(r"(https?)://(?:([A-Za-z0-9.-]+)|\[([0-9A-Fa-f:]+)\])(?::([0-9]{1,5}))?(?:[/?#][!-~]*)?")


def check_rpc(url, name="--rpc"):
    """--rpc, or SOLANA_RPC: the https address of a Solana node, or http for a node on this machine (common.py's own
    example). The message never repeats the address: one that does not parse can still hold a key."""
    m = RPC_URL.fullmatch(url)
    if not m or (m.group(4) and int(m.group(4)) > 65535) or (m[1] == "http" and (m[2] or m[3]).lower() not in LOOPBACK):
        raise Refused("%s takes the https address of a Solana node (http only for a node on your own machine)" % name)
    return url


def is_loopback(via):
    return re.sub(r":\d+$", "", via).strip("[]") in LOOPBACK


def source_of(num, rpc=None):
    """The host version 3's fact num's scripts read from, as the Script: line names it."""
    if num in RPC_FACTS:
        return host_of(rpc if rpc is not None else common.RPC)
    try:
        m = re.search(LINK_FACTS[num], common.entry(num))
    except (KeyError, SystemExit):
        m = None
    return host_of(m.group(m.lastindex or 0)) if m else "unknown"


def fact_of(a):
    """The version 3 fact an answer copies, if checks/ has a script for it (a promise has none)."""
    kind, num = a.get("copies") or (None, None)
    return num if kind == "FACT" and num in SCRIPTS else None


def plural(n, word):
    return "%d %s%s" % (n, word, "" if n == 1 else "s")


def status_text():
    d = ledger_data()
    rows = ["ledger.txt %s | process.md %s" % (sha8("ledger.txt"), sha8("process.md")),
            "members: " + ", ".join(d["members"]),
            "open votes: " + ("; ".join("%s, %s" % (v["subject"], v["how"]) for v in d["open_votes"]) or "none")]
    for q in d["questions"]:
        rows.append("Q%d %s (opened %s)" % (q["num"], q["state"]["state"], q["opened"]))
        for a in q["answers"]:
            num = fact_of(a)
            rows.append("  answer %-3d posters %s; %s, %s, %s, script %s" % (
                a["num"], ", ".join(a["posters"]), plural(a["lines"], "WRONG IF line"), plural(len(a["results"]), "check"),
                a["state"]["state"], "fact %d's, reads %s" % (num, source_of(num)) if num else "no"))
    return "\n".join(rows)


def verdict_of(outputs):
    """One word for the fact from its scripts' "verdict:" lines, or None if any script printed none."""
    words = [VERDICT.search(o) for o in outputs]
    if not words or not all(words):
        return None
    got = {w.group(1) for w in words}
    return next((w for w in ("DOESN'T HOLD", "CAN'T TELL") if w in got), "HOLDS")


def execute(num, say=lambda s: None, rpc=None):
    """Run the fact's scripts: (the commands as typed, their outputs). A script that fails or hangs stops everything.
    rpc points the scripts that read the node at another one."""
    if num not in SCRIPTS:
        raise Refused("fact %d has no script in checks/: open its link and look" % num)
    if rpc is not None and num not in RPC_FACTS:
        raise Refused("fact %d reads a link, not the Solana node: --rpc does nothing here" % num)
    # SOLANA_RPC is checked like --rpc: it is how the MCP server sets the node, and a malformed one put its key in an error
    url = (check_rpc(rpc) if rpc is not None else check_rpc(common.RPC, "SOLANA_RPC") if num in RPC_FACTS else common.RPC)
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", **({"SOLANA_RPC": rpc} if rpc is not None else {})}
    if not _busy.acquire(blocking=False):
        raise Refused("another script run is still going: wait for it")
    try:
        cmds, outs = [], []
        for spec in SCRIPTS[num]:
            name, *args = spec.split()
            say("running python checks/%s ..." % spec)
            try:
                done = subprocess.run([sys.executable, str(HERE / name), *args], cwd=ROOT, capture_output=True, text=True,
                                      encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL, timeout=SCRIPT_TIMEOUT,
                                      creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                                      env=env)
            except subprocess.TimeoutExpired:
                raise Refused("python checks/%s ran over %d seconds and was stopped" % (spec, SCRIPT_TIMEOUT))
            shown = redact(done.stdout, url) if num in RPC_FACTS else done.stdout
            if done.returncode:
                raise Refused("python checks/%s failed:\n%s%s" % (spec, shown, redact(done.stderr, url)))
            cmds.append("python checks/" + spec)
            outs.append(shown)
        return cmds, outs
    finally:
        _busy.release()


def script_line(cmds, word, when, source):
    """What ran and whose it is (the weekly page keeps both in the SEEN item), what it said, on which ledger, when, and
    where it read from: two results that name one source are one witness, so lint says so."""
    return "Script: %s by %s said %s on ledger %s at %s via %s" % (
        " and ".join(cmds), AUTHOR, word or "no verdict", sha8("ledger.txt"), when, source)


def run_entry(num, say=lambda s: None, rpc=None):
    """(the scripts' output, the closing Script: line)."""
    cmds, outs = execute(num, say, rpc)
    word = verdict_of(outs)
    when = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")   # the ledger's dates are UTC
    return "\n".join(outs), script_line(cmds, word, when, source_of(num, rpc))


def check_name(who):
    if not NAME.fullmatch(who):
        raise Refused("--as takes your name as it appears in the chat: one line of letters, digits, spaces, . ' and -, "
                      "at most 40 characters")


def draft_post(q, a, who, date, word, script):
    """The CHECK post on question q's answer a for a person to finish. It leaves out "I opened the link myself." on
    purpose, and it is checked to hold nothing but the header, empty Line/Saw/New lines and one Script: line, whatever
    it was given."""
    check_name(who)
    n = a["lines"]
    head = "CHECK Q%d ANSWER %d · %s · lines %s · %s · %s" % (
        q["num"], a["num"], word or "RESULT", ",".join(map(str, range(1, n + 1))), who, date)
    post = "\n".join([head] + ["Line %d:\nSaw:" % i for i in range(1, n + 1)] + ["New:", script]) + "\n"
    if "opened the link" in post.lower() or not all(POST_LINE.fullmatch(ln) for ln in post.splitlines()):
        raise Refused("the draft would hold more than a header, empty lines and one Script: line; not printing it")
    return post


def draft(qn, an, who, say=lambda s: None, rpc=None):
    """(the post, notes for the person). The answer and the name are checked before a script that can take minutes."""
    check_name(who)
    data = ledger_data()
    q = next((x for x in data["questions"] if x["num"] == qn), None)
    a = q and next((x for x in q["answers"] if x["num"] == an), None)
    if not a:
        raise Refused("the ledger has no Q%d answer %d" % (qn, an))
    num = fact_of(a)
    if num is None:
        raise Refused("Q%d answer %d copies no version 3 fact that has a script in checks/: open its link and look"
                      % (qn, an))
    cmds, outs = execute(num, say, rpc)
    word = verdict_of(outs)
    if word == "CAN'T TELL":
        raise Refused("the script says CAN'T TELL: that is not a result, so there is nothing to post")
    when = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    notes = [] if who in data["members"] else ["%s is not a member, so a post by them is an outsider's (rule 4)" % who]
    if who in a["posters"]:
        notes.append("%s posted or changed this answer, so their result counts for nothing (rule 4)" % who)
    if AUTHOR in a["posters"]:   # Saw: a script none of the answer's posters wrote
        notes.append("%s, who wrote these scripts, is among this answer's posters, so a result that leans on them is no "
                     "Saw (WORDS USED HERE): open every link by hand, and say so." % AUTHOR)
    if any("NOT SETTLED" in o for o in outs):   # the script's verdict covers only part of the answer's WRONG IF lines
        word = None
        notes.append("The script leaves part of this answer unsettled (NOT SETTLED in its output): the result and the "
                     "lines are yours to decide, and those lines are by hand.")
    line = script_line(cmds, verdict_of(outs), when, source_of(num, rpc))
    return draft_post(q, a, who, when[:10], word, line), notes + [NEXT_STEP]


def source_notes(posts, data):
    """One note for each answer where two checkers (members other than its posters) name the same node: that is one
    witness, not two. Only answers that copy a fact read from the node, since --rpc is what changes it; a node on a
    member's own machine is their own."""
    answers = {(q["num"], a["num"]): a for q in data["questions"] for a in q["answers"]}
    members = {m.lower() for m in data["members"]}
    by = {}
    for p in posts:
        a = answers.get((p["q"], p["a"]))
        via = (p["via"] or "").rstrip(".,;)").lower()   # a person's full stop after the host is not a second source
        via = via[:-4] if via.endswith(":443") else via    # nor is https's own port written out
        if (a and fact_of(a) in RPC_FACTS and via and via != "unknown" and not is_loopback(via)
                and p["who"].lower() in members and p["who"].lower() not in {x.lower() for x in a["posters"]}):
            by.setdefault((p["q"], p["a"], via), set()).add(p["who"])
    return ["Q%d answer %d: %s all read via %s, which is one source, not two. What makes them two checks is the link "
            "each opened by hand and the new thing each named; a second node (--rpc) is a second source."
            % (q, a, " and ".join(sorted(who)), via) for (q, a, via), who in sorted(by.items()) if len(who) > 1]


def lint(text, data, now=None):
    """The reasons the weekly page, or this helper, would hold this post back. An empty list means it would go in."""
    return review(text, data, now)[0]


def review(text, data, now=None):
    """(the reasons to hold the post back, notes that hold nothing back). More than one post in the text is fine: the
    notes compare them."""
    node = shutil.which("node")
    if not node:
        raise Refused("lint needs node (test_claims.js does too)")
    payload = {"text": text, "data": data, "now": now or dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d"),
               "claims": str(ROOT / "assets" / "claims.js")}
    done = subprocess.run([node, "-e", NODE], input=json.dumps(payload), capture_output=True, text=True, encoding="utf-8",
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if done.returncode:
        raise Refused("node failed:\n" + done.stderr)
    out = json.loads(done.stdout)
    notes = source_notes(out["posts"], data)
    if not out["checks"]:
        return ["no CHECK line found: the first line is CHECK Q n ANSWER k · HOLDS or DOESN'T HOLD · lines 1,2 · "
                "Name · YYYY-MM-DD"], notes
    if not out["held"] and not out["add"]:
        return ["nothing to add: the ledger already has this result"], notes
    return out["held"], notes


def read_post(arg):
    """The post's text from a file or stdin, as bytes decoded here: UTF-8, or UTF-16 (what PowerShell's > writes)."""
    try:
        raw = sys.stdin.buffer.read() if arg == "-" else Path(arg).read_bytes()
        return raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8-sig")
    except (OSError, UnicodeError) as e:
        raise Refused("cannot read the post: %s" % e)


def options(args, allowed):
    """{--as: name, --rpc: node} from the words after the numbers. An option that is not allowed here, one given twice
    or one with no value is refused: a typo (--rcp, --rpc=URL) or an empty $NODE must not run on the default node."""
    got = {}
    for i in range(0, len(args), 2):
        name = args[i]
        if name not in allowed or name in got:
            raise Refused("%r is not an option here, or is given twice (this command takes %s; put a name with a space in "
                          "quotes)" % (name, " ".join(allowed)))
        if i + 1 >= len(args):
            raise Refused("%s needs a value after it" % name)
        got[name] = args[i + 1]
    return got


def main(argv):
    for stream in (sys.stdout, sys.stderr):   # a name or a page outside the console's code page must not crash a long run
        getattr(stream, "reconfigure", lambda **k: None)(encoding="utf-8")
    cmd = argv[1] if len(argv) > 1 else ""
    err = lambda s: print(s, file=sys.stderr)   # noqa: E731
    num = lambda i: int(argv[i]) if len(argv) > i and argv[i].isascii() and argv[i].isdigit() else None   # noqa: E731
    try:
        if cmd == "status":
            print(status_text())
        elif cmd == "run" and num(2) is not None:
            out, line = run_entry(num(2), err, options(argv[3:], ("--rpc",)).get("--rpc"))
            print(out + "\n" + line)
        elif cmd == "draft" and num(2) is not None and num(3) is not None:
            opt = options(argv[4:], ("--as", "--rpc"))
            if "--as" not in opt:
                raise Refused("draft needs --as <your name in the chat>")
            post, notes = draft(num(2), num(3), opt["--as"], err, opt.get("--rpc"))
            print(post, end="")
            err("\n".join(notes))
        elif cmd == "lint" and len(argv) > 2:
            why, notes = review("\n\n".join(read_post(a) for a in argv[2:]), ledger_data())
            print("\n".join(why) if why else "ok: the weekly page would take this post")
            print("".join("note: %s\n" % n for n in notes), end="")
            sys.exit(1 if why else 0)
        else:
            print(__doc__)
            sys.exit(2)
    except Refused as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main(sys.argv)
