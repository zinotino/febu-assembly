"""Build the Assembly's pages, next to this file, from the texts beside them. All share one set of tabs.

  febu-assembly.html  the front page: status, the open question with a check card under each of its open answers (it
                      writes the result post), the proposals waiting for yeses, "your week" by name, every question,
                      and the ledger's HOW TO CHECK AN ANSWER (#check; /start.html redirects there)
  weekly.html   the weekly turn (rule 7): paste the week's chat, get the SEEN items, proposals, yeses and votes to add,
                the answers that would close, a LAST POSTS line and the lines left to read; it never edits ledger.txt
  write.html    the answer form: an answer to the open question laid out for ledger.txt and for the chat
  ledger.html   ledger.txt as a page, in the text's own order: STATUS as a banner, each question with its answers as
                cards (#q-1, #q-1-answer-2), shown as the Assembly's (rule 3)
  how.html      how.txt: the ledger in plain words, with assets/how-it-works.svg and how-it-connects.svg
  process.html  process.md: the whole process in one file, the clock and the tests (needs the markdown package;
                otherwise the committed page is kept while process.md is unchanged)
  tests.html    tests.txt as a page       (background: no tab, and nothing on the front page links it)
  ledger.json   not a page: the ledger's state as data for an agent (ledger_json): the text's hash, the members, the
                proposals, each question and its answers' posters, WRONG IF clauses, results and state, the votes;
                addresses cut, no links

ledger.txt and archive/ are served as they are; ledger.html prints their SHA-256 (rule 7 relies on that hash).
The pages follow the texts' headings, not their line numbers: reword the texts and re-run.
    python build.py
They load nothing from other sites. Styling is assets/findings.css plus assets/ledger.css; the browser side is
assets/claims.js (tap to copy, the hash checks, and the same rules 2, 4, 5 and 8 for the weekly page).
"""
import datetime
import hashlib
from urllib.parse import quote
import html
import json
import re
import sys
from collections import namedtuple
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LEDGER = ROOT / "ledger.txt"
TESTS = ROOT / "tests.txt"
HOW = ROOT / "how.txt"
PROCESS = ROOT / "process.md"

# This notation never goes on a public page.
BANNED = re.compile(r"GF\(3\)|\btrits?\b|(?<![\w=\"'-])[-\u2212]1(?![\d])", re.I)
# Wallet addresses and transaction signatures belong on the ledger page and its raw text only.
ADDRESS = re.compile(r"\b[1-9A-HJ-NP-Za-km-z]{32,}\b")


def raw_text(path):
    """The file as served: one form of line end, whatever the checkout did to them."""
    return path.read_bytes().replace(b"\r\n", b"\n")


def explorer(url):
    """The same record on explorer.solana.com, for a solscan.io link, so no check rests on one explorer (known bug
    4). An account link with nothing after the address is about what the account holds: the explorer's tokens tab.
    Any other account link (its transfers) becomes the explorer's history, newest first; it has no out-only view."""
    m = re.match(r"https://solscan\.io/(tx|account|token)/(\w+)(\S*)$", url)
    if not m:
        return None
    kind, key, rest = m.groups()
    if kind == "tx":
        return "https://explorer.solana.com/tx/" + key
    return "https://explorer.solana.com/address/%s%s" % (key, "" if rest or kind == "token" else "/tokens")


# ---------------------------------------------------------------------------------------------------------------
# Reading the plain text. Its layout carries the structure: numbered rules, labelled rows ("Member     one of the
# seven"), continuation lines indented under the text they continue, and anything indented further than that, or
# lined up in columns, is shown exactly as written (hashes, addresses, templates).

Ln = namedtuple("Ln", "ind txt tag raw")   # indent, text, a note set off to the right, the line without that note
BLANK = Ln(None, "", None, "")

WIDTH = 92                                                  # the text is wrapped near here
NUM = re.compile(r"(?:[PW]?\d+)\.\s+(?=\S)")                # "1. ", "14. ", "W3. "
BULLET = re.compile(r"[-*]\s+(?=\S)")                     # "- a risk", "* a footnote"
LABEL = re.compile(r"[A-Z][a-z]+\s{2,}(?=\S)")              # "Member     one of the seven ..."
HANG = re.compile(r"[A-Z][^:]{0,30}:\s+(?=\S)")             # "Febu:    the wallet ...", continued further in
TABLE_RULE = re.compile(r"^\s*-{4,}(?:\s+-{4,})+\s*$")      # the dashes under a table's header row
TAG = re.compile(r"\s{3,}(\([^()]*\)|\[[^\[\]]*\])\s*$")    # "(changed 2026-10-13)", "[A, ledger entry 6]"
HARD = re.compile(r" \| |\S{30,}|[^:\s]\s{2,}\S")           # a line that only reads right as written
COLUMNS = re.compile(r"[^:.,;!?\s]\s{2,}\S")               # words lined up in columns (not two spaces after a stop)
SUBHEAD = re.compile(r"[A-Z]{4,}\b")                        # "FACT n. (who, date)", over the lines under it


def indent(s):
    return len(s) - len(s.lstrip(" "))


def to_lines(raws):
    out = []
    for raw in raws:
        raw, tag = raw.rstrip(), None
        m = TAG.search(raw)
        if m and (raw[:m.start()].strip() or indent(raw) >= 40):
            raw, tag = raw[:m.start()].rstrip(), m.group(1)
        out.append(Ln(indent(raw), raw.strip(), tag, raw) if raw.strip() else BLANK._replace(tag=tag))
    return out


def sections(text):
    """The title line, then (heading, body lines) for each heading that starts at the left edge."""
    lines = text.split("\n")
    out = []
    for raw in lines[1:]:
        if raw[:1].strip():
            out.append((raw.rstrip(), []))
        elif out:
            out[-1][1].append(raw)
    return lines[0], out


def short(heading):
    return re.split(r"[(:.]", heading, maxsplit=1)[0].strip()


def slug(heading):
    return re.sub(r"[^a-z0-9]+", "-", short(heading).lower()).strip("-")


def titled(title):
    """'THE LEDGER: PROMISES AND FACTS (version 2)' -> ('the ledger: promises and facts', 'version 2')"""
    m = re.match(r"(.*?)\s*\((.*)\)$", title)
    return (m.group(1), m.group(2)) if m else (title, "")


class Doc:
    """How text becomes inline HTML on one page: links to the ledger's sections, rules, known bugs and files."""

    def __init__(self, ledger_sections, base, files=None):
        self.base = base
        self.files = files or {}
        self.secs = {short(h): slug(h) for h, _ in ledger_sections if len(short(h)) >= 5}
        names = "|".join(re.escape(s) for s in sorted(self.secs, key=len, reverse=True)) or "(?!)"
        self.inline = re.compile(
            r"(?P<url>https?://[^\s<>\"]+)|(?P<file>\b(?:archive/)?\w[\w.-]*\.(?:txt|py)\b)|(?P<tok>\b[0-9A-Za-z]{32,}\b)"
            r"|(?P<bug>\bKNOWN BUGS \d+)|(?P<sec>\b(?:%s)(?![\w-]))|(?P<rule>\b[Rr]ules? \d+(?:(?:, | and | to )\d+)*)"
            % names)

    def fmt(self, text):
        out, pos, e = [], 0, html.escape
        for m in self.inline.finditer(text):
            out.append(e(text[pos:m.start()]))
            pos, s, kind = m.end(), m.group(), m.lastgroup
            if kind == "url":
                url = s.rstrip(".,;:)")
                alt = explorer(url)
                out.append('<a href="%s" rel="noopener noreferrer">%s</a>%s%s' % (e(url), e(url), (
                    ' <a class="alt" href="%s" rel="noopener noreferrer" title="the same on a second explorer">'
                    '(explorer.solana.com)</a>' % e(alt)) if alt else "", e(s[len(url):])))
            elif kind == "file":
                href = self.files.get(s)
                out.append('<a href="%s">%s</a>' % (e(href), e(s)) if href else e(s))
            elif kind == "tok":
                out.append('<code class="tok" title="tap to copy">%s</code>' % s)
            elif kind == "sec":
                out.append('<a href="%s#%s">%s</a>' % (self.base, self.secs[s], e(s)))
            else:
                anchor = {"rule": "rule-", "bug": "bug-"}[kind]
                out.append(re.sub(r"\d+", lambda d: '<a href="%s#%s%s">%s</a>' % (self.base, anchor, d.group(), d.group()), s))
        out.append(e(text[pos:]))
        return "".join(out)

    def tags(self, lines):
        return "".join(' <span class="tag">%s</span>' % self.fmt(ln.tag) for ln in lines if ln.tag)

    def para(self, lines):
        parts = []
        for k, ln in enumerate(lines):
            parts.append(self.fmt(ln.txt))
            if k + 1 < len(lines):   # a line that stops well short of the margin was ended on purpose
                reach = len(ln.raw) + 1 + len(lines[k + 1].txt.split(" ", 1)[0])
                ended = reach <= WIDTH - 14 or ln.txt.endswith("?") or (reach <= WIDTH and ln.txt[-1] in '.!:)"')
                parts.append("<br>" if ended else " ")
        return "<p>%s%s</p>" % ("".join(parts), self.tags(lines))

    def pre(self, lines):
        base = min(ln.ind for ln in lines if ln.txt)
        body = "\n".join(self.fmt(ln.raw[base:]) + self.tags([ln]) for ln in lines)
        return '<pre class="lit">%s</pre>' % body

    def table(self, lines):
        rule = lines[1].raw
        cols = [m.start() for m in re.finditer(r"-+", rule)]
        cut = lambda raw: [raw[a:b].strip() for a, b in zip(cols, cols[1:] + [None])]
        head, rows = cut(lines[0].raw), []
        for ln in lines[2:]:
            cells = cut(ln.raw)
            if rows and not cells[0]:
                rows[-1] = [(a + " " + b).strip() for a, b in zip(rows[-1], cells)]
            else:
                rows.append(cells)
        th = "".join("<th>%s</th>" % self.fmt(c) for c in head)
        tr = "".join("<tr>%s</tr>" % "".join('<td data-th="%s">%s</td>' % (html.escape(t), self.fmt(c) or "&nbsp;")
                                              for t, c in zip(head, r)) for r in rows)
        return '<div class="tbl stack"><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (th, tr)

    def blocks(self, L, col, ids=""):
        """HTML for lines whose text starts at column col. ids gives numbered rows an anchor, as in "rule-5"."""
        out, i = [], 0
        while i < len(L):
            ln = L[i]
            if not ln.txt:
                if ln.tag:   # a note on a line of its own belongs to what is above it
                    out.append('<p class="tags">%s</p>' % self.tags([ln]))
                i += 1
            elif i + 1 < len(L) and TABLE_RULE.match(L[i + 1].raw):
                j = until(L, i, lambda x: x.txt)
                out.append(self.table(L[i:j]))
                i = j
            elif " | " in ln.txt:        # formats written with bars, with whatever is indented under them
                j = until(L, i + 1, lambda x: x.txt and (x.ind > ln.ind or " | " in x.txt and x.ind == ln.ind))
                out.append(self.pre(L[i:j]))
                i = j
            elif ln.ind > col:           # indented further than the text: shown as written, unless it is prose
                j = deeper(L, i, col)
                run, base = L[i:j], min(x.ind for x in L[i:j] if x.txt)
                if marker(ln.txt):       # "   1." lined up under "  10.": the same list
                    out.append(self.blocks(run, base, ids))
                else:   # plain words are a note under the line above; anything else is shown as written
                    plain = not any(HARD.search(x.txt) for x in run if x.txt)
                    out.append('<div class="nest">%s</div>' % self.blocks(run, base) if plain else self.pre(run))
                i = j
            elif marker(ln.txt):
                m = marker(ln.txt)
                tcol = ln.ind + m.end()
                j = deeper(L, i + 1, tcol - 1)
                first = Ln(tcol, ln.txt[m.end():], ln.tag, ln.raw)
                kind = "r-num" if NUM.match(ln.txt) else "r-bul" if BULLET.match(ln.txt) else "r-lab"
                mark = m.group().strip()
                rid = ' id="%s%s"' % (ids, mark.rstrip(".")) if ids and kind == "r-num" else ""
                out.append(self.row(kind, mark, self.blocks([first] + L[i + 1:j], tcol, ids), rid))
                i = j
            elif hanging(L, i):
                m = HANG.match(ln.txt)
                j = deeper(L, i + 1, ln.ind)
                tcol = L[i + 1].ind if j > i + 1 else ln.ind + m.end()
                first = Ln(tcol, ln.txt[m.end():], ln.tag, ln.raw)
                out.append(self.row("r-hang", m.group().strip(), self.blocks([first] + L[i + 1:j], tcol)))
                i = j
            elif COLUMNS.search(ln.txt):   # lined up in columns (a template, a table): as written, with what is under it
                j = deeper(L, i + 1, ln.ind)
                out.append(self.pre(L[i:j]))
                i = j
            elif SUBHEAD.match(ln.txt) and i + 1 < len(L) and L[i + 1].txt and L[i + 1].ind > ln.ind:
                j = deeper(L, i + 1, ln.ind)
                out.append('<div class="eg"><h4>%s</h4>%s</div>' % (self.fmt(ln.txt), self.blocks(L[i + 1:j], L[i + 1].ind)))
                i = j
            else:
                j = i + 1
                while j < len(L) and L[j].txt and L[j].ind == ln.ind and not starts_block(L, j):
                    j += 1
                out.append(self.para(L[i:j]))
                i = j
        return "".join(out)

    def row(self, kind, mark, inner, rid=""):
        return '<div class="row %s"%s><span class="k">%s</span><div class="v">%s</div></div>' % (kind, rid, self.fmt(mark), inner)


