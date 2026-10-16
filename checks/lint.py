"""Does ledger.txt keep its own rules? Anyone can run this; it reads files, needs no key and posts nothing.

    python checks/lint.py                    ledger.txt in this checkout against git HEAD's: run it before you commit
    python checks/lint.py --rev HEAD~1       against an earlier commit: run it after you commit
    python checks/lint.py --prev FILE        against a saved copy, such as the file whose hash was last posted
    python checks/lint.py --test             offline tests

It checks the file, not a chat post (`agent.py lint` checks a post). One line per rule it can test:
  I1  nothing rewritten (rule 2): an entry only grows (SEEN items, CHANGED, NOTE, UNPAID and WITHDRAWN lines added
      under the old ones; "nobody yet" giving way to the first SEEN item; new entries), and the rest of the file only
      gains lines in CHANGES TO THE RULES and a higher "next entry" number. Any other change passes only when CHANGES TO
      THE RULES names an archive/ copy of the earlier version with its SHA-256. Text replaced by "[removed]" passes if
      the rest of its line is kept.
  I2  entries numbered 1 to n, in order, with no gap and no repeat, and "the next entry" is n + 1 (Number)
  I3  no SEEN item by the entry's writer (rule 3)
  I4  no SEEN item while STATUS says Proposed, on or before the day of adoption, or after today; and none on a promise
      before its BY date (rule 3, STATUS)
  I5  an entry that had a SEEN item never changes and gains no CHANGED line; an entry that does change gains a dated
      CHANGED line; and every CHANGED line is dated on or before its entry's first SEEN item (HOW AN ENTRY IS WRITTEN)
  I6  every SEEN item reads in the weekly page's form; one that does not is listed for a person to read (rule 6)
  I7  every SEEN item names a result its kind has, and WRONG IF lines its entry has (Result)
  I8  nobody whose bond shows UNPAID has posted a promise since (Bond)
  I9  every archive/ copy the file names is there, with the SHA-256 printed beside it (rule 7)
A SEEN item that does not read (I6) is not tested by I3, I4 or I7: a person reads it.
Exit: 0 when nothing FAILs, 1 when a line FAILs, 2 when there was no earlier version to compare.
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
REMOVED = "[removed]"
GROWS = ("SEEN", "CHANGED", "NOTE", "UNPAID", "WITHDRAWN")       # an entry's fields that only gain lines
NAMED = re.compile(r"\barchive/[\w.-]+\.txt\b")
NEXT = re.compile(r"\s*The next entry is number (\d{1,6})\.\s*$")
LABEL = re.compile(r"^\s*[A-Z]{2,}(?: [A-Z]+)?\s+")   # "    SAYS      ", at the start only


class Unreadable(Exception):
    pass


def read(raw):
    """The file as served (LF line ends, whatever the checkout did to them), as text."""
    try:
        return raw.replace(b"\r\n", b"\n").decode("utf-8")
    except UnicodeDecodeError as e:
        raise Unreadable("not UTF-8: %s" % e)


def sha256(data):
    return hashlib.sha256(data.encode("utf-8") if isinstance(data, str) else data).hexdigest()


def parse(text):
    """(sections, entries as (kind, number, who, fields), member names), read the way build.py reads them."""
    try:
        secs = build.sections(text)[1]
        found = build.entries(build.entries_section(secs)[1])
        return secs, [it[1:] for it in found if it[0] == "entry"], build.member_names(secs)
    except SystemExit as e:
        raise Unreadable(str(e))


def keeps(new, old):
    """Whether new is old with parts replaced by "[removed]", each part at least one character, and something other
    than a field label kept. Linear: the kept pieces are found in order."""
    pieces = new.split(REMOVED)
    if len(pieces) < 2 or not re.search(r"\w", LABEL.sub("", "".join(pieces), count=1)):
        return False
    if not (old.startswith(pieces[0]) and old.endswith(pieces[-1])):
        return False
    pos, end = len(pieces[0]), len(old) - len(pieces[-1])
    for p in pieces[1:-1]:
        i = old.find(p, pos + 1, end)
        if i < 0:
            return False
        pos = i + len(p)
    return end > pos


def same(new, old):
    return new == old or keeps(new, old)


def prefix(new, old):
    """Whether the list old is the start of the list new, line by line (each kept or "[removed]")."""
    return len(new) >= len(old) and all(same(n, o) for n, o in zip(new, old))


def shape(who, fields):
    """An entry as I1 and I5 compare it: (who, the fixed fields in order, each growing field's lines, SEEN items)."""
    fixed = [(lab, " ".join(ln.txt for ln in ls if ln.txt)) for lab, ls in fields if lab not in GROWS]
    grows = {lab: [" ".join(ln.txt for ln in ls if ln.txt) for l2, ls in fields if l2 == lab] for lab in GROWS}
    return who, fixed, grows, build.seen_items(fields)


def entry_change(old, new):
    """What changed in one entry, or None: the first field that changed, other than by growing."""
    (ow, of, og, oi), (nw, nf, ng, ni) = old, new
    if not same(nw, ow):
        return "header"
    if len(nf) != len(of) or any(nl != ol or not same(nt, ot) for (nl, nt), (ol, ot) in zip(nf, of)):
        return next((ol for (nl, nt), (ol, ot) in zip(nf, of) if nl != ol or not same(nt, ot)), "fields")
    if oi and not prefix(ni, oi):
        return "SEEN items"
    said = " ".join(og["SEEN"])
    if not oi and said and not re.fullmatch(r"(?i)nobody yet", said) and not " ".join(ng["SEEN"]).startswith(said):
        return "SEEN"
    for lab in GROWS[1:]:
        if not prefix(ng[lab], og[lab]):
            return lab
    return None


def places(text):
    """Each line's (entry such as "FACT 6", or None for the ledger's other text; its section's heading)."""
    out, cur, sec = [], None, ""
    for raw in text.split("\n"):
        m = build.ENTRY.match(raw)
        if m:
            cur = "%s %s" % (m.group(1), m.group(2))
        elif raw[:1].strip():
            cur, sec = None, build.short(raw)
        elif raw.strip() and build.indent(raw) <= 2:
            cur = None
        out.append((cur, sec))
    return out


def text_changes(prev, new):
    """The ledger's text outside the entries, earlier against new: ([removed] count, changes as (where, text))."""
    def lines(text):
        return [(i + 1, sec, raw) for i, (raw, (who, sec)) in enumerate(zip(text.split("\n"), places(text)))
                if who is None and raw.strip()]
    a, b = lines(prev), lines(new)
    removed, out = 0, []

    def added(j):
        if b[j][1] != "CHANGES TO THE RULES":
            out.append(("line %d, added" % b[j][0], b[j][2]))

    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, [x[2] for x in a], [x[2] for x in b],
                                                      autojunk=False).get_opcodes():
        if op == "equal":
            continue
        pairs = min(i2 - i1, j2 - j1) if op == "replace" else 0
        for off in range(i2 - i1):
            k, old = a[i1 + off][0], a[i1 + off][2]
            got = b[j1 + off][2] if off < pairs else None
            m, n = NEXT.match(old), NEXT.match(got or "")
            if m and n and int(n.group(1)) > int(m.group(1)):
                continue                                                  # "the next entry" goes up as entries are added
            if got is not None and keeps(got, old):
                removed += 1
                continue
            out.append(("line %d" % k, old))
        for j in range(j1 + pairs, j2):
            added(j)
    return removed, out


