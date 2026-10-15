"""Does ledger.txt keep its own rules? Anyone can run this; it reads files, needs no key and posts nothing.

    python checks/lint.py                    ledger.txt in this checkout against git HEAD's: run it before you commit
    python checks/lint.py --rev HEAD~1       against an earlier commit: run it after you commit
    python checks/lint.py --prev FILE        against a saved copy, such as the file whose hash was last posted
    python checks/lint.py --test             offline tests

It checks the file, not a chat post (`agent.py lint` checks a post). One line per rule it can test:
  I1  append-only (rule 2): every line of the earlier version is still there, in order. Three rewrites pass: "nobody
      yet" giving way to the first SEEN item, text replaced by "[removed]", and any rewrite when CHANGES TO THE RULES
      names an archive/ copy of the earlier version with its SHA-256.
  I2  entries numbered 1 to n, in order, with no gap and no repeat (Number)
  I3  no SEEN item by the entry's writer (rule 3)
  I4  no SEEN item while STATUS says Proposed, on or before the day of adoption, or after today; and none on a promise
      before its BY date (rule 3, STATUS)
  I5  an entry that had a SEEN item never changes: no line rewritten, no CHANGED line added; and every CHANGED line is
      dated on or before its entry's first SEEN item (HOW AN ENTRY IS WRITTEN)
  I6  every SEEN item reads in the weekly page's form; one that does not is listed for a person to read (rule 6)
  I7  every SEEN item names a result its kind has, and WRONG IF lines its entry has (Result)
  I8  nobody whose bond shows UNPAID has posted a promise since (Bond)
  I9  every archive/ copy that CHANGES TO THE RULES names is there, with that SHA-256 (rule 7)
A SEEN item that does not read (I6) is not tested by I3, I4 or I7: a person reads it.
"""
import argparse
import datetime as dt
import difflib
import hashlib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import build  # noqa: E402  the site's own reading of the file, so the lint and the pages cannot disagree

OK, WARN, FAIL, CANT = "OK", "WARN", "FAIL", "CAN'T TELL"
NOBODY = re.compile(r"\s*SEEN\s+nobody yet\s*$")
FIRST_ITEM = re.compile(r"\s*SEEN\s+- ")
REMOVED = "[removed]"
ARCHIVED = re.compile(r"archive/([\w.-]+\.txt)\s+SHA-256\s+([0-9a-f]{64})")
ADOPTED = re.compile(r"\bAdopted on (\d{4}-\d\d-\d\d)")
DAYS_AFTER = re.compile(r"(\d+) days after this version is adopted")


def read(raw):
    """The file as served: LF line ends, whatever the checkout did to them."""
    return raw.replace(b"\r\n", b"\n").decode("utf-8")


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse(text):
    """(sections, entries as (kind, number, who, fields), member names), read the way build.py reads them."""
    secs = build.sections(text)[1]
    found = build.entries(build.entries_section(secs)[1])
    return secs, [it[1:] for it in found if it[0] == "entry"], build.member_names(secs)


def owners(text):
    """Each line's entry ("FACT 6"), or None for the ledger's other text: an entry runs to the next line at the edge."""
    out, cur = [], None
    for raw in text.split("\n"):
        m = build.ENTRY.match(raw)
        if m:
            cur = "%s %s" % (m.group(1), m.group(2))
        elif raw.strip() and build.indent(raw) <= 2:
            cur = None
        out.append(cur)
    return out


def rewrites(prev, new):
    """The earlier version's lines that the new one does not keep as they were: (how many gave way to a first SEEN
    item, how many to "[removed]", the rest as (line number, entry or None, text))."""
    a, b = prev.split("\n"), new.split("\n")
    own = owners(prev)
    first, removed, other = 0, 0, []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op in ("equal", "insert"):
            continue
        block = b[j1:j2]
        for k in range(i1, i2):
            if NOBODY.match(a[k]) and any(FIRST_ITEM.match(x) for x in block):
                first += 1
            elif any(REMOVED in x and re.fullmatch(re.escape(x).replace(re.escape(REMOVED), ".+?"), a[k]) for x in block):
                removed += 1
            else:
                other.append((k + 1, own[k], a[k]))
    return first, removed, other


def archive_refs(secs, archive):
    """(name, SHA-256 named, SHA-256 of the file in archive/ or None) for each copy CHANGES TO THE RULES names."""
    body = " ".join(next((b for h, b in secs if build.short(h) == "CHANGES TO THE RULES"), []))
    out = []
    for name, said in ARCHIVED.findall(re.sub(r"\s+", " ", body)):
        path = archive / name
        out.append((name, said, sha256(read(path.read_bytes())) if path.is_file() else None))
    return out


def first_date(text):
    m = build.DATE.search(text)
    return m.group() if m else None


