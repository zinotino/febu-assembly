# febu Assembly: the ledger

The febu Assembly's ledger of promises and facts about febu, the texts that go with it, and the script that
turns them into the Assembly's pages on https://febu-assembly.vercel.app (assembly, the ledger, four tests).

| File | What it is |
|---|---|
| `ledger.txt` | The ledger. Edit this one. It is served byte for byte, and its SHA-256 is the hash in rule 6. |
| `fact-6-steps.txt` | Fact 6 as four steps, each a link, with all 44 payments. |
| `tests.txt` | The four tests. Reading, not the experiment: served at `/tests.html`, not linked from the front page. |
| `process.md` | The whole process in one file: the ledger, the scripts, money, the 30-day clock and its stop rule, the decisions waiting. Adds no rule; where it and `ledger.txt` differ, the ledger wins. Shown as the "the process" tab (`process.html`, needs the `markdown` package, otherwise the committed page is kept while `process.md` is unchanged). |
| `paid.md` | The shape for a member who wants to pay for scripts: their own promise, the cap, two tests of its own. Not linked from the site, not part of the vote. |
| `archive/` | Empty at the clean start of 2026-10-15. Each later change to `ledger.txt` puts the text before it here, word for word. Add to it; never edit or delete. |
| `timestamps/` | OpenTimestamps proofs that `ledger.txt` and the archive files existed by a Bitcoin block. One so far, for the current `ledger.txt`; the archive files have none (see "Records outside the group"). |
| `api/archive.js` | Asks the Internet Archive to save `ledger.txt` once a day. |
| `checks/` | Scripts that re-read facts 1 to 6, 8 and 9 from public sources, for anyone to run. |
| `build.py` | Write the pages from the texts. `test_build.py` tests the people page and how the build reads SEEN lines (rule 3). |
| `assets/` | The pages' stylesheets, and `claims.js`: tap to copy, hash checks, and the member flows below. Written by hand. `node test_claims.js` tests its reading of a pasted chat. |
| `assets/card.png`, `make_card.py` | The 1200x630 picture a chat shows when someone pastes a link (every page names it in its `og:image` tag). `make_card.py` draws it; it holds nothing that changes with the ledger, so redraw it only to change the look. |
| `febu-assembly.html`, `ledger.html`, `how.html`, `process.html`, `tests.html`, `people.html`, `weekly.html`, `write.html`, `assembly.ics` | Written by `build.py`. Don't edit them by hand. |


## One project

This repo is the whole of the Assembly: the pages, the ledger, the two daily jobs, and the unofficial archive of imfebu.com (the "den"). It replaces two repos and two project names that were easy to confuse:

| Old name | What it was | Now |
|---|---|---|
| `febu-host` (private GitHub repo) | The den, the scripture reader, the members page, and a proxy to this repo | Folded in here on 2026-10-15; the repo is archived. Every current file is here byte for byte. Only superseded page renders, the dropped draw page and earlier den bundles exist solely in its history. |
| Vercel project `febu-assembly` | Deployed from `febu-host` | Deploys from this repo. https://febu-assembly.vercel.app is the front door. |
| Vercel project `febu-ledger` | This repo, under another project name | Only a redirect now: the first routes in `vercel.json` answer every path on https://febu-ledger.vercel.app with a 308 to the same path on https://febu-assembly.vercel.app (`/` goes to `/febu-assembly.html`), so nothing is served from it. The project is kept so that nobody else can register the name and serve a different `ledger.txt` at an address people were once given. Delete it only if you accept that. |

| Path | What it is |
|---|---|
| `/` , `index.html`, `assets/index-*.js`, `assets/index-reconstructed.css`, `assets/shim.js`, `assets/community.json`, `assets/scripture.json` | The den: the 2026-08-14 imfebu front end, patched to talk to our Supabase. Its app routes (`/library/scripture` and the rest) fall back to `index.html`. See `DEN.md`. |
| `scripture.html` | Plain-text scripture reader. |
| `api/keepalive.js` | A daily read so the free Supabase project is not paused. |
| `test_routes.py` | Checks `vercel.json`: the Assembly's security headers sit on the Assembly's files only (the den needs inline styles and Supabase), `/` is the den here and the front page on the old domain, unknown paths reach the den. |

