# febu Assembly: the ledger

The febu Assembly's ledger of promises and facts about febu, the texts that go with it, and the script that
turns them into the Assembly's pages on https://febu-assembly.vercel.app (assembly, the ledger, four tests,
findings).

| File | What it is |
|---|---|
| `ledger.txt` | The ledger. Edit this one. It is served byte for byte, and its SHA-256 is the hash in rule 6. |
| `fact-6-steps.txt` | Fact 6 as four steps, each a link, with all 44 payments. |
| `tests.txt` | The four tests. |
| `process.md` | The whole process in one file: the ledger, scripts and money as add-ons, the 30-day clock and its stop rule, the decisions waiting. Adds no rule; where it and `ledger.txt` differ, the ledger wins. Shown as the "the process" tab (`process.html`, built like `findings.html`: needs the `markdown` package, otherwise the committed page is kept while `process.md` is unchanged). |
| `findings.md` | Z's findings report. |
| `archive/` | Earlier versions, word for word. Add to it; never edit or delete. |
| `timestamps/` | OpenTimestamps proofs that `ledger.txt` and the archive files existed by a Bitcoin block. |
| `api/archive.js` | Asks the Internet Archive to save `ledger.txt` once a day. |
| `checks/` | Scripts that re-read facts 1 to 6, 8 and 9 from public sources, for anyone to run. |
| `build.py`, `findings_html.py` | Write the pages from the texts. `test_build.py` tests the people page and how the build reads SEEN lines (rule 3). |
| `assets/` | The pages' stylesheets, and `claims.js`: tap to copy, hash checks, and the member flows below. Written by hand. `node test_claims.js` tests its reading of a pasted chat. |
| `assets/card.png`, `make_card.py` | The 1200x630 picture a chat shows when someone pastes a link (every page names it in its `og:image` tag). `make_card.py` draws it; it holds nothing that changes with the ledger, so redraw it only to change the look. |
| `febu-assembly.html`, `ledger.html`, `how.html`, `process.html`, `tests.html`, `findings.html`, `people.html`, `weekly.html`, `write.html` | Written by `build.py`. Don't edit them by hand. |

## Member flows

Each turns one job into one page and one message for the chat. None of them posts, stores or sends anything.

- **Check card** (front page, under each entry rule 3 has not closed): tick the WRONG IF lines you tested, say what you
  saw on each, name one new thing on the page, pick your result. Copy waits until the new thing is filled in. The post's
  first line is the part a machine reads: `CHECK FACT 8 · HOLDS · lines 1,3 · Laura · 2026-10-15`. WRONG IF lines are
  numbered by clause, split at ", or" and "; or", the way `checks/resolve.py` names them.
- **Your next move** (front page): pick your name to see the entries you can check, the open votes with their closing date
  (the version from STATUS and the last "yes" or "object" date in the ledger; more subjects from one STATUS line
  `Also up for the vote by 2026-10-22: the Saw line; the stop rule.`), and whose weekly turn it is. Weeks are counted from
  the first date in STATUS, in Member order, on the reader's own clock.
- **The weekly turn** (`weekly.html`, rule 6): paste the week's chat. It reads the CHECK, VOTE and ENTRY posts and lists
  the SEEN lines to add in the ledger's layout, the SEEN lines with no post, the entries rule 3 would close, the votes
  against rule 7, and every line it could not read. You paste its blocks into `ledger.txt` (Editing in the browser).
- **Write an entry** (`write.html`): SAYS, LINK and one WRONG IF line per part of SAYS, laid out for `ledger.txt` and as
  a chat post. Facts only; write a promise by hand from HOW AN ENTRY IS WRITTEN.

A SEEN line the weekly page writes reads `- Laura, 2026-10-15: HOLDS on lines 1, 3. Saw: ... New: ... 14 minutes.`,
the first replacing "nobody yet". The build reads that form back to decide which entries rule 3 has closed; a SEEN line
written another way still shows, but is left to a person to count.

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
5. Commit and push. Vercel rebuilds the pages from the texts (see Publishing). Running the build yourself first
   shows a mistake before anyone else does; then commit the pages it writes along with `ledger.txt`.

## Rebuild

Python 3. The ledger, the front page and the tests page need nothing else; `findings.html` also needs the
`markdown` package:

