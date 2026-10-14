"""Lay out findings.md as one static page: no scripts, no outside fonts. build.py swaps its <style> for
assets/findings.css and adds the tabs, then writes findings.html. Edit the markdown, then run python build.py.
"""
import html
import re
import sys
from collections import Counter

import markdown

CLAIM_HEADER = "| # | Claim | Verdict | What decides it | Check | Row |"
# The sheet allows four verdict words. Anything else stops the build.
VERDICTS = (("Holds", "yes"), ("Does not hold", "no"), ("Partly", "part"), ("Open", "open"))

CSS = """
:root{
  --paper:#f1f6ef; --ink:#15213b; --soft:#526079; --rule:#c3d2c5;
  --yes:#1a7046; --no:#b02a22; --part:#8a5f00; --open:#42577e;
  --form:"Bahnschrift","DIN Alternate","DIN Condensed","Roboto Condensed","Arial Narrow",sans-serif-condensed,sans-serif;
  --text:"Segoe UI Variable Text","Segoe UI",system-ui,-apple-system,"Helvetica Neue",Arial,sans-serif;
  --mono:ui-monospace,"Cascadia Mono","SF Mono",Consolas,Menlo,monospace;
}
@media (prefers-color-scheme:dark){
  :root{
    --paper:#0f1513; --ink:#e3e9e2; --soft:#9aaba1; --rule:#2b3a32;
    --yes:#63cc96; --no:#ff8f85; --part:#e3b655; --open:#a3b6dd;
  }
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--paper);color:var(--ink);font:17px/1.55 var(--text)}
main{max-width:52rem;margin:0 auto;padding:clamp(1.75rem,6vw,4.5rem) 1rem 5rem}
.v-yes{--v:var(--yes);--m:"\\2713"} .v-no{--v:var(--no);--m:"\\2715"}
.v-part{--v:var(--part);--m:"~"} .v-open{--v:var(--open);--m:"?"}

h1,h2,main>h3,thead th,.verdict,.tally b{font-family:var(--form);font-stretch:85%}
h1{margin:0;font-size:clamp(2.2rem,8vw,3.9rem);line-height:.98;text-transform:uppercase;letter-spacing:.01em}
.nb{white-space:nowrap}
.sub{margin:.6rem 0 2rem;color:var(--soft);font-size:1.1rem}
h2{margin:3.5rem 0 .9rem;font-size:1.65rem;line-height:1.15}
main>h3{margin:2.5rem 0 .5rem;font-size:1.25rem}
p,ul{margin:0 0 .9rem}
ul{padding-left:1.2rem}
li{margin-bottom:.45rem}
code{font-family:var(--mono);font-size:.86em;overflow-wrap:anywhere;padding:.05em .3em;border-radius:3px;
  background:color-mix(in srgb,var(--rule) 45%,transparent)}

/* The whole sheet at a glance: one mark per claim, in order. */
.mast{padding-bottom:1.25rem;border-bottom:3px double var(--ink)}
.strip{display:flex;flex-wrap:wrap;gap:4px}
.strip a{display:grid;place-items:center;width:1.85rem;height:1.85rem;border-radius:2px;background:var(--v);
  color:var(--paper);font:700 1.05rem/1 var(--text);text-decoration:none;transition:transform .12s}
.strip a.v-open{background:none;color:var(--v);box-shadow:inset 0 0 0 2px var(--v)}
.strip a::before{content:var(--m)}
.strip a:hover{transform:translateY(-2px)}
a:focus-visible{outline:2px solid var(--ink);outline-offset:2px}
.tally{display:flex;flex-wrap:wrap;gap:.3rem 1.4rem;list-style:none;margin:.9rem 0 1.5rem;padding:0}
.tally li{margin:0;color:var(--v)}
.tally li::before{content:var(--m) "\\00a0";font-weight:700}
.tally b{font-size:1.2rem;margin-left:.3rem}
.intro{color:var(--soft)}
.intro p:first-child{color:var(--ink);font-size:1.1rem}
.intro strong{color:var(--ink)}

/* One claim: the mark in the margin, the claim and what decides it beside it. */
.claim{display:grid;grid-template-columns:11.5rem 1fr;padding:1.15rem 0;border-top:1px solid var(--rule);scroll-margin-top:1rem}
.claim:target{background:color-mix(in srgb,var(--rule) 40%,transparent)}
.mark{padding-right:1rem;color:var(--v)}
.num{display:block;font:600 .78rem/1.6 var(--mono);color:var(--soft)}
.verdict{display:block;font-size:1.2rem;line-height:1.15;text-transform:uppercase;letter-spacing:.04em}
.verdict::before{content:var(--m) "\\00a0"}
.qual{display:block;margin-top:.15rem;font-size:.9rem;line-height:1.3}
.body{padding-left:1.25rem;border-left:1px solid var(--rule)}
.body h3{margin:0 0 .35rem;font-size:1.06rem;line-height:1.4}
.body p{margin:0}
.body .meta{display:flex;flex-wrap:wrap;gap:.2rem 1.5rem;margin-top:.6rem;font:.78rem/1.7 var(--mono);color:var(--soft)}
.lvl{display:inline-block;min-width:1.5em;padding:0 .3em;border:1px solid currentColor;border-radius:2px;
  color:var(--ink);text-align:center}

.tbl{overflow-x:auto;margin:.75rem 0 1rem}
table{width:100%;border-collapse:collapse;font-size:.95rem}
th,td{padding:.45rem .9rem .45rem 0;border-bottom:1px solid var(--rule);text-align:left;vertical-align:top}
thead th{border-bottom:2px solid var(--ink);font-size:1.05rem}
td:not(:first-child){font-family:var(--mono);font-size:.86rem}

@media (max-width:40rem){
  body{font-size:16px}
  .claim{grid-template-columns:1fr}
  .mark{display:flex;flex-wrap:wrap;align-items:baseline;gap:0 .6rem;padding:0 0 .4rem}
  .num,.verdict,.qual{display:inline}
  .body{padding-left:0;border-left:0}
  th,td{padding-right:.6rem}
}
@media (prefers-reduced-motion:no-preference){html{scroll-behavior:smooth}}
"""