def due(fields, adopted):
    """A promise's BY date: the date it names, or N days after adoption when it says so; None if neither."""
    by = build.text_of(fields, "BY")
    m = DAYS_AFTER.search(by)
    if first_date(by):
        return first_date(by)
    if m and adopted:
        return (dt.date.fromisoformat(adopted) + dt.timedelta(days=int(m.group(1)))).isoformat()
    return None


def lint(new, prev, archive, today):
    """Rows of (status, what) for the new text against the earlier one (None when there is none to compare)."""
    rows = []

    def add(status, what):
        rows.append((status, what))

    try:
        secs, ents, names = parse(new)
        body, proposed = build.status(secs)
    except SystemExit as e:
        return [(FAIL, "the build cannot read ledger.txt: %s" % e)]
    try:
        before = {"%s %s" % (k, n): f for k, n, _, f in parse(prev)[1]} if prev is not None else None
    except SystemExit as e:
        before = None
        add(CANT, "the build cannot read the earlier version (%s): I1 and I5 compare nothing" % e)

    # I9, first: I1 leans on it
    refs = archive_refs(secs, archive)
    broken = [(n, s, got) for n, s, got in refs if got != s]
    for n, s, got in broken:
        add(FAIL, "I9 CHANGES TO THE RULES names archive/%s SHA-256 %s..., but %s" % (
            n, s[:8], "archive/ has no such file" if got is None else "that file hashes to %s..." % got[:8]))
    if not broken:
        add(OK, "I9 the %d archive/ cop%s CHANGES TO THE RULES names %s there, each with its SHA-256" % (
            len(refs), "y" if len(refs) == 1 else "ies", "is" if len(refs) == 1 else "are"))

    # I1
    other = []
    if before is None:
        add(CANT, "I1 no earlier version to compare: pass --prev FILE or --rev REV")
    else:
        first, removed, other = rewrites(prev, new)
        was = sha256(prev)
        kept = next((n for n, s, got in refs if s == was and got == s), None)
        note = "%d first SEEN item%s in place of \"nobody yet\", %d [removed]" % (first, "" if first == 1 else "s", removed)
        if not other:
            add(OK, "I1 every line of the earlier version (%s...) is still there; %s" % (was[:8], note))
        elif kept:
            add(OK, "I1 %d line(s) of the earlier version rewritten, and CHANGES TO THE RULES keeps it as archive/%s; %s"
                % (len(other), kept, note))
        else:
            k, who, txt = other[0]
            add(FAIL, "I1 %d line(s) of the earlier version (%s...) rewritten or removed, and no CHANGES TO THE RULES "
                "line names an archive/ copy of it with that SHA-256; the first is line %d%s: %r"
                % (len(other), was[:8], k, " (%s)" % who if who else "", txt.strip()[:70]))

    # I2
    nums = [int(n) for _, n, _, _ in ents]
    if nums == list(range(1, len(nums) + 1)):
        add(OK, "I2 the %d entries are numbered 1 to %d in order" % (len(nums), len(nums)))
    else:
        add(FAIL, "I2 the entries are numbered %s; one series from 1, in order, was expected" % nums)

    m = ADOPTED.search(re.sub(r"\s+", " ", " ".join(body)))
    adopted = m.group(1) if m and not proposed else None
    any_items, said_cant = False, False

    for kind, num, who, fields in ents:
        label = "%s %s" % (kind, num)
        writer = build.writer(who, fields, names)
        res = build.results(fields)
        any_items = any_items or bool(res)

        for name, date, word, lines in res:
            item = "%s: %s's SEEN item of %s" % (label, name, date)
            if name == writer:                                                     # I3
                add(FAIL, "I3 %s is by its writer; nobody checks their own entry (rule 3)" % item)
            if proposed:                                                           # I4
                add(FAIL, "I4 %s is in the file while STATUS says Proposed: posts before adoption close nothing and "
                    "go in no file" % item)
            elif adopted is None and not said_cant:
                said_cant = True
                add(CANT, "I4 STATUS says neither Proposed nor \"Adopted on <date>\": SEEN dates against adoption "
                    "are not checked")
            elif adopted and date <= adopted:
                add(FAIL, "I4 %s is not after the day of adoption, %s: it was the dry run" % (item, adopted))
            if date > today:
                add(FAIL, "I4 %s is dated after today (%s, UTC)" % (item, today))
            if kind == "PROMISE" and not proposed:
                by = due(fields, adopted)
                if by is None:
                    add(CANT, "I4 %s: the BY line names no date, so its results' dates are not checked" % item)
                elif date < by:
                    add(FAIL, "I4 %s comes before the promise's date, %s" % (item, by))
            if word not in build.RESULTS[kind]:                                    # I7
                add(FAIL, "I7 %s says %s; a %s's result is %s" % (item, word, kind.lower(), " or ".join(build.RESULTS[kind])))
            n_lines = len(build.wrong_if(fields))
            if kind == "FACT" and not lines:
                add(FAIL, "I7 %s names no WRONG IF line" % item)
            elif kind == "FACT" and any(n < 1 or n > n_lines for n in lines):
                add(FAIL, "I7 %s names line(s) %s; %s has %d WRONG IF line(s)" % (item, list(lines), label, n_lines))
            elif kind == "PROMISE" and lines:
                add(FAIL, "I7 %s names WRONG IF lines; a promise has none" % item)

        changed = [first_date(" ".join(ln.txt for ln in ls)) for lab, ls in fields if lab == "CHANGED"]  # I5
        if None in changed:
            add(WARN, "I5 %s: a CHANGED line names no date" % label)
        dates = [d for _, d, _, _ in res]
        if dates and any(d and d > min(dates) for d in changed):
            add(FAIL, "I5 %s: a CHANGED line is dated after its first SEEN item (%s)" % (label, min(dates)))
        old = before.get(label) if before else None
        if old is not None and build.checked(old):
            moved = [k for k, w, _ in other if w == label]
            if moved:
                add(FAIL, "I5 %s had a SEEN item in the earlier version, and its line %d changed; an entry never changes "
                    "after its first check" % (label, moved[0]))
            if len(changed) > sum(1 for lab, _ in old if lab == "CHANGED"):
                add(FAIL, "I5 %s: a CHANGED line was added after its first SEEN item" % label)

        unread = [it for it in build.seen_items(fields) if not build.SEEN_ITEM.match(it.replace("’", "'"))]  # I6
        for it in unread:
            add(WARN, "I6 %s: a SEEN item a script cannot read, for a person to check: %r" % (label, it[:70]))
        if build.checked(fields) and not build.seen_items(fields):
            add(WARN, "I6 %s: SEEN says more than \"nobody yet\" but holds no item in the weekly page's form" % label)

    for kind, num, who, fields in ents:                                            # I8
        if not any(lab == "UNPAID" for lab, _ in fields):
            continue
        writer = build.writer(who, fields, names)
        since = first_date(build.text_of(fields, "UNPAID")) or ""
        later = ["%s %s" % (k, n) for k, n, w, f in ents
                 if k == "PROMISE" and build.writer(w, f, names) == writer and (first_date(w) or "") > since]
        if later:
            add(CANT, "I8 %s %s's bond shows UNPAID (%s), and %s has posted %s since: check by hand that the bond was "
                "paid first" % (kind, num, since or "no date", writer, ", ".join(later)))

    blurbs = {"I3": "no SEEN item is by its entry's writer",
              "I4": ("every SEEN item is after adoption (%s), not after today, and none on a promise before its date"
                     % adopted) if any_items else "no SEEN item in the weekly page's form yet",
              "I5": "no checked entry has changed, and every CHANGED line comes before its entry's first SEEN item",
              "I6": "every SEEN item reads in the weekly page's form",
              "I7": "every SEEN item names a result its kind has and WRONG IF lines its entry has",
              "I8": "nobody whose bond shows UNPAID has posted a promise since"}
    for key, text in blurbs.items():
        if not any(s.startswith(key + " ") for _, s in rows):
            add(OK, "%s %s" % (key, text))
    return sorted(rows, key=lambda r: int(r[1][1]) if re.match(r"I\d ", r[1]) else 0)


