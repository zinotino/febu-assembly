"""Build the Assembly's pages, next to this file, from the texts beside them. All share one set of tabs.

  febu-assembly.html  the front page: status, a check card under each open entry (it writes the result post),
                      "your next move" by name, every entry and whether anyone has checked it, and the ledger's
                      HOW TO CHECK AN ENTRY (#check; /start.html redirects there)
  weekly.html   the weekly turn (rule 6): paste the week's chat, get the SEEN lines to add, the entries that would
                close, the vote counts and the lines left to read; it never edits ledger.txt
  write.html    the entry form: a fact laid out for ledger.txt and for the chat
  ledger.html   ledger.txt as a page, in the text's own order: STATUS as a banner, each entry as a card
                (#fact-6, with #6 kept for links made before version 2), and under the fact that
                fact-6-steps.txt is about, its steps and every row with a link
  how.html      how.txt: the ledger in plain words, with assets/how-it-works.svg and how-it-connects.svg
  process.html  process.md: the whole process in one file, the clock and the tests (needs the markdown package;
                otherwise the committed page is kept while process.md is unchanged)
  tests.html    tests.txt as a page       (background: no tab, and nothing on the front page links it)
  people.html   each name ledger.txt gives as a writer or in a SEEN line: what they wrote, what they checked
                (reached from the front page's "who" window, not a tab)
  ledger.json   not a page: the ledger's state as data for an agent (ledger_json): the text's hash, the members, the
                votes, each entry's writer, headline, WRONG IF clauses and results; addresses cut, no links

ledger.txt and archive/ are served as they are; ledger.html prints their SHA-256 (rule 6 relies on that hash).
The pages follow the texts' headings, not their line numbers: reword the texts and re-run.
    python build.py
They load nothing from other sites. Styling is assets/findings.css plus assets/ledger.css; the browser side is
assets/claims.js (tap to copy, and the hash checks).
"""
import datetime
import hashlib
from urllib.parse import quote
import html
import json
import re
import sys
from collections import namedtuple
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LEDGER = ROOT / "ledger.txt"
TESTS = ROOT / "tests.txt"
STEPS = ROOT / "fact-6-steps.txt"
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
    """How text becomes inline HTML on one page: links to the ledger's sections, rules, facts and files."""

    def __init__(self, ledger_sections, base, files=None):
        self.base = base
        self.files = files or {}
        self.secs = {short(h): slug(h) for h, _ in ledger_sections if len(short(h)) >= 5}
        names = "|".join(re.escape(s) for s in sorted(self.secs, key=len, reverse=True)) or "(?!)"
        self.inline = re.compile(
            r"(?P<url>https?://[^\s<>\"]+)|(?P<file>\b(?:archive/)?\w[\w.-]*\.(?:txt|py)\b)|(?P<tok>\b[0-9A-Za-z]{32,}\b)"
            r"|(?P<bug>\bKNOWN BUGS \d+)|(?P<sec>\b(?:%s)(?![\w-]))|(?P<rule>\b[Rr]ules? \d+(?:(?:, | and | to )\d+)*)"
            r"|(?P<fact>\b(?:[Ff]acts?|entry) \d+(?:(?:, | and | to )\d+)*)" % names)

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
                anchor = {"rule": "rule-", "bug": "bug-", "fact": "fact-"}[kind]
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
# The ledger's own parts: entries, fact 6's steps and rows, the carried-over predictions.

ENTRY = re.compile(r"  (FACT|PROMISE) (\d+)\.\s*(?:\((.*)\))?\s*$")
FIELD = re.compile(r"([A-Z]+(?: [A-Z]+)?)(?: {2,}| (?=[a-z\d])|$)")   # "SAYS      one", "IF BROKEN what", "WITHDRAWN 2026-"
HEADLINE = {"FACT": "SAYS", "PROMISE": "WILL"}

# What the site adds beside an entry, never in it. Fact 1: Solscan's $FEBU filter on the creator wallet's transfers
# shows nothing (not even fact 2's sale), so point at the wallet's $FEBU account; checks/resolve.py fact1 derives it.
FACT1_ACCOUNT = "https://solscan.io/account/6PeGko4hvJn8EioYxKera24TrKMfkGUVM7egzrRwNVTo"
SITE_NOTES = {("FACT", "1"): (
    '<p class="hint">Beside the entry, not part of it: Solscan&rsquo;s $FEBU filter on this wallet&rsquo;s transfers '
    'shows nothing, not even the 09-22 sale (fact 2). The wallet&rsquo;s $FEBU account lists its $FEBU swaps, with the '
    'sale as a control: <a href="%s" rel="noopener noreferrer">%s</a> <a class="alt" href="%s" rel="noopener noreferrer">'
    '(explorer.solana.com)</a></p>' % (FACT1_ACCOUNT, FACT1_ACCOUNT, explorer(FACT1_ACCOUNT)))}
CARD_NOTES = {("FACT", "1"): 'Solscan&rsquo;s $FEBU filter on this wallet&rsquo;s transfers shows nothing, not even the '
                             '09-22 sale: use the wallet&rsquo;s $FEBU account, <a href="ledger.html#fact-1">linked under '
                             'fact 1 on the ledger page</a>.'}
W_ITEM = re.compile(r"  (W\d+)\. ")                         # a prediction carried over from version 1
VERDICT = re.compile(r"\b(FAILED|HELD|HOLDS|DOESN'T HOLD|KEPT|BROKEN|CAN'T TELL)((?: (?:in|on) [a-z]+)?)[.:]\s*")
VERDICT_CLASS = {"HELD": "yes", "HOLDS": "yes", "KEPT": "yes", "FAILED": "no", "DOESN'T HOLD": "no", "BROKEN": "no"}


def anchor(kind, num):
    return "%s-%s" % (kind.lower(), num)


def entries(body):
    """THE ENTRIES in order: ('entry', kind, number, who, [(label, [Ln])]) or ('text', [raw lines]) for lines between."""
    out, fcol = [], None
    for raw in body:
        m = ENTRY.match(raw)
        if m:
            out.append(("entry", m.group(1), m.group(2), m.group(3) or "", []))
            fcol = None
            continue
        if not raw.strip():
            continue
        cur = out[-1] if out and out[-1][0] == "entry" else None
        if cur and (fcol is None or indent(raw) >= fcol):
            fcol = indent(raw) if fcol is None else fcol
            f = FIELD.match(raw[fcol:]) if indent(raw) == fcol else None
            if f:
                tcol = fcol + f.end()
                cur[4].append((f.group(1), [Ln(tcol, raw[tcol:].strip(), None, raw.rstrip())]))
            elif cur[4]:
                cur[4][-1][1].extend(to_lines([raw]))
            else:
                sys.exit("%s %s: a line before its first field: %r" % (cur[1], cur[2], raw))
        elif out and out[-1][0] == "text":
            out[-1][1].append(raw)
        else:
            out.append(("text", [raw]))
    return out


def single(html_text):
    """The inside of one paragraph, for a heading. Anything longer stays as it is."""
    if html_text.startswith("<p>") and html_text.endswith("</p>") and html_text.count("<p>") == 1:
        return html_text[3:-4]
    return html_text


def site_note(notes, kind, num, fields):
    """The site's note beside an entry, until the entry's own LINK names the account the note points at."""
    return "" if FACT1_ACCOUNT.rsplit("/", 1)[1] in text_of(fields, "LINK") else notes.get((kind, num), "")


def text_of(fields, label):
    """Every line of the entry's fields with this label, as one line of text."""
    return " ".join(ln.txt for lab, lines in fields if lab == label for ln in lines if ln.txt)


def seen(fields):
    """The entry's SEEN lines as one line of text."""
    return text_of(fields, "SEEN")


def checked(fields):
    """Whether anyone has posted what they saw on this entry (its SEEN lines say more than "nobody yet")."""
    return bool(re.sub(r"(?i)\bnobody yet\b", "", seen(fields)).strip())


def entry_li(kind, num, fields, state):
    """One entry as a line of the front page's list: its number, what it says, where it stands, a link to it."""
    says = " ".join(ln.txt for ln in dict(fields)[HEADLINE[kind]] if ln.txt)
    return ('<li><a href="ledger.html#%s"><span class="num">%s %s</span><span class="says">%s</span>'
            '<span class="state">%s</span></a></li>' % (anchor(kind, num), kind.lower(), num, html.escape(says), state))