PAGE = """<!doctype html>
<!-- Built by build.py from findings.md. Edit the markdown, not this file. -->
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{css}</style>
</head>
<body>
<main>
<header class="mast">
<h1>{h1}</h1>
<p class="sub">{sub}</p>
<nav class="strip" aria-label="Every verdict, in claim order">{strip}</nav>
<ul class="tally">{tally}</ul>
<div class="intro">{intro}</div>
</header>
{body}
</main>
</body>
</html>
"""


def to_html(md_text):
    out = markdown.markdown(md_text, extensions=["tables"])
    return out.replace("<table>", '<div class="tbl"><table>').replace("</table>", "</table></div>")


def inline(text):
    out = markdown.markdown(text)
    return out[3:-4] if out.startswith("<p>") and out.endswith("</p>") else out


def split_verdict(text):
    for head, cls in VERDICTS:
        if text.startswith(head):
            return head, text[len(head):].lstrip(":, "), cls
    sys.exit(f"verdict is not one of the four words: {text!r}")


def claim_html(num, claim, verdict, decides, check, row):
    head, qual, cls = split_verdict(verdict)
    levels = re.sub(r"\b([ABC])\b", r'<b class="lvl">\1</b>', html.escape(check))
    qual_html = f'<span class="qual">{html.escape(qual)}</span>' if qual else ""
    return (
        f'<article class="claim v-{cls}" id="c{num}">'
        f'<div class="mark"><span class="num">{num}</span>'
        f'<strong class="verdict">{head}</strong>{qual_html}</div>'
        f'<div class="body"><h3>{inline(claim)}</h3><p>{inline(decides)}</p>'
        f'<p class="meta"><span>Check: {levels}</span><span>Row: {html.escape(row)}</span></p>'
        "</div></article>"
    )


def build(md_text):
    lines = md_text.splitlines()
    title, _, sub = lines[0].lstrip("# ").partition(": ")
    parts, chunk, claims = [], [], []

    def flush():
        if chunk:
            parts.append(to_html("\n".join(chunk)))
            chunk.clear()

    i = 1
    while i < len(lines):
        line = lines[i]
        if line.strip() == CLAIM_HEADER:
            flush()
            i += 2  # header and separator
            while i < len(lines) and lines[i].startswith("|"):
                claims.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                parts.append(claim_html(*claims[-1]))
                i += 1
            continue
        if line.startswith("## "):
            flush()
        chunk.append(line)
        i += 1
    flush()

    nums = [int(c[0]) for c in claims]
    assert nums == list(range(1, len(nums) + 1)), f"claim numbers are not 1..n: {nums}"
    marks = [(n, *split_verdict(c[2])) for n, c in zip(nums, claims)]
    counts = Counter(cls for _, _, _, cls in marks)
    strip = "".join(
        f'<a class="v-{cls}" href="#c{n}" title="{n}. {head}" aria-label="Claim {n}: {head}"></a>'
        for n, head, _, cls in marks
    )
    tally = "".join(f'<li class="v-{cls}">{head}<b>{counts[cls]}</b></li>' for head, cls in VERDICTS)
    h1 = re.sub(r"(\d{4}-\d\d-\d\d)", r'<span class="nb">\1</span>', html.escape(title))
    return PAGE.format(
        title=html.escape(title), h1=h1, sub=html.escape(sub[:1].upper() + sub[1:]), css=CSS,
        strip=strip, tally=tally, intro=parts[0], body="\n".join(parts[1:]),
    ), counts
