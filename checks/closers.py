"""Who closes the entries? Anyone can run this; it reads a file, needs no key and posts nothing.

    python checks/closers.py             ledger.txt in this checkout
    python checks/closers.py FILE        a saved copy, such as the file whose hash was last posted
    python checks/closers.py --test      offline tests

Rule 3 closes an entry when two members other than its writer post the same result, and it trusts that those two
checked apart. Two who share a blind spot, or agree in advance, can close a false fact. This prints, for every entry
rule 3 has closed, its writer, its two closers and the day it closed, read by build.py's own entry_state(), so this
and the pages cannot disagree. Then the totals: entries written and closes made per name, closes per pair of
closers, and the share of all closes taken by the busiest pair and by the busiest closer. A pair that made at least
half the closes, or a writer who wrote at least half the closed entries, gets a FLAG line for the group to read. It
is a reading, not a rule: no line fails. The output is plain text for the weekly turn to paste into the chat.
Exit: 0 when it ran, 2 when nothing has closed yet, 1 when the file cannot be read.
"""
import hashlib
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import build  # noqa: E402  the site's own reading of the file


def tally(text):
    """The closed entries as (entry, result, writer, (closer, closer), day), and the counts, from the file's text.
    A WITHDRAWN promise counts nowhere."""
    secs = build.sections(text)[1]
    names, on = build.member_names(secs), build.adopted(secs)
    rows, written = [], Counter()
    for _, kind, num, who, fields in (it for it in build.entries(build.entries_section(secs)[1]) if it[0] == "entry"):
        st = build.entry_state(kind, who, fields, names, on)
        if st["state"] == "WITHDRAWN":
            continue
        author = build.writer(who, fields, names)
        written[author] += 1
        if st["state"] in build.CLOSED and st["by"]:   # a promise withdrawn late is BROKEN with no closers: not rule 3
            rows.append(("%s %s" % (kind.lower(), num), build.state_text(st, kind, fields), author, tuple(sorted(st["by"])),
                         st["since"]))
    n = len(rows)
    closed = Counter(r[2] for r in rows)
    pairs = Counter(" and ".join(r[3]) for r in rows)
    flags = ["FLAG: %s made %s, at least half. Rule 3 trusts two closers who check apart." % (p, share(c, n, "closes"))
             for p, c in ranked(pairs) if 2 * c >= n]
    flags += ["FLAG: %s wrote %s, at least half." % (w, share(c, n, "closed entries")) for w, c in ranked(closed)
              if 2 * c >= n]
    return {"rows": rows, "written": written, "closed": closed, "closers": Counter(x for r in rows for x in r[3]),
            "pairs": pairs, "flags": flags}


def ranked(counts):
    """Most first, then by name, so a tie always prints the same way."""
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))


def share(c, n, what):
    return "%d of the %d %s (%d%%)" % (c, n, what, 100 * c / n + 0.5)   # half rounds up


def busiest(counts, n, on=""):
    """Every name tied at the top, with its share of all closes."""
    top = ranked(counts)[0][1]
    return "%s, %s%s" % ("; ".join(k for k, c in ranked(counts) if c == top), on, share(top, n, "closes"))


def report(t, name, sha):
    n = len(t["rows"])
    out = ["Who closed what: %s %s..., read by build.py." % (name, sha[:8])]
    if not n:
        out.append("Nothing has closed under rule 3 yet.")
    else:
        out.append("Closed under rule 3: %d entr%s." % (n, "y" if n == 1 else "ies"))
        out += ["- %s, %s: written by %s, closed by %s on %s." % (e, res, w, " and ".join(by), day)
                for e, res, w, by, day in t["rows"]]
    out.append("Entries written: %s." % ", ".join("%s %d (%d closed)" % (w, c, t["closed"][w])
                                                  for w, c in ranked(t["written"])))
    if n:
        out.append("Closes per closer: %s." % ", ".join("%s %d" % kv for kv in ranked(t["closers"])))
        out.append("Closes per pair: %s." % ", ".join("%s %d" % kv for kv in ranked(t["pairs"])))
        out.append("Busiest pair: %s." % busiest(t["pairs"], n))
        out.append("Busiest closer: %s." % busiest(t["closers"], n, "one of the two on "))
        out += t["flags"]
    return "\n".join(out)


def main(argv):
    if "--test" in argv:
        import test_closers
        for name in sorted(n for n in dir(test_closers) if n.startswith("test_")):
            getattr(test_closers, name)()
            print("ok", name)
        return 0
    path = Path(argv[0]) if argv else ROOT / "ledger.txt"
    try:
        raw = build.raw_text(path)
        t = tally(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, SystemExit) as e:   # build.py stops on a file it cannot read, and says why
        print("%s cannot be read: %s" % (path.name, e))
        return 1
    print(report(t, path.name, hashlib.sha256(raw).hexdigest()))
    return 0 if t["rows"] else 2


if __name__ == "__main__":
    sys.stdout.reconfigure(errors="replace")
    sys.exit(main(sys.argv[1:]))