**One address.** The Assembly and the den share https://febu-assembly.vercel.app, so they share browser storage. The Assembly keeps nothing there that anyone could use (the name a member picked and unfinished posts, on the device; no token, no key), but a script that ran in the den could still read those, and one that ran could be made to do worse. What keeps one in from the other:

- Every path that is not an Assembly file gets a content-security policy (the first route in `vercel.json`): scripts from this address only, no inline script, no `javascript:` links, connections to this address and the one Supabase project only. A post that smuggles in a script, an event handler or a `javascript:` link does nothing. Checked in a browser on 2026-10-15: with the policy on, the den's home, library and community pages load with no violations, and an inline script and a `javascript:` link are both refused.
- The den's bundle puts raw HTML into the page in two places only, both react-tweet's rendering of a tweet's own text, and in one theme script the policy blocks. The count of 16 this file used to give was the string `dangerouslySetInnerHTML` appearing in React's own code. Posts and comments are drawn as text.
- Not covered: a bug in the bundle's own code that a post can steer into running, which the policy does not stop. It would reach a picked name and an unfinished post, nothing more. If that worries you, the den goes, and nothing else changes.

`test_routes.py` checks both policies on every path. The one environment variable the site can use (set in Vercel, never in the repo) is `CRON_SECRET`: with it set in the `febu-assembly` project, only the daily cron may call `/api/archive`. It is not set today, so anyone may call it; that asks the Internet Archive to save a public file and nothing else, and the worst a caller can do is get the daily save refused for a while. The copies in the old `febu-ledger` project are not used any more and can be removed.

## Member flows

Each turns one job into one page and one message for the chat. None of them posts, stores or sends anything.

- **Check card** (front page, under each entry rule 3 has not closed): tick the WRONG IF lines you tested, say what you
  saw on each, name one new thing on the page, pick your result. Copy waits until the new thing is filled in. The post's
  first line is the part a machine reads: `CHECK FACT 8 · HOLDS · lines 1,3 · Laura · 2026-10-15`. WRONG IF lines are
  numbered by clause, split at ", or" and "; or", the way `checks/resolve.py` names them.
- **Your week** (front page): pick your name to see four numbered steps. Check: the entries open to you. Vote: what is
  open, with its closing date (the version from STATUS and the last "yes" or "object" date in the ledger; more subjects
  from one STATUS line `Also up for the vote by 2026-10-22: the Saw line; the stop rule.`). Weekly turn: when yours comes,
  counted from the first date in STATUS in Member order, on the reader's own clock. Write. Under the steps, a reminder
  post of what is due for anyone to paste into the chat, and `assembly.ics`: the vote's closing day, twelve weekly turns
  and each known bug's fix-by day as all-day calendar events. The banner's Due line shows the same dates. The
  device remembers the name picked and any unfinished check card (localStorage, cleared when the post is copied);
  `#me=Name` in the address picks a name, so each member has a link of their own. Nothing leaves the page.
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
   `archive/` (for example `archive/ledger-before-2026-11-04.txt`) and cite that copy's SHA-256 under CHANGES TO
   THE RULES, the way the lines already there do. The build stops if a cited hash doesn't match the file.
4. Keep lines to 92 characters. A short line meant to stand on its own keeps to 80; a longer one runs on into
   the next line on the page.
5. Commit and push. Vercel rebuilds the pages from the texts (see Publishing). Running the build yourself first
   shows a mistake before anyone else does; then commit the pages it writes along with `ledger.txt`.

## Rebuild

Python 3. The ledger, the front page and the tests page need nothing else; `process.html` also needs the
`markdown` package when `process.md` changes:

```bash
pip install markdown
```

```bash
python build.py
```

It prints `ledger.txt`'s SHA-256. It stops with a message, and writes nothing, if a page would show notation
the ledger keeps off its pages, if a wallet address or transaction signature would appear anywhere but
the ledger page, if a SHA-256 the ledger cites doesn't match its archive file, or if fact 6's rows aren't
numbered 1 to n or don't add up to its total. Without `markdown`, it keeps `process.html` as it is if that was
built from the same `process.md`, and stops if `process.md` has changed since.