def marker(txt):
    return None if " | " in txt else NUM.match(txt) or BULLET.match(txt) or LABEL.match(txt)


def until(L, i, keep):
    while i < len(L) and keep(L[i]):
        i += 1
    return i


def deeper(L, i, col):
    """End of the run from i of lines indented past col. Blank lines stay in the run when it carries on after them."""
    j = i
    while j < len(L):
        if L[j].txt:
            if L[j].ind <= col:
                break
        else:
            k = until(L, j, lambda x: not x.txt)
            if k == len(L) or L[k].ind <= col:
                break
        j += 1
    return j


def prose(run):
    texts = [ln for ln in run if ln.txt]
    return any(len(ln.raw) >= 80 for ln in texts) and not any(HARD.search(ln.txt) for ln in texts)


def hanging(L, i):
    """'Febu:    the wallet ...' with its continuation indented under the text after the label, or on one line with
    the text lined up after the label the way the rows around it are."""
    if not HANG.match(L[i].txt):
        return False
    if i + 1 < len(L) and L[i + 1].txt and L[i + 1].ind > L[i].ind:
        return prose(L[i:deeper(L, i + 1, L[i].ind)])
    return bool(re.match(r"[A-Z][^:]{0,30}:\s{2,}\S", L[i].txt))


def starts_block(L, j):
    t = L[j].txt
    return bool(marker(t) or " | " in t or hanging(L, j) or COLUMNS.search(t)
                or j + 1 < len(L) and TABLE_RULE.match(L[j + 1].raw))


# ---------------------------------------------------------------------------------------------------------------
# The ledger's own parts (version 5): proposals, questions and their answers, VOTES and LAST POSTS, and where each
# stands under rules 2, 4, 5 and 8. model() reads them all; the pages, ledger.json, checks/lint.py and checks/closers.py
# read model(), so none of them can disagree.

PROPOSAL = re.compile(r"  P ?(\d+)\.\s+([^,:]+?), (\d{4}-\d\d-\d\d): (.*?)\s*$")   # "  P1. Ann, 2026-10-24: Did ...?"
QUESTION = re.compile(r"  Q ?(\d+)\.\s*(?:\((.*)\))?\s*$")                        # "  Q1. (opened 2026-10-30, from P1)"
ANSWER = re.compile(r" {3,}ANSWER (\d+)\.\s*(?:\((.*)\))?\s*$")                    # "    ANSWER 1.   (Ann, 2026-10-31)"
OPENED = re.compile(r"\bopened (\d{4}-\d\d-\d\d), from P ?(\d+)\b")
WHO = re.compile(r"\s*([^,:]+?), (\d{4}-\d\d-\d\d)\b")    # "Ann, 2026-10-31": who posted an answer, or wrote a CHANGED line
COPIED = re.compile(r"\b(fact|promise) (\d+)\b", re.I)    # "(Ann, 2026-10-31, version 3's fact 6)": a copied answer (Posters)
YES = re.compile(r"(.+?) (\d{4}-\d\d-\d\d)")             # "Crypto Fish 2026-10-25", one item of a Yes: line
VOTE_HEAD = re.compile(r"\s+(.+?), posted (\d{4}-\d\d-\d\d), SHA-256 ([0-9a-f]{64})\s*$")
VOTE_ITEM = re.compile(r"\s+- (.+?), (\d{4}-\d\d-\d\d): (YES|OBJECT)\b")
LAST = re.compile(r"( +)- (\d{4}-\d\d-\d\d): (.*?)\s*$")
FIELD = re.compile(r"([A-Z]+(?: [A-Z]+)?)(?: {2,}| (?=[a-z\d])|$)")   # "SAYS      one", "WRONG IF  what", "ASKS    it"
V3 = "archive/08_CLAIMS_LEDGER_v3.txt"   # version 3's entries, word for word: a copied answer's writer is read from it
DAYS = 30                                # rule 5: a question not closed by the end of the 30th day after it opened
ACTIVE_DAYS = 90                         # WORDS USED HERE, Member: a post dated in the 90 days up to and including the day
BOTH = ["DOESN'T HOLD", "HOLDS"]


def nest(body, head):
    """body split at each line `head` matches: ("item", match, the lines indented further than it) in order, and
    ("text", None, raw lines) for what comes between."""
    out = []
    for raw in body:
        m = head.match(raw)
        cur = out[-1] if out else None
        if m:
            out.append(("item", m, []))
        elif cur and cur[0] == "item" and (not raw.strip() or indent(raw) > indent(cur[1].string)):
            cur[2].append(raw)
        elif cur and cur[0] == "text":
            cur[2].append(raw)
        else:
            out.append(("text", None, [raw]))
    return out


def fields_of(raws, what):
    """An item's labelled fields in order, [(label, [Ln])]: a field starts at the first line's indent ("SAYS      one"),
    and every other line continues the field above it."""
    out, fcol = [], None
    for raw in raws:
        if not raw.strip():
            continue
        fcol = indent(raw) if fcol is None else fcol
        f = FIELD.match(raw[fcol:]) if indent(raw) == fcol else None
        if f:
            tcol = fcol + f.end()
            out.append((f.group(1), [Ln(tcol, raw[tcol:].strip(), None, raw.rstrip())]))
        elif out:
            out[-1][1].extend(to_lines([raw]))
        else:
            sys.exit("%s: a line before its first field: %r" % (what, raw))
    return out


def text_of(fields, label):
    """Every line of the fields with this label, as one line of text."""
    return " ".join(ln.txt for lab, lines in fields if lab == label for ln in lines if ln.txt)


def checked(fields):
    """Whether anyone has posted what they saw on this answer (its SEEN lines say more than "nobody yet")."""
    return bool(re.sub(r"(?i)\bnobody yet\b", "", text_of(fields, "SEEN")).strip())


def single(html_text):
    """The inside of one paragraph, for a heading. Anything longer stays as it is."""
    if html_text.startswith("<p>") and html_text.endswith("</p>") and html_text.count("<p>") == 1:
        return html_text[3:-4]
    return html_text


def section(secs, name, need=True):
    body = next((b for h, b in secs if short(h) == name), None)
    if body is None and need:
        sys.exit("the ledger has no %s section: version 5 keeps proposals under PROPOSED QUESTIONS and questions "
                 "under THE QUESTIONS" % name)
    return body or []


def proposals(body):
    """PROPOSED QUESTIONS in order: number, who, date, what it asks, its yeses [(name, date)], the question it opened as
    (or None), any Yes: item that does not read as "Name YYYY-MM-DD" (lint lists those), and every Yes: item as written
    (`said`, which lint compares)."""
    out = []
    for kind, m, under in nest(body, PROPOSAL):
        if kind != "item":
            continue
        asks, yes, opened = [m.group(4)], None, None
        for s in (r.strip() for r in under if r.strip()):
            o = re.match(r"Opened as Q ?(\d+)\b", s)
            if o:
                opened = int(o.group(1))
            elif s.startswith("Yes:"):
                yes = [s[4:]]
            elif yes is not None and opened is None:
                yes.append(s)
            else:
                asks.append(s)
        items = [y.strip() for y in " ".join(yes or []).strip().rstrip(".").split(",") if y.strip()]
        out.append({"num": int(m.group(1)), "who": m.group(2).strip(), "date": m.group(3), "asks": " ".join(asks),
                    "yes": [YES.fullmatch(y).groups() for y in items if YES.fullmatch(y)],
                    "unread": [y for y in items if not YES.fullmatch(y)], "said": items, "opened": opened})
    return out


def questions(body):
    """THE QUESTIONS in order: number, the day it opened and the proposal it came from, what it asks, its own fields
    (ASKS, NOTE), and its answers: number, who posted it and when, the rest of its header, its fields."""
    out = []
    for kind, m, under in nest(body, QUESTION):
        if kind != "item":
            continue
        num, head = int(m.group(1)), m.group(2) or ""
        o, own, answers = OPENED.search(head), [], []
        for k, a, lines in nest(under, ANSWER):
            if k == "text":
                own += lines
                continue
            w = WHO.match(a.group(2) or "")
            answers.append({"num": int(a.group(1)), "head": a.group(2) or "", "who": w.group(1).strip() if w else "",
                            "date": a_day(w.group(2)) if w else None,
                            "fields": fields_of(lines, "Q%d answer %s" % (num, a.group(1)))})
        fields = fields_of(own, "Q%d" % num)
        out.append({"num": num, "head": head, "opened": a_day(o.group(1)) if o else None,
                    "from": int(o.group(2)) if o else None, "asks": text_of(fields, "ASKS"), "fields": fields,
                    "answers": answers})
    return out


def changes(fields):
    """Each CHANGED line's (who, date), written "CHANGED   Bo, 2026-11-02: what changed"; (None, None) for one that
    names nobody that way (lint I5)."""
    return [(w.group(1).strip(), w.group(2)) if w else (None, None)
            for w in (WHO.match(lines[0].txt) for lab, lines in fields if lab == "CHANGED")]


def v3_writer(kind, num, members):
    """Who wrote version 3's FACT or PROMISE num, from its archive copy: the name before its date, or for an entry in the
    group's name the member its text says proposed it."""
    path = ROOT / V3
    if not path.exists():
        sys.exit("an answer copies version 3's %s %s, and %s is not there to say who wrote it" % (kind.lower(), num, V3))
    m = re.search(r"^  %s %s\. \(([^,)]*)[^\n]*\n((?:(?: {4}.*)?\n)*)" % (kind, num), raw_text(path).decode("utf-8"), re.M)
    if not m:
        sys.exit("an answer copies version 3's %s %s, which %s does not have" % (kind.lower(), num, V3))
    name = m.group(1).strip()
    said = " ".join(m.group(2).split())
    return name if name in members else next(
        (x for x in members if re.search(r"(?<!\w)%s proposed it" % re.escape(x), said)), name)


def posters(a, members):
    """Rule 4's posters (Posters): who posted the answer, who changed it with a CHANGED line, and for an answer copied from
    version 3 (its header names the entry: "(Ann, 2026-10-31, version 3's fact 6)"), that entry's writer."""
    out = {a["who"]} | {w for w, _ in changes(a["fields"]) if w}
    c = COPIED.search(a["head"])
    if c:
        out.add(v3_writer(c.group(1).upper(), c.group(2), members))
    return out - {""}


# A SEEN item as the weekly page writes it: "- Laura, 2026-10-30: HOLDS on lines 1, 2. Items: line 1, all 1; line 2,
# all 164. Saw: ... New: ...", with "Script: python checks/x.py by Ann via host." before Saw: when a script ran. A slot
# word in that place written any other way ("items:", "Item:", a count with no full stop) leaves the whole item to a
# person (lint I6), so a sample cannot pass for a full check by being misspelt. KEPT and BROKEN are read so that lint
# can say they are no result here (I7).
ITEMS = r"(?:line \d+, )?(?:all \d+|\d+ of \d+)"
SEEN_ITEM = re.compile(r"- (.+?), (\d{4}-\d\d-\d\d): (HOLDS|DOESN'T HOLD|KEPT|BROKEN)(?: on lines? ([\d, and]+?))?\."
                       r"(?: Items: (%s(?:; %s)*)\.|(?!\s*(?i:items?)\b))" % (ITEMS, ITEMS) +
                       r"(?: Script: (.+?) by ([^:;,]+?)(?: via (\S+?))?\.(?= Saw:)|(?!\s*(?i:script)\b))")
