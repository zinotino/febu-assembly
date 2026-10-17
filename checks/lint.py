"""Does ledger.txt keep its own rules? Anyone can run this; it reads files, needs no key and posts nothing.

    python checks/lint.py                    ledger.txt in this checkout against git HEAD's: run it before you commit
    python checks/lint.py --rev HEAD~1       against an earlier commit: run it after you commit
    python checks/lint.py --prev FILE        against a saved copy, such as the file whose hash was last posted
    python checks/lint.py --test             offline tests

It checks the file, not a chat post (`agent.py lint` checks a post). One line per rule it can test:
  I1  nothing rewritten (rule 6): a proposal only gains yeses and its "Opened as" line; a question only gains NOTE
      lines and answers; an answer only grows (SEEN items, CHANGED and NOTE lines under the old ones; "nobody yet"
      giving way to the first SEEN item); and the rest of the file only gains lines in PROPOSED QUESTIONS, THE
      QUESTIONS, VOTES, LAST POSTS and CHANGES TO THE RULES, gives up its "None yet" lines there, and raises its "next"
      numbers. Any other change passes only when CHANGES TO THE RULES names an archive/ copy of the earlier version with
      its SHA-256, as a new version does on the day it is adopted. An answer reworded under a CHANGED line is such a
      change too: I5 asks for the line, I1 for the copy. Text replaced by "[removed]" (rule 6) passes if the rest of
      its line is kept, in what a proposal, question, answer or objection says; never in a name or date rule 4 counts
      by (an answer's header, a proposer, a yes, a SEEN item up to Saw:, a CHANGED line up to its colon, a vote) nor
      anywhere else in the file.
  I2  proposals P1 to Pn, questions Q1 to Qn and each question's answers numbered from 1, in order, with no gap or
      repeat, and the "next" numbers one past the last (Number); each question opened from the proposal and on the day
      rule 2 gives, and each "Opened as Q n" under the proposal its question names
  I3  no SEEN item by one of its answer's posters, or on a script one of them wrote: it counts for nothing (rule 4, Saw)
  I4  no SEEN item while STATUS says Proposed, before its answer's first day (adoption, the question's opening, the
      answer's own date), or after today; and no other date the file's state is read from (a proposal, a yes, a
      question's opening, an answer's header, a CHANGED line, a vote, a LAST POSTS line) after today or off the
      calendar
  I5  an answer that had a SEEN item never changes and gains no CHANGED line; an answer that does change gains a
      CHANGED line; and every CHANGED line names who changed it and when ("Name, YYYY-MM-DD:"), on or before its
      answer's first SEEN item (HOW A QUESTION IS WRITTEN, Posters)
  I6  every SEEN item reads in the weekly page's form, and every Yes: item as "Name YYYY-MM-DD"; one that does not is
      listed for a person to read (rule 7)
  I7  every SEEN item says HOLDS or DOESN'T HOLD and names WRONG IF lines its answer has (Result)
  I9  every archive/ copy the file names is there, with the SHA-256 printed beside it (rule 8)
There is no I8: version 3's bonds are gone (rule 9). A SEEN item that does not read (I6) is not tested by I3, I4 or I7:
a person reads it. Exit: 0 when nothing FAILs, 1 when a line FAILs, 2 when there was no earlier version to compare.
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
GROWS = ("SEEN", "CHANGED", "NOTE")                               # an answer's fields that only gain lines
GAINS = ("PROPOSED QUESTIONS", "THE QUESTIONS", "VOTES", "LAST POSTS", "CHANGES TO THE RULES")   # sections that gain lines
NONE = re.compile(r"\s*None\b")                                   # "None yet.": gives way to the section's first item
NAMED = re.compile(r"\barchive/[\w.-]+\.txt\b")
NEXT = re.compile(r"The next (proposal is P|question is Q) ?(\d{1,6})\.")
LABEL = re.compile(r"^\s*[A-Z]{2,}(?: [A-Z]+)?\s+")   # "      SAYS      ", at the start only


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
    """(sections, the state build.py reads from them: members, proposals, questions and answers, rule 2's order)."""
    try:
        secs = build.sections(text)[1]
        return secs, build.model(secs)
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


def same(new, old, head=None):
    """new is old, or old with parts replaced by "[removed]". With head, the text up to and including its first
    occurrence in old (who and when, which rule 4 counts by) is kept whole."""
    if new == old:
        return True
    if not keeps(new, old):
        return False
    i = old.find(head) if head else 0
    return i >= 0 and (not head or new[:i + len(head)] == old[:i + len(head)])


def prefix(new, old, head=None):
    """Whether the list old is the start of the list new, item by item (each kept or "[removed]" past head)."""
    return len(new) >= len(old) and all(same(n, o, head) for n, o in zip(new, old))


def shape(head, fields):
    """An answer as I1 and I5 compare it: (its header, the fixed fields in order, each growing field's lines, SEEN items)."""
    fixed = [(lab, " ".join(ln.txt for ln in ls if ln.txt)) for lab, ls in fields if lab not in GROWS]
    grows = {lab: [" ".join(ln.txt for ln in ls if ln.txt) for l2, ls in fields if l2 == lab] for lab in GROWS}
    return head, fixed, grows, build.seen_items(fields)


def answer_change(old, new):
    """What changed in one answer, or None: the first field that changed, other than by growing."""
    (oh, of, og, oi), (nh, nf, ng, ni) = old, new
    if nh != oh:   # who posted it, and when: rule 4 sets them aside (Posters)
        return "header"
    if len(nf) != len(of) or any(nl != ol or not same(nt, ot) for (nl, nt), (ol, ot) in zip(nf, of)):
        return next((ol for (nl, nt), (ol, ot) in zip(nf, of) if nl != ol or not same(nt, ot)), "fields")
    if oi and not prefix(ni, oi, " Saw:"):
        return "SEEN items"
    said = " ".join(og["SEEN"])
    if not oi and said and not re.fullmatch(r"(?i)nobody yet", said) and not " ".join(ng["SEEN"]).startswith(said):
        return "SEEN"
    for lab, head in (("CHANGED", ": "), ("NOTE", None)):
        if not prefix(ng[lab], og[lab], head):
            return lab
    return None


def proposal_change(old, new):
    """What changed in one proposal, or None: it may only gain Yes: items and its "Opened as" line."""
    if not (new["who"] == old["who"] and new["date"] == old["date"] and same(new["asks"], old["asks"])):
        return "header"
    if new["said"][:len(old["said"])] != old["said"]:
        return "Yes: line"
    if old["opened"] is not None and new["opened"] != old["opened"]:
        return "Opened as line"
    return None


def question_change(old, new):
    """What changed in one question other than its answers, or None: it may only gain NOTE lines."""
    if new["head"] != old["head"]:
        return "header"
    fixed = lambda q: [(lab, " ".join(ln.txt for ln in ls if ln.txt)) for lab, ls in q["fields"] if lab != "NOTE"]  # noqa: E731
    notes = lambda q: [" ".join(ln.txt for ln in ls if ln.txt) for lab, ls in q["fields"] if lab == "NOTE"]  # noqa: E731
    o, n = fixed(old), fixed(new)
    if len(n) != len(o) or any(nl != ol or not same(nt, ot) for (nl, nt), (ol, ot) in zip(n, o)):
        return "fields"
    if not prefix(notes(new), notes(old)):
        return "NOTE"
    return None


def places(text):
    """Each line's (proposal or question such as "P2" or "Q1", or None for the ledger's other text; its section)."""
    out, cur, sec = [], None, ""
    for raw in text.split("\n"):
        p = build.PROPOSAL.match(raw) if sec == "PROPOSED QUESTIONS" else None
        q = build.QUESTION.match(raw) if sec == "THE QUESTIONS" else None
        if p or q:
            cur = "P%s" % p.group(1) if p else "Q%s" % q.group(1)
        elif raw[:1].strip():
            cur, sec = None, build.short(raw)
        elif raw.strip() and build.indent(raw) <= 2:
            cur = None
        out.append((cur, sec))
    return out


def text_changes(prev, new):
    """The ledger's text outside the proposals and questions, earlier against new: ([removed] count, changes as
    (where, text)). Lines may be added in GAINS, a "None ..." line there may go, a "next" number may rise, and an
    objection in VOTES may have words replaced by "[removed]"."""
    def lines(text):
        return [(i + 1, sec, raw) for i, (raw, (item, sec)) in enumerate(zip(text.split("\n"), places(text)))
                if item is None and raw.strip()]
    a, b = lines(prev), lines(new)
    removed, out = 0, []

    def added(j):
        if b[j][1] not in GAINS:
            out.append(("line %d, added" % b[j][0], b[j][2]))

    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, [x[2] for x in a], [x[2] for x in b],
                                                      autojunk=False).get_opcodes():
        if op == "equal":
            continue
        pairs = min(i2 - i1, j2 - j1) if op == "replace" else 0
        left = set(range(j1, j2))                                          # the new lines not matched to an old one
        for off in range(i2 - i1):
            k, sec, old = a[i1 + off]
            got = b[j1 + off][2] if off < pairs else None
            m, n = NEXT.search(old), NEXT.search(got or "")
            if (m and n and m.group(1) == n.group(1) and int(n.group(2)) > int(m.group(2))
                    and old.replace(m.group(), "") == got.replace(n.group(), "")):
                left.discard(j1 + off)                                     # "the next proposal" goes up as they are added
            elif (got is not None and sec == "VOTES" and not build.VOTE_HEAD.match(old)
                  and same(got, old, ": " if old.lstrip().startswith("- ") else None)):
                left.discard(j1 + off)                                     # an objection's words, not who or when
                removed += 1
            elif not (NONE.match(old) and sec in GAINS[:4]):               # a placeholder gives way to the first item
                out.append(("line %d" % k, old))
        for j in sorted(left):
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