def entry_html(kind, num, who, fields, doc, st, extra=""):
    f = dict(fields)
    head = HEADLINE[kind]
    if head not in f:
        sys.exit("%s %s has no %s line" % (kind, num, head))
    verdict = state_text(st, kind, fields) or ("checks posted, see SEEN" if checked(fields) else "not yet checked")
    aid, name = anchor(kind, num), "%s %s" % (kind.lower(), num)
    meta = ['<span>cite as: ledger %s, %s</span>' % (name, verdict), '<span><a href="#%s">link to this %s</a></span>'
            % (aid, kind.lower())]
    if who:
        meta.insert(0, '<span>posted by %s</span>' % html.escape(who))
    rows = "".join('<div><dt>%s</dt><dd>%s</dd></div>' % (label, doc.blocks(lines, lines[0].ind))
                   for label, lines in fields if label != head)
    alias = '<span class="alias" id="%s"></span>' % num if kind == "FACT" else ""   # ledger.html#6, from version 1
    return ('%s<article class="claim entry v-open" id="%s"><div class="mark"><span class="num">%s</span>'
            '<strong class="verdict">%s</strong></div><div class="body"><h3>%s</h3><dl class="fields">%s</dl>%s'
            '<p class="meta">%s</p></div></article>'
            % (alias, aid, name, verdict, single(doc.blocks(f[head], f[head][0].ind)), rows, extra, "".join(meta)))


SIG = r"[1-9A-HJ-NP-Za-km-z]{60,90}"   # a Solana transaction signature
ROW = re.compile(r"\s*(\d+)\s+(\d{4}-\d\d-\d\d \d\d:\d\d)\s+(\d+(?:\.\d+)?)\s+((?:https://solscan\.io/tx/)?%s)(\s+\*)?\s*$" % SIG)
TOTAL = re.compile(r"\s*total\s+(\d+(?:\.\d+)?)\s*$")


def rows_html(head, body, aid, doc):
    """'THE 44 COLLECTIONS ...': every row with a link to it, checked here so a row cannot go missing unseen."""
    want = int(re.match(r"THE (\d+) ", head).group(1))
    rows, total, cols, notes = [], None, None, []
    for raw in body:
        m, t = ROW.match(raw), TOTAL.match(raw)
        if m:
            rows.append(m.groups())
        elif t:
            total = Decimal(t.group(1))
        elif raw.strip() and not rows:
            cols = re.split(r"\s{2,}", raw.strip())
        elif raw.strip():
            notes.append(raw)
    nums = [int(r[0]) for r in rows]
    if nums != list(range(1, want + 1)):
        sys.exit("%s: rows numbered %s, not 1 to %d" % (head, nums, want))
    got = sum(Decimal(r[2]) for r in rows)
    if total is None or got.quantize(total) != total:   # the total line is rounded; compare to as many places
        sys.exit("%s: the rows add up to %s, the total line says %s" % (head, got, total))
    if not cols or len(cols) != 4:
        sys.exit("%s: the line above the rows should name its four columns" % head)
    th = "".join('<th%s>%s</th>' % (' class="n"' if k == 2 else "", html.escape(c)) for k, c in enumerate(cols))
    tr = "".join('<tr id="%s-row-%s"><td>%s</td><td>%s</td><td class="n">%s%s</td><td><a href="https://solscan.io/tx/%s" '
                 'rel="noopener noreferrer" title="open row %s on solscan.io">%s&hellip;</a> <a class="alt" href="%s" '
                 'rel="noopener noreferrer" title="open row %s on explorer.solana.com">explorer</a></td></tr>'
                 % (aid, n, n, d, sol, " *" if star else "", sig, n, sig[:8], explorer("https://solscan.io/tx/" + sig), n)
                 for n, d, sol, sig, star in ((n, d, sol, link.rsplit("/", 1)[-1], star) for n, d, sol, link, star in rows))
    foot = '<tfoot><tr><td></td><td>total</td><td class="n">%s</td><td></td></tr></tfoot>' % total
    rest = head[len(short(head)):].strip()
    return ('<details class="win rows" id="%s-rows"><summary><span class="t">%s</span>%s</summary><div class="win-body">'
            '<p class="hint">Each row opens on solscan.io, where the link shows the start of the transaction\'s '
            'signature (the whole of it is in the link), and on explorer.solana.com.</p>'
            '<div class="tbl"><table><thead><tr>%s</tr></thead><tbody>%s</tbody>%s</table></div>%s</div></details>'
            % (aid, html.escape(short(head).capitalize()), ' <span class="q">%s</span>' % html.escape(rest) if rest else "",
               th, tr, foot,
               doc.blocks(to_lines(notes), min(indent(n) for n in notes)) if notes else ""))


def steps_fact(text):
    m = re.match(r"FACT (\d+) AS STEPS", text)
    if not m:
        sys.exit("%s should start 'FACT n AS STEPS'" % STEPS.name)
    return m.group(1)


def steps_html(text, doc):
    """Fact n's steps file as HTML: its own words, each STEP as a small window, the rows as a table."""
    title, secs = sections(text)
    aid = anchor("FACT", steps_fact(text))
    parts = []
    for head, body in secs:
        st, n = re.match(r"STEP (\d+)\s+(.*)", head), re.match(r"THE \d+ ", head)
        if head.startswith("THE FACT"):
            continue   # the fact itself is the card this sits in
        if st:
            parts.append('<section class="win step" id="%s-step-%s"><h4 class="bar"><span class="n">%s</span>%s</h4>'
                         '<div class="win-body">%s</div></section>'
                         % (aid, st.group(1), st.group(1), doc.fmt(st.group(2)), doc.blocks(to_lines(body), 2)))
        elif n:   # "THE 44 COLLECTIONS": every row checked, or the build stops
            parts.append(rows_html(head, body, aid, doc))
        else:
            parts.append('<h4 class="walk-h">%s</h4>%s' % (html.escape(head), doc.blocks(to_lines(body), 2)))
    return '<div class="walk" id="%s-steps"><h4 class="walk-title">%s</h4>%s</div>' % (
        aid, html.escape(titled(title)[0].capitalize()), "".join(parts))


def w_items(L):
    """Where the W items start in the lines L, and each one: (number, what it said, its result, "in part" or "",
    what follows the result)."""
    starts = [i for i, ln in enumerate(L) if ln.txt and W_ITEM.match(ln.raw)]
    out = []
    for a, b in zip(starts, starts[1:] + [len(L)]):
        item = [ln for ln in L[a:b] if ln.txt]
        num, rest = item[0].txt.split(". ", 1)
        said = " ".join([rest] + [ln.txt for ln in item[1:]])
        m = VERDICT.search(said)
        said, after = (said[:m.start()].strip(), said[m.end():].strip()) if m else (said, "")
        word, qual = (m.group(1), m.group(2).strip()) if m else ("see text", "")
        out.append((num, said, word, qual, after))
    return (starts[0] if starts else len(L)), out


def predictions(body, doc):
    """The intro, then each W item as a window with its result in the title bar."""
    L = to_lines(body)
    first, items = w_items(L)
    out = [doc.blocks(L[:first], 2)]
    for num, said, word, qual, after in items:
        cls = "part" if qual == "in part" else VERDICT_CLASS.get(word, "open")
        out.append('<article class="claim pred v-%s" id="%s"><div class="mark"><span class="num">%s</span>%s'
                   '<strong class="verdict">%s</strong></div><div class="body"><h3>%s</h3>%s</div></article>'
                   % (cls, num, num, '<span class="qual">%s</span>' % qual if qual else "", word, doc.fmt(said),
                      "<p>%s</p>" % doc.fmt(after) if after else ""))
    return "".join(out)


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
    description = description or "The febu Assembly: a public ledger of promises and facts about febu that anyone can check."
    return vetted(name, SHELL.format(
        title=html.escape(title), h1=html.escape(h1), sub=html.escape(sub), tabs=tabs_html(name), mast=mast, body=body,
        foot=foot, connect=connect, source=source, edit="the text" if source else "the script",
        description=html.escape(description), meta=meta_tags(share or "febu assembly: " + title.lower(), description),
        bar=BAR % "rules and entries by one author, not yet adopted or checked by anyone else"))


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


def entries_section(secs):
    """The one section holding entries ('  FACT 1. (who, date)'), whatever its heading says."""
    found = [(h, b) for h, b in secs if any(ENTRY.match(r) for r in b)]
    if len(found) != 1:
        sys.exit("the ledger should have one section with entries in it (lines like '  FACT 1. (who, date)'); "
                 "found %d" % len(found))
    return found[0]


def status_banner(secs, doc, brief=False, task=""):
    """The STATUS section as a banner. Proposed rules say so first, in plain words. On the front page (brief) the
    banner is the immediate task and the group's goal, which assembly_page writes as `task`."""
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
            '<p>This page is laid out from a plain text file, and the file is the ledger. The hash in rule 6 is this '
            'file\'s SHA-256. Anyone may keep a copy: two copies with the same SHA-256 are the same, letter for letter.</p>'
            '<dl class="kv files">%s</dl>'
            '<div class="tool compare"><label for="copy-file">Compare a copy you hold</label>'
            '<input type="file" id="copy-file" accept=".txt,text/plain"><p class="hint">The file is read on your device. '
            'Nothing is sent.</p><p class="msg" id="copy-result" role="status"></p></div></section>' % "".join(rows))