ITEM = re.compile(r"(?:line (\d+), )?(?:all (\d+)|(\d+) of (\d+))")
CLAUSE = re.compile(r"[;,] or ")                            # "a, or b; or c": one WRONG IF line per clause
DATE = re.compile(r"\b\d{4}-\d\d-\d\d\b")
CHAT = "  ·  "                                         # between the parts of a post's first line


def wrong_if(fields):
    """The answer's WRONG IF lines, one per clause, in the order written. A check names them by number, from 1."""
    text = text_of(fields, "WRONG IF").rstrip(".")
    return [c.strip() for c in CLAUSE.split(text) if c.strip()]


def seen_items(fields):
    """The SEEN items as written, each joined into one line: an item starts with "- " at the first item's indent."""
    items, col = [], None
    for ln in (ln for lab, lines in fields if lab == "SEEN" for ln in lines if ln.txt):
        if ln.txt.startswith("- ") and (col is None or ln.ind <= col):
            col = ln.ind if col is None else col
            items.append(ln.txt)
        elif items:
            items[-1] += " " + ln.txt
    return items


def items_of(text):
    """An Items slot as (line, opened, of) parts: "line 2, all 164" is (2, 164, 164), "20 of 164" with no line is
    (0, 20, 164)."""
    return tuple((int(ln or 0), int(a or n), int(a or of)) for ln, a, n, of in ITEM.findall(text or ""))


def results(fields):
    """The SEEN items in the weekly page's form, in order: (name, date, result, WRONG IF line numbers, Items parts, and
    (script, author, host) or None). A SEEN item written another way is left to a person to read."""
    found = (SEEN_ITEM.match(it.replace("’", "'")) for it in seen_items(fields))
    return [(m.group(1), m.group(2), m.group(3), tuple(sorted({int(n) for n in re.findall(r"\d+", m.group(4) or "")})),
             items_of(m.group(5)), m.group(6) and (m.group(6), m.group(7), m.group(8)))
            for m in found if m]


def full(lines, items, n):
    """A HOLDS that is "the same result" (Result): it names every one of the n WRONG IF lines and its Items slot says
    "all" for each, with no sample anywhere. An Items part with no "line n," stands for every line."""
    every, alls = set(range(1, n + 1)), {ln for ln, k, of in items if k == of}
    return n > 0 and set(lines) == every and all(k == of for _, k, of in items) and (every <= alls or 0 in alls)


def days_after(d, n):
    """The date n days after d, stopping at the calendar's ends."""
    try:
        return (datetime.date.fromisoformat(d) + datetime.timedelta(days=n)).isoformat()
    except OverflowError:
        return (datetime.date.max if n > 0 else datetime.date.min).isoformat()


def a_day(d):
    """d if it is a real date, else None."""
    try:
        return days_after(d, 0)
    except (TypeError, ValueError, OverflowError):
        return None


def active(posts, name, day):
    """Whether the file shows a post of theirs dated in the 90 days up to and including day (WORDS USED HERE, Member)."""
    first = days_after(day, 1 - ACTIVE_DAYS)
    return any(first <= d <= day for d in posts.get(name, ()))


def standing(found, posters, members, start, n, posts=None):
    """Where an answer stands under rules 4 and 5, from its results in date order (the file's order within a day).
    It closes HOLDS, or DOESN'T HOLD, on the day three members other than its posters, each active that day, have
    posted the same result, at least one of them by hand (no Script slot); with fewer than four active members left
    once the posters are set aside, every one of them is needed, and never fewer than two. The same result: for HOLDS,
    every WRONG IF line with "all" for each (full); for DOESN'T HOLD, one line in common. A check run on a poster's
    script is no Saw and counts for nothing. Two people, member or not, other than the posters, with one result and
    two others with the other keep it open; after a close, two posting the word it did not close on reopen it. Either
    way, from then on only results posted after that day count. `held` is the first day it closed HOLDS, which closes
    its question (rule 4) even if it reopens later. Results dated before `start` count for nothing, and none count
    while it is None. `posts` gives each name's other dated posts, for "active". assets/claims.js has the same
    function; checks/states.json holds the cases both must pass."""
    out = {"state": "OPEN", "lines": [], "since": None, "by": [], "both": [], "held": None}
    dated = {k: set(v) for k, v in (posts or {}).items()}
    for r in found:
        if a_day(r[1]):
            dated.setdefault(r[0], set()).add(r[1])
    every, members, holds, wrong = set(range(1, n + 1)), list(members), {}, {}
    for name, date, word, lines, items, script in sorted(
            (r for r in found if start and a_day(r[1]) and r[1] >= start), key=lambda r: r[1]):
        if name in posters or (script and script[1] in posters) or (out["both"] and date <= out["since"]):
            continue
        hand = not script
        if word == "HOLDS" and full(lines, items, n):
            holds[name] = holds.get(name) or hand
        elif word == "DOESN'T HOLD" and set(lines) & every:
            for ln in set(lines) & every:
                by = wrong.setdefault(ln, {})
                by[name] = by.get(name) or hand
        else:
            continue                                                       # a sample, or no result here: a SEEN item
        pair = [ln for ln in sorted(wrong) if len(wrong[ln]) >= 2]
        if out["state"] != "OPEN":
            if pair if out["state"] == "HOLDS" else len(holds) >= 2:            # reopened (rule 5)
                out, holds, wrong = dict(out, state="OPEN", lines=[], since=date, by=[], both=BOTH), {}, {}
            continue
        if any(len(holds) >= 2 and len(set(holds) | set(wrong[ln])) >= 4 for ln in pair):   # kept open (rule 5)
            out, holds, wrong = dict(out, since=date, both=BOTH), {}, {}
            continue
        others = [m for m in members if m not in posters and active(dated, m, date)]
        need = 3 if len(others) >= 4 else max(2, len(others))
        ok = lambda ns: sorted(m for m in ns if m in members and m not in posters and active(dated, m, date))  # noqa: E731
        shut = [ln for ln in sorted(wrong) if len(ok(wrong[ln])) >= need and any(wrong[ln][m] for m in ok(wrong[ln]))]
        if len(ok(holds)) >= need and any(holds[m] for m in ok(holds)):
            out = dict(out, state="HOLDS", lines=sorted(every), since=date, by=ok(holds), both=[], held=out["held"] or date)
        elif shut:
            out = dict(out, state="DOESN'T HOLD", lines=shut, since=date, by=ok(wrong[shut[0]]), both=[])
        else:
            continue
        holds, wrong = {}, {}
    return out


def question_state(opened, answers, as_of):
    """Rule 5 for a question: CLOSED on the day one of its answers first closes HOLDS within the 30 days after it opened
    (`until` is the last of them); CAN'T TELL from the day after, if none has and the file has a later date; OPEN
    otherwise. A close after that day stands for its answer, and the question stays CAN'T TELL."""
    until = days_after(opened, DAYS) if opened else None
    out = {"state": "OPEN", "since": None, "until": until, "answer": None}
    held = min(((a["state"]["held"], a["num"]) for a in answers if a["state"]["held"]), default=None)
    if not until:
        return out
    if held and held[0] <= until:
        return dict(out, state="CLOSED", since=held[0], answer=held[1])
    if as_of and as_of > until:
        return dict(out, state="CAN'T TELL", since=days_after(until, 1))
    return out


def reach(p, members, adopted):
    """Rule 2: the day a proposal has "yes" from three members other than its proposer, counting yeses from the day of
    adoption (STATUS) and not before the proposal itself; None until it has."""
    got = []
    for name, date in sorted(p["yes"], key=lambda y: y[1]):
        if (adopted and a_day(date) and date >= max(adopted, p["date"]) and name in members and name != p["who"]
                and name not in got):
            got.append(name)
            if len(got) == 3:
                return date
    return None


def slot(props, frees, adopted):
    """Rule 2 in order: [(proposal number, the day it opens)], the first for Q1. frees[k] is the day Q k+1 left the slot
    (closed, or CAN'T TELL after its 30 days), None while it holds it. When the slot is free, the proposal that reached
    three yeses first opens, that day; if none has, the next to reach three, on its day. A tie goes to the one posted
    first. Each proposal's "reach" is reach()."""
    seq, free, used = [], adopted, set()
    while free:
        ready = sorted((p["reach"], p["num"]) for p in props if p["reach"] and p["num"] not in used)
        if not ready:
            break
        r, num = ready[0]
        seq.append((num, max(r, free)))
        used.add(num)
        free = frees[len(seq) - 1] if len(seq) <= len(frees) else None
    return seq


def freed(q_state):
    """The day a question left the slot, or None while it holds it."""
    return q_state["since"] if q_state["state"] in ("CLOSED", "CAN'T TELL") else None


def vote_list(body):
    """VOTES in order: each text put to a vote (its name, the day it was posted, its SHA-256) with its votes
    [(member, date, YES or OBJECT)] in the order written."""
    out = []
    for raw in body:
        h, v = VOTE_HEAD.match(raw), VOTE_ITEM.match(raw)
        if h:
            out.append({"subject": h.group(1).strip(), "posted": h.group(2), "sha": h.group(3), "votes": []})
        elif v and out:
            out[-1]["votes"].append((v.group(1).strip(), v.group(2), v.group(3)))
    return out


def vote_state(v, members, posts, as_of):
    """Rule 8, counted from VOTES alone: at the end of each day from the 7th after the post, on the votes dated by then,
    each member's latest vote standing, among the members active that day. `passed` is the first day it holds, up to the
    file's last date (a later day is not the file's to say); yes and object are the count that day, or on the last day
    counted."""
    out = {"passed": None, "yes": [], "object": []}
    first = days_after(v["posted"], 7) if a_day(v["posted"]) else None
    if not first or not as_of or as_of < first:
        return out
    posts = {k: set(ds) for k, ds in posts.items()}
    for name, date, _ in v["votes"]:                                     # a vote is a post (Member)
        if a_day(date):
            posts.setdefault(name, set()).add(date)
    # the count changes only on a day a vote is dated, or a post starts or leaves someone's 90 days
    days = {first} | {d for ds in posts.values() for p in ds for d in (p, days_after(p, ACTIVE_DAYS))}
    for day in sorted(d for d in days if first <= d <= as_of):
        latest = {name: word for name, date, word in sorted(v["votes"], key=lambda x: x[1]) if date <= day}
        act = [m for m in members if active(posts, m, day)]
        out = {"passed": None, "yes": [m for m in act if latest.get(m) == "YES"],
               "object": [m for m in act if latest.get(m) == "OBJECT"]}
        if len(out["yes"]) >= (4 if len(act) >= 5 else max(2, len(act))) and len(out["object"]) <= 1:
            return dict(out, passed=day)
    return out


def last_posts(body):
    """LAST POSTS lines in order: (the turn's day, {member: the date of their last post, or None for "none"}). A line
    may wrap: what is further in continues it."""
    out, cur = [], None
    for raw in body:
        m = LAST.match(raw)
        if m:
            cur = [m.group(2), m.group(3), len(m.group(1))]
            out.append(cur)
        elif raw.strip():
            if cur and indent(raw) > cur[2]:
                cur[1] += " " + raw.strip()
            else:
                cur = None
    rows = []
    for day, text, _ in out:
        got = {}
        for part in text.rstrip(".").split(","):
            p = re.fullmatch(r"\s*(.+?) (\d{4}-\d\d-\d\d|none)\s*", part)
            if p:
                got[p.group(1)] = a_day(p.group(2))
        rows.append((day, got))
    return rows


