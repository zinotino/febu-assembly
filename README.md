# febu Assembly: the ledger

The febu Assembly's ledger of promises and facts about febu, the texts that go with it, and the script that
turns them into the Assembly's pages on https://febu-assembly.vercel.app (assembly, the ledger, four tests,
findings).

| File | What it is |
|---|---|
| `ledger.txt` | The ledger. Edit this one. It is served byte for byte, and its SHA-256 is the hash in rule 6. |
| `fact-6-steps.txt` | Fact 6 as four steps, each a link, with all 44 payments. |
| `tests.txt` | The four tests. |
| `findings.md` | Z's findings report. |
| `archive/` | Earlier versions, word for word. Add to it; never edit or delete. |
| `build.py`, `findings_html.py` | Write the four pages from the texts. |
| `assets/` | The pages' stylesheets, and `claims.js` (tap to copy, hash checks). Written by hand. |
| `febu-assembly.html`, `ledger.html`, `tests.html`, `findings.html` | Written by `build.py`. Don't edit them by hand. |

## Add an entry

1. In `ledger.txt`, under THE ENTRIES, write it the way HOW AN ENTRY IS WRITTEN shows, lined up like the
   entries above it. Use the number the line "The next entry is number n." gives, then raise that number.
2. Nothing is removed or rewritten (rule 2). A result is a SEEN line. A change to an entry before anyone
   checks it is a CHANGED line inside the entry. Anything else gets a dated line under CHANGES TO THE RULES.
3. Before rewording what is already there, or changing a rule (rule 7), copy the served `ledger.txt` into
   `archive/` (for example `archive/08_CLAIMS_LEDGER_v2.2.txt`) and cite that copy's SHA-256 under CHANGES TO
   THE RULES, the way the lines already there do. The build stops if a cited hash doesn't match the file.
4. Keep lines to 92 characters. A short line meant to stand on its own keeps to 80; a longer one runs on into
   the next line on the page.
5. Rebuild, then commit `ledger.txt` and the pages together, and push.

## Rebuild

Python 3 and the `markdown` package:

```bash
pip install markdown
```

```bash
python build.py
```

It prints `ledger.txt`'s SHA-256. It stops with a message, and writes nothing, if a page would show notation
the ledger keeps off its pages, if a wallet address or transaction signature would appear anywhere but
the ledger page, if a SHA-256 the ledger cites doesn't match its archive file, or if fact 6's rows aren't
numbered 1 to n or don't add up to its total.

An edit made on github.com changes `ledger.txt` but not the pages. Until someone runs the build and pushes,
the ledger page shows the old text, and its hash check reports a different SHA-256.

## Publishing

Every push to `main` redeploys the Vercel project `febu-ledger`. There is no build step: Vercel serves the
files as committed. https://febu-assembly.vercel.app forwards the Assembly's addresses to that project
(`febu-host`'s `vercel.json`), so the links stay the same and `ledger.txt` arrives byte for byte. After a
push, download https://febu-assembly.vercel.app/ledger.txt and check that its SHA-256 is the one the build
printed.

## A second editor

Z adds them on GitHub: Settings, Collaborators, Add people, role Write. They then clone, edit, build and push
the same way Z does. On Vercel's free plan a collaborator's push deploys only because this repository is
public. Anyone else can propose a change as a pull request, or copy the whole thing and run it their own way
(rule 7).

## Checking the history (rule 2)

`git log -p -- ledger.txt` shows every change to the ledger since it moved here on 2026-10-14. Earlier
versions are in `archive/`, with the SHA-256 the ledger cites for each one.