def ledger_page(text, raw, steps_text):
    title, secs = sections(text)
    archives = archived(text)
    num6 = steps_fact(steps_text)
    files = {p: p for p, _, _ in archives}
    files[STEPS.name] = "#%s-steps" % anchor("FACT", num6)
    doc = Doc(secs, "", files)
    walk = steps_html(steps_text, doc)

    by = {short(h): (h, b) for h, b in secs}
    ent_head = entries_section(secs)[0]
    w_heads = [h for h, b in secs if any(W_ITEM.match(r) for r in b)]
    items = entries(dict(secs)[ent_head])
    st = entry_states(secs)
    found = {(it[1], it[2]) for it in items if it[0] == "entry"}
    if ("FACT", num6) not in found:
        sys.exit("%s is about fact %s, which the ledger does not have" % (STEPS.name, num6))

    def entries_html():
        out = []
        for it in items:
            if it[0] == "text":
                out.append(doc.blocks(to_lines(it[1]), 2))
            else:
                _, kind, num, who, fields = it
                out.append(entry_html(kind, num, who, fields, doc, st[num], (walk if (kind, num) == ("FACT", num6) else "")
                                      + site_note(SITE_NOTES, kind, num, fields)))
        return "".join(out)

    ids = {"THE RULES": "rule-", "KNOWN BUGS": "bug-"}
    body, strip, wins = [], [], []
    for head, b in secs:
        s = short(head)
        if s in ("STATUS", "WHAT THIS IS"):
            continue   # both are in the masthead
        if head == ent_head:
            inner = entries_html()
            strip += ['<a class="v-open" href="#%s" title="%s %s">%s%s</a>' % (anchor(k, n), k.capitalize(), n,
                      "" if k == "FACT" else k[0], n) for _, k, n, _, _ in (it for it in items if it[0] == "entry")]
        elif head in w_heads:
            inner = predictions(b, doc)
            strip += ['<a class="v-no" href="#%s" title="%s: failed">%s</a>' % (w, w, w)
                      for w in (W_ITEM.match(r).group(1) for r in b if W_ITEM.match(r))]
        else:
            inner = doc.blocks(to_lines(b), 2, ids.get(s, ""))
        body.append('<section id="%s"><h2>%s</h2>%s</section>' % (slug(head), html.escape(head), inner))
        wins.append((slug(head), s.lower()))
    body.append(files_html((raw, hashlib.sha256(raw).hexdigest()), archives))

    jump = '<nav class="jump" aria-label="On this page">%s<a href="#the-text">the text and its hash</a></nav>' % "".join(
        '<a href="#%s">%s</a>' % w for w in wins)
    intro = by.get("WHAT THIS IS")
    mast = (status_banner(secs, doc) + '<nav class="strip nums" aria-label="Every entry, in order">%s</nav>' % "".join(strip)
            + jump + ('<div class="intro" id="what-this-is">%s</div>' % doc.blocks(to_lines(intro[1]), 2) if intro else ""))
    h1, sub = titled(title)
    return page("ledger.html", "The ledger", h1.lower(), sub, "\n".join(body), mast=mast, connect="'self'",
                source=" from ledger.txt and %s" % STEPS.name,
                description="The Assembly's promises and facts about febu, each with a link anyone can open, and the "
                "rules for checking them." + (" Proposed, not yet adopted." if status(secs)[1] else ""),
                foot='Built from <a href="ledger.txt">ledger.txt</a>. ' + QUIET), archives


def check_section(secs, doc, steps_num):
    """HOW TO CHECK AN ENTRY, word for word from the ledger, as one window (#check on the front page)."""
    head, b = next(((h, b) for h, b in secs if "CHECK" in short(h) and any(NUM.match(r.strip()) for r in b)),
                   (None, None))
    if head is None:
        sys.exit("the ledger has no section on checking (a heading with CHECK in it, and numbered steps); "
                 "the front page shows it")
    L = to_lines(b)
    steps = [i for i, ln in enumerate(L) if ln.txt and ln.ind == 2 and NUM.match(ln.txt)]
    if not steps:
        sys.exit("HOW TO CHECK AN ENTRY has no numbered steps")
    after = deeper(L, steps[-1] + 1, 4)
    return ('<section class="win howto" id="check" aria-labelledby="howto-h"><h2 class="bar" id="howto-h">%s</h2>'
            '<div class="win-body">%s<div class="after">%s</div>'
            '<p class="go"><a href="ledger.html#fact-%s-steps">Fact %s has its own steps and every row, on the ledger page</a></p>'
            '</div></section>'
            % (html.escape(head.capitalize()), doc.blocks(L[steps[0]:after], 2), doc.blocks(L[after:], 2),
               steps_num, steps_num))


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
        sys.exit("WORDS USED HERE has no Member line; the assembly and people pages read the members from it")
    return [n.strip() for n in m.group(1).split(",")]


CHEAPEST = re.compile(r"entries ((?:\d+(?:, | and )?)+) are the cheapest", re.I)


def cheapest(secs, items):
    """The entries STATUS calls the cheapest to check, in its order; without that sentence, the first three facts
    nobody has checked."""
    m = CHEAPEST.search(re.sub(r"\s+", " ", " ".join(status(secs)[0])))
    found = {it[2]: it for it in items if it[0] == "entry"}
    return [found[n] for n in re.findall(r"\d+", m.group(1)) if n in found] if m else [
        it for it in items if it[0] == "entry" and it[1] == "FACT" and not checked(it[4])][:3]


# ---------------------------------------------------------------------------------------------------------------
# Member flows: the check card, your next move, the weekly page and the entry form. Each one writes text for a member
# to paste into the chat or into ledger.txt; none of them posts, stores or sends anything (claims.js does the typing).

RESULTS = {"FACT": ("HOLDS", "DOESN'T HOLD"), "PROMISE": ("KEPT", "BROKEN")}
# A SEEN item as the weekly page writes it: "- Laura, 2026-10-16: HOLDS on lines 1, 2. Saw: ... New: ... 9 minutes."
SEEN_ITEM = re.compile(r"- (.+?), (\d{4}-\d\d-\d\d): (HOLDS|DOESN'T HOLD|KEPT|BROKEN)(?: on lines? ([\d, and]+?))?\.")
CLAUSE = re.compile(r"[;,] or ")                            # "a, or b; or c": one WRONG IF line per clause
DATE = re.compile(r"\b\d{4}-\d\d-\d\d\b")
CHAT = "  ·  "                                         # between the parts of a post's first line


def wrong_if(fields):
    """The entry's WRONG IF lines, one per clause, in the order written. A check names them by number, from 1."""
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


def results(fields):
    """The SEEN items in the weekly page's form, in order: (name, date, result, WRONG IF line numbers). A SEEN line
    written another way is left to a person to read."""
    found = (SEEN_ITEM.match(it.replace("’", "'")) for it in seen_items(fields))
    return [(m.group(1), m.group(2), m.group(3), tuple(sorted({int(n) for n in re.findall(r"\d+", m.group(4) or "")})))
            for m in found if m]


def writer(who, fields, members):
    """Who wrote the entry, for rule 3: the name before its date, or for an entry in the group's name the member its
    text says proposed it."""
    name = who.split(",")[0].strip()
    if name in members:
        return name
    said = " ".join(ln.txt for _, lines in fields for ln in lines)
    return next((m for m in members if re.search(r"(?<!\w)%s proposed it" % re.escape(m), said)), name)


ADOPTED = re.compile(r"\bAdopted on (\d{4}-\d\d-\d\d)")
DAYS_AFTER = re.compile(r"(\d{1,4}) days after this version is adopted")
DISPUTE_DAYS = 30                                           # rule 4: a disputed entry not closed in 30 days
CLOSED = ("HOLDS", "DOESN'T HOLD", "KEPT", "BROKEN")


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


def adopted(secs):
    """The day STATUS says this version was adopted ("Adopted on 2026-10-22"), or None while it says Proposed."""
    body, proposed = status(secs)
    m = ADOPTED.search(" ".join(" ".join(body).split()))
    return None if proposed or not m else a_day(m.group(1))


def due(fields, adopted_on):
    """A promise's BY date: the date it names, or N days after adoption when it says so; None if neither."""
    by = text_of(fields, "BY")
    m = DATE.search(by)
    if m:
        return a_day(m.group())
    m = DAYS_AFTER.search(by)
    return days_after(adopted_on, int(m.group(1))) if m and a_day(adopted_on) else None