def posts_of(props, qs, votes, last):
    """Every dated post the file shows, by name, for "active" (WORDS USED HERE, Member): proposals and yeses, answers
    posted or changed, SEEN items, VOTES items, and each member's date on a LAST POSTS line."""
    out = {}

    def add(name, date):
        if name and a_day(date):
            out.setdefault(name, set()).add(date)
    for p in props:
        add(p["who"], p["date"])
        for n, d in p["yes"]:
            add(n, d)
    for q in qs:
        for a in q["answers"]:
            add(a["who"], a["date"])
            for n, d in changes(a["fields"]) + [r[:2] for r in a["results"]]:
                add(n, d)
    for v in votes:
        for n, d, _ in v["votes"]:
            add(n, d)
    for _, row in last:
        for n, d in row.items():
            add(n, d)
    return out


def model(secs):
    """The ledger's state from its sections: members, adoption, proposals, questions and their answers, votes, LAST
    POSTS, each name's dated posts, the file's last date (`as_of`) and rule 2's order of openings (`slot`)."""
    names, on = member_names(secs), adopted(secs)
    props = proposals(section(secs, "PROPOSED QUESTIONS"))
    qs = questions(section(secs, "THE QUESTIONS"))
    votes = vote_list(section(secs, "VOTES", need=False))
    last = last_posts(section(secs, "LAST POSTS", need=False))
    for q in qs:
        for a in q["answers"]:
            a.update(posters=posters(a, names), lines=wrong_if(a["fields"]), results=results(a["fields"]))
    posts = posts_of(props, qs, votes, last)
    as_of = max([d for ds in posts.values() for d in ds] + [q["opened"] for q in qs if q["opened"]]
                + [d for d, _ in last if a_day(d)] + [v["posted"] for v in votes if a_day(v["posted"])], default=None)
    for q in qs:
        for a in q["answers"]:
            a["start"] = max(q["opened"], a["date"]) if on and q["opened"] and a["date"] else None
            a["state"] = standing(a["results"], a["posters"], names, a["start"], len(a["lines"]), posts)
        q["state"] = question_state(q["opened"], q["answers"], as_of)
    for p in props:
        p["reach"] = reach(p, names, on)
    for v in votes:
        v.update(vote_state(v, names, posts, as_of))
    return {"members": names, "adopted": on, "proposals": props, "questions": qs, "votes": votes, "last": last,
            "posts": {k: sorted(v) for k, v in posts.items()}, "as_of": as_of,
            "slot": slot(props, [freed(q["state"]) for q in qs], on),
            "next": {"proposal": next_number(secs, "PROPOSED QUESTIONS", "proposal is P", props),
                     "question": next_number(secs, "THE QUESTIONS", "question is Q", qs)}}


def next_number(secs, name, said, items):
    """The number the section says comes next ("The next proposal is P2."), or one past the highest."""
    m = re.search(r"The next %s ?(\d+)" % said, " ".join(section(secs, name)))
    return int(m.group(1)) if m else 1 + max([x["num"] for x in items] or [0])


def open_question(m):
    return next((q for q in m["questions"] if q["state"]["state"] == "OPEN"), None)


def answer_id(q, a):
    return "q-%d-answer-%d" % (q, a)


def state_text(st):
    """An answer's state in a few words, or None while it is OPEN with nothing to add to its SEEN lines."""
    s = st["state"]
    if s == "DOESN'T HOLD":
        return "DOESN'T HOLD on line%s %s" % ("s" if len(st["lines"]) > 1 else "", ", ".join(map(str, st["lines"])))
    if s != "OPEN":
        return s
    if st["both"]:
        return "both results posted twice by %s: only posts after it count (rule 5)" % st["since"]
    return None


def question_text(q):
    """Where a question stands, in a line."""
    st = q["state"]
    head = "opened %s, from P%s" % (q["opened"], q["from"]) if q["opened"] else "not opened"
    if st["state"] == "CLOSED":
        return "%s; closed %s: answer %d HOLDS" % (head, st["since"], st["answer"])
    if st["state"] == "CAN'T TELL":
        return "%s; CAN'T TELL from %s (rule 5)" % (head, st["since"])
    return "%s; open, CAN'T TELL after %s unless an answer closes HOLDS" % (head, st["until"]) if st["until"] else head


def answer_html(q, a, doc):
    """One answer as a card on the ledger page, shown as the Assembly's (rule 3): the file keeps who posted it."""
    f = dict(a["fields"])
    if "SAYS" not in f:
        sys.exit("Q%d answer %d has no SAYS line" % (q["num"], a["num"]))
    aid, name = answer_id(q["num"], a["num"]), "Q%d answer %d" % (q["num"], a["num"])
    verdict = state_text(a["state"]) or ("checks posted, see SEEN" if checked(a["fields"]) else "not yet checked")
    rows = "".join('<div><dt>%s</dt><dd>%s</dd></div>' % (label, doc.blocks(lines, lines[0].ind))
                   for label, lines in a["fields"] if label != "SAYS")
    return ('<article class="claim entry v-open" id="%s"><div class="mark"><span class="num">answer %d</span>'
            '<strong class="verdict">%s</strong></div><div class="body"><h3>%s</h3><dl class="fields">%s</dl>'
            '<p class="meta"><span>the Assembly&rsquo;s answer</span><span>cite as: ledger %s, %s</span>'
            '<span><a href="#%s">link to this answer</a></span></p></div></article>'
            % (aid, a["num"], html.escape(verdict), single(doc.blocks(f["SAYS"], f["SAYS"][0].ind)), rows, name,
               html.escape(verdict), aid))


def question_html(q, doc):
    rows = "".join('<div><dt>%s</dt><dd>%s</dd></div>' % (label, doc.blocks(lines, lines[0].ind))
                   for label, lines in q["fields"] if label != "ASKS")
    return ('<section class="question" id="q-%d"><h3>Q%d. %s</h3><p class="meta"><span>%s</span></p>%s%s</section>'
            % (q["num"], q["num"], doc.fmt(q["asks"]), html.escape(question_text(q)),
               '<dl class="fields">%s</dl>' % rows if rows else "", "".join(answer_html(q, a, doc) for a in q["answers"])))


# ---------------------------------------------------------------------------------------------------------------
# Pages

SHELL = """<!doctype html>
<!-- Built by build.py{source}. Edit {edit}, not this file. -->
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; connect-src {connect}; base-uri 'none'; form-action 'none'">
<meta name="referrer" content="no-referrer">
<title>{title}</title>
<meta name="description" content="{description}">
{meta}
<link rel="icon" href="/favicon.ico">
<link rel="stylesheet" href="/assets/findings.css">
<link rel="stylesheet" href="/assets/ledger.css">
</head>
<body>
{bar}
<main>
<header class="mast">
<div class="mast-title"><h1>{h1}</h1>
<p class="sub">{sub}</p></div>
{tabs}
{mast}
</header>
{body}
<footer class="foot">{foot}</footer>
</main>
<script src="/assets/claims.js"></script>
</body>
</html>
"""

TABS = (("/", "febu archive"), ("febu-assembly.html", "assembly"),   # "/" is the den: the archive is the home page
        ("how.html", "how it works"), ("process.html", "the process"),
        ("ledger.html", "the ledger"))
QUIET = "Nothing on this page is stored or counted, and it loads nothing from other sites."
BAR = '<div class="archive-bar">unverified: %s &middot; [ <a href="/">home</a> ] [ <a href="/febu-assembly.html">assembly</a> ]</div>'


SITE = "https://febu-assembly.vercel.app"               # the card image's address must be absolute for a chat to fetch it
FRONT = SITE + "/febu-assembly.html"                    # "/" is the den, so links to the Assembly name its page
CARD = SITE + "/assets/card.png"                        # 1200x630, made by make_card.py
CARD_ALT = "A claim costs a link and a line that would prove it wrong. A check costs a click."


def meta_tags(title, description):
    """What a chat shows when someone pastes a link to the page: a title, two lines and the card (Open Graph, which
    Discord, Telegram, Slack and iMessage read, and the Twitter card tags, which X reads)."""
    t, d = html.escape(title, quote=True), html.escape(description, quote=True)
    pairs = (("property", "og:type", "website"), ("property", "og:site_name", "febu assembly"),
             ("property", "og:title", t), ("property", "og:description", d), ("property", "og:image", CARD),
             ("property", "og:image:width", "1200"), ("property", "og:image:height", "630"),
             ("property", "og:image:alt", CARD_ALT), ("name", "twitter:card", "summary_large_image"),
             ("name", "twitter:title", t), ("name", "twitter:description", d), ("name", "twitter:image", CARD),
             ("name", "theme-color", "#000080"))
    return "\n".join('<meta %s="%s" content="%s">' % p for p in pairs)


def tabs_html(name):
    return '<nav class="tabs" aria-label="Assembly pages">%s</nav>' % "".join(
        '<a href="%s"%s>%s</a>' % (href, ' aria-current="page"' if href == name else "", label) for href, label in TABS)


def vetted(name, out):
    """The page, unless it carries notation or (off the ledger page) an address it may not."""
    hit = BANNED.search(re.sub(r"<[^>]+>", " ", out)) or (name != "ledger.html" and ADDRESS.search(out))
    if hit:
        sys.exit("%s: %r may not be on this page" % (name, hit.group()))
    return out


def page(name, title, h1, sub, body, mast="", foot=QUIET, connect="'none'", source="", description="", share=""):
    """`share` is the title a chat shows for the page; by default "febu assembly: " and the page's title."""
    description = description or ("The febu Assembly: a public ledger of what a group has found out about febu, one "
                                  "question at a time, that anyone can check.")
    return vetted(name, SHELL.format(
        title=html.escape(title), h1=html.escape(h1), sub=html.escape(sub), tabs=tabs_html(name), mast=mast, body=body,
        foot=foot, connect=connect, source=source, edit="the text" if source else "the script",
        description=html.escape(description), meta=meta_tags(share or "febu assembly: " + title.lower(), description),
        bar=BAR % "rules by one author, not yet adopted or checked by anyone else"))


PROCESS_DESC = ("The Assembly's whole process in one file: the ledger, the scripts that check it, money, the 30-day "
                "clock and its stop rule, and the decisions waiting. Adds no rule.")
PROCESS_CLOCK = "process.html#7-the-clock-from-now-to-a-decision"
PROCESS_FOLD = ("1-why-it-exists", "9-what-it-cannot-do", "11-what-became-of-what-you-have-seen")   # folded in place


def md_tables(out):
    """markdown's plain tables, in the stylesheet's stacking form: data-th on every cell, so a phone shows the header
    beside each value (the way Doc.table writes them)."""
    def one(m):
        heads = re.findall(r"<th>(.*?)</th>", m.group(), re.S)
        def row(r):
            cells = iter(heads)
            return re.sub(r"<td>", lambda _: '<td data-th="%s">' % html.escape(re.sub(r"<[^>]+>", "", next(cells, ""))),
                          r.group())
        body = re.sub(r"<tr>.*?</tr>", row, m.group().split("<tbody>", 1)[1], flags=re.S)
        return '<div class="tbl stack">%s<tbody>%s</div>' % (m.group().split("<tbody>", 1)[0], body)
    return re.sub(r"<table>.*?</table>", one, out, flags=re.S)


def process_page():
    """process.md as a page: the title line becomes the heading, each ## section is a section with the heading's own
    anchor (markdown's toc ids: '7-the-clock-from-now-to-a-decision'). Needs the markdown package; without it the
    committed page is kept while process.md is unchanged."""
    text = raw_text(PROCESS).decode("utf-8")
    mark = "from process.md (sha256 %s)" % hashlib.sha256(raw_text(PROCESS)).hexdigest()[:16]
    try:
        import markdown
    except ModuleNotFoundError:
        built = ROOT / "process.html"
        if built.exists() and mark in built.read_text(encoding="utf-8"):
            return built.read_text(encoding="utf-8")
        sys.exit("process.md has changed since process.html was built, and building it needs the markdown package "
                 "(pip install markdown)")
    first, rest = text.split("\n", 1)
    h1, sub = titled(first.lstrip("# ").strip())
    body = markdown.markdown(rest, extensions=["tables", "fenced_code", "toc"])
    body = md_tables(body)
    # each h2 opens a section; the toc extension gave it an id
    body = re.sub(r'<h2 id="([^"]+)">', lambda m: '</section><section id="%s"><h2>' % m.group(1), body)
    body = '<section class="md-lead">' + body + "</section>"
    body = body.replace('<section class="md-lead"></section>', "")
    for sid in PROCESS_FOLD:   # background, folded where it stands: the heading opens it
        body = re.sub(r'<section id="%s"><h2>(.*?)</h2>(.*?)</section>' % re.escape(sid),
                      r'<section id="%s"><details class="fold"><summary><h2>\1</h2></summary>\2</details></section>'
                      % sid, body, count=1, flags=re.S)
    return page("process.html", "The process", h1.lower(), sub.lower(), '<div class="md">%s</div>' % body,
                source=" " + mark, description=PROCESS_DESC)