def archive_rows(text, archive):
    """I9: each archive/... copy the file names, against the file and the SHA-256 beside it. (rows, {SHA: name})."""
    rows, have, named = [], {}, sorted(set(NAMED.findall(text)))
    for path in named:
        name = path.split("/", 1)[1]
        f = archive / name
        if not f.is_file():
            rows.append((FAIL, "I9 the file names %s, and archive/ has no such file" % path))
            continue
        got = sha256(f.read_bytes().replace(b"\r\n", b"\n"))
        said = re.search(re.escape(path) + r"\s+SHA-256\s+([0-9a-fA-F]{64})\b", text)
        if said and said.group(1).lower() != got:
            rows.append((FAIL, "I9 the file gives %s the SHA-256 %s..., but the copy in archive/ hashes to %s..." % (
                path, said.group(1)[:8], got[:8])))
        elif said:
            have[got] = name
    if not rows:
        rows.append((OK, "I9 the %d archive/ cop%s the file names %s there, and every SHA-256 printed beside one "
                     "matches" % (len(named), "y" if len(named) == 1 else "ies", "is" if len(named) == 1 else "are")))
    return rows, have


def first_date(text):
    m = build.DATE.search(text)
    return m.group() if m else None


def lint(new, prev, archive, today):
    """Rows of (status, what) for the new text against the earlier one (None when there is none to compare)."""
    try:
        return _lint(new, prev, archive, today)
    except (Unreadable, ValueError) as e:
        return [(FAIL, "the lint cannot read ledger.txt: %s" % e)]