def first_day(kind, who, fields, adopted_on):
    """The first day an entry's results count: the day after adoption (posts count from the next day), and not before
    the entry's own date, or a promise's BY date. None while none count."""
    if not a_day(adopted_on):
        return None
    days = [days_after(adopted_on, 1)] + [d for d in DATE.findall(who)[:1] if a_day(d)]
    if kind == "PROMISE":
        days.append(due(fields, adopted_on))
    return None if None in days else max(days)


def standing(found, author, members, start):
    """Where an entry stands under rules 3 and 4, from its results in date order (the file's order within a day).
    Two members other than the writer posting the same result on the same WRONG IF lines close it, on the day of the
    second post. Two people, member or not, posting the same other word keep it open or reopen it: it carries both
    results, only later posts count, and 30 days on without a close it is CAN'T TELL (`until` is the last day it can
    close). An entry nobody disputes stays OPEN however long it waits (WORDS USED HERE). Results dated before `start`
    count for nothing, and none count while it is None. assets/claims.js has the same function; checks/states.json
    holds the cases both must pass.
    ponytail: everyone on the Member line counts as active; the 90-day silence is in the chat, not the file."""
    out = {"state": "OPEN", "lines": [], "since": None, "by": [], "both": [], "until": None}
    people, members = {}, set(members)
    for name, date, word, lines in sorted((r for r in found if start and a_day(r[1]) and r[1] >= start),
                                          key=lambda r: r[1]):
        if out["until"] and date > out["until"]:
            return dict(out, state="CAN'T TELL", since=days_after(out["until"], 1), until=None)
        if name == author:
            continue
        people.setdefault((word, tuple(lines)), set()).add(name)
        words = sorted({w for (w, _), names in people.items() if len(names) >= 2})
        if out["state"] != "OPEN":
            if set(words) - {out["state"]}:                        # reopened (rule 3)
                out, people = dict(out, state="OPEN", lines=[], by=[], both=words, since=date,
                                   until=days_after(date, DISPUTE_DAYS)), {}
            continue
        done = next(((w, ls, names & members) for (w, ls), names in people.items() if len(names & members) >= 2), None)
        if done and len(words) > 1:                                 # kept open (rule 3)
            out, people = dict(out, both=words, since=date, until=days_after(date, DISPUTE_DAYS)), {}
        elif done:
            out = {"state": done[0], "lines": list(done[1]), "since": date, "by": sorted(done[2]), "both": [],
                   "until": None}
    return out


def entry_state(kind, who, fields, members, adopted_on):
    """standing() for one entry of the file, with `start` added; a promise's WITHDRAWN line decides it: up to 7 days
    before its date it is WITHDRAWN, later it counts as BROKEN (HOW AN ENTRY IS WRITTEN)."""
    start = first_day(kind, who, fields, adopted_on)
    st = standing(results(fields), writer(who, fields, members), members, start)
    w = DATE.search(text_of(fields, "WITHDRAWN")) if kind == "PROMISE" and a_day(adopted_on) else None
    if w and a_day(w.group()):
        by = due(fields, adopted_on)
        late = by is not None and w.group() > days_after(by, -7)
        st = {"state": "BROKEN" if late else "WITHDRAWN", "lines": [], "since": w.group(), "by": [], "both": [],
              "until": None}
    return dict(st, start=start)


def entry_states(secs):
    """entry_state() for every entry, by number."""
    names, on = member_names(secs), adopted(secs)
    return {n: entry_state(k, w, f, names, on)
            for _, k, n, w, f in (it for it in entries(entries_section(secs)[1]) if it[0] == "entry")}


def state_text(st, kind, fields):
    """An entry's state in a few words, or None while it is OPEN with nothing to add to its SEEN lines. A close on some
    of a fact's WRONG IF lines says so: the text lets one stand on any lines (ASSEMBLY_SPEC section 5, gap 1)."""
    s, ls, of = st["state"], st["lines"], len(wrong_if(fields)) if kind == "FACT" else 0
    if s in CLOSED and ls and len(ls) < of:
        return "%s on line%s %s only, of %d" % (s, "s" if len(ls) > 1 else "", ", ".join(map(str, ls)), of)
    if s != "OPEN":
        return s
    if st["both"]:
        return "disputed, %s: CAN'T TELL after %s unless it closes" % (" and ".join(st["both"]), st["until"])
    return None


def checkable(kind, fields):
    """A fact can be checked any time; a promise once its BY line names a date (its results come on or after it)."""
    return kind == "FACT" or bool(DATE.search(text_of(fields, "BY")))


def short_addr(text):
    """Off the ledger page an address shows as its first eight letters, the way the ledger writes UqN2p5bA..."""
    return ADDRESS.sub(lambda m: m.group()[:8] + "...", text)


def name_options(members):
    return ('<option value="">choose</option>%s<option value="*">someone else</option>'
            % "".join('<option>%s</option>' % html.escape(m) for m in members))


def check_card(kind, num, author, fields, members):
    """The check card: tick the WRONG IF lines you tested, say what you saw on each, one new thing on the page, the
    minutes, your name and your result. claims.js writes the chat post from it; Copy waits for the new thing."""
    aid = anchor(kind, num)
    if kind == "FACT":
        tests = ('<fieldset class="cc-set"><legend>Which WRONG IF lines did you test? Say what you saw on each.</legend>'
                 '<ol class="lns">%s</ol></fieldset>' % "".join(
                     '<li><label class="ln"><input type="checkbox" class="ln-on" value="%d"><span class="n">%d</span>'
                     '<span class="t">%s</span></label><input type="text" class="saw" data-line="%d" autocomplete="off" '
                     'aria-label="What you saw on line %d" placeholder="What you saw: the number, the words or the date" '
                     'hidden></li>' % (i, i, html.escape(short_addr(t)), i, i) for i, t in enumerate(wrong_if(fields), 1)))
    else:
        tests = ('<label class="f">What you saw at the KNOWN BY link, on or after %s<input type="text" class="saw" '
                 'autocomplete="off" placeholder="The number, the words or the date"></label>'
                 % html.escape(text_of(fields, "BY")))
    yes, no = RESULTS[kind]
    who = ('<span class="by">%s wrote it, so %s cannot check it (rule 3).</span>' % ((html.escape(author),) * 2)
           if author in members else "")
    if site_note(CARD_NOTES, kind, num, fields):
        who += " " + CARD_NOTES[(kind, num)]
    return (
        '<div class="cc" id="check-%s" data-kind="%s" data-num="%s" data-writer="%s" hidden>'
        '<p class="cc-lead">Open the entry\'s link and look before you read anyone\'s post about it. Fill this in and '
        'the post writes itself below. %s</p>%s'
        '<label class="f">One thing on the page that is not in the entry or in any earlier post <b>needed</b>'
        '<input type="text" class="new" autocomplete="off" placeholder="A number, a name, a date, a word"></label>'
        '<div class="cc-pair"><label class="f">Minutes it took<input type="number" class="min" min="1" step="1" '
        'inputmode="numeric" placeholder="12"></label><label class="f">Your name<select class="who">%s</select>'
        '<input type="text" class="other" autocomplete="off" placeholder="Your name in the chat" '
        'aria-label="Your name in the chat" hidden></label></div>'
        '<fieldset class="res"><legend>Your result</legend>'
        '<label class="pill yes"><input type="radio" name="res-%s" value="%s"><span>%s</span></label>'
        '<label class="pill no"><input type="radio" name="res-%s" value="%s"><span>%s</span></label></fieldset>'
        '<label class="tick"><input type="checkbox" class="opened">I opened the link myself. No AI wrote this result.'
        '</label><div class="post-box"><p class="post-h">Your post, as the chat will show it</p>'
        '<pre class="post" aria-live="polite"></pre></div><p class="need" id="need-%s"></p>'
        '<p class="acts"><button type="button" class="btn primary cc-copy" disabled aria-describedby="need-%s">'
        'Copy the post</button></p><p class="hint">Paste it in the chat yourself: this page sends nothing. That '
        'week\'s member copies it into the ledger as a SEEN line (rule 6), from the first turn after the vote.</p></div>'
        % (aid, kind, num, html.escape(author), who, tests, name_options(members), aid, yes, yes, aid, no, no, aid, aid))