def status(secs):
    """(the STATUS section's lines, whether it says the rules are only proposed)"""
    body = next((b for h, b in secs if short(h) == "STATUS"), None)
    if body is None:
        sys.exit("the ledger has no STATUS section")
    return body, bool(re.search(r"\bProposed\b", " ".join(body)))


ADOPTED = re.compile(r"\bAdopted on (\d{4}-\d\d-\d\d)")


def adopted(secs):
    """The day STATUS says this version was adopted ("Adopted on 2026-10-22"), or None while it says Proposed."""
    body, proposed = status(secs)
    m = ADOPTED.search(" ".join(" ".join(body).split()))
    return None if proposed or not m else a_day(m.group(1))


def status_banner(secs, doc, brief=False, task=""):
    """The STATUS section as a banner. Proposed rules say so first, in plain words. On the front page (brief) the
    banner is the immediate task, which assembly_page writes as `task`."""
    body, proposed = status(secs)
    head = "Proposed, not yet adopted" if proposed else "Status"
    inner = (task + '<p><a href="%s">What happens next, step by step</a> &middot; <a href="ledger.html#status">'
             'Read the status</a></p>' % PROCESS_CLOCK if brief else doc.blocks(to_lines(body), 2))
    return '<div class="banner%s" id="status" role="note"><strong>%s</strong>%s</div>' % (
        (" proposed" if proposed else "") + (" brief" if brief else ""), head, inner)


def archived(text):
    """Each archive/... text the ledger names: (path, bytes, SHA-256), checked against any SHA-256 printed beside it."""
    out = []
    named = set(re.findall(r"\barchive/[\w.-]+\.txt\b", text))
    for path in sorted(named, key=lambda p: ([int(n) for n in re.findall(r"\d+", p)], p)):   # v1, v2, v2.1; the path breaks ties, so the page is the same on every build
        src = ROOT / path
        if not src.exists():
            sys.exit("the ledger names %s, which is not in archive/" % path)
        raw = raw_text(src)
        digest = hashlib.sha256(raw).hexdigest()
        said = re.search(re.escape(path) + r"\s+SHA-256\s+([0-9a-f]{64})", text)
        if said and said.group(1) != digest:
            sys.exit("the ledger gives %s the SHA-256 %s, but the file's is %s" % (path, said.group(1), digest))
        out.append((path, raw, digest))
    return out


def files_html(current, archives):
    def item(label, path, raw, digest):
        return ('<div><dt>%s</dt><dd><a href="%s">%s</a>, %s bytes<br><code class="tok" data-sha-of="%s" '
                'data-name="%s" title="tap to copy">%s</code><span class="hint served" role="status"></span></dd></div>'
                % (label, path, path, "{:,}".format(len(raw)), path, path, digest))
    rows = [item("this version", "ledger.txt", *current)]
    for path, raw, digest in archives:
        v = re.search(r"_v(\d+(?:\.\d+)?)\.txt$", path)
        rows.append(item("version %s" % v.group(1) if v else "archived", path, raw, digest))
    return ('<section id="the-text"><h2>THE TEXT ITSELF</h2>'
            '<p>This page is laid out from a plain text file, and the file is the ledger. The hash the weekly turn posts '
            '(rule 7) is this file\'s SHA-256. Anyone may keep a copy: two copies with the same SHA-256 are the same, '
            'letter for letter.</p>'
            '<dl class="kv files">%s</dl>'
            '<div class="tool compare"><label for="copy-file">Compare a copy you hold</label>'
            '<input type="file" id="copy-file" accept=".txt,text/plain"><p class="hint">The file is read on your device. '
            'Nothing is sent.</p><p class="msg" id="copy-result" role="status"></p></div></section>' % "".join(rows))


def ledger_page(text, raw, m):
    title, secs = sections(text)
    archives = archived(text)
    doc = Doc(secs, "", {p: p for p, _, _ in archives})
    qs = iter(m["questions"])
    ids = {"THE RULES": "rule-", "KNOWN BUGS": "bug-", "PROPOSED QUESTIONS": "prop-"}
    body, wins = [], []
    for head, b in secs:
        s = short(head)
        if s in ("STATUS", "WHAT THIS IS"):
            continue   # both are in the masthead
        if s == "THE QUESTIONS":
            inner = "".join(question_html(next(qs), doc) if kind == "item" else doc.blocks(to_lines(lines), 2)
                            for kind, _, lines in nest(b, QUESTION))
        else:
            inner = doc.blocks(to_lines(b), 2, ids.get(s, ""))
        body.append('<section id="%s"><h2>%s</h2>%s</section>' % (slug(head), html.escape(head), inner))
        wins.append((slug(head), s.lower()))
    body.append(files_html((raw, hashlib.sha256(raw).hexdigest()), archives))

    strip = "".join('<a class="v-open" href="#q-%d" title="Question %d">Q%d</a>' % ((q["num"],) * 3)
                    for q in m["questions"])
    jump = '<nav class="jump" aria-label="On this page">%s<a href="#the-text">the text and its hash</a></nav>' % "".join(
        '<a href="#%s">%s</a>' % w for w in wins)
    intro = next((b for h, b in secs if short(h) == "WHAT THIS IS"), None)
    mast = (status_banner(secs, doc) + ('<nav class="strip nums" aria-label="Every question, in order">%s</nav>' % strip
                                        if strip else "")
            + jump + ('<div class="intro" id="what-this-is">%s</div>' % doc.blocks(to_lines(intro), 2) if intro else ""))
    h1, sub = titled(title)
    return page("ledger.html", "The ledger", h1.lower(), sub, "\n".join(body), mast=mast, connect="'self'",
                source=" from ledger.txt",
                description="The Assembly's questions about febu, one at a time, each answer with a link anyone can "
                "open, and the rules for checking them." + (" Proposed, not yet adopted." if status(secs)[1] else ""),
                foot='Built from <a href="ledger.txt">ledger.txt</a>. ' + QUIET), archives


def check_section(secs, doc):
    """HOW TO CHECK AN ANSWER, word for word from the ledger, as one window (#check on the front page)."""
    head, b = next(((h, b) for h, b in secs if "CHECK" in short(h) and any(NUM.match(r.strip()) for r in b)),
                   (None, None))
    if head is None:
        sys.exit("the ledger has no section on checking (a heading with CHECK in it, and numbered steps); "
                 "the front page shows it")
    L = to_lines(b)
    steps = [i for i, ln in enumerate(L) if ln.txt and ln.ind == 2 and NUM.match(ln.txt)]
    after = deeper(L, steps[-1] + 1, 4)
    return ('<section class="win howto" id="check" aria-labelledby="howto-h"><h2 class="bar" id="howto-h">%s</h2>'
            '<div class="win-body">%s<div class="after">%s</div></div></section>'
            % (html.escape(head.capitalize()), doc.blocks(L[steps[0]:after], 2), doc.blocks(L[after:], 2)))


def tests_page(text, ledger_secs):
    title, secs = sections(text)
    doc = Doc(ledger_secs, "ledger.html")
    body = "\n".join('<section id="%s"><h2>%s</h2>%s</section>' % (slug(h), html.escape(h), doc.blocks(to_lines(b), 2))
                     for h, b in secs)
    h1, sub = titled(title)
    return page("tests.html", "Four tests", h1.lower(), sub, body, source=" from tests.txt",
                description="Four tests for who gains, who pays, who gets bailed out and who decides, run on febu "
                "and on the Assembly's ledger.")


HOW_FOLD = ("HOW IT ANSWERS FEBU", "FOUR QUESTIONS FROM THE CHAT", "WHAT IT COULD BECOME")   # reading, folded


def how_page(text, ledger_secs):
    """how.txt as tests.txt is laid out, with a picture under THE PICTURE (assets/how-it-works.svg) and under
    HOW IT CONNECTS (assets/how-it-connects.svg). The sections in HOW_FOLD, which how.txt keeps last, are one
    folded window at the end: background, not the process."""
    title, secs = sections(text)
    doc = Doc(ledger_secs, "ledger.html")

    def fig(name, height, alt):
        return ('<figure class="how"><a href="/assets/%s.svg"><img src="/assets/%s.svg" width="960" height="%d" '
                'alt="%s"></a></figure>' % (name, name, height, alt))
    figs = {"THE PICTURE": fig("how-it-works", 700, "One entry in four steps: a claim is written, two people check, a "
                                "result, the record. Below, febu's pages in the same four slots, with the third slot, "
                                "the check, empty."),
            "HOW IT CONNECTS": fig("how-it-connects", 700, "Five columns: the record outside, the people (a writer, two "
                                    "checkers, a voter), the chat with its ENTRY, CHECK and VOTE posts, the file "
                                    "ledger.txt, and the copies outside. Under the chat and the file, the weekly turn "
                                    "copies the week's posts into the file and posts its hash.")}
    def sec(h, b):
        return '<section id="%s"><h2>%s</h2>%s%s</section>' % (slug(h), html.escape(h), figs.get(short(h), ""),
                                                             doc.blocks(to_lines(b), 2))
    core = [(h, b) for h, b in secs if short(h) not in HOW_FOLD]
    more = [(h, b) for h, b in secs if short(h) in HOW_FOLD]
    body = "\n".join(sec(h, b) for h, b in core)
    if more:
        body += ('<details class="win lead" id="more" data-open-wide><summary><span class="t">more</span><span class="q">'
                 '%s</span></summary><div class="win-body">%s</div></details>'
                 % (html.escape(", ".join(short(h).lower() for h, _ in more)), "\n".join(sec(h, b) for h, b in more)))
    h1, sub = titled(title)
    return page("how.html", "How it works", h1.lower(), sub, body, source=" from how.txt",
                description="The Assembly's ledger in plain words: one sentence, one picture, how it answers febu, "
                "the four parts, what it runs on, what it cannot do and what it could become.")


def member_names(secs):
    """The names on the Member line of WORDS USED HERE, in its order."""
    by = {short(h): b for h, b in secs}
    m = re.search(r"\bMember\s{2,}(.+?)\.\s", " ".join(by.get("WORDS USED HERE", [])))
    if not m:
        sys.exit("WORDS USED HERE has no Member line; the pages read the members from it")
    return [n.strip() for n in m.group(1).split(",")]


# ---------------------------------------------------------------------------------------------------------------
# Member flows: the check card, your week, the weekly page and the answer form. Each one writes text for a member to
# paste into the chat or into ledger.txt; none of them posts, stores or sends anything (claims.js does the typing).


def open_votes(title, secs, m):
    """What waits on a vote, as (subject, day, how): while STATUS says Proposed, this version, "by" the last date the
    ledger gives for "yes" or "object"; after, each text in VOTES that has not passed, "counted from" its 7th day
    (rule 8). Proposals that live only in the chat are not listed; the weekly page counts any VOTE post."""
    if status(secs)[1]:
        flat = re.sub(r"\s+", " ", " ".join(r for _, b in secs for r in b))
        dates = re.findall(r'"yes" or "object" by (\d{4}-\d\d-\d\d)', flat)
        return [(titled(title)[1] or "this version", dates[-1] if dates else None, "by")]
    return [(v["subject"], days_after(v["posted"], 7), "counted from") for v in m["votes"] if not v["passed"]]


def turn_start(secs):
    """The first date in STATUS: the weekly turns (rule 7) are counted in weeks from it, in Member order."""
    m = DATE.search(" ".join(status(secs)[0]))
    return m.group() if m else None