Next to every solscan.io link on the ledger page, the build adds the same record on explorer.solana.com, so no
check rests on one explorer (known bug 4). `ledger.txt` itself keeps only the links it has.

## Publishing

Every push to `main` redeploys the Vercel project built from this repo, `febu-assembly` (and `febu-ledger`, which only redirects). Vercel first runs `python3 build.py` (the
`buildCommand` in `vercel.json`), then serves the folder, so `ledger.txt` arrives byte for byte. After a push, download https://febu-assembly.vercel.app/ledger.txt and check that its
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
| `python checks/release.py --posted d3e17658` | The release: the served `ledger.txt` against this checkout and git, the hash a post names (and which archived version it is, if not the served file), the headers, the Internet Archive's captures, and whether each timestamp proof is pending or in a block. CAN'T TELL when a read is incomplete | seconds |

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

Two kinds of dated record that nobody in the group controls. Both start from the clean-start text of
2026-10-15; copies dated before then are of drafts that were withdrawn.

**Two daily crons** (`crons` in `vercel.json`), neither of which takes input or changes anything: `/api/archive`
(below); and `/api/keepalive`, one read of the den's `site_stats` with the publishable key, so the free Supabase
project is never idle long enough to pause.

**The Internet Archive, every day.** `api/archive.js` runs once a day (the `crons` entry in `vercel.json`; on
Vercel's free plan it fires some time between 04:00 and 05:00 UTC) and asks the Archive to save
https://febu-assembly.vercel.app/ledger.txt. Nobody has to do anything. Every copy, with its date and time:
https://web.archive.org/web/*/https://febu-assembly.vercel.app/ledger.txt. Until 2026-10-15 the save was of the old address, `febu-ledger.vercel.app`; those copies are listed under that address and are of the withdrawn drafts. To hash a copy, put `id_` after its date
in the address, so you get the file as it was saved rather than the Archive's page around it. The Archive sends it
compressed, so let your tool unpack it:

```bash
curl -s --compressed https://web.archive.org/web/<YYYYMMDDhhmmss>id_/https://febu-assembly.vercel.app/ledger.txt | sha256sum
```

**OpenTimestamps.** `timestamps/` holds proofs that a file existed by the time of a Bitcoin block. A proof holds
the file's SHA-256 and nothing else, so it shows nothing about who made it. Each is named after what it proves: `timestamps/ledger-<first 8 characters of the SHA-256>.txt.ots` for a
version of `ledger.txt`, and `timestamps/<name>.ots` for `archive/<name>`. There is one so far:
`timestamps/ledger-d3e17658.txt.ots`, for the `ledger.txt` of 2026-10-15 (SHA-256 `d3e17658...`). It was made with the
`opentimestamps` Python library, because the `ots` client would not start on that machine; it holds the same four
calendar promises and verifies the same way. It was upgraded the same way on 2026-10-15: Bitcoin blocks 971607 and
971608 (18:08 and 18:10 UTC) carry it, through two of the four calendars; the other two had not answered yet. The archive files have no proof; stamp one the same way if the group wants it.

Install the client (Python 3), then verify a proof against the file it names:

```bash
pip install opentimestamps-client
```

```bash
ots verify -f ledger.txt timestamps/ledger-<8 characters>.txt.ots
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

`git log -p -- ledger.txt` shows every change to the ledger since the clean start of 2026-10-15; the history
before it was cut along with the drafts it described. From here on, earlier versions are in `archive/`, with the
SHA-256 the ledger cites for each one.


## One write path

A result, a second or a vote reaches the ledger one way: a post in the chat, which the weekly turn copies into
`ledger.txt` (rules 3, 6 and 7). The site reads and prepares posts; it stores nothing and signs nobody in. A sign-in
(a one-time name claim) and a live record of seconds and checks were built for a second way and removed on 2026-10-15
before any rule came to depend on them: nothing on the site called the record, and the ledger counts only what the
chat shows. A second way to write would have given rule 8 a second thing only one person could run. The code is in git:
`git log --diff-filter=D -- api/claim.js` finds the commit that removed it.