```bash
pip install markdown
```

```bash
python build.py
```

It prints `ledger.txt`'s SHA-256. It stops with a message, and writes nothing, if a page would show notation
the ledger keeps off its pages, if a wallet address or transaction signature would appear anywhere but
the ledger page, if a SHA-256 the ledger cites doesn't match its archive file, or if fact 6's rows aren't
numbered 1 to n or don't add up to its total. Without `markdown`, it keeps `findings.html` as it is if that was
built from the same `findings.md`, and stops if `findings.md` has changed since.

Next to every solscan.io link on the ledger page, the build adds the same record on explorer.solana.com, so no
check rests on one explorer (known bug 4). `ledger.txt` itself keeps only the links it has.

## Publishing

Every push to `main` redeploys the Vercel project `febu-ledger`. Vercel first runs `python3 build.py` (the
`buildCommand` in `vercel.json`), then serves the folder. https://febu-assembly.vercel.app forwards the
Assembly's addresses to that project (`febu-host`'s `vercel.json`), so the links stay the same and `ledger.txt`
arrives byte for byte. After a push, download https://febu-assembly.vercel.app/ledger.txt and check that its
SHA-256 is the one the build printed (Vercel's build log prints it too).

### Editing in the browser, with no tools

Open `ledger.txt` on GitHub, press the pencil (Edit this file), make the change, and commit it to `main`. Vercel
rebuilds the pages from it in a minute or two. If the edit breaks something the build checks (the list under
Rebuild), the build stops, that deployment fails, and the site keeps serving the version before it. GitHub then
shows a red cross beside the commit, with Vercel's message behind it. The broken commit stays in the history
(rule 2); fix it with another commit. The build checks only that list: any other edit goes live as written.

After such an edit the pages in the repository lag behind `ledger.txt` until someone runs the build and commits
them. The site does not lag, because Vercel builds its own.

## Rerunnable checks

`checks/` re-reads the facts a machine can read, with Python 3 and nothing else: no packages, no account, no key.
Each takes its addresses and transactions from `ledger.txt` and `fact-6-steps.txt`, so it tests what the ledger
says, and prints what it saw. `resolve.py` also names which WRONG IF lines tripped. None of them posts anything:
a person reads the output, compares it with the entry's WRONG IF lines, opens a link by hand, and posts (HOW TO
CHECK AN ENTRY). Say in your post that you ran a script. Until the Saw line is adopted (rule 7), a script run alone
is not a Saw.

| Script | Reads | Takes |
|---|---|---|
| `python checks/fact2.py` | Fact 2: the creator wallet's $FEBU before and after the sale the ledger links, and whether it holds any $FEBU now | seconds |
| `python checks/fact5.py` | Fact 5: on how many of pages 1-24 and 25-164 each of the eight words appears, in the scripture copy behind the fact's link | seconds |
| `python checks/fact6.py` | Fact 6: adds up the 44 rows, then re-reads every row's transaction and step 1's trade | a minute or two |
| `python checks/resolve.py fact1` | Fact 1: the creator wallet's $FEBU account in the window | about a minute |
| `python checks/resolve.py fact3` | Fact 3: the phrase in the archived script, and the time the tweet id gives | seconds |
| `python checks/resolve.py fact4` | Fact 4: every page's book against the rotation, on the scripture copy behind the link | seconds |
| `python checks/resolve.py fact8` | Fact 8's three lines, reading the creator's wrapped-SOL account, the quiet end of every payment out | about a minute |
| `python checks/resolve.py door2` | Fact 8's other way out: every transaction on pump's creator vault in the window | about 3 minutes |
| `python checks/resolve.py test9` | Fact 9 on the real transaction, then on one-change copies and four lazy versions it must catch | seconds |
| `python checks/resolve.py claimsim` | Whether a stranger can send the fee claim: a dry run the node simulates, nothing sent | seconds |

- The chain checks ask the public node https://api.mainnet-beta.solana.com. To ask another, your own for example,
  set `SOLANA_RPC` (`SOLANA_RPC=http://127.0.0.1:8899 python checks/fact6.py`). The public node turns away fast
  callers; the scripts wait and retry.
- `fact5.py` takes a copy of your own too, in the same form, which is how KNOWN BUGS 3 gets fixed:
  `python checks/fact5.py my-copy.json`. It prints the copy's SHA-256, so two people can tell whether they counted
  the same copy.