def calendar_ics(votes, members, start, secs):
    """The ledger's dates as a calendar file, all-day events only: each vote's day, the weekly turns for twelve weeks
    from the first date in STATUS in Member order (rule 7), and each known bug's fix-by day."""
    def day(d):
        return d.replace("-", "")

    ev = []
    for by in sorted({b for _, b, _ in votes if b}):
        ev.append((by, days_after(by, 1), "Assembly vote: " + "; ".join("%s (%s %s)" % (v, h, b) for v, b, h in votes
                                                                         if b == by), "vote-" + by))
    close = max((b for _, b, h in votes if b and h == "by"), default="")
    if start:
        for w in range(12):
            d = days_after(start, 7 * w)
            dry = ", a dry run: the vote is open" if days_after(d, 7) <= close else ""   # process.md section 10, the freeze
            ev.append((d, days_after(d, 7), "Assembly weekly turn: %s (rule 7)%s" % (members[w % len(members)], dry),
                       "turn-" + d))
    bugs = re.sub(r"\s+", " ", " ".join(next((b for h, b in secs if short(h).startswith("KNOWN BUGS")), [])))
    for n, d in re.findall(r"\b(\d{1,2})\. (?=[A-Z])(?:(?!\b\d{1,2}\. [A-Z]).)*?Fix by:\s*(\d{4}-\d\d-\d\d)", bugs):
        ev.append((d, days_after(d, 1), "Assembly: known bug %s, fix by" % n, "bug-" + n))
    def text(t):   # RFC 5545 TEXT: backslash, semicolon and comma are escaped; line breaks cannot occur here
        return t.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
    out = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//febu assembly//ledger.txt//EN"]
    for a, b, what, uid in ev:                      # the UID's domain is only an id: changing it would double every event already imported
        out += ["BEGIN:VEVENT", "UID:%s@febu-ledger.vercel.app" % uid, "DTSTAMP:%sT000000Z" % day(start or a),
                "DTSTART;VALUE=DATE:" + day(a), "DTEND;VALUE=DATE:" + day(b), "SUMMARY:" + text(what), "URL:" + FRONT,
                "END:VEVENT"]
    return "\r\n".join(out + ["END:VCALENDAR"]) + "\r\n"


def short_addr(text):
    """Off the ledger page an address shows as its first eight letters, the way the ledger writes UqN2p5bA..."""
    return ADDRESS.sub(lambda m: m.group()[:8] + "...", text)


def name_options(members):
    return ('<option value="">choose</option>%s<option value="*">someone else</option>'
            % "".join('<option>%s</option>' % html.escape(m) for m in members))


def check_card(q, a, members):
    """The check card: tick the WRONG IF lines you tested, say what you saw on each and how many of its items you opened,
    one new thing on the page, your name and your result. claims.js writes the chat post from it, and says so when a
    HOLDS does not name every line with "all" for each (Result): it still goes in, and counts toward nothing."""
    aid = answer_id(q["num"], a["num"])
    tests = ('<fieldset class="cc-set"><legend>Which WRONG IF lines did you test? Say what you saw on each.</legend>'
             '<ol class="lns">%s</ol></fieldset>' % "".join(
                 '<li><label class="ln"><input type="checkbox" class="ln-on" value="%d"><span class="n">%d</span>'
                 '<span class="t">%s</span></label><input type="text" class="saw" data-line="%d" autocomplete="off" '
                 'aria-label="What you saw on line %d" placeholder="What you saw: the number, the words or the date" '
                 'hidden><input type="text" class="items" data-line="%d" autocomplete="off" aria-label="Items you '
                 'opened on line %d" placeholder="How many of its items you opened: all 1, all 164, or 20 of 164" '
                 'hidden></li>' % (i, i, html.escape(short_addr(t)), i, i, i, i) for i, t in enumerate(a["lines"], 1)))
    return (
        '<div class="cc" id="check-%s" data-q="%d" data-a="%d" data-lines="%d" data-posters="%s" hidden>'
        '<p class="cc-lead">Open the answer\'s links and look before you read anyone\'s post about it. Fill this in and '
        'the post writes itself below. Whoever posted or changed the answer does not check it (rule 4).</p>%s'
        '<label class="f">One thing on the page that is not in the answer or in any earlier post <b>needed</b>'
        '<input type="text" class="new" autocomplete="off" placeholder="A number, a name, a date, a word"></label>'
        '<div class="cc-pair"><label class="f">Your name<select class="who">%s</select>'
        '<input type="text" class="other" autocomplete="off" placeholder="Your name in the chat" '
        'aria-label="Your name in the chat" hidden></label></div>'
        '<fieldset class="res"><legend>Your result</legend>'
        '<label class="pill yes"><input type="radio" name="res-%s" value="HOLDS"><span>HOLDS</span></label>'
        '<label class="pill no"><input type="radio" name="res-%s" value="DOESN\'T HOLD"><span>DOESN\'T HOLD</span>'
        '</label></fieldset>'
        '<label class="tick"><input type="checkbox" class="opened">I opened the links myself. No AI wrote this result.'
        '</label><div class="post-box"><p class="post-h">Your post, as the chat will show it</p>'
        '<pre class="post" aria-live="polite"></pre></div><p class="need" id="need-%s"></p>'
        '<p class="acts"><button type="button" class="btn primary cc-copy" disabled aria-describedby="need-%s">'
        'Copy the post</button></p><p class="hint">Paste it in the chat yourself: this page sends nothing. That '
        'week\'s member copies it into the ledger as a SEEN item (rule 7).</p></div>'
        % (aid, q["num"], a["num"], len(a["lines"]), html.escape("|".join(sorted(a["posters"]))), tests,
           name_options(members), aid, aid, aid, aid))


def answer_state_text(a):
    st = a["state"]
    found = len(a["results"])
    return (state_text(st) or ("%d result%s posted" % (found, "" if found == 1 else "s") if found
                               else "checks posted" if checked(a["fields"]) else "not yet checked"))


def pick_li(q, a, members):
    """One answer as a card on the front page: what it says, where it stands, a way in, and while it is OPEN, the check
    card that writes the result post. No name: the answer is the Assembly's (rule 3)."""
    done = a["state"]["state"] != "OPEN"
    card = "" if done else check_card(q, a, members)
    aid = answer_id(q["num"], a["num"])
    toggle = ('<button type="button" class="btn primary cc-open" aria-expanded="false" aria-controls="check-%s">'
              'Check it here</button>' % aid if card else "")
    return ('<li class="pick" id="pick-%s"><div class="top"><span class="num">Q%d answer %d</span><span class="chip%s">'
            '%s</span></div><p class="says">%s</p><p class="acts"><a class="btn%s" href="ledger.html#%s">Open the '
            'answer</a>%s</p>%s</li>' % (aid, q["num"], a["num"], " done" if done else "",
                                         html.escape(("closed: " if done else "") + answer_state_text(a)),
                                         html.escape(text_of(a["fields"], "SAYS")), "" if card else " primary", aid,
                                         toggle, card))


def yes_count(p, members, adopted_on):
    """(the yeses that count toward rule 2 so far, the day it reached three or None)"""
    got = {n for n, d in p["yes"] if n in members and n != p["who"] and adopted_on and a_day(d)
           and d >= max(adopted_on, p["date"])}
    return len(got), p["reach"]


def next_move(members, m, todo, waiting, votes, start, remind):
    """Pick your name, see your week as five numbered steps: check (the open answers you did not post and have no SEEN
    item on yet), propose and say yes (the proposals not yours that have no yes of yours), vote (what is open), the
    weekly turn (yours when the order reaches you) and write. One panel per name, written here; claims.js shows the one
    picked, counts the days to each date and works out the turns from the device's date. The device remembers the name
    (claims.js), and #me=Name in the address picks it, so each member has a link. Under the steps: a post that reminds
    the group what is due, for anyone to send, and the dates as a calendar file (assembly.ics). No totals: rule 9."""
    q = open_question(m)

    def chip(text, cls="", **attrs):
        return '<span class="chip%s"%s>%s</span>' % (" " + cls if cls else "", "".join(
            ' data-%s="%s"' % (k, html.escape(v)) for k, v in attrs.items()), html.escape(text))

    def step(n, title, chip_html, body):
        return '<li class="st"><span class="n">%d</span><div><h3>%s %s</h3>%s</div></li>' % (n, title, chip_html, body)

    def copy(label, text):
        return '<button type="button" class="btn copy" data-copy="%s">%s</button>' % (html.escape(text), label)

    def panel(name):
        mine = [(qq, a) for qq, a in todo if name == "*" or (name not in a["posters"]
                                                               and name not in {r[0] for r in a["results"]})]
        rows = "".join('<li><a href="#check-%s"><span class="num">Q%d answer %d</span><span class="says">%s</span></a>'
                       '</li>' % (answer_id(qq["num"], a["num"]), qq["num"], a["num"],
                                  html.escape(text_of(a["fields"], "SAYS"))) for qq, a in mine)
        if rows:
            check, c = '<ul class="todo">%s</ul>' % rows, chip("%d open to you" % len(mine), "due")
        else:
            check, c = "<p>None open to you right now.</p>", chip("none open")
        if name == "*":
            check = ('<p class="hint">Your result counts toward keeping an answer open or reopening it, not toward '
                     'closing it (rule 5). Post it in the chat; any member adds the line.</p>') + check
            yes, y = "<p>Only members propose and say yes (rule 2).</p>", chip("members only")
            vote, v = "<p>Only members vote (rule 8).</p>", chip("members only")
            turn, t = "<p>Only members take the turn (rule 7).</p>", chip("members only")
        else:
            open_to = [p for p in waiting if p["who"] != name and name not in {n for n, _ in p["yes"]}]
            yes = "".join('<p>P%d: %s</p><p class="acts">%s</p>' % (
                p["num"], html.escape(p["asks"]), copy("Copy a yes", CHAT.join(("YES P%d" % p["num"], name, "{today}"))))
                for p in open_to) or "<p>No proposal waits for your yes.</p>"
            yes += ('<p>Propose a question a link anyone can open could settle (rule 1). The first proposal with three '
                    'yeses from other members opens next (rule 2).</p><p class="acts">%s</p>'
                    % copy("Copy a proposal", CHAT.join(("PROPOSE P%d" % m["next"]["proposal"],
                                                      "<the question, in one sentence>", name, "{today}"))))
            y = chip("%d waiting" % len(open_to), "due") if open_to else chip("any time")
            if votes:
                vote = "".join(
                    '<p>%s: &ldquo;yes&rdquo; or &ldquo;object&rdquo;%s (rule 8).</p><p class="acts">%s%s</p>'
                    % (html.escape(s), " %s %s" % (how, by) if by else "", copy("Copy a yes", CHAT.join(
                        ("VOTE YES", s, name, "{today}"))), copy("Copy an objection", CHAT.join(
                            ("VOTE OBJECT", s, name, "{today}")) + "\nWhich line is wrong: \nWhat would change my mind: "))
                    for s, by, how in votes)
                v = (chip("by " + votes[0][1], "due", due=votes[0][1]) if votes[0][1] and votes[0][2] == "by"
                     else chip("open", "due"))
            else:
                vote, v = "<p>Nothing is up for a vote in the ledger.</p>", chip("none open")
            turn = ('<p class="turn-me" data-name="%s">Yours when the order reaches you%s.</p><p class="turn-you" hidden>'
                    '<b>That is you this week.</b><a class="btn primary" href="weekly.html">Do the weekly turn</a></p>'
                    '<p class="hint">Paste the week\'s chat. The page lists the SEEN items, proposals, yeses and votes '
                    'to add and a LAST POSTS line, for you to copy into the ledger (rule 7).</p>'
                    % (html.escape(name), ", counted from %s" % start if start else ""))
            t = chip("in Member order", "turn-chip", name=name)
        write = ('<p><a href="write.html">Write an answer to Q%d</a>: what it says, a link anyone can open, and one line '
                 'for each part of it that would prove it wrong.</p>' % q["num"] if q else
                 "<p>No question is open, so there is nothing to answer yet. Propose one (step 2).</p>")
        link = "" if name == "*" else (
            '<p class="mylink">Your link, for a bookmark or your DM thread: <a href="#me=%s">%s#me=%s</a> '
            '<button type="button" class="btn copy" data-copy="%s#me=%s">Copy your link</button></p>'
            % (quote(name), FRONT.split("//")[1], quote(name), FRONT, quote(name)))
        return ('<div class="moves" data-who="%s" hidden><ol class="steps">%s%s%s%s%s</ol>%s</div>'
                % (html.escape(name), step(1, "Check", c, check), step(2, "Propose and say yes", y, yes),
                   step(3, "Vote", v, vote), step(4, "Weekly turn", t, turn), step(5, "Write", chip("any time"), write),
                   link))

    chips = "".join('<label class="name"><input type="radio" name="me" value="%s"><span>%s</span></label>'
                    % (html.escape(n), html.escape(n if n != "*" else "someone else")) for n in members + ["*"])
    turn = ('<div class="turn" data-from="%s" data-order="%s"><h3>Weekly turn (rule 7)</h3><p class="turn-now">One '
            'member a week, in this order%s: %s. A turn not done by the end of its week passes to the next.</p></div>'
            % (start or "", html.escape("|".join(members)), ", counted from %s" % start if start else "",
               html.escape(", ".join(members))))
    first_vote = next((v for v in votes if v[1] and v[2] == "by"), None)
    remind_html = ('<div class="remind"><h3>Remind the group</h3><p>What is due, as one post for the chat. Anyone '
                   'can send it; the dates come from the ledger.</p><pre class="lit keep" id="due-post" data-by="%s">%s'
                   '</pre><p class="acts"><button type="button" class="btn copy" data-copy="%s">Copy the reminder'
                   '</button><a class="btn" href="assembly.ics" download>Add the dates to your calendar</a></p></div>'
                   % (html.escape(first_vote[1] if first_vote else ""), html.escape(remind), html.escape(remind)))
    return ('<section class="win next" id="next" aria-labelledby="next-h"><h2 class="bar" id="next-h">your week'
            '<span class="q">pick your name, then the five steps</span></h2><div class="win-body"><fieldset class="names">'
            '<legend>Pick your name</legend>%s</fieldset><p class="hint moves-none">Pick a name to see what you can '
            'check, what waits for your yes, what is up for a vote, and when your weekly turn comes. The name is a '
            'claim, like a post in the chat: the site vouches for nobody. This device keeps it, with any unfinished '
            'post, so you come back to it. The first line of every post is what the weekly page reads: keep it as the '
            'buttons write it.</p><p class="acts links-all"><button type="button" class="btn copy" data-copy="%s">Copy '
            'a link for each member</button></p>%s%s%s</div></section>'
            % (chips, html.escape("\n".join("%s: %s#me=%s" % (n, FRONT, quote(n)) for n in members)),
               "".join(panel(n) for n in members + ["*"]), turn, remind_html))