def _lint(new, prev, archive, today):
    rows = []

    def add(status, what):
        rows.append((status, what))

    secs, ents, names = parse(new)
    try:
        body, proposed = build.status(secs)
    except SystemExit as e:
        raise Unreadable(str(e))
    old_ents = None
    if prev is not None:
        try:
            old_ents = parse(prev)[1]
        except Unreadable as e:
            add(CANT, "I1 the earlier version cannot be read (%s): I1 and I5 compare nothing" % e)

    found, have = archive_rows(new, archive)
    rows.extend(found)

    # I1 and the comparing half of I5
    now = {"%s %s" % (k, n): (k, n, w, f) for k, n, w, f in ents}
    if old_ents is None and prev is None:
        add(CANT, "I1 no earlier version to compare: pass --prev FILE or --rev REV")
    elif old_ents is not None:
        removed, changes = text_changes(prev, new)
        firsts = 0
        for k, n, w, f in old_ents:
            label = "%s %s" % (k, n)
            checked = build.checked(f)
            if label not in now:
                changes.append((label, "the entry is gone"))
                if checked:
                    add(FAIL, "I5 %s had a SEEN item in the earlier version, and it is gone" % label)
                continue
            nk, nn, nw, nf = now[label]
            old_shape, new_shape = shape(w, f), shape(nw, nf)
            what = entry_change(old_shape, new_shape)
            gained = len(new_shape[2]["CHANGED"]) - len(old_shape[2]["CHANGED"])
            if not build.results(f) and build.results(nf):
                firsts += 1
            if checked and build.results(nf)[:len(build.results(f))] != build.results(f):
                what = what or "SEEN results"
            if what:
                changes.append((label, "its %s changed" % what))
            if checked and what:
                add(FAIL, "I5 %s had a SEEN item in the earlier version, and its %s changed; an entry never changes "
                    "after its first check" % (label, what))
            elif checked and gained > 0:
                add(FAIL, "I5 %s: a CHANGED line was added after its first SEEN item" % label)
            elif what and gained <= 0:
                add(FAIL, "I5 %s: its %s changed with no new dated CHANGED line" % (label, what))
        was = sha256(prev)
        note = "%d first SEEN item%s, %d [removed]" % (firsts, "" if firsts == 1 else "s", removed)
        if not changes:
            add(OK, "I1 the earlier version (%s...) is all still here; it only grew. %s" % (was[:8], note))
        elif was in have:
            add(OK, "I1 %d change(s) to the earlier version, and the file keeps it as archive/%s. %s"
                % (len(changes), have[was], note))
        else:
            where, txt = changes[0]
            add(FAIL, "I1 %d change(s) to the earlier version (%s...), and the file names no archive/ copy of it with "
                "that SHA-256; the first is %s: %r" % (len(changes), was[:8], where, txt.strip()[:70]))

    # I2
    nums = [n for _, n, _, _ in ents]
    if nums != [str(i) for i in range(1, len(nums) + 1)]:
        add(FAIL, "I2 the entries are numbered %s; one series from 1, in order, was expected" % ", ".join(nums))
    nxt = [int(m.group(1)) for m in map(NEXT.match, new.split("\n")) if m]
    if nxt and nxt[-1] != len(nums) + 1:
        add(FAIL, "I2 the file says the next entry is number %d; after %d entries it is %d" % (
            nxt[-1], len(nums), len(nums) + 1))
    elif nums == [str(i) for i in range(1, len(nums) + 1)]:
        add(OK, "I2 the %d entries are numbered 1 to %d in order%s" % (
            len(nums), len(nums), ", and the next is %d" % nxt[-1] if nxt else ""))

    adopted = build.adopted(secs)
    any_items, said_cant = False, False

    for kind, num, who, fields in ents:
        label = "%s %s" % (kind, num)
        writer = build.writer(who, fields, names)
        res = build.results(fields)
        any_items = any_items or bool(res)

        for name, date, word, lines, *_ in res:
            item = "%s: %s's SEEN item of %s" % (label, name, date)
            if name.strip().casefold() == writer.strip().casefold():               # I3
                add(FAIL, "I3 %s is by its writer; nobody checks their own entry (rule 3)" % item)
            if not build.a_day(date):                                              # I4
                add(FAIL, "I4 %s: %s is not a date on the calendar, so it counts toward nothing" % (item, date))
            if proposed:
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
                by = build.due(fields, adopted)
                if by is None:
                    add(CANT, "I4 %s: the BY line names no date this can read, so its results' dates are not "
                        "checked" % item)
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
        dates = [r[1] for r in res]
        if dates and any(d and d > min(dates) for d in changed):
            add(FAIL, "I5 %s: a CHANGED line is dated after its first SEEN item (%s)" % (label, min(dates)))

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
              "I5": "no checked entry has changed, every change has its CHANGED line, and every CHANGED line comes "
                    "before its entry's first SEEN item",
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
    try:
        new = read((ROOT / "ledger.txt").read_bytes())
    except (OSError, Unreadable) as e:
        print("FAIL       ledger.txt cannot be read: %s" % e)
        return 1
    prev, where = None, args.prev or "git " + args.rev
    try:
        prev = read(Path(args.prev).read_bytes()) if args.prev else read(git_show(args.rev))
    except (OSError, subprocess.CalledProcessError, Unreadable) as e:
        where = "nothing: %s could not be read (%s)" % (where, str(e).strip()[:80])
    print("ledger.txt %s... against %s%s" % (sha256(new)[:8], where, " (%s...)" % sha256(prev)[:8] if prev else ""))
    if prev == new:
        print("  the two are the same file; after you commit, pass --rev HEAD~1 to lint the commit")
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    rows = lint(new, prev, ROOT / "archive", today)
    for status, what in rows:
        print("%-10s %s" % (status, what))
    bad = sum(s == FAIL for s, _ in rows)
    print("\n%d line(s) FAIL, %d WARN, %d CAN'T TELL" % (bad, sum(s == WARN for s, _ in rows), sum(s == CANT for s, _ in rows)))
    return 1 if bad else 2 if any(s == CANT and w.startswith("I1 ") for s, w in rows) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
