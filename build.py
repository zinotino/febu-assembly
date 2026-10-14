"""Build the Assembly's pages, next to this file, from the texts beside them. All four share one set of tabs.

  febu-assembly.html  the front page: status, every entry and whether anyone has checked it, and the ledger's
                      HOW TO CHECK AN ENTRY (#check; /start.html redirects there)
  ledger.html   ledger.txt as a page, in the text's own order: STATUS as a banner, each entry as a card
                (#fact-6, with #6 kept for links made before version 2), and under the fact that
                fact-6-steps.txt is about, its steps and every row with a link
  tests.html    tests.txt as a page
  findings.html findings.md (findings_html.py) in the den's look, inside the tabs

ledger.txt and archive/ are served as they are; ledger.html prints their SHA-256 (rule 6 relies on that hash).
The pages follow the texts' headings, not their line numbers: reword the texts and re-run.
    python build.py
They load nothing from other sites. Styling is assets/findings.css plus assets/ledger.css; the browser side is
assets/claims.js (tap to copy, and the hash checks).
"""
import hashlib
import html
import re
import sys
from collections import namedtuple
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LEDGER = ROOT / "ledger.txt"
TESTS = ROOT / "tests.txt"
STEPS = ROOT / "fact-6-steps.txt"
FINDINGS = ROOT / "findings.md"

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
FIELD = re.compile(r"([A-Z]+(?: [A-Z]+)?)(?: {2,}| (?=[a-z])|$)")   # "SAYS      one", "IF BROKEN what"
HEADLINE = {"FACT": "SAYS", "PROMISE": "WILL"}
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


def checked(fields):
    """Whether anyone has posted what they saw on this entry (its SEEN line says someone other than "nobody")."""
    seen = " ".join(ln.txt for ln in dict(fields).get("SEEN", []) if ln.txt)
    return bool(seen) and not seen.lower().startswith("nobody")


def entry_html(kind, num, who, fields, doc, extra=""):
    f = dict(fields)
    head = HEADLINE[kind]
    if head not in f:
        sys.exit("%s %s has no %s line" % (kind, num, head))
    verdict = "checks posted, see SEEN" if checked(fields) else "not yet checked"
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


def predictions(body, doc):
    """The intro, then each W item as a window with its result in the title bar."""
    L = to_lines(body)
    starts = [i for i, ln in enumerate(L) if ln.txt and W_ITEM.match(ln.raw)]
    out = [doc.blocks(L[:starts[0] if starts else len(L)], 2)]
    for a, b in zip(starts, starts[1:] + [len(L)]):
        item = [ln for ln in L[a:b] if ln.txt]
        num, rest = item[0].txt.split(". ", 1)
        said = " ".join([rest] + [ln.txt for ln in item[1:]])
        m = VERDICT.search(said)
        said, after = (said[:m.start()].strip(), said[m.end():].strip()) if m else (said, "")
        word, qual = (m.group(1), m.group(2).strip()) if m else ("see text", "")
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

TABS = (("febu-assembly.html", "assembly"), ("ledger.html", "the ledger"), ("tests.html", "four tests"),
        ("findings.html", "findings"))
QUIET = "Nothing on this page is stored or counted, and it loads nothing from other sites."
BAR = ('<div class="archive-bar">unverified: %s &middot; [ <a href="/">home</a> ] [ <a href="/library/scripture">scripture'
       '</a> ] [ <a href="/febu-assembly.html">febu assembly</a> ]</div>')


def tabs_html(name):
    return '<nav class="tabs" aria-label="Assembly pages">%s</nav>' % "".join(
        '<a href="%s"%s>%s</a>' % (href, ' aria-current="page"' if href == name else "", label) for href, label in TABS)


def vetted(name, out):
    """The page, unless it carries notation or (off the ledger page) an address it may not."""
    hit = BANNED.search(re.sub(r"<[^>]+>", " ", out)) or (name != "ledger.html" and ADDRESS.search(out))
    if hit:
        sys.exit("%s: %r may not be on this page" % (name, hit.group()))
    return out


