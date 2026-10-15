"""The Assembly's live record: who seconded which entry and who checked it, in one SQLite file next to this script,
and the ledger page served with the record filled in. A first slice for the dry run; it runs on this machine only.

    python live/server.py            the site on http://127.0.0.1:8767, with ledger.html wired to the record
    python live/server.py export     the nightly job: the record's SECONDED and SEEN lines into ledger.txt, then
                                     python build.py

The entries stay in ledger.txt. Each time the record opens it copies their number, kind, writer, dates and text
from there, and it adds what the text cannot take by itself: seconds and checks. Nothing in the record is changed
or deleted once written (rule 2); SQLite refuses it.

A claim needs a second before anyone checks it: someone other than its writer says they want it checked and that
its WRONG IF lines test what it says. This is proposed, not yet in the ledger's rules.

The stranger lane: with ASSEMBLY_STRANGERS=1 as well, someone with no claim may post a check (never a second) under a
name that is not a member's. Rule 3 already says what that is worth: with another stranger or a member, two of them
posting the other result reopen a closed entry or split an open one; they never close one. The record keeps a salted
hash of the poster's address, so one source posts once per entry and only a few times a day, and never shows it.

Who you are: with ASSEMBLY_CLAIMS_URL set (the site's /api/claim), every post carries the token the front page's name
claim gave that device, and the name comes from asking that endpoint whose token it is. The typed name is ignored.
ponytail: without it, who you are is a name you type, so anyone can post as anyone. Fine on one machine for the dry
run; the version anyone else can reach sets it. A token proves a device holds the claim, not who is at it.
"""
import datetime as dt
import hashlib
import http.server
import ipaddress
import json
import os
import re
import secrets
import sqlite3
import sys
import textwrap
import urllib.error
import urllib.parse
import urllib.request
from contextlib import contextmanager
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import build  # noqa: E402  (the ledger's own reader)

DB = HERE / "record.db"
PORT = 8767
CLAIMS = os.environ.get("ASSEMBLY_CLAIMS_URL", "")          # set: posts need a claimed device (see the top)
STRANGERS = os.environ.get("ASSEMBLY_STRANGERS") == "1"     # with CLAIMS: checks from outside the seven, no claim
HANDLE = re.compile(r"[A-Za-z0-9][A-Za-z0-9 ._'-]{1,39}")   # a stranger's name: plain ASCII, so no lookalike of a member's
STRANGER_PER_ENTRY = 6                                      # checks from outside the seven one entry takes in all
STRANGER_PER_DAY = 5                                        # checks one source may post in 24 hours
SALT = HERE / "salt"
NOTATION = "That has notation the ledger keeps off its pages. Say it in words."
SERVED = {".html", ".css", ".js", ".txt", ".svg", ".png", ".ico", ".ics"}   # what the page needs, nothing else
CANT_TELL_DAYS = 30                                         # rule 4
RESULTS = {"FACT": ("HOLDS", "DOESN'T HOLD"), "PROMISE": ("KEPT", "BROKEN")}
NAME = re.compile(r"[A-Za-z0-9][\w .'-]{0,39}")
DATE = re.compile(r"\d{4}-\d\d-\d\d")
LONGEST = 1000                                              # characters in one answer
MOST_MINUTES = 600
NOBODY = "    SEEN      nobody yet"
RECORD_FIELD = re.compile(r"    (SECONDED|SEEN)(?: {2,}|$)")
LIVE_HEAD = '<link rel="stylesheet" href="/live/live.css"><script src="/live/live.js" defer></script></head>'