def one_sentence(how_secs):
    """how.txt's ONE SENTENCE as three short lines, one to a clause."""
    body = next((b for h, b in how_secs if short(h) == "ONE SENTENCE"), None)
    if body is None:
        sys.exit("how.txt has no ONE SENTENCE section; the front page opens with it")
    clauses = [c.strip().rstrip(".") for c in " ".join(r.strip() for r in body).split(";")]
    return "".join("<span>%s.</span>" % html.escape(c[0].upper() + c[1:]) for c in clauses if c)


def assembly_page(title, secs, how_secs, m):
    """The Assembly's front page, for someone who has just followed a link: the task now in the banner, what this is in
    a sentence, the open question with a check card under each of its open answers, the proposals waiting for yeses;
    then your week by name (check, propose and say yes, vote, the weekly turn, write, with what is due, a reminder post
    and the calendar file), every question, how to check, who and the scripts. Answers are shown as the Assembly's,
    with no name, and nothing is totalled by member (rules 3 and 9)."""
    doc = Doc(secs, "ledger.html")
    names = m["members"]
    q = open_question(m)
    todo = [(q, a) for a in q["answers"] if a["state"]["state"] == "OPEN"] if q else []
    waiting = [p for p in m["proposals"] if p["opened"] is None]
    proposed = status(secs)[1]
    votes = open_votes(title, secs, m)
    start = turn_start(secs)

    if q and todo:
        task = "<p><strong>Your task now:</strong> check an answer to Q%d below and post what you saw." % q["num"]
    elif q:
        task = ('<p><strong>Your task now:</strong> Q%d has no open answer: <a href="write.html">write one</a>.'
                % q["num"])
    else:
        task = ("<p><strong>Your task now:</strong> no question is open. Propose one, or say yes to one below "
                "(<a href=\"#next\">pick your name</a>).")
    if votes:
        task += (' Then vote &ldquo;yes&rdquo; or &ldquo;object&rdquo; on %s (<a href="#next">pick your name</a>).'
                 % html.escape("; ".join(s for s, _, _ in votes)))
    task += "</p>"
    due = ['Q%d: CAN\'T TELL after <time data-due="%s">%s</time>' % (q["num"], q["state"]["until"], q["state"]["until"])
           ] if q and q["state"]["until"] else []
    due += ['vote %s %s <time data-due="%s">%s</time>' % (html.escape(s), how, by, by) for s, by, how in votes if by]
    if start:
        due.append('weekly turn: <span class="due-turn">in Member order from %s%s</span>'
                   % (start, ", a dry run until the vote closes" if proposed else ""))
    due.append('<a href="assembly.ics" download>the dates as a calendar</a>')
    task += '<p class="due"><b>Due</b> %s</p>' % " &middot; ".join(due)

    remind = ["DUE" + CHAT + "{today}"]
    if q:
        remind.append("Open question: Q%d, CAN'T TELL after %s. Post: CHECK Q%d ANSWER n%sHOLDS%slines 1,2%s<your name>"
                      "%s<date>." % (q["num"], q["state"]["until"], q["num"], CHAT, CHAT, CHAT, CHAT))
    if waiting:
        remind.append("Proposals waiting for yeses: %s. Post: YES P%d%s<your name>%s<date>."
                      % (", ".join("P%d" % p["num"] for p in waiting), waiting[0]["num"], CHAT, CHAT))
    if votes:
        remind.append("Vote: %s. Post: VOTE YES%s<what>%s<your name>%s<date>."
                      % ("; ".join("%s (%s %s)" % (s, how, by) if by else s for s, by, how in votes), CHAT, CHAT, CHAT))
    if start:
        remind.append("Weekly turn this week, to {turnend}: {turn}. Next: {next}.")
    remind = "\n".join(remind + [FRONT])

    if q:
        picks = ('<p class="says">Q%d asks: %s</p><p class="hint">%s</p>' % (q["num"], doc.fmt(q["asks"]),
                                                                              html.escape(question_text(q)))
                 + ('<ul class="picks">%s</ul>' % "".join(pick_li(qq, a, names) for qq, a in todo) if todo else
                    '<p>No open answer yet. <a href="write.html">Write one</a>.</p>'))
    else:
        picks = "<p>No question is open. The first proposal with three yeses from other members opens next (rule 2).</p>"
    props = "".join('<li><a href="ledger.html#prop-P%d"><span class="num">P%d</span><span class="says">%s</span>'
                    '<span class="state">%s</span></a></li>' % (p["num"], p["num"], html.escape(p["asks"]), (
                        "three yeses on %s" % p["reach"] if p["reach"] else "%d of 3 yeses" % yes_count(
                            p, names, m["adopted"])[0])) for p in waiting)
    if props:
        picks += '<h3>Proposed questions</h3><ul class="entries">%s</ul>' % props
    first_win = ('<section class="win start" id="start" aria-labelledby="start-h"><h2 class="bar" id="start-h">'
                 'start here: %s</h2><div class="win-body"><p class="sentence">%s</p>%s%s'
                 '<p class="go"><a href="how.html">How it works, in one picture</a> <a href="#every">Every question</a>'
                 '</p></div></section>' % ("the open question" if q else "no question open", one_sentence(how_secs),
                                           picks, '<p class="hint">The vote week is also a dry run. Post what you '
                                           'saw.</p>' if proposed else ""))
    rows = "".join('<li><a href="ledger.html#q-%d"><span class="num">Q%d</span><span class="says">%s</span>'
                   '<span class="state">%s</span></a></li>' % (x["num"], x["num"], html.escape(x["asks"]),
                                                               html.escape(question_text(x))) for x in m["questions"])
    every = ('<details class="win lead" id="every" data-open-wide><summary><span class="t">every question</span>'
             '<span class="q">%d so far</span></summary><div class="win-body">%s<p class="go"><a href="ledger.html">'
             'Read the whole ledger</a></p></div></details>'
             % (len(m["questions"]), '<ul class="entries">%s</ul>' % rows if rows else "<p>None yet.</p>"))

    def small(key, title, text, href, go):
        return ('<section class="win" aria-labelledby="%s-h"><h2 class="bar" id="%s-h">%s</h2><div class="win-body">'
                '<p>%s</p><p class="go"><a href="%s">%s</a></p></div></section>' % (key, key, title, text, href, go))

    body = (first_win + next_move(names, m, todo, waiting, votes, start, remind) + every + check_section(secs, doc) +
            '<div class="more">%s</div>' % "".join([
                small("who", "who: members (%d)" % len(names), "Any three of them who did not post an answer, one of "
                      "them opening every link by hand, close it (rule 4). Anyone at all can keep one open or reopen "
                      "it with a second person (rule 5).", "ledger.html#words-used-here", "Members, posters and Saw"),
                small("scripts", "run a script", "The scripts read version 3's facts, kept word for word in the "
                      "archive, with Python 3 and no account or key. A script counts toward Saw when none of an "
                      "answer's posters wrote it, you ran it yourself, and you opened one link by hand: say whose it "
                      'is on the Script: line. <a href="%s">What makes a script count</a>.'
                      % "process.html#5-add-on-a-scripts",
                      "https://github.com/zinotino/febu-assembly/tree/main/checks", "The scripts, with a line each")]))
    return page("febu-assembly.html", "febu assembly", "febu assembly",
                "%d members studying febu, one question at a time, in a ledger anyone can check" % len(names), body,
                mast=status_banner(secs, doc, brief=True, task=task), source=" from ledger.txt", connect="'self'",
                share="febu assembly: one question about febu at a time, answers anyone can check",
                description="One question about febu at a time; each answer has a link and a line that would prove it "
                "wrong. %s%s" % ("Q%d is open: check an answer." % q["num"] if q else "No question is open yet.",
                                 " Proposed, not yet adopted." if proposed else ""),
                foot='This site and the ledger file are run by Z for now (<a href="ledger.html#bug-1">known bug 1</a>). '
                'This page keeps your name and unfinished posts on your device only, and loads nothing from other '
                'sites. Nothing is counted.')


GITHUB_EDIT = "https://github.com/zinotino/febu-assembly/edit/main/ledger.txt"


def clip(s):
    """An address cut to its first 7 characters: they belong on the ledger page and in ledger.txt only."""
    return ADDRESS.sub(lambda m: m.group()[:7] + "…", s)


def ledger_dict(title, secs, m, more=False):
    """What the weekly page needs from ledger.txt: the members in order, each name's dated posts (for "active"), the
    proposals, each question and its answers' posters, WRONG IF line count, results and state, rule 2's order, the
    votes, the last LAST POSTS line and the next numbers. No addresses. more=True adds each answer's SAYS, WRONG IF
    clauses, page address and the version-3 entry it copies, if any (ledger.json)."""
    qs = []
    for q in m["questions"]:
        ans = []
        for a in q["answers"]:
            e = {"num": a["num"], "posters": sorted(a["posters"]), "lines": len(a["lines"]),
                 "empty": not checked(a["fields"]), "start": a["start"], "state": a["state"],
                 "results": [[n, d, w, list(ls), [list(i) for i in it], sc and list(sc)]
                             for n, d, w, ls, it, sc in a["results"]]}
            if more:
                cp = COPIED.search(a["head"])
                e.update(says=clip(text_of(a["fields"], "SAYS")), wrong_if=[clip(c) for c in a["lines"]],
                         url="%s/ledger.html#%s" % (SITE, answer_id(q["num"], a["num"])),
                         copies=cp and [cp.group(1).upper(), int(cp.group(2))])   # agent.py runs that entry's scripts
            ans.append(e)
        qs.append({"num": q["num"], "opened": q["opened"], "from": q["from"], "asks": clip(q["asks"]),
                   "state": q["state"], "answers": ans})
    return {"members": m["members"], "adopted": m["adopted"], "as_of": m["as_of"], "posts": m["posts"],
            "proposals": [{"num": p["num"], "who": p["who"], "date": p["date"], "asks": clip(p["asks"]),
                           "yes": [list(y) for y in p["yes"]], "opened": p["opened"], "reach": p["reach"]}
                          for p in m["proposals"]],
            "questions": qs, "slot": [list(s) for s in m["slot"]], "next": m["next"],
            "votes": [{"subject": v["subject"], "posted": v["posted"], "votes": [list(x) for x in v["votes"]],
                       "passed": v["passed"]} for v in m["votes"]],
            "open_votes": [{"subject": s, "day": d, "how": h} for s, d, h in open_votes(title, secs, m)],
            "last": [m["last"][-1][0], m["last"][-1][1]] if m["last"] else None}