def page(name, title, h1, sub, body, mast="", foot=QUIET, connect="'none'", source="", description=""):
    return vetted(name, SHELL.format(
        title=html.escape(title), h1=html.escape(h1), sub=html.escape(sub), tabs=tabs_html(name), mast=mast, body=body,
        foot=foot, connect=connect, source=source, edit="the text" if source else "the script",
        description=html.escape(description),
        bar=BAR % "rules and entries by one author, not yet adopted or checked by anyone else"))


def findings_page():
    """findings.md as findings_html.py lays it out, with the den's stylesheet in place of its own, the archive bar,
    and the tabs. Returns the page and its verdict counts.

    findings_html.py needs the markdown package, which Vercel's build image lacks. Without it the page built from
    this same findings.md is kept as it is (counts None), so the ledger's pages still build with Python alone; if
    findings.md has changed since, the build stops rather than serve the old findings.
    ponytail: the mark covers findings.md only. After changing TABS, BAR or findings_html.py, rebuild with markdown
    and commit findings.html, or Vercel keeps serving the old one beside new pages."""
    mark = "from findings.md (sha256 %s)" % hashlib.sha256(raw_text(FINDINGS)).hexdigest()[:16]   # 32+ would be an "address"
    try:
        import findings_html
    except ModuleNotFoundError as err:
        built = ROOT / "findings.html"
        if err.name != "markdown":
            raise
        if built.exists() and mark in built.read_text(encoding="utf-8"):
            return built.read_text(encoding="utf-8"), None
        sys.exit("findings.md has changed since findings.html was built, and building it needs the markdown package "
                 "(pip install markdown)")
    out, counts = findings_html.build(FINDINGS.read_text(encoding="utf-8"))
    for pattern, repl in (
            (r"from findings\.md\.", mark + "."),
            (r"<style>.*?</style>", '<link rel="icon" href="/favicon.ico">\n<link rel="stylesheet" href="/assets/findings.css">'),
            (r"<body>\n", "<body>\n" + BAR % "one author's verdicts, not yet checked by anyone else" + "\n"),
            (r'(<h1>.*?</h1>\n<p class="sub">.*?</p>)', r'<div class="mast-title">\1</div>' + "\n" + tabs_html("findings.html"))):
        out, n = re.subn(pattern, repl, out, count=1, flags=re.S)
        if n != 1:
            sys.exit("findings_html.py's page no longer has %r; findings.html is made from it" % pattern)
    return vetted("findings.html", out), counts


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


def status_banner(secs, doc, brief=False):
    """The STATUS section as a banner. Proposed rules say so first, in plain words."""
    body, proposed = status(secs)
    head = "Proposed, not yet adopted" if proposed else "Status"
    inner = ('<p>These rules are a draft until the group adopts them. <a href="ledger.html#status">Read the status</a>.</p>'
             if brief else doc.blocks(to_lines(body), 2))
    return '<div class="banner%s" id="status" role="note"><strong>%s</strong>%s</div>' % (
        (" proposed" if proposed else "") + (" brief" if brief else ""), head, inner)


def archived(text):
    """Each archive/... text the ledger names: (path, bytes, SHA-256), checked against any SHA-256 printed beside it."""
    out = []
    named = set(re.findall(r"\barchive/[\w.-]+\.txt\b", text))
    for path in sorted(named, key=lambda p: [int(n) for n in re.findall(r"\d+", p)]):   # v1, v2, v2.1
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
                out.append(entry_html(kind, num, who, fields, doc, walk if (kind, num) == ("FACT", num6) else ""))
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
            + jump + ('<div class="intro">%s</div>' % doc.blocks(to_lines(intro[1]), 2) if intro else ""))
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