SCHEMA = """
CREATE TABLE IF NOT EXISTS entries(num INTEGER PRIMARY KEY, kind TEXT NOT NULL, writer TEXT NOT NULL, posted TEXT,
  due TEXT, says TEXT NOT NULL, test TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS seconds(id INTEGER PRIMARY KEY, num INTEGER NOT NULL REFERENCES entries(num),
  who TEXT NOT NULL, at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS checks(id INTEGER PRIMARY KEY, num INTEGER NOT NULL REFERENCES entries(num),
  who TEXT NOT NULL, result TEXT NOT NULL, saw TEXT NOT NULL, tested TEXT NOT NULL, new TEXT NOT NULL,
  minutes INTEGER NOT NULL, at TEXT NOT NULL);
""" + "".join("""
CREATE TRIGGER IF NOT EXISTS {0}_not_rewritten BEFORE UPDATE ON {0} BEGIN SELECT RAISE(ABORT, 'rule 2'); END;
CREATE TRIGGER IF NOT EXISTS {0}_not_removed BEFORE DELETE ON {0} BEGIN SELECT RAISE(ABORT, 'rule 2'); END;
""".format(t) for t in ("seconds", "checks"))
# ponytail: rule 2 lets personal information become "[removed]"; the triggers refuse that too, until someone needs it


class Refused(Exception):
    """A post the rules turn away. Its message is shown to the person as it is."""


class NotSignedIn(Refused):
    """The post carries no claim, or one the claim service does not know. Answered 401."""


def connect(path=DB):
    conn = sqlite3.connect(path, isolation_level=None)      # writes open their own transaction (write below)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    if not any(c["name"] == "via" for c in conn.execute("PRAGMA table_info(checks)")):
        conn.execute("ALTER TABLE checks ADD COLUMN via TEXT")   # null for a member; a stranger's source hash
    return conn