def pick_li(kind, num, fields, author, members, st):
    """One entry as a card on the front page: what it says, where it stands (st, from entry_state), a way in, and while
    it is OPEN, the check card that writes the result post."""
    says = text_of(fields, HEADLINE[kind])
    found = results(fields)
    done = st["state"] != "OPEN"
    state = state_text(st, kind, fields)
    if done:
        state = ("closed: " if st["state"] in CLOSED else "") + state
    elif not state:
        state = ("%d result%s posted" % (len(found), "" if len(found) == 1 else "s") if found
                 else "checks posted" if checked(fields) else "not yet checked")
    card = check_card(kind, num, author, fields, members) if checkable(kind, fields) and not done else ""
    toggle = ('<button type="button" class="btn primary cc-open" aria-expanded="false" aria-controls="check-%s">'
              'Check it here</button>' % anchor(kind, num) if card else "")
    return ('<li class="pick" id="pick-%s"><div class="top"><span class="num">%s %s</span><span class="chip%s">%s</span>'
            '</div><p class="says">%s</p><p class="acts"><a class="btn%s" href="ledger.html#%s">Open the entry</a>%s</p>'
            '%s</li>' % (anchor(kind, num), kind.lower(), num, " done" if done else "", html.escape(state),
                         html.escape(says), "" if card else " primary", anchor(kind, num), toggle, card))


def open_votes(title, secs):
    """What waits on a rule 7 vote, from ledger.txt: while STATUS says proposed, the version in the title, closing on
    the last date the ledger gives for "yes" or "object". Proposals that live only in the chat are not listed; the
    weekly page counts any VOTE post."""
    if not status(secs)[1]:
        return []
    flat = re.sub(r"\s+", " ", " ".join(r for _, b in secs for r in b))
    dates = re.findall(r'"yes" or "object" by (\d{4}-\d\d-\d\d)', flat)
    by = dates[-1] if dates else None
    votes = [(titled(title)[1] or "this version", by)]
    # STATUS may add: 'Also up for the vote by 2026-10-22: the Saw line; the stop rule.' (one line, subjects by ';')
    m = re.search(r"Also up for the vote by (\d{4}-\d\d-\d\d): ([^.]+)\.", re.sub(r"\s+", " ", " ".join(status(secs)[0])))
    if m:
        votes += [(sub.strip(), m.group(1)) for sub in m.group(2).split(";") if sub.strip()]
    return votes


def turn_start(secs):
    """The first date in STATUS: the weekly turns (rule 6) are counted in weeks from it, in Member order."""
    m = DATE.search(" ".join(status(secs)[0]))
    return m.group() if m else None