def ledger_data(title, secs, m):
    """ledger_dict as JSON in the weekly page."""
    return ('<script type="application/json" id="ledger-data">%s</script>'
            % json.dumps(ledger_dict(title, secs, m)).replace("</", "<\\/"))


def ledger_json(title, secs, raw, m):
    """ledger.json: the same state for an agent that reads data and not pages, with the hash of the text it came from.
    Links and addresses stay in ledger.txt, which wins wherever the two differ. Nothing can be posted back."""
    out = {"about": "A read-only index of ledger.txt, written by build.py. ledger.txt is the record and wins where they "
                    "differ. Links are not here, and an address is cut to its first 7 characters: read ledger.txt for them.",
           "ledger": {"url": SITE + "/ledger.txt", "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)},
           "proposed": status(secs)[1], **ledger_dict(title, secs, m, more=True)}
    text = json.dumps(out, indent=1, ensure_ascii=False) + "\n"
    vetted("ledger.json", text.replace(out["ledger"]["sha256"], ""))   # a hash with no 0 in it (1 in 60) reads as an address
    return text


def step(n, key, head, inner, hidden=False):
    return ('<section class="win step" id="%s" aria-labelledby="%s-h"%s><h2 class="bar" id="%s-h"><span class="n">%d</span>'
            '%s</h2><div class="win-body">%s</div></section>' % (key, key, " hidden" if hidden else "", key, n, head, inner))


def weekly_page(title, secs, m):
    """The weekly turn (rule 7) as one page: paste the week's chat, and claims.js reads every CHECK, PROPOSE, YES, VOTE
    and ANSWER post in it and lists, in the ledger's layout, the SEEN items to add and the answers rule 4 would close,
    the proposals and yeses to add and what rule 2 opens, the VOTES items and the count under rule 8, a LAST POSTS
    line, and every line it could not read. It never edits the file: the member pastes into ledger.txt on GitHub."""
    doc = Doc(secs, "ledger.html")
    out = lambda key: '<div id="%s"></div>' % key   # noqa: E731
    body = ('<div class="intro"><p>%s</p></div>' % doc.fmt(
                "Each week one member, in Member order, checks both ways: every result, proposal, yes and vote posted in "
                "the chat that week is in the file, and every SEEN, PROPOSED and VOTES item in the file has its post in "
                "the chat (rule 7). Paste the week's chat below. This page reads the posts whose first line starts "
                "CHECK, PROPOSE, YES, VOTE or ANSWER, and shows you everything else to read yourself. It changes "
                "nothing: you copy what it writes into ledger.txt.")
            + step(1, "w-paste", "paste the week's chat",
                   '<label class="f" for="chat">Everything posted in the chat this week, copied out of it</label>'
                   '<textarea id="chat" rows="10" spellcheck="false" autocomplete="off" placeholder="CHECK Q1 ANSWER 1'
                   + html.escape(CHAT) + 'HOLDS' + html.escape(CHAT) + 'lines 1,2' + html.escape(CHAT) + 'Laura'
                   + html.escape(CHAT) + '2026-11-02&#10;Line 1: ...&#10;Saw: ...&#10;Items: all 1"></textarea>'
                   '<p class="hint">Read on your device. Nothing is sent or kept: reload the page and it is gone.</p>'
                   '<p class="msg" id="w-sum" role="status"></p>')
            + step(2, "w-seen", "SEEN items and answers to add", out("w-seen-out"), hidden=True)
            + step(3, "w-back", "SEEN items with no post in what you pasted", out("w-back-out"), hidden=True)
            + step(4, "w-close", "answers that would close (rule 4)", out("w-close-out"), hidden=True)
            + step(5, "w-props", "proposals and yeses, and what opens (rule 2)", out("w-props-out"), hidden=True)
            + step(6, "w-votes", "votes (rule 8)", out("w-votes-out"), hidden=True)
            + step(7, "w-last", "the LAST POSTS line", out("w-last-out"), hidden=True)
            + step(8, "w-unread", "lines it could not read", out("w-unread-out"), hidden=True)
            + step(9, "w-file", "put it in the file, then post the hash",
                   '<ol class="plain">' + ('<li>Not during a vote: until the vote closes the file does not change, so '
                                           'this week stops at step 8 and you post what it would add.</li>'
                                           if status(secs)[1] else '') + '<li><a href="%s" rel="noopener '
                   'noreferrer">Open ledger.txt on GitHub</a> and press '
                   'the pencil (README, &ldquo;Editing in the browser&rdquo;).</li><li>Paste each block where its step '
                   'says, lined up like the lines around it. Add nothing else.</li><li>Commit to main (only Z can '
                   'today, KNOWN BUGS 1; anyone else gets &ldquo;Propose changes&rdquo;, which Z merges). The site '
                   'rebuilds in a minute or two; if the build stops, GitHub shows a red cross and the site keeps the '
                   'version before.</li><li>Open <a href="ledger.html#the-text">the ledger page</a> and copy the new '
                   'SHA-256. Post it in the chat and in one public place outside it, naming the place.</li></ol>'
                   % GITHUB_EDIT)
            + ledger_data(title, secs, m))
    return page("weekly.html", "The weekly turn", "the weekly turn", "paste the week's chat, copy what goes in the file",
                body, mast=status_banner(secs, doc, brief=True), source=" from ledger.txt",
                description="The febu Assembly's weekly turn: paste the week's chat and get the SEEN items, proposals, "
                "yeses and votes to add, the answers that would close and a LAST POSTS line, ready to copy into the "
                "ledger.")


def write_page(secs, m):
    """The answer form: SAYS, LINK and one WRONG IF line per part of SAYS, for the open question. claims.js lays it out
    as the ledger writes answers and as a chat post."""
    doc = Doc(secs, "ledger.html")
    how = next((b for h, b in secs if short(h) == "HOW A QUESTION IS WRITTEN"), None)
    if how is None:
        sys.exit("the ledger has no HOW A QUESTION IS WRITTEN section; the answer form shows it")
    q = open_question(m)
    n = len(q["answers"]) + 1 if q else 1
    wi = ('<li class="wi"><span class="n">1</span><input type="text" class="wi-t" autocomplete="off" aria-label="WRONG IF '
          'line 1" placeholder="the balance on 2026-10-14 was below 11.12 SOL"><button type="button" class="btn wi-x" '
          'aria-label="Remove WRONG IF line 1">Remove</button><p class="warn" hidden>No date in this line. If someone '
          'outside the group could make it true later, with a transfer or a new post, end it: &ldquo;by the end of '
          '2026-10-14&rdquo;.</p></li>')
    form = ('<div class="wf" data-q="%s" data-next="%d"><div class="cc-pair"><label class="f">Your name<select class="who">'
            '%s</select><input type="text" class="other" autocomplete="off" placeholder="Your name in the chat" '
            'aria-label="Your name in the chat" hidden></label><p class="f num-note">%s</p></div>'
            '<label class="f">SAYS<span class="q">one sentence</span><textarea class="says" rows="3" '
            'placeholder="Between 2026-09-29 and 2026-10-09 the wallet that created $FEBU bought no $FEBU."></textarea>'
            '</label><label class="f">LINK<span class="q">full links anyone can open without asking you (rule 3), one '
            'to a line; a line of words says what to look for</span><textarea class="link" rows="3" spellcheck="false" '
            'placeholder="https://..."></textarea></label><fieldset class="cc-set wis-set"><legend>WRONG IF<span '
            'class="q">one line for each part of SAYS</span></legend><p class="prompt">Could a stranger make this '
            'true? End-date it.</p><ol class="wis">%s</ol><p class="acts"><button type="button" class="btn wi-add">'
            'Add a WRONG IF line</button></p></fieldset><p class="need" id="need-w"></p></div>'
            % (q["num"] if q else "", n, name_options(m["members"]),
               "This will be <b>answer %d to Q%d</b>, the number the ledger gives next. If someone posts an answer "
               "before yours, take the one after." % (n, q["num"]) if q else
               "<b>No question is open</b>, so there is nothing to answer yet.", wi))
    copy = lambda cls, label: ('<p class="acts"><button type="button" class="btn primary %s" disabled '   # noqa: E731
                               'aria-describedby="need-w">%s</button></p>' % (cls, label))
    body = ('<div class="intro"><p>%s</p></div>' % doc.fmt(
                "Write an answer to the open question the way the ledger writes them, and post it in the chat. Nobody "
                "approves it, and the pages show it as the Assembly's (rule 3). Three members who did not post or "
                "change it check it by opening its links (rule 4). Every part of SAYS needs a WRONG IF line that would "
                "catch it; if SAYS claims more, cut SAYS.")
            + step(1, "w-form", "write it", form)
            + step(2, "w-chat", "post it in the chat",
                   '<pre class="post keep chat-out" aria-live="polite"></pre>%s<p class="hint">Paste it yourself: this '
                   'page sends nothing. Until its first SEEN item anyone may change it with a dated CHANGED line '
                   '("CHANGED   Name, YYYY-MM-DD: what changed"); after that, never: post a new answer.</p>'
                   % copy("w-copy-chat", "Copy the chat post"))
            + step(3, "w-file", "put it in ledger.txt",
                   '<pre class="post keep entry-out"></pre>%s<p class="hint">%s week\'s member: on '
                   '<a href="%s" rel="noopener noreferrer">ledger.txt on GitHub</a>, press the pencil, and paste it '
                   'under the question, after its last answer (README, Add an answer). Only Z can commit there today '
                   '(KNOWN BUGS 1); anyone else gets &ldquo;Propose changes&rdquo;, which Z merges.</p>'
                   % (copy("w-copy-entry", "Copy the answer"), (
                       "Not during a vote: until the vote closes the file does not change, and your chat post waits in "
                       "the chat. After it, the" if status(secs)[1] else "The"), GITHUB_EDIT))
            + '<details class="win" id="how-written"><summary><span class="t">how a question is written</span><span '
              'class="q">in the ledger\'s own words</span></summary><div class="win-body">%s</div></details>'
            % doc.blocks(to_lines(how), 2))
    return page("write.html", "Write an answer", "write an answer", "what it says, a link, and what would prove it wrong",
                body, mast=status_banner(secs, doc, brief=True), source=" from ledger.txt",
                description="Write an answer to the febu Assembly's open question: what it says, a link anyone can "
                "open, and what would prove it wrong. Laid out for the ledger and the chat.")


def main():
    raw = raw_text(LEDGER)
    text = raw.decode("utf-8").rstrip("\n")
    title, secs = sections(text)
    m = model(secs)
    how = raw_text(HOW).decode("utf-8").rstrip("\n")
    ledger, archives = ledger_page(text, raw, m)
    pages = {
        "ledger.html": ledger,
        "tests.html": tests_page(raw_text(TESTS).decode("utf-8").rstrip("\n"), secs),
        "how.html": how_page(how, secs),
        "febu-assembly.html": assembly_page(title, secs, sections(how)[1], m),
        "weekly.html": weekly_page(title, secs, m),
        "write.html": write_page(secs, m),
        "process.html": process_page(),
    }
    index = ledger_json(title, secs, raw, m)   # before any file is written: a refusal must not leave the repo half built
    if LEDGER.read_bytes() != raw:   # the page prints the hash of the LF text, so serve exactly that
        LEDGER.write_bytes(raw)
    for name, out in pages.items():
        (ROOT / name).write_text(out, encoding="utf-8", newline="\n")
    (ROOT / "ledger.json").write_text(index, encoding="utf-8", newline="\n")
    (ROOT / "assembly.ics").write_bytes(calendar_ics(open_votes(title, secs, m), m["members"], turn_start(secs),
                                                     secs).encode("utf-8"))
    print("ledger.txt sha256 %s (%d bytes); %s; wrote %s" % (
        hashlib.sha256(raw).hexdigest(), len(raw), ", ".join("%s sha256 %s" % (p, d[:16]) for p, _, d in archives),
        ", ".join([*pages, "ledger.json"])))


if __name__ == "__main__":
    main()