@contextmanager
def write(conn):
    """One transaction that holds the lock from its first read, so two posts cannot both pass the same check."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")


def now():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


# ---------------------------------------------------------------------------------------------------------------
# The ledger's text in, the record's lines out.

def read_ledger(text):
    """(the members, in the Member line's order; the entries, as rows for the entries table)."""
    secs = build.sections(text)[1]
    found = []
    for item in build.entries(build.entries_section(secs)[1]):
        if item[0] != "entry":
            continue
        _, kind, num, who, fields = item
        f = {label: " ".join(ln.txt for ln in lines if ln.txt) for label, lines in fields}
        writer = who.split(",")[0].strip()
        if writer == "the group":                           # rule 3: such an entry's writer is who proposed it
            m = re.search(r"(\w+) proposed it", f.get("CHANGED", ""))
            writer = m.group(1) if m else writer
        posted, due = DATE.search(who), DATE.search(f.get("BY", ""))
        found.append(dict(num=int(num), kind=kind, writer=writer, posted=posted and posted.group(0),
                          due=due and due.group(0), says=f[build.HEADLINE[kind]],
                          test=f.get("WRONG IF") or f.get("KNOWN BY", "")))
    return build.member_names(secs), found


def seed(conn, entries):
    with write(conn):
        for e in entries:
            conn.execute("INSERT INTO entries VALUES(:num, :kind, :writer, :posted, :due, :says, :test) ON CONFLICT(num) "
                         "DO UPDATE SET kind=:kind, writer=:writer, posted=:posted, due=:due, says=:says, test=:test", e)


def rows(conn, table, num):
    return [dict(r) for r in conn.execute("SELECT * FROM %s WHERE num=? ORDER BY id" % table, (num,))]


def stop(s):
    return s if s[-1:] in ".!?" else s + "."


def wrap(first, text, rest):
    return textwrap.wrap(text, width=build.WIDTH, initial_indent=first, subsequent_indent=rest,
                         break_long_words=False, break_on_hyphens=False)


def record_lines(conn, num):
    """The entry's SECONDED and SEEN lines as the ledger writes them, from the record: one dash per check."""
    out = []
    seconds, checks = rows(conn, "seconds", num), rows(conn, "checks", num)
    if seconds:
        out += wrap("    SECONDED  ", "; ".join("%s, %s" % (s["who"], s["at"][:10]) for s in seconds), " " * 14)
    if not checks:
        return out + [NOBODY]
    for i, c in enumerate(checks):
        text = "- %s, %s: %s. Saw: %s Tested: %s New: %s %d minute%s." % (
            c["who"], c["at"][:10], c["result"], stop(c["saw"]), stop(c["tested"]), stop(c["new"]), c["minutes"],
            "" if c["minutes"] == 1 else "s")
        out += wrap("    SEEN      " if i == 0 else " " * 14, text, " " * 16)
    return out


def field_texts(lines):
    """{SECONDED or SEEN: its text, spacing collapsed} for an entry's lines of the two."""
    out, label = {}, None
    for line in lines:
        m = RECORD_FIELD.match(line)
        if m:
            label, line = m.group(1), line[m.end():]
        out[label] = (out.get(label, "") + " " + line.strip()).strip()
    return out


def kept(old, new):
    """Whether everything the ledger already shows for an entry is still in what the record writes now. The record
    only grows, so an earlier export is the beginning of a later one; anything else was written by hand."""
    were, are = field_texts(old), field_texts(new)
    return all(are.get(k, "").startswith(v) for k, v in were.items() if v != "nobody yet")


def export_text(conn, text):
    """The ledger's text with each entry's SECONDED and SEEN lines written from the record. Stops, rather than
    drop them, at lines the record does not hold (rule 2)."""
    lines, out, num, old, i = text.split("\n"), [], None, [], 0
    while i < len(lines):
        raw = lines[i]
        if raw[:1].strip():                                 # a heading: past the entries
            num = None
        m = build.ENTRY.match(raw)
        if m:
            num = int(m.group(2))
        f = RECORD_FIELD.match(raw) if num is not None else None
        if not f:
            out.append(raw)
            i += 1
            continue
        j = i + 1
        while j < len(lines) and lines[j].strip() and build.indent(lines[j]) > 4:
            j += 1
        old, i = old + lines[i:j], j
        if f.group(1) == "SEEN":
            new = record_lines(conn, num)
            if not kept(old, new):
                sys.exit("entry %d: ledger.txt has SECONDED or SEEN lines the record does not; put them in the record "
                         "first, so nothing is lost (rule 2)" % num)
            out, old = out + new, []
    return "\n".join(out)


def refuse_banned(text):
    """Stop before writing what the build would refuse: a post that got past the filters would otherwise fail every
    deploy, and the record cannot take it back (rule 2)."""
    hit = build.BANNED.search(text)
    if hit:
        sys.exit("export stopped: %r in the record's text is notation the ledger keeps off its pages. Nothing was written; "
                 "find the post and let the weekly turn put '[removed]' there by hand (rule 2)." % hit.group())


def export():
    raw = build.raw_text(build.LEDGER).decode("utf-8")
    conn = connect()
    seed(conn, read_ledger(raw.rstrip("\n"))[1])
    new = export_text(conn, raw)
    conn.close()
    refuse_banned(new)
    if new != raw:
        build.LEDGER.write_bytes(new.encode("utf-8"))
    print("export: ledger.txt %s" % ("rewritten from the record" if new != raw else "already matches the record"))
    build.main()


# ---------------------------------------------------------------------------------------------------------------
# Rules 3 and 4, and the two kinds of post.

def standing(writer, members, checks, at):
    """Rules 3 and 4 over one entry's checks, oldest first: (state, results, since). state is OPEN, CLOSED, SPLIT
    (kept open or reopened: two people each posted a different result) or CAN'T TELL (split for 30 days). since is
    where the posts that count now begin: a reopened entry closes counting only posts made after it reopened."""
    members = {m.lower() for m in members}
    state, results, since, split_at = "OPEN", [], 0, None
    for i, c in enumerate(checks):
        people = {}
        for p in checks[since:i + 1]:
            if p["who"].lower() != writer.lower():
                people.setdefault(p["result"], set()).add(p["who"].lower())
        two = sorted(r for r, who in people.items() if len(who) >= 2)
        if state == "CLOSED":
            rivals = [r for r in two if r != results[0]]
            if rivals:
                state, results, since, split_at = "SPLIT", results + rivals[:1], i + 1, c["at"]
        elif len(two) >= 2:
            if state == "OPEN":
                state, results, since, split_at = "SPLIT", two, i + 1, c["at"]
        else:
            closing = [r for r in two if len(people[r] & members) >= 2]
            if closing:
                state, results, since = "CLOSED", closing, i + 1
    if state == "SPLIT" and at - dt.datetime.fromisoformat(split_at) >= dt.timedelta(days=CANT_TELL_DAYS):
        state = "CAN'T TELL"
    return state, results, since


def entry(conn, num):
    row = conn.execute("SELECT * FROM entries WHERE num=?", (num,)).fetchone()
    if row is None:
        raise Refused("There is no entry %d." % num)
    return dict(row)


def view(conn, members, num, at):
    """One entry as the page shows it: the entries row, its seconds and checks, and where it stands."""
    e = entry(conn, num)
    e["seconds"] = rows(conn, "seconds", num)
    e["checks"] = [{k: v for k, v in c.items() if k != "via"} for c in rows(conn, "checks", num)]   # the source stays private
    e["state"], e["results"], _ = standing(e["writer"], members, e["checks"], at)
    return e


def listing(conn, members, at):
    return {"members": members, "signin": bool(CLAIMS), "strangers": bool(CLAIMS and STRANGERS),
            "entries": [view(conn, members, r["num"], at) for r in conn.execute("SELECT num FROM entries ORDER BY num")]}


def name(body, members):
    who = " ".join(str(body.get("who") or "").split())
    if not NAME.fullmatch(who):
        raise Refused("Type your name: letters and numbers, at most 40 characters.")
    if build.BANNED.search(who):
        raise Refused(NOTATION)
    return next((m for m in members if m.lower() == who.lower()), who)


def fold(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def words(s):
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def stranger_name(body, members):
    """The name a stranger posts under: plain ASCII, and not any member's, however it is spaced or capitalised."""
    who = " ".join(str(body.get("who") or "").split())
    if not HANDLE.fullmatch(who):
        raise Refused("Pick a name to post under: 2 to 40 letters (A to Z), numbers, spaces or . _ ' -")
    if build.BANNED.search(who):
        raise Refused(NOTATION)
    mine = words(who)
    if fold(who) in {fold(m) for m in members} or any(
            re.search("(?<![a-z0-9])%s(?![a-z0-9])" % re.escape(words(m)), mine) for m in members):
        raise Refused("That name is, or holds, a member's name. Members post from the device that claimed it. "
                      "Pick another name.")
    return who


def source_of(address):
    """A salted hash of where a post came from: enough to tell two posts came from one place, not to find the place.
    An IPv6 address counts as its /64, the size one customer is given, so one household is one source."""
    try:
        ip = ipaddress.ip_address(address.split("%")[0])
        if ip.version == 6:
            address = str(ipaddress.ip_network((ip, 64), strict=False))
    except ValueError:
        pass
    if not SALT.exists():
        SALT.write_text(secrets.token_hex(16))
    return hashlib.sha256((SALT.read_text() + address).encode()).hexdigest()[:16]


def ask_claims(token, url=None):
    """(status, body) from the claim endpoint for this token: whose device is it."""
    req = urllib.request.Request(url or CLAIMS, headers={"Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, {}


def sign_in(body, auth, ask=ask_claims):
    """body with `who` set to the name that claimed the token in the Authorization header, whatever was typed."""
    token = re.sub(r"^Bearer\s+", "", auth or "", flags=re.I).strip()
    if not token:
        raise NotSignedIn("Claim your name on the front page first, then post from the same device.")
    try:
        status, got = ask(token)
    except (OSError, ValueError):
        raise Refused("The name claim did not answer. Post again in a minute.") from None
    if status == 401:
        raise NotSignedIn("This device has no claim, or it was reissued. Claim your name on the front page again.")
    if status != 200 or not NAME.fullmatch(str(got.get("name", ""))):
        raise Refused("The name claim did not answer. Post again in a minute.")
    return dict(body, who=got["name"])


def answer(body, key, label):
    s = " ".join(str(body.get(key) or "").split())
    if not s:
        raise Refused("%s is empty." % label)
    if len(s) > LONGEST:
        raise Refused("%s is longer than %d characters." % (label, LONGEST))
    if build.BANNED.search(s):
        raise Refused("%s has notation the ledger keeps off its pages. Say it in words." % label)
    return s


def second(conn, members, num, body, at):
    e = entry(conn, num)
    who = name(body, members)
    if who.lower() == e["writer"].lower():
        raise Refused("You wrote this entry. Someone else has to second it.")
    if body.get("tests") is not True:
        raise Refused("Tick the box to second it. If its test does not check what it says, say so in the chat instead.")
    with write(conn):
        if any(s["who"].lower() == who.lower() for s in rows(conn, "seconds", num)):
            raise Refused("You have already seconded this entry.")
        conn.execute("INSERT INTO seconds(num, who, at) VALUES(?, ?, ?)", (num, who, at.isoformat()))
    return view(conn, members, num, at)


def check(conn, members, num, body, at, via=None):
    """via: set for a stranger (the source hash). Rule 3 then does the rest: a name outside the Member line counts
    toward keeping open or reopening an entry and never toward closing it."""
    e = entry(conn, num)
    who = stranger_name(body, members) if via else name(body, members)
    if who.lower() == e["writer"].lower():
        raise Refused("Nobody checks their own entry (rule 3).")
    if e["kind"] == "PROMISE" and not e["due"]:
        raise Refused("This promise has no date yet, so nobody can check it.")
    if e["kind"] == "PROMISE" and at.date().isoformat() < e["due"]:
        raise Refused("This promise can be checked on or after %s." % e["due"])
    if body.get("result") not in RESULTS[e["kind"]]:
        raise Refused("Pick a result: %s or %s." % RESULTS[e["kind"]])
    saw = answer(body, "saw", "What you saw")
    tested = answer(body, "tested", "What you tested")
    new = answer(body, "new", "The thing nobody has written yet")
    minutes = body.get("minutes")
    if type(minutes) is not int or not 0 < minutes <= MOST_MINUTES:
        raise Refused("Say how many minutes it took, from 1 to %d." % MOST_MINUTES)
    if body.get("opened") is not True:
        raise Refused("Tick the box only if you opened the link yourself. An AI may help you look; it never posts.")
    with write(conn):
        if not rows(conn, "seconds", num):
            raise Refused("This entry needs a second before anyone checks it.")
        checks = rows(conn, "checks", num)
        since = standing(e["writer"], members, checks, at)[2]
        if any(c["who"].lower() == who.lower() for c in checks[since:]):
            raise Refused("You have already posted a check on this entry. If you see it differently now, say so in "
                          "the chat.")
        if via:
            if any(c["via"] == via for c in checks[since:]):
                raise Refused("A check has already come from your connection on this entry. If you see it differently "
                              "now, say so in the chat.")
            if sum(1 for c in checks if c["via"]) >= STRANGER_PER_ENTRY:
                raise Refused("This entry already has %d checks from outside the seven. Say it in the chat." % STRANGER_PER_ENTRY)
            day_ago = (at - dt.timedelta(days=1)).isoformat()
            if conn.execute("SELECT count(*) FROM checks WHERE via=? AND at>?", (via, day_ago)).fetchone()[0] >= STRANGER_PER_DAY:
                raise Refused("That is as many checks as one connection posts in a day. Come back tomorrow.")
        # ponytail: catches a copied "new thing" only word for word; a person still has to read it
        if any(c["new"].lower() == new.lower() for c in checks):
            raise Refused("Someone already posted that as their new thing. Name something nobody has written yet.")
        conn.execute("INSERT INTO checks(num, who, result, saw, tested, new, minutes, at, via) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     (num, who, body["result"], saw, tested, new, minutes, at.isoformat(), via))
    return view(conn, members, num, at)


# ---------------------------------------------------------------------------------------------------------------
# The site, as Vercel serves it, plus the record.

def with_record(act):
    """Run act(conn, members) on the record, after copying the entries in from ledger.txt as it stands."""
    members, found = read_ledger(build.raw_text(build.LEDGER).decode("utf-8").rstrip("\n"))
    conn = connect()
    try:
        seed(conn, found)
        return act(conn, members)
    finally:
        conn.close()


def ledger_page():
    """ledger.html built from ledger.txt as it stands (nothing written to disk), wired to the record."""
    raw = build.raw_text(build.LEDGER)
    steps = build.raw_text(build.STEPS).decode("utf-8").rstrip("\n")
    page, _ = build.ledger_page(raw.decode("utf-8").rstrip("\n"), raw, steps)
    return page.replace("</head>", LIVE_HEAD, 1)


def servable(path):
    """Whether the record's server may hand this path out: a page or what it loads, never the salt, the database, the
    source or anything hidden. The check is on the decoded path, so %-escapes and .. get no further."""
    p = urllib.parse.unquote(path.split("?")[0].split("#")[0])
    parts = [x for x in p.split("/") if x]
    if chr(92) in p or any(x.startswith(".") for x in parts):
        return False
    if parts[:1] == ["live"]:
        return p in ("/live/live.js", "/live/live.css")
    return Path(p).suffix.lower() in SERVED


def host_ok(host):
    """Only this machine's own name, so a page on another site cannot reach the record by rebinding its address."""
    return host in ("127.0.0.1:%d" % PORT, "localhost:%d" % PORT)


class Handler(http.server.SimpleHTTPRequestHandler):
    timeout = 15                                            # a connection that stalls is dropped, not held

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(build.ROOT), **kwargs)

    def send(self, code, body, kind):
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def json(self, code, data):
        self.send(code, json.dumps(data).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self):
        if not host_ok(self.headers.get("Host")):
            return self.json(403, {"error": "This record answers on this machine only."})
        path = self.path.split("?")[0]
        if path == "/":
            self.send_response(302)
            self.send_header("Location", "/ledger.html")
            self.end_headers()
        elif path == "/ledger.html":
            self.send(200, ledger_page().encode("utf-8"), "text/html; charset=utf-8")
        elif path == "/api/entries":
            self.json(200, with_record(lambda conn, members: listing(conn, members, now())))
        elif servable(path):
            super().do_GET()
        else:
            self.json(404, {"error": "Nothing is served at that address."})

    def do_POST(self):
        if not host_ok(self.headers.get("Host")):
            return self.json(403, {"error": "This record answers on this machine only."})
        m = re.fullmatch(r"/api/entries/(\d+)/(second|check)", self.path)
        if not m:
            return self.json(404, {"error": "Nothing is posted at that address."})
        # JSON only: a page on another site can send a plain-text form here without asking, but not JSON
        if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
            return self.json(415, {"error": "Send the post as JSON."})
        size = int(self.headers.get("Content-Length") or 0)
        if not 0 < size <= 16384:
            return self.json(413, {"error": "The post is empty or too long."})
        try:
            body = json.loads(self.rfile.read(size))
        except ValueError:
            return self.json(400, {"error": "The post is not JSON."})
        if not isinstance(body, dict):
            return self.json(400, {"error": "The post is not a set of answers."})
        num, kind, auth = int(m.group(1)), m.group(2), self.headers.get("Authorization")
        # ponytail: the source is the connection's address; behind a proxy it needs the proxy's forwarded address
        via = source_of(self.client_address[0]) if CLAIMS and STRANGERS and not auth and kind == "check" else None
        try:
            if CLAIMS and not via:
                body = sign_in(body, auth)
            act = second if kind == "second" else (lambda *a: check(*a, via=via))
            self.json(201, with_record(lambda conn, members: act(conn, members, num, body, now())))
        except NotSignedIn as e:
            self.json(401, {"error": str(e)})
        except Refused as e:
            self.json(400, {"error": str(e)})


def main():
    if sys.argv[1:] == ["export"]:
        return export()
    if STRANGERS and not CLAIMS:
        sys.exit("ASSEMBLY_STRANGERS needs ASSEMBLY_CLAIMS_URL: without sign-in every post is a typed name.")
    if not CLAIMS:
        print("note: no ASSEMBLY_CLAIMS_URL, so names are typed and anyone can post as anyone (this machine only)", flush=True)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print("the live ledger: http://127.0.0.1:%d/ledger.html (record: %s)" % (PORT, DB), flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