def assembly_page(secs, steps_num):
    """The Assembly's front page: every entry with whether anyone has checked it, how to check one, then the rest."""
    doc = Doc(secs, "ledger.html")
    by = {short(h): b for h, b in secs}
    m = re.search(r"\bMember\s{2,}(.+?)\.\s", " ".join(by.get("WORDS USED HERE", [])))
    if not m:
        sys.exit("WORDS USED HERE has no Member line; the assembly page counts the members from it")
    members = len(m.group(1).split(","))
    items = entries(entries_section(secs)[1])
    rows, done = [], 0
    for _, kind, num, _, fields in (it for it in items if it[0] == "entry"):
        says = " ".join(ln.txt for ln in dict(fields)[HEADLINE[kind]] if ln.txt)
        done += checked(fields)
        rows.append('<li><a href="ledger.html#%s"><span class="num">%s %s</span><span class="says">%s</span>'
                    '<span class="state">%s</span></a></li>' % (anchor(kind, num), kind.lower(), num, html.escape(says),
                    "checks posted" if checked(fields) else "not yet checked"))
    after = "".join(doc.blocks(to_lines(it[1]), 2) for it in items if it[0] == "text")
    intro = '<div class="intro">%s</div>' % doc.blocks(to_lines(by["WHAT THIS IS"]), 2) if "WHAT THIS IS" in by else ""

    def small(key, title, text, href, go):
        return ('<section class="win" aria-labelledby="%s-h"><h2 class="bar" id="%s-h">%s</h2><div class="win-body">'
                '<p>%s</p><p class="go"><a href="%s">%s</a></p></div></section>' % (key, key, title, text, href, go))

    body = (intro +
            '<section class="win lead" aria-labelledby="lead-h"><h2 class="bar" id="lead-h">the ledger: promises and facts'
            '<span class="q">%d entries &middot; checked by someone other than the writer: %d</span></h2>'
            '<div class="win-body"><ul class="entries">%s</ul>%s'
            '<p class="cta"><a href="#check">Check an entry</a><a href="ledger.html">Read the whole ledger</a></p>'
            '</div></section>' % (len(rows), done, "".join(rows), after) + check_section(secs, doc, steps_num) +
            '<div class="more">%s</div>' % "".join([
                small("why", "why: four tests", "Witness asked what an answer to febu would look like if we approached "
                      "it the way Satoshi approached money. Four tests, run on febu and on this ledger.",
                      "tests.html", "Read the four tests"),
                small("who", "who: members (%d)" % members, "Any two of them, other than an entry's writer, can close it "
                      "(rule 3). Anyone at all can reopen one.", "members.html", "See the members"),
                small("from", "from: Z's findings", "One member's study of febu, checked by nobody "
                      "else. A finding counts here only once it is written as a fact and two other members check it.",
                      "findings.html", "Read Z's findings")]))
    return page("febu-assembly.html", "febu assembly", "febu assembly",
                "%d members studying febu, and a ledger anyone can check" % members, body,
                mast=status_banner(secs, doc), source=" from ledger.txt",
                description="The febu Assembly: a public ledger of promises and facts about febu that anyone can check."
                + (" Proposed, not yet adopted." if status(secs)[1] else ""),
                foot='This site and the ledger file are run by Z for now (<a href="ledger.html#bug-1">known bug 1</a>). '
                + QUIET)


def main():
    raw = raw_text(LEDGER)
    text = raw.decode("utf-8").rstrip("\n")
    secs = sections(text)[1]
    steps = raw_text(STEPS).decode("utf-8").rstrip("\n")
    ledger, archives = ledger_page(text, raw, steps)
    findings, counts = findings_page()
    pages = {
        "ledger.html": ledger,
        "tests.html": tests_page(raw_text(TESTS).decode("utf-8").rstrip("\n"), secs),
        "febu-assembly.html": assembly_page(secs, steps_fact(steps)),
        "findings.html": findings,
    }
    if LEDGER.read_bytes() != raw:   # the page prints the hash of the LF text, so serve exactly that
        LEDGER.write_bytes(raw)
    for name, out in pages.items():
        (ROOT / name).write_text(out, encoding="utf-8", newline="\n")
    print("ledger.txt sha256 %s (%d bytes); %s; wrote %s; findings: %s" % (
        hashlib.sha256(raw).hexdigest(), len(raw), ", ".join("%s sha256 %s" % (p, d[:16]) for p, _, d in archives),
        ", ".join(pages), "%d claims %s" % (sum(counts.values()), dict(counts)) if counts else
        "kept as built from this findings.md (no markdown package here)"))


if __name__ == "__main__":
    main()
