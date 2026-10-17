"""Who closes the answers? Anyone can run this; it reads a file, needs no key and posts nothing.

    python checks/closers.py             ledger.txt in this checkout
    python checks/closers.py FILE        a saved copy, such as the file whose hash was last posted
    python checks/closers.py --test      offline tests

Rule 4 closes an answer when three members other than its posters post the same result, one of them by hand, and it
trusts that those three checked apart. Three who share a blind spot, or agree in advance, can close a false answer. This
prints, for every answer rule 4 has closed, its posters, its closers and the day it closed, read by build.py's own
model(), so this and the pages cannot disagree. Then the totals: answers posted and closed per poster, closes per
closer, closes per set of closers, and the share of all closes taken by the busiest set and by the busiest closer. A set
that made at least half the closes, or a poster on at least half the closed answers, gets a FLAG line for the group to
read. It is a reading, not a rule: no line fails. The output is plain text for the weekly turn to paste into the chat;
rule 9 keeps such totals out of the file and off the group's pages.
Exit: 0 when it ran, 2 when nothing has closed yet, 1 when the file cannot be read.
"""
import hashlib
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import build  # noqa: E402  the site's own reading of the file

CLOSED = ("HOLDS", "DOESN'T HOLD")


def tally(text):
    """The closed answers as (answer, result, posters, closers, day), and the counts, from the file's text."""
    m = build.model(build.sections(text)[1])
    rows, posted = [], Counter()
    for q in m["questions"]:
        for a in q["answers"]:
            ps, st = tuple(sorted(a["posters"])), a["state"]
            posted.update(ps)
            if st["state"] in CLOSED and st["by"]:
                rows.append(("Q%d answer %d" % (q["num"], a["num"]), build.state_text(st), ps, tuple(st["by"]), st["since"]))
    n = len(rows)
    closed = Counter(p for r in rows for p in r[2])
    sets = Counter(", ".join(r[3]) for r in rows)
    flags = ["FLAG: %s made %s, at least half. Rule 4 trusts closers who check apart." % (s, share(c, n, "closes"))
             for s, c in ranked(sets) if 2 * c >= n]
    flags += ["FLAG: %s posted %s, at least half." % (w, share(c, n, "closed answers")) for w, c in ranked(closed)
              if 2 * c >= n]
    return {"rows": rows, "posted": posted, "closed": closed, "closers": Counter(x for r in rows for x in r[3]),
            "sets": sets, "flags": flags}


def ranked(counts):
    """Most first, then by name, so a tie always prints the same way."""
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))


def share(c, n, what):
    return "%d of the %d %s (%d%%)" % (c, n, what, 100 * c / n + 0.5)   # half rounds up


def busiest(counts, n, on=""):
    """Every name tied at the top, with its share of all closes."""
    top = ranked(counts)[0][1]
    return "%s, %s%s" % ("; ".join(k for k, c in ranked(counts) if c == top), on, share(top, n, "closes"))


def names(xs):
    return ", ".join(xs[:-1]) + " and " + xs[-1] if len(xs) > 1 else "".join(xs)


def report(t, name, sha):
    n = len(t["rows"])
    out = ["Who closed what: %s %s..., read by build.py." % (name, sha[:8])]
    if not n:
        out.append("Nothing has closed under rule 4 yet.")
    else:
        out.append("Closed under rule 4: %d answer%s." % (n, "" if n == 1 else "s"))
        out += ["- %s, %s: posted by %s, closed by %s on %s." % (a, res, names(ps), names(by), day)
                for a, res, ps, by, day in t["rows"]]
    out.append("Answers per poster (who posted or changed it, or wrote the fact it copies): %s." % (", ".join(
        "%s %d (%d closed)" % (w, c, t["closed"][w]) for w, c in ranked(t["posted"])) or "none yet"))
    if n:
        out.append("Closes per closer: %s." % ", ".join("%s %d" % kv for kv in ranked(t["closers"])))
        out.append("Closes per set of closers: %s." % "; ".join("%s %d" % kv for kv in ranked(t["sets"])))
        out.append("Busiest set: %s." % busiest(t["sets"], n))
        out.append("Busiest closer: %s." % busiest(t["closers"], n, "one of the closers on "))
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