def git_show(rev):
    return subprocess.run(["git", "show", "%s:ledger.txt" % rev], cwd=str(ROOT), capture_output=True, check=True).stdout


def main(argv):
    sys.stdout.reconfigure(errors="replace")
    if "--test" in argv:
        import test_lint
        for name in sorted(n for n in dir(test_lint) if n.startswith("test_")):
            getattr(test_lint, name)()
            print("ok", name)
        return 0
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--prev", help="the earlier version, as a file")
    ap.add_argument("--rev", default="HEAD", help="the earlier version, as a git revision (default HEAD)")
    args = ap.parse_args(argv)
    new = read((ROOT / "ledger.txt").read_bytes())
    prev, where = None, args.prev or "git " + args.rev
    try:
        prev = read(Path(args.prev).read_bytes()) if args.prev else read(git_show(args.rev))
    except (OSError, subprocess.CalledProcessError):
        where = "nothing: %s could not be read" % where
    print("ledger.txt %s... against %s%s" % (sha256(new)[:8], where, " (%s...)" % sha256(prev)[:8] if prev else ""))
    if prev == new:
        print("  the two are the same file; after you commit, pass --rev HEAD~1 to lint the commit")
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    rows = lint(new, prev, ROOT / "archive", today)
    for status, what in rows:
        print("%-10s %s" % (status, what))
    bad = sum(s == FAIL for s, _ in rows)
    print("\n%d line(s) FAIL, %d WARN, %d CAN'T TELL" % (bad, sum(s == WARN for s, _ in rows), sum(s == CANT for s, _ in rows)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