def calendar_ics(votes, members, start, secs):
    """The ledger's dates as a calendar file, all-day events only: each vote's closing day, the weekly turns for
    twelve weeks from the first date in STATUS in Member order (rule 6), and each known bug's fix-by day."""
    def day(d):
        return d.replace("-", "")

    ev = []
    for by in sorted({b for _, b in votes if b}):
        ev.append((by, days_after(by, 1), "Assembly vote closes: " + "; ".join(v for v, b in votes if b == by),
                   "vote-" + by))
    close = max((b for _, b in votes if b), default="")
    if start:
        for w in range(12):
            d = days_after(start, 7 * w)
            dry = ", a dry run: the vote is open" if days_after(d, 7) <= close else ""   # process.md section 10, the freeze
            ev.append((d, days_after(d, 7), "Assembly weekly turn: %s (rule 6)%s" % (members[w % len(members)], dry),
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


def next_number(items):
    m = re.search(r"next entry is number (\d+)", " ".join(" ".join(it[1]) for it in items if it[0] == "text"))
    return int(m.group(1)) if m else 1 + max([int(it[2]) for it in items if it[0] == "entry"] or [0])


def next_move(members, todo, votes, start, posted, remind):
    """Pick your name, see your week as four numbered steps: check (the entries open to you: not yours, no SEEN line
    of yours yet), vote (what is open, with its closing date), the weekly turn (yours when the order reaches you) and
    write. One panel per name, written here; claims.js shows the one picked, counts the days to each date and works
    out the turns from the device's date. The device remembers the name (claims.js), and #me=Name in the address
    picks it, so each member has a link. Under the steps: a post that reminds the group what is due, for anyone to
    send, and the dates as a calendar file (assembly.ics)."""
    def chip(text, cls="", **attrs):
        return '<span class="chip%s"%s>%s</span>' % (" " + cls if cls else "", "".join(
            ' data-%s="%s"' % (k, html.escape(v)) for k, v in attrs.items()), html.escape(text))

    def step(n, title, chip_html, body):
        return '<li class="st"><span class="n">%d</span><div><h3>%s %s</h3>%s</div></li>' % (n, title, chip_html, body)

    def panel(name):
        mine = [t for t in todo if name == "*" or (t[3] != name and not re.search(r"(?<!\w)%s(?!\w)" % re.escape(name), t[4]))]
        rows = "".join('<li><a href="#check-%s"><span class="num">%s %s</span><span class="says">%s</span></a></li>'
                       % (anchor(k, n), k.lower(), n, html.escape(s)) for k, n, s, _, _ in mine)
        if rows:
            check, c = '<ul class="todo">%s</ul>' % rows, chip("%d open to you" % len(mine), "due")
        elif name != "*" and todo and all(t[3] == name for t in todo):
            check, c = ("<p>None: you wrote every open entry, and nobody checks their own (rule 3). Write one for the "
                        "others.</p>", chip("none: all yours"))
        else:
            check, c = "<p>None open to you right now.</p>", chip("none open")
        if name == "*":
            check = ('<p class="hint">Your result counts toward keeping an entry open or reopening it, not toward '
                     'closing it (rule 3). Post it in the chat; any member adds the line.</p>') + check
            vote, v = "<p>Only members vote (rule 7).</p>", chip("members only")
            turn, t = "<p>Only members take the turn (rule 6).</p>", chip("members only")
        else:
            w, p = posted.get(name, (0, 0))
            if w or p:
                check = '<p class="hint">You have written %d entr%s and posted %d check%s so far.</p>' % (
                    w, "y" if w == 1 else "ies", p, "" if p == 1 else "s") + check
            if votes:
                vote = "".join(
                    '<p>Ledger %s: &ldquo;yes&rdquo; or &ldquo;object&rdquo; %s (rule 7).</p><p class="acts">'
                    '<button type="button" class="btn copy" data-copy="%s">Copy a yes</button>'
                    '<button type="button" class="btn copy" data-copy="%s">Copy an objection</button></p>'
                    % (html.escape(v), "by %s" % by if by else "within 7 days of the post that showed it",
                       html.escape(CHAT.join(("VOTE YES", v, name, "{today}"))),
                       html.escape(CHAT.join(("VOTE OBJECT", v, name, "{today}")) + "\nWhich line is wrong: \n"
                                   "What would change my mind: ")) for v, by in votes)
                v = chip("by " + votes[0][1], "due", due=votes[0][1]) if votes[0][1] else chip("7 days from the post", "due")
            else:
                vote, v = "<p>Nothing is up for a vote in the ledger.</p>", chip("none open")
            turn = ('<p class="turn-me" data-name="%s">Yours when the order reaches you%s.</p><p class="turn-you" hidden>'
                    '<b>That is you this week.</b><a class="btn primary" href="weekly.html">Do the weekly turn</a></p>'
                    '<p class="hint">Paste the week\'s chat. The page lists the SEEN lines to add, the entries that '
                    'would close and the votes, for you to copy into the ledger (rule 6).</p>'
                    % (html.escape(name), ", counted from %s" % start if start else ""))
            t = chip("in Member order", "turn-chip", name=name)
        write = ('<p><a href="write.html">Write an entry</a>: a fact, a link anyone can open, and one line for each '
                 'part of it that would prove it wrong. The page lays it out for the ledger and the chat.</p>')
        link = "" if name == "*" else (
            '<p class="mylink">Your link, for a bookmark or your DM thread: <a href="#me=%s">%s#me=%s</a> '
            '<button type="button" class="btn copy" data-copy="%s#me=%s">Copy your link</button></p>'
            % (quote(name), FRONT.split("//")[1], quote(name), FRONT, quote(name)))
        return ('<div class="moves" data-who="%s" hidden><ol class="steps">%s%s%s%s</ol>%s</div>'
                % (html.escape(name), step(1, "Check", c, check), step(2, "Vote", v, vote),
                   step(3, "Weekly turn", t, turn), step(4, "Write", chip("any time"), write), link))

    chips = "".join('<label class="name"><input type="radio" name="me" value="%s"><span>%s</span></label>'
                    % (html.escape(n), html.escape(n if n != "*" else "someone else")) for n in members + ["*"])
    turn = ('<div class="turn" data-from="%s" data-order="%s"><h3>Weekly turn (rule 6)</h3><p class="turn-now">One '
            'member a week, in this order%s: %s. A turn not done by the end of its week passes to the next.</p></div>'
            % (start or "", html.escape("|".join(members)), ", counted from %s" % start if start else "",
               html.escape(", ".join(members))))
    remind_html = ('<div class="remind"><h3>Remind the group</h3><p>What is due, as one post for the chat. Anyone '
                   'can send it; the dates come from the ledger.</p><pre class="lit keep" id="due-post" data-by="%s">%s'
                   '</pre><p class="acts"><button type="button" class="btn copy" data-copy="%s">Copy the reminder'
                   '</button><a class="btn" href="assembly.ics" download>Add the dates to your calendar</a></p></div>'
                   % (html.escape(votes[0][1] if votes and votes[0][1] else ""), html.escape(remind), html.escape(remind)))
    return ('<section class="win next" id="next" aria-labelledby="next-h"><h2 class="bar" id="next-h">your week'
            '<span class="q">pick your name, then the four steps</span></h2><div class="win-body"><fieldset class="names">'
            '<legend>Pick your name</legend>%s</fieldset><p class="hint moves-none">Pick a name to see what you can '
            'check, what is up for a vote, and when your weekly turn comes. The name is a claim, like a post in the '
            'chat: the site vouches for nobody. This device keeps it, with any unfinished post, so you come back to '
            'it. The first line of every post is what the weekly page reads: keep it as the buttons write it.</p>'
            '<p class="acts links-all"><button type="button" class="btn copy" data-copy="%s">Copy a link for each '
            'member</button></p>%s%s%s</div></section>'
            % (chips, html.escape("\n".join("%s: %s#me=%s" % (n, FRONT, quote(n)) for n in members)),
               "".join(panel(n) for n in members + ["*"]), turn, remind_html))


def one_sentence(how_secs):
    """how.txt's ONE SENTENCE as three short lines, one to a clause."""
    body = next((b for h, b in how_secs if short(h) == "ONE SENTENCE"), None)
    if body is None:
        sys.exit("how.txt has no ONE SENTENCE section; the front page opens with it")
    clauses = [c.strip().rstrip(".") for c in " ".join(r.strip() for r in body).split(";")]
    return "".join("<span>%s.</span>" % html.escape(c[0].upper() + c[1:]) for c in clauses if c)


def assembly_page(title, secs, steps_num, how_secs):
    """The Assembly's front page, for someone who has just followed a link: the task now and the group's goal in the
    banner, what this is in a sentence, three entries to check, each with its check card, and the other open ones
    folded under them; then your week by name (check, vote, the weekly turn, write, with what is due, a reminder
    post and the calendar file), every entry, how to check, who and the scripts. The four tests are reading, not
    the experiment: served, not linked from here."""
    doc = Doc(secs, "ledger.html")
    by = {short(h): b for h, b in secs}
    names = member_names(secs)
    members = len(names)
    items = entries(entries_section(secs)[1])
    ents = [it for it in items if it[0] == "entry"]
    author = {it[2]: writer(it[3], it[4], names) for it in ents}
    first = cheapest(secs, items)
    st = entry_states(secs)
    open_ = [it for it in ents if checkable(it[1], it[4]) and st[it[2]]["state"] == "OPEN"]
    rest = [it for it in open_ if it not in first]
    picks = '<ul class="picks">%s</ul>' % "".join(pick_li(k, n, f, author[n], names, st[n]) for _, k, n, _, f in first)
    if rest:
        picks += ('<details class="others"><summary>%d more open entr%s to check</summary><ul class="picks">%s</ul>'
                  '</details>' % (len(rest), "y" if len(rest) == 1 else "ies",
                                  "".join(pick_li(k, n, f, author[n], names, st[n]) for _, k, n, _, f in rest)))
    todo = [(k, n, text_of(f, HEADLINE[k]), author[n], seen(f)) for _, k, n, _, f in open_]
    rows, done = [], 0
    for _, kind, num, _, fields in (it for it in items if it[0] == "entry"):
        done += checked(fields)
        rows.append(entry_li(kind, num, fields, state_text(st[num], kind, fields)
                             or ("checks posted" if checked(fields) else "not yet checked")))
    after = "".join(doc.blocks(to_lines(it[1]), 2) for it in items if it[0] == "text")
    proposed = status(secs)[1]
    votes = open_votes(title, secs)
    shut = sum(1 for it in ents if st[it[2]]["state"] in CLOSED)
    goal = next((it for it in ents if it[1] == "PROMISE" and "entries under rule 3" in text_of(it[4], "WILL")), None)
    task = "<p><strong>Your task now:</strong> check one entry below and post what you saw."
    if votes:
        task += (' Then vote &ldquo;yes&rdquo; or &ldquo;object&rdquo;%s on %s (<a href="#next">pick your name</a>).'
                 % (" by %s" % votes[0][1] if votes[0][1] else "",
                    ", ".join(html.escape(v) for v, _ in votes[:-1]) + (" and " if len(votes) > 1 else "")
                    + html.escape(votes[-1][0])))
    task += "</p>"
    posted = {n: (sum(1 for it in ents if author[it[2]] == n),
                  sum(1 for it in ents if re.search(r"(?<!\w)%s(?!\w)" % re.escape(n), seen(it[4])))) for n in names}
    start = turn_start(secs)
    by = votes[0][1] if votes and votes[0][1] else ""
    due = []
    if by:
        due.append('vote closes <time data-due="%s">%s</time>' % (by, by))
    if start:
        due.append('weekly turn: <span class="due-turn">in Member order from %s%s</span>'
                   % (start, ", a dry run until the vote closes" if proposed else ""))
    due.append('<a href="assembly.ics" download>the dates as a calendar</a>')
    task += '<p class="due"><b>Due</b> %s</p>' % " &middot; ".join(due)
    remind = ["DUE" + CHAT + "{today}"]
    if votes:
        remind.append("Vote %s: %s. Post: VOTE YES%s<what>%s<your name>%s<date>."
                      % ("by %s ({days})" % by if by else "within 7 days of the post", "; ".join(v for v, _ in votes),
                         CHAT, CHAT, CHAT))
    if open_:
        remind.append("Open to check: %s%s. Post: CHECK FACT n%sHOLDS%slines 1,3%s<your name>%s<date>."
                      % (", ".join("%s %s" % (k.lower(), n) for _, k, n, _, _ in open_[:3]),
                         " and %d more" % (len(open_) - 3) if len(open_) > 3 else "", CHAT, CHAT, CHAT, CHAT))
    if start:
        remind.append("Weekly turn this week, to {turnend}: {turn}. Next: {next}.")
    if goal:
        remind.append("Goal (PROMISE %s): %d of %d entries closed." % (goal[2], shut, len(ents)))
    remind = "\n".join(remind + [FRONT])
    if goal:
        task += ('<p><strong>The group&rsquo;s goal</strong> (<a href="ledger.html#%s">PROMISE %s</a>): %s %s '
                 'Closed so far: %d of %d.</p>' % (anchor("PROMISE", goal[2]), goal[2],
                                                 html.escape(text_of(goal[4], "WILL")),
                                                 "By " + html.escape(text_of(goal[4], "BY").rstrip(".")) + ".",
                                                 shut, len(ents)))

    def small(key, title, text, href, go):
        return ('<section class="win" aria-labelledby="%s-h"><h2 class="bar" id="%s-h">%s</h2><div class="win-body">'
                '<p>%s</p><p class="go"><a href="%s">%s</a></p></div></section>' % (key, key, title, text, href, go))

    first_win = ('<section class="win start" id="start" aria-labelledby="start-h"><h2 class="bar" id="start-h">'
             'start here: check one claim<span class="q">%d of %d checked by someone else</span>'
             '</h2><div class="win-body"><p class="sentence">%s</p>%s%s'
             '<p class="go"><a href="how.html">How it works, in one picture</a> <a href="#every">Every entry</a></p>'
             '</div></section>' % (done, len(rows), one_sentence(how_secs), picks,
                                   '<p class="hint">The vote week is also a dry run. Post what you saw, and how many '
                                   'minutes it took.</p>' if proposed else ""))
    every = ('<details class="win lead" id="every" data-open-wide><summary><span class="t">every entry</span>'
             '<span class="q">%d entries &middot; checked by someone other than the writer: %d</span></summary>'
             '<div class="win-body"><ul class="entries">%s</ul>%s<p class="go"><a href="ledger.html">Read the whole '
             'ledger</a></p></div></details>' % (len(rows), done, "".join(rows), after))
    body = (first_win + next_move(names, todo, votes, start, posted, remind) + every +
            check_section(secs, doc, steps_num) +
            '<div class="more">%s</div>' % "".join([
                small("who", "who: members (%d)" % members, "Any two of them, other than an entry's writer, can close it "
                      "(rule 3). Anyone at all can reopen one.", "people.html", "See what each one wrote and checked"),
                small("scripts", "run a script", "Eight entries have a script that reads their record for you, with "
                      "Python 3 and no account or key. Say in your post that you ran one, and still open one link by "
                      "hand: until the Saw line is adopted, a script run alone is not a Saw. <code>python "
                      "checks/resolve.py test9</code> takes seconds; <code>fact8</code> about a minute; "
                      '<code>checks/fact6.py</code> a minute or two. <a href="%s">What makes a script count</a>.'
                      % "process.html#5-add-on-a-scripts",
                      "https://github.com/zinotino/febu-assembly/tree/main/checks", "The scripts, with a line each")]))
    return page("febu-assembly.html", "febu assembly", "febu assembly",
                "%d members studying febu, and a ledger anyone can check" % members, body,
                mast=status_banner(secs, doc, brief=True, task=task), source=" from ledger.txt", connect="'self'",
                share="febu assembly: claims about febu that anyone can check",
                description="%d claims about febu, each with a link and a line that would prove it wrong. %s Pick one "
                "and check it.%s" % (len(rows), "%d checked so far." % done if done else "None checked yet.",
                                     " Proposed, not yet adopted." if proposed else ""),
                foot='This site and the ledger file are run by Z for now (<a href="ledger.html#bug-1">known bug 1</a>). '
                'This page keeps your name and unfinished posts on your device only, and loads nothing from other '
                'sites. Nothing is counted.')


def people_page(secs):
    """Each name the ledger gives as an entry's writer or in a SEEN line, in the Member line's order (anyone not on it
    after, as they first appear): the entries they wrote, the entries whose SEEN lines name them, and the failed
    predictions a heading gives them ("Z'S PREDICTIONS ..."). Nothing is totalled: the ledger keeps no totals."""
    doc = Doc(secs, "ledger.html")
    members = member_names(secs)
    st = entry_states(secs)
    wrote, saw, preds = {}, {}, {}
    for _, kind, num, who, fields in (it for it in entries(entries_section(secs)[1]) if it[0] == "entry"):
        li = entry_li(kind, num, fields, state_text(st[num], kind, fields)
                      or ("checks posted, see SEEN" if checked(fields) else "open, not yet checked"))
        if who:
            wrote.setdefault(who.split(",")[0].strip(), []).append(li)
        # ponytail: a check is credited to a name on the Member line; a non-member's needs a fixed SEEN line format
        for name in members:
            if re.search(r"(?<!\w)%s(?!\w)" % re.escape(name), seen(fields)):
                saw.setdefault(name, []).append(li)
    for head, b in secs:
        if not any(W_ITEM.match(r) for r in b):
            continue
        m = re.match(r"(\w+)'S ", head)
        owner = [n for n in members if m and n.upper().startswith(m.group(1))]
        if len(owner) != 1:
            sys.exit("%r: whose predictions? Its heading should start with a member's name, or its first letters, "
                     "and 'S" % head)
        L = to_lines(b)
        first, items = w_items(L)
        rows = "".join('<li><a href="ledger.html#%s"><span class="num">%s</span><span class="says">%s</span>'
                       '<span class="state">%s</span></a></li>' % (num, num, html.escape(said), (word + " " + qual).strip().lower())
                       for num, said, word, qual, _ in items)
        preds.setdefault(owner[0], []).append('<h3>%s</h3>%s<ul class="entries">%s</ul>' % (
            html.escape(short(head).capitalize()), doc.blocks(L[:first], 2), rows))

    def part(title, rows):
        return "<h3>%s</h3>%s" % (title, '<ul class="entries">%s</ul>' % "".join(rows) if rows else "<p>None yet.</p>")

    def window(name):
        pid = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        return ('<section class="win person" id="%s" aria-labelledby="%s-h"><h2 class="bar" id="%s-h">%s%s</h2>'
                '<div class="win-body">%s%s%s</div></section>'
                % (pid, pid, pid, html.escape(name), "" if name in members else '<span class="q">not on the Member line</span>',
                   part("Entries written", wrote.get(name)), part("Checks posted", saw.get(name)), "".join(preds.get(name, []))))

    named = set(wrote) | set(saw) | set(preds)
    rest = [n for n in members if n not in named]
    body = ('<div class="intro"><p>%s</p></div>' % doc.fmt(
                "Everyone the ledger names as an entry's writer or in a SEEN line, in the order of the Member line in "
                "WORDS USED HERE. Under each name, what they wrote and what they checked, each with where it stands "
                "today and a link to it in the ledger. An entry is open until two members other than its writer post "
                "the same result (rule 3). No totals, no rankings, no scores.")
            + "".join(window(n) for n in [n for n in members if n in named] + [n for n in wrote if n not in members])
            + ('<p class="hint">Nothing stands under these names yet: %s.</p>' % html.escape(", ".join(rest)) if rest else ""))
    return page("people.html", "By person", "by person", "what stands under each name in the ledger, entry by entry",
                body, mast=status_banner(secs, doc, brief=True), source=" from ledger.txt",
                description="Each name in the febu Assembly's ledger, with the entries they wrote and the checks they "
                "posted, entry by entry." + (" Proposed, not yet adopted." if status(secs)[1] else ""))


GITHUB_EDIT = "https://github.com/zinotino/febu-assembly/edit/main/ledger.txt"


def clip(s):
    """An address cut to its first 7 characters: they belong on the ledger page and in ledger.txt only."""
    return ADDRESS.sub(lambda m: m.group()[:7] + "…", s)


def ledger_dict(title, secs, more=False):
    """What the weekly page needs from ledger.txt: the members in order, each entry's writer, WRONG IF line count and
    SEEN items, the open votes and the next entry number. No addresses. more=True adds each entry's headline, WRONG IF
    clauses and page address (ledger.json)."""
    names, st = member_names(secs), entry_states(secs)
    items = entries(entries_section(secs)[1])
    ents = []
    for _, k, n, w, f in (it for it in items if it[0] == "entry"):
        e = {"kind": k, "num": int(n), "writer": writer(w, f, names), "lines": len(wrong_if(f)), "empty": not checked(f),
             "results": [[a, d, r, list(ls)] for a, d, r, ls in results(f)], "state": st[n]}
        if more:
            e.update(says=clip(text_of(f, HEADLINE[k])), wrong_if=[clip(c) for c in wrong_if(f)],
                     url="%s/ledger.html#%s" % (SITE, anchor(k, n)))
        ents.append(e)
    return {"members": names, "adopted": adopted(secs), "entries": ents, "next": next_number(items),
            "votes": [{"subject": v, "by": by} for v, by in open_votes(title, secs)]}


def ledger_data(title, secs):
    """ledger_dict as JSON in the weekly page."""
    return ('<script type="application/json" id="ledger-data">%s</script>'
            % json.dumps(ledger_dict(title, secs)).replace("</", "<\\/"))


def ledger_json(title, secs, raw):
    """ledger.json: the same state for an agent that reads data and not pages, with the hash of the text it came from.
    Links and addresses stay in ledger.txt, which wins wherever the two differ. Nothing can be posted back."""
    out = {"about": "A read-only index of ledger.txt, written by build.py. ledger.txt is the record and wins where they "
                    "differ. Links are not here, and an address is cut to its first 7 characters: read ledger.txt for them.",
           "ledger": {"url": SITE + "/ledger.txt", "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)},
           "proposed": status(secs)[1], **ledger_dict(title, secs, more=True)}
    text = json.dumps(out, indent=1, ensure_ascii=False) + "\n"
    vetted("ledger.json", text.replace(out["ledger"]["sha256"], ""))   # a hash with no 0 in it (1 in 60) reads as an address
    return text


def step(n, key, head, inner, hidden=False):
    return ('<section class="win step" id="%s" aria-labelledby="%s-h"%s><h2 class="bar" id="%s-h"><span class="n">%d</span>'
            '%s</h2><div class="win-body">%s</div></section>' % (key, key, " hidden" if hidden else "", key, n, head, inner))


def weekly_page(title, secs):
    """The weekly turn (rule 6) as one page: paste the week's chat, and claims.js reads every CHECK and VOTE post in it
    and lists the SEEN lines to add in the ledger's layout, the entries rule 3 would close, the votes against rule 7,
    and every line it could not read. It never edits the file: the member pastes into ledger.txt on GitHub."""
    doc = Doc(secs, "ledger.html")
    out = lambda key: '<div id="%s"></div>' % key
    body = ('<div class="intro"><p>%s</p></div>' % doc.fmt(
                "Each week one member, in Member order, checks both ways: every result posted in the chat that week is "
                "in the file, and every SEEN line in the file has its post in the chat (rule 6). Paste the week's chat "
                "below. This page reads the posts whose first line starts CHECK or VOTE, and shows you everything else "
                "to read yourself. It changes nothing: you copy what it writes into ledger.txt.")
            + step(1, "w-paste", "paste the week's chat",
                   '<label class="f" for="chat">Everything posted in the chat this week, copied out of it</label>'
                   '<textarea id="chat" rows="10" spellcheck="false" autocomplete="off" placeholder="CHECK FACT 8'
                   + html.escape(CHAT) + 'HOLDS' + html.escape(CHAT) + 'lines 1,2,3' + html.escape(CHAT) + 'Laura'
                   + html.escape(CHAT) + '2026-10-16&#10;Line 1: ...&#10;Saw: ..."></textarea>'
                   '<p class="hint">Read on your device. Nothing is sent or kept: reload the page and it is gone.</p>'
                   '<p class="msg" id="w-sum" role="status"></p>')
            + step(2, "w-seen", "SEEN lines to add", out("w-seen-out"), hidden=True)
            + step(3, "w-back", "SEEN lines with no post in what you pasted", out("w-back-out"), hidden=True)
            + step(4, "w-close", "entries that would close (rule 3)", out("w-close-out"), hidden=True)
            + step(5, "w-votes", "votes (rule 7)", out("w-votes-out"), hidden=True)
            + step(6, "w-unread", "lines it could not read", out("w-unread-out"), hidden=True)
            + step(7, "w-file", "put it in the file, then post the hash",
                   '<ol class="plain">' + ('<li>Not during a vote: until the vote closes the file does not change, so '
                                           'this week stops at step 6 and you post what it would add.</li>'
                                           if status(secs)[1] else '') + '<li><a href="%s" rel="noopener '
                   'noreferrer">Open ledger.txt on GitHub</a> and press '
                   'the pencil (README, &ldquo;Editing in the browser&rdquo;).</li><li>Paste each block where step 2 '
                   'says, lined up like the lines around it. Add nothing else.</li><li>Commit to main (only Z can '
                   'today, KNOWN BUGS 1; anyone else gets &ldquo;Propose changes&rdquo;, which Z merges). The site '
                   'rebuilds in a minute or two; if the build stops, GitHub shows a red cross and the site keeps the '
                   'version before.</li><li>Open <a href="ledger.html#the-text">the ledger page</a> and copy the new '
                   'SHA-256. Post it somewhere the group does not control, then in the chat.</li></ol>' % GITHUB_EDIT)
            + ledger_data(title, secs))
    return page("weekly.html", "The weekly turn", "the weekly turn", "paste the week's chat, copy what goes in the file",
                body, mast=status_banner(secs, doc, brief=True), source=" from ledger.txt",
                description="The febu Assembly's weekly turn: paste the week's chat and get the SEEN lines, the entries "
                "that would close and the vote counts, ready to copy into the ledger.")


def write_page(secs):
    """The entry form: SAYS, LINK and one WRONG IF line per part of SAYS. claims.js lays it out as the ledger writes
    entries and as a chat post. Facts only for now; a promise is written by hand from HOW AN ENTRY IS WRITTEN."""
    doc = Doc(secs, "ledger.html")
    names = member_names(secs)
    n = next_number(entries(entries_section(secs)[1]))
    how = next((b for h, b in secs if short(h) == "HOW AN ENTRY IS WRITTEN"), None)
    if how is None:
        sys.exit("the ledger has no HOW AN ENTRY IS WRITTEN section; the entry form shows it")
    wi = ('<li class="wi"><span class="n">1</span><input type="text" class="wi-t" autocomplete="off" aria-label="WRONG IF '
          'line 1" placeholder="the balance on 2026-10-14 was below 11.12 SOL"><button type="button" class="btn wi-x" '
          'aria-label="Remove WRONG IF line 1">Remove</button><p class="warn" hidden>No date in this line. If someone '
          'outside the group could make it true later, with a transfer or a new post, end it: &ldquo;by the end of '
          '2026-10-14&rdquo;.</p></li>')
    form = ('<div class="wf" data-next="%d"><div class="cc-pair"><label class="f">Your name<select class="who">%s</select>'
            '<input type="text" class="other" autocomplete="off" placeholder="Your name in the chat" '
            'aria-label="Your name in the chat" hidden></label><p class="f num-note">This will be <b>fact %d</b>, the '
            'number the ledger gives next. If someone posts an entry before yours, take the one after.</p></div>'
            '<label class="f">SAYS<span class="q">one sentence</span><textarea class="says" rows="3" '
            'placeholder="Between 2026-09-29 and 2026-10-09 the wallet that created $FEBU bought no $FEBU."></textarea>'
            '</label><label class="f">LINK<span class="q">full links anyone can open without asking you (rule 1), one '
            'to a line; a line of words says what to look for</span><textarea class="link" rows="3" spellcheck="false" '
            'placeholder="https://..."></textarea></label><fieldset class="cc-set wis-set"><legend>WRONG IF<span '
            'class="q">one line for each part of SAYS</span></legend><p class="prompt">Could a stranger make this '
            'true? End-date it.</p><ol class="wis">%s</ol><p class="acts"><button type="button" class="btn wi-add">'
            'Add a WRONG IF line</button></p></fieldset><p class="need" id="need-w"></p></div>'
            % (n, name_options(names), n, wi))
    copy = lambda cls, label: ('<p class="acts"><button type="button" class="btn primary %s" disabled '
                               'aria-describedby="need-w">%s</button></p>' % (cls, label))
    body = ('<div class="intro"><p>%s</p></div>' % doc.fmt(
                "Write a fact the way the ledger writes them, and post it in the chat. Nobody approves it. Two members "
                "other than you check it by opening the link (rule 3). Every part of SAYS needs a WRONG IF line that "
                "would catch it; if SAYS claims more, cut SAYS.")
            + step(1, "w-form", "write it", form)
            + step(2, "w-chat", "post it in the chat",
                   '<pre class="post keep chat-out" aria-live="polite"></pre>%s<p class="hint">Paste it yourself: this page '
                   'sends nothing. Until the first SEEN line you may change WRONG IF with a dated CHANGED line; after '
                   'that, never.</p>' % copy("w-copy-chat", "Copy the chat post"))
            + step(3, "w-file", "put it in ledger.txt",
                   '<pre class="post keep entry-out"></pre>%s<p class="hint">%s week\'s member: on '
                   '<a href="%s" rel="noopener noreferrer">ledger.txt on GitHub</a>, press the pencil, paste it under '
                   'THE ENTRIES above &ldquo;The next entry is number %d.&rdquo;, and raise that number by one (README, '
                   'Add an entry). Only Z can commit there today (KNOWN BUGS 1); anyone else gets &ldquo;Propose '
                   'changes&rdquo;, which Z merges.</p>' % (copy("w-copy-entry", "Copy the entry"), (
                       "Not during a vote: until the vote closes the file does not change, and your chat post waits in "
                       "the chat. After it, the" if status(secs)[1] else "The"), GITHUB_EDIT, n))
            + '<details class="win" id="how-written"><summary><span class="t">how an entry is written</span><span '
              'class="q">in the ledger\'s own words</span></summary><div class="win-body">%s</div></details>'
            % doc.blocks(to_lines(how), 2))
    return page("write.html", "Write an entry", "write an entry", "a fact, a link, and what would prove it wrong",
                body, mast=status_banner(secs, doc, brief=True), source=" from ledger.txt",
                description="Write a fact for the febu Assembly's ledger: what it says, a link anyone can open, and what "
                "would prove it wrong. Laid out for the ledger and the chat.")


def main():
    raw = raw_text(LEDGER)
    text = raw.decode("utf-8").rstrip("\n")
    title, secs = sections(text)
    steps = raw_text(STEPS).decode("utf-8").rstrip("\n")
    ledger, archives = ledger_page(text, raw, steps)
    pages = {
        "ledger.html": ledger,
        "tests.html": tests_page(raw_text(TESTS).decode("utf-8").rstrip("\n"), secs),
        "how.html": how_page(raw_text(HOW).decode("utf-8").rstrip("\n"), secs),
        "febu-assembly.html": assembly_page(title, secs, steps_fact(steps),
                                            sections(raw_text(HOW).decode("utf-8").rstrip("\n"))[1]),
        "people.html": people_page(secs),
        "weekly.html": weekly_page(title, secs),
        "write.html": write_page(secs),
        "process.html": process_page(),
    }
    index = ledger_json(title, secs, raw)   # before any file is written: a refusal must not leave the repo half built
    if LEDGER.read_bytes() != raw:   # the page prints the hash of the LF text, so serve exactly that
        LEDGER.write_bytes(raw)
    for name, out in pages.items():
        (ROOT / name).write_text(out, encoding="utf-8", newline="\n")
    (ROOT / "ledger.json").write_text(index, encoding="utf-8", newline="\n")
    (ROOT / "assembly.ics").write_bytes(calendar_ics(open_votes(title, secs), member_names(secs), turn_start(secs),
                                                     secs).encode("utf-8"))
    print("ledger.txt sha256 %s (%d bytes); %s; wrote %s" % (
        hashlib.sha256(raw).hexdigest(), len(raw), ", ".join("%s sha256 %s" % (p, d[:16]) for p, _, d in archives),
        ", ".join([*pages, "ledger.json"])))


if __name__ == "__main__":
    main()