- `fact6.py` does not test "had received nothing from it by the end of 2026-10-14". Thousands of trades touched the
  fee account, too many for a public node; `resolve.py fact8` and `door2` read the two ways out instead.
- Never send the fee claim to see what happens. It pays the creator wallet and makes a WRONG IF line true.
- `python checks/test_checks.py` tests the scripts' own reading of the texts, offline.

## Records outside the group (rule 6)

Two kinds of dated record that nobody in the group controls. The ledger's dated line of 2026-10-14 under CHANGES
TO THE RULES names both.

**The Internet Archive, every day.** `api/archive.js` runs once a day (the `crons` entry in `vercel.json`; on
Vercel's free plan it fires some time between 04:00 and 05:00 UTC) and asks the Archive to save
https://febu-ledger.vercel.app/ledger.txt. Nobody has to do anything. Every copy, with its date and time:
https://web.archive.org/web/*/https://febu-ledger.vercel.app/ledger.txt. To hash a copy, put `id_` after its date
in the address, so you get the file as it was saved rather than the Archive's page around it. The Archive sends it
compressed, so let your tool unpack it:

```bash
curl -s --compressed https://web.archive.org/web/20261014170819id_/https://febu-ledger.vercel.app/ledger.txt | sha256sum
```

That first copy is `b43c02f1…`, the version before the dated line.

**OpenTimestamps.** `timestamps/` holds proofs that a file existed by the time of a Bitcoin block. A proof holds
the file's SHA-256 and nothing else, so it shows nothing about who made it. Each is named after what it proves:

| Proof | File |
|---|---|
| `timestamps/ledger-87ddd678.txt.ots` | `ledger.txt` as version 3 was first served, 2026-10-14 |
| `timestamps/ledger-3d9f5e36.txt.ots` | `ledger.txt` as of the dated line about these records |
| `timestamps/ledger-b43c02f1.txt.ots` | `ledger.txt` just before it (`git show 6d519d0:ledger.txt`) |
| `timestamps/<name>.ots` | `archive/<name>`, one for each file there |

Install the client (Python 3), then verify a proof against the file it names:

```bash
pip install opentimestamps-client
```

```bash
ots verify -f ledger.txt timestamps/ledger-3d9f5e36.txt.ots
```

"Success! Bitcoin block N attests existence as of DATE" is the result. "Pending confirmation in Bitcoin
blockchain" means the calendars have not yet put it in a block; that takes a few hours after stamping. "File does
not match original!" means the file is not the one stamped.

- **Against your own Bitcoin node.** `ots verify` asks the Bitcoin Core node on the same machine (it reads
  `~/.bitcoin/bitcoin.conf`), or the one you name with `--bitcoin-node http://user:pass@host:8332`. It needs only
  block headers, so a pruned node is enough. With no node, `ots --no-bitcoin verify -f FILE PROOF` prints "check
  that Bitcoin block N has merkleroot M", which any block explorer shows; or https://opentimestamps.org checks a
  proof in the browser against public block explorers.
- **Upgrade.** A new proof only says which calendars promised to put it in a block. Once they have, anyone can
  fetch the rest of the path into Bitcoin and keep it in the file, so the proof no longer needs the calendars:

  ```bash
  ots upgrade timestamps/*.ots
  ```

  Commit the upgraded files (it leaves `.bak` copies, which git ignores).
- **Stamp a new version.** After a change to `ledger.txt` is live, any member can stamp it and commit the proof:

  ```bash
  f=timestamps/ledger-$(sha256sum ledger.txt | cut -c1-8).txt && cp ledger.txt $f && ots stamp $f && rm $f
  ```

## A second editor

Z adds them on GitHub: Settings, Collaborators, Add people, role Write. They can then edit in the browser, or
clone, edit, build and push the same way Z does. On Vercel's free plan a collaborator's push deploys only because
this repository is public. Anyone else can propose a change as a pull request, or copy the whole thing and run it their own way
(rule 7).

## Checking the history (rule 2)

`git log -p -- ledger.txt` shows every change to the ledger since it moved here on 2026-10-14. Earlier
versions are in `archive/`, with the SHA-256 the ledger cites for each one.