def ordinal(n):
    return "%d%s" % (n, "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))


def lint(new, prev, archive, today):
    """Rows of (status, what) for the new text against the earlier one (None when there is none to compare)."""
    try:
        return _lint(new, prev, archive, today)
    except (Unreadable, ValueError) as e:
        return [(FAIL, "the lint cannot read ledger.txt: %s" % e)]


def compare(prev, new, old_m, m, have, add):
    """I1 and the comparing half of I5: the earlier version against this one, item by item and line by line."""
    removed, changes = text_changes(prev, new)
    firsts = 0
    props = {p["num"]: p for p in m["proposals"]}
    for p in old_m["proposals"]:
        what = proposal_change(p, props[p["num"]]) if p["num"] in props else "proposal, gone"
        if what:
            changes.append(("P%d" % p["num"], "its %s changed" % what))
    qs = {q["num"]: q for q in m["questions"]}
    for q in old_m["questions"]:
        if q["num"] not in qs:
            changes.append(("Q%d" % q["num"], "the question is gone"))
            if any(build.checked(a["fields"]) for a in q["answers"]):
                add(FAIL, "I5 Q%d had a SEEN item in the earlier version, and it is gone" % q["num"])
            continue
        nq = qs[q["num"]]
        what = question_change(q, nq)
        if what:
            changes.append(("Q%d" % q["num"], "its %s changed" % what))
        now = {a["num"]: a for a in nq["answers"]}
        for a in q["answers"]:
            label, checked = "Q%d answer %d" % (q["num"], a["num"]), build.checked(a["fields"])
            if a["num"] not in now:
                changes.append((label, "the answer is gone"))
                if checked:
                    add(FAIL, "I5 %s had a SEEN item in the earlier version, and it is gone" % label)
                continue
            na = now[a["num"]]
            old_shape, new_shape = shape(a["head"], a["fields"]), shape(na["head"], na["fields"])
            what = answer_change(old_shape, new_shape)
            gained = len(new_shape[2]["CHANGED"]) - len(old_shape[2]["CHANGED"])
            if not a["results"] and na["results"]:
                firsts += 1
            if checked and na["results"][:len(a["results"])] != a["results"]:
                what = what or "SEEN results"
            if what:
                changes.append((label, "its %s changed" % what))
            if checked and what:
                add(FAIL, "I5 %s had a SEEN item in the earlier version, and its %s changed; an answer never changes "
                    "after its first check: post a new answer" % (label, what))
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


def numbering(secs, m, today):
    """I2 rows: the numbers, the links between proposals and questions, and rule 2's order of openings."""
    props, qs, rows = m["proposals"], m["questions"], []

    def add(status, what):
        rows.append((status, what))

    for what, nums, word in (("proposals", [p["num"] for p in props], "P"), ("questions", [q["num"] for q in qs], "Q")):
        if nums != list(range(1, len(nums) + 1)):
            add(FAIL, "I2 the %s are numbered %s; one series from %s1, in order, was expected"
                % (what, ", ".join("%s%d" % (word, n) for n in nums), word))
    for q in qs:
        nums = [a["num"] for a in q["answers"]]
        if nums != list(range(1, len(nums) + 1)):
            add(FAIL, "I2 Q%d's answers are numbered %s; 1, 2 and on, in order, was expected"
                % (q["num"], ", ".join(map(str, nums))))
    for name, kind, items in (("PROPOSED QUESTIONS", "proposal is P", props), ("THE QUESTIONS", "question is Q", qs)):
        said = [int(x.group(2)) for x in NEXT.finditer(" ".join(build.section(secs, name))) if kind in x.group()]
        last = max([x["num"] for x in items] or [0])
        if said and said[-1] != last + 1:
            add(FAIL, "I2 the file says the next %s%d; after %s%d it is %s%d" % (kind, said[-1], kind[-1], last, kind[-1],
                                                                                 last + 1))
    by_num = {p["num"]: p for p in props}
    for q in qs:
        p = by_num.get(q["from"])
        if not q["opened"] or q["from"] is None:
            add(FAIL, "I2 Q%d's header does not read \"(opened YYYY-MM-DD, from P n)\"" % q["num"])
        elif not p:
            add(FAIL, "I2 Q%d says it is from P%d, and the file has no P%d" % (q["num"], q["from"], q["from"]))
        elif p["opened"] != q["num"]:
            add(FAIL, "I2 Q%d is from P%d, and P%d says %s" % (q["num"], p["num"], p["num"], "Opened as Q%d" % p["opened"]
                                                              if p["opened"] else "nothing about opening"))
    for p in props:
        if p["opened"] and not any(q["num"] == p["opened"] and q["from"] == p["num"] for q in qs):
            add(FAIL, "I2 P%d says it opened as Q%d, and no Q%d in the file is from P%d" % (p["num"], p["opened"],
                                                                                         p["opened"], p["num"]))
    proposed = build.status(secs)[1]
    seq = m["slot"]
    if qs and not m["adopted"]:
        add(FAIL if proposed else CANT, "I2 %d question(s) in the file while STATUS %s: nothing opens before adoption "
            "(rule 2)" % (len(qs), "says Proposed" if proposed else "gives no \"Adopted on <date>\""))
    elif m["adopted"]:
        for k, q in enumerate(qs):
            if k >= len(seq):
                add(FAIL, "I2 Q%d is in the file, and by the file's own dates rule 2 opens no %s question"
                    % (q["num"], ordinal(k + 1)))
                break
            if (q["from"], q["opened"]) != seq[k]:
                add(FAIL, "I2 Q%d opened %s from P%s; by the file's own dates rule 2 opens P%d on %s"
                    % (q["num"], q["opened"], q["from"], seq[k][0], seq[k][1]))
                break
        else:
            for k in range(len(qs), len(seq)):
                if seq[k][1] <= today:
                    add(WARN, "I2 rule 2 opens P%d as Q%d on %s, and the file does not have it yet: the weekly turn "
                        "adds it (rule 7)" % (seq[k][0], k + 1, seq[k][1]))
    if not any(s == FAIL for s, _ in rows):
        add(OK, "I2 %d proposal(s), %d question(s) and their answers are numbered in order, the next numbers follow, "
            "and each question opened from its proposal on the day rule 2 gives" % (len(props), len(qs)))
    return rows


def _lint(new, prev, archive, today):
    rows = []

    def add(status, what):
        rows.append((status, what))

    secs, m = parse(new)
    proposed = build.status(secs)[1]
    found, have = archive_rows(new, archive)
    rows.extend(found)

    if prev is None:
        add(CANT, "I1 no earlier version to compare: pass --prev FILE or --rev REV")
    else:
        try:
            old_m = parse(prev)[1]
        except Unreadable as e:
            was = sha256(prev)
            if was in have:
                add(OK, "I1 the earlier version (%s...) is another version of the ledger, kept word for word as "
                    "archive/%s: this text replaces it (rule 8)" % (was[:8], have[was]))
            else:
                add(CANT, "I1 the earlier version cannot be read (%s), and the file names no archive/ copy with its "
                    "SHA-256: I1 and I5 compare nothing" % e)
        else:
            compare(prev, new, old_m, m, have, add)

    rows.extend(numbering(secs, m, today))

    adopted, any_items, said_cant = m["adopted"], False, False
    for q in m["questions"]:
        for a in q["answers"]:
            label, res, n_lines = "Q%d answer %d" % (q["num"], a["num"]), a["results"], len(a["lines"])
            any_items = any_items or bool(res)
            if not a["who"] or not a["date"]:                                         # I5
                add(FAIL, "I5 %s's header does not read \"(Name, YYYY-MM-DD)\", so its posters cannot be read" % label)
            for name, date, word, lines, items, script in res:
                item = "%s: %s's SEEN item of %s" % (label, name, date)
                if name in a["posters"]:                                              # I3
                    add(WARN, "I3 %s is by one of its posters: it counts for nothing (rule 4)" % item)
                elif script and script[1] in a["posters"]:
                    add(WARN, "I3 %s ran %s's script, a poster's: it counts for nothing (Saw)" % (item, script[1]))
                if not build.a_day(date):                                             # I4
                    add(FAIL, "I4 %s: %s is not a date on the calendar, so it counts toward nothing" % (item, date))
                elif proposed:
                    add(FAIL, "I4 %s is in the file while STATUS says Proposed: posts before adoption close nothing "
                        "and go in no file" % item)
                elif adopted is None and not said_cant:
                    said_cant = True
                    add(CANT, "I4 STATUS says neither Proposed nor \"Adopted on <date>\": SEEN dates are not checked")
                elif a["start"] and date < a["start"]:
                    add(FAIL, "I4 %s is dated before %s, the first day %s's results count (adoption, the question's "
                        "opening, the answer's own date)" % (item, a["start"], label))
                if date > today:
                    add(FAIL, "I4 %s is dated after today (%s, UTC)" % (item, today))
                if word not in ("HOLDS", "DOESN'T HOLD"):                             # I7
                    add(FAIL, "I7 %s says %s; a result is HOLDS or DOESN'T HOLD" % (item, word))
                if not lines:
                    add(FAIL, "I7 %s names no WRONG IF line" % item)
                elif any(n < 1 or n > n_lines for n in lines):
                    add(FAIL, "I7 %s names line(s) %s; %s has %d WRONG IF line(s)" % (item, list(lines), label, n_lines))

            changed = build.changes(a["fields"])                                       # I5
            if (None, None) in changed:
                add(FAIL, "I5 %s: a CHANGED line does not start \"Name, YYYY-MM-DD:\", so who changed it cannot be "
                    "read (Posters)" % label)
            dates = [r[1] for r in res]
            if dates and any(d and d > min(dates) for _, d in changed):
                add(FAIL, "I5 %s: a CHANGED line is dated after its first SEEN item (%s)" % (label, min(dates)))

            unread = [it for it in build.seen_items(a["fields"]) if not build.SEEN_ITEM.match(it.replace("’", "'"))]
            for it in unread:                                                         # I6
                add(WARN, "I6 %s: a SEEN item a script cannot read, for a person to check: %r" % (label, it[:70]))
            if build.checked(a["fields"]) and not build.seen_items(a["fields"]):
                add(WARN, "I6 %s: SEEN says more than \"nobody yet\" but holds no item in the weekly page's form" % label)

    for p in m["proposals"]:
        for y in p["unread"]:
            add(WARN, "I6 P%d: a Yes: item that does not read as \"Name YYYY-MM-DD\", for a person to check: %r"
                % (p["num"], y[:70]))
    for where, what, date in dated(m):                                                # I4
        if not build.a_day(date):
            add(FAIL, "I4 %s: %s, %s, is not a date on the calendar" % (where, what, date))
        elif date > today:
            add(FAIL, "I4 %s: %s is dated %s, after today (%s, UTC); the file's state is read up to its last date"
                % (where, what, date, today))

    blurbs = {"I3": "no SEEN item is by its answer's posters or on a script one of them wrote",
              "I4": ("every SEEN item is on or after its answer's first day and not after today, and every other "
                     "date the state is read from is a day on the calendar, not after today") if any_items else
                    "no SEEN item in the weekly page's form yet, and every date the state is read from is a day on the "
                    "calendar, not after today",
              "I5": "no checked answer has changed, every change has its CHANGED line, and every CHANGED line names "
                    "who and when, before its answer's first SEEN item",
              "I6": "every SEEN item and every Yes: item reads in the weekly page's form",
              "I7": "every SEEN item says HOLDS or DOESN'T HOLD and names WRONG IF lines its answer has"}
    for key, text in blurbs.items():
        if not any(s.startswith(key + " ") for _, s in rows):
            add(OK, "%s %s" % (key, text))
    return sorted(rows, key=lambda r: int(r[1][1]) if re.match(r"I\d ", r[1]) else 0)


def dated(m):
    """(where, what, date) for every date the model reads other than SEEN items (those are tested with their answer)."""
    out = []
    for p in m["proposals"]:
        out.append(("P%d" % p["num"], "%s's proposal" % p["who"], p["date"]))
        out += [("P%d" % p["num"], "%s's yes" % n, d) for n, d in p["yes"]]
    for q in m["questions"]:
        for a in q["answers"]:
            where = "Q%d answer %d" % (q["num"], a["num"])
            out += [(where, "its header", a["date"])] if a["date"] else []
            out += [(where, "%s's CHANGED line" % w, d) for w, d in build.changes(a["fields"]) if d]
        out += [("Q%d" % q["num"], "its opening", q["opened"])] if q["opened"] else []
    for v in m["votes"]:
        out.append(("VOTES, %s" % v["subject"], "the day it was posted", v["posted"]))
        out += [("VOTES, %s" % v["subject"], "%s's vote" % n, d) for n, d, _ in v["votes"]]
    for day, row in m["last"]:
        out.append(("LAST POSTS", "the line", day))
        out += [("LAST POSTS, %s" % day, "%s's last post" % n, d) for n, d in row.items() if d]
    return out


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
