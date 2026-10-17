# febu Assembly: the ledger

The febu Assembly's ledger, one question at a time about febu, the texts that go with it, and the script that
turns them into the Assembly's pages on https://febu-assembly.vercel.app (assembly, the ledger, four tests).

| File | What it is |
|---|---|
| `ledger.txt` | The ledger, version 5: proposals, the questions they open, and the answers under each. Edit this one. It is served byte for byte, and its SHA-256 is the hash in rule 7. |
| `fact-6-steps.txt` | Version 3's fact 6 as four steps, each a link, with all 44 payments. `checks/fact6.py` reads it; no page shows it. |
| `tests.txt` | The four tests. Reading, not the experiment: served at `/tests.html`, not linked from the front page. |
| `process.md` | Version 3's whole process in one file: its ledger, the scripts, money, the 30-day clock and its stop rule, the decisions waiting. Adds no rule, and describes the version before this one: version 5's rules are all in `ledger.txt`. Shown as the "the process" tab (`process.html`, needs the `markdown` package, otherwise the committed page is kept while `process.md` is unchanged). |
| `paid.md` | Version 3's shape for a member who wants to pay for scripts. Rule 9 of version 5 has no pay. Not linked from the site. |
| `archive/` | Empty at the clean start of 2026-10-15. Each later change to `ledger.txt` puts the text before it here, word for word: version 3's last text is `archive/08_CLAIMS_LEDGER_v3.txt`, with its nine entries. Add to it; never edit or delete. |
| `timestamps/` | OpenTimestamps proofs that `ledger.txt` and the archive files existed by a Bitcoin block. One so far, for version 3's `ledger.txt` (`d3e17658`); the archive files have none (see "Records outside the group"). |
| `api/archive.js` | Asks the Internet Archive to save `ledger.txt` once a day. |
| `checks/` | Scripts that re-read version 3's facts 1 to 6, 8 and 9 from public sources, for anyone to run. An answer that copies one of those facts can be checked with them. `lint.py` tests the file against its own rules, `closers.py` reads who closes the answers. `agent.py` and `mcp_server.py` let a member's AI run the scripts and draft a check post (see `AGENTS.md`). |
| `ledger.json` | Written by `build.py`: a read-only index of `ledger.txt` for an agent (its hash, the members and their dated posts, the proposals and their yeses, each question with its answers' posters, WRONG IF clauses, results and state, the votes). No links, addresses cut to 7 characters; `ledger.txt` wins. |
| `build.py` | Write the pages from the texts, and the state of every answer under rules 4 and 5, every question under rules 2 and 5, and every vote under rule 8 (`model`, also in `ledger.json`). `test_build.py` tests how the build reads SEEN items, the worked version-5 ledger in `checks/fixtures/`, the states against `checks/states.json`, and adoption day in a copy of the repo. |
| `assets/` | The pages' stylesheets, and `claims.js`: tap to copy, hash checks, and the member flows below. Written by hand. `node test_claims.js` tests its reading of a pasted chat, and its copy of `standing` against the same `checks/states.json`. |
| `assets/card.png`, `make_card.py` | The 1200x630 picture a chat shows when someone pastes a link (every page names it in its `og:image` tag). `make_card.py` draws it; it holds nothing that changes with the ledger, so redraw it only to change the look. |
| `febu-assembly.html`, `ledger.html`, `how.html`, `process.html`, `tests.html`, `weekly.html`, `write.html`, `assembly.ics` | Written by `build.py`. Don't edit them by hand. |


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

- **Check card** (front page, under each answer to the open question that rule 4 has not closed): tick the WRONG IF
  lines you tested, say what you saw on each and, for a line over many items, how many you opened, name one new thing
  on the page, pick your result. Copy waits until the new thing is filled in. The post's first line is the part a
  machine reads: `CHECK Q1 ANSWER 2 · HOLDS · lines 1,3 · Laura · 2026-11-02`. WRONG IF lines are numbered by clause,
  split at ", or" and "; or" (Result, in WORDS USED HERE).
- **Your week** (front page): pick your name to see five numbered steps. Check: the open answers you did not post and
  have no SEEN item on yet. Propose and say yes: the proposals not yours that have no yes of yours (rule 2). Vote: what
  is open, with its date (while STATUS says Proposed, this version and the last "yes" or "object" date in STATUS;
  after, each text in VOTES that has not passed, counted from its 7th day). Weekly turn: when yours comes, counted from
  the first date in STATUS in Member order, on the reader's own clock. Write. Under the steps, a reminder post of what
  is due for anyone to paste into the chat, and `assembly.ics`: each vote's day, twelve weekly turns and each known
  bug's fix-by day as all-day calendar events. The banner's Due line shows the same dates. The device remembers the
  name picked and any unfinished check card (localStorage, cleared when the post is copied); `#me=Name` in the address
  picks a name, so each member has a link of their own. Nothing leaves the page.
- **The weekly turn** (`weekly.html`, rule 7): paste the week's chat. It reads the CHECK, PROPOSE, YES, VOTE and ANSWER
  posts and lists, in the ledger's layout, the SEEN items to add, the new proposals and yeses, the question rule 2
  opens, the new answers, the VOTES items with each count under rule 8, and one LAST POSTS line; then the answers rule
  4 would close or rule 5 would keep open or reopen, and every line it could not read. You paste its blocks into
  `ledger.txt` (Editing in the browser).
- **Write an answer** (`write.html`): SAYS, LINK and one WRONG IF line per part of SAYS, for the open question, laid out
  for `ledger.txt` and as a chat post that starts `ANSWER Q1 · Laura · 2026-11-04`.

The other posts' first lines: `PROPOSE · the question, in one sentence · Laura · 2026-11-02`, `YES P4 · Laura ·
2026-11-03`, and `VOTE YES · rule 4 wording · Laura · 2026-11-03` (an OBJECT adds the lines "Which line is wrong:" and
"What would change my mind:"). "|" or "•" work in place of "·".

A SEEN item the weekly page writes reads `- Laura, 2026-11-02: HOLDS on lines 1, 3. Items: line 3, all 164. Saw: ...
New: ...`, the first replacing "nobody yet", with `Script: <command> by <who> via <where>.` before `Saw:` when a script
did part of it. The build reads that form back to decide which answers rules 4 and 5 have closed, kept open or
reopened; a SEEN item written another way still shows, but is left to a person to count.

## Add an answer

1. In `ledger.txt`, under THE QUESTIONS, put it under its question after the last answer, the way HOW A QUESTION IS
   WRITTEN shows, lined up like the answers above it, numbered in the order posted. A proposal goes under PROPOSED
   QUESTIONS with the number the line "The next proposal is P n." gives; a question opened under rule 2 goes under THE
   QUESTIONS with the number "The next question is Q n." gives, with "Opened as Q n." under its proposal. Then raise
   that number.
2. Nothing is removed or rewritten (rule 6). A result is a SEEN item. A change to an answer before its first SEEN
   item is a CHANGED line inside the answer that names who changed it. NOTE lines may be added at any time. Anything
   else gets a dated line under CHANGES TO THE RULES.
3. Before rewording what is already there, or changing a rule (rule 8), copy the served `ledger.txt` into
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
the ledger page, if a SHA-256 the ledger cites doesn't match its archive file, if the text is not laid out the way
version 5 is (one PROPOSED QUESTIONS section and one THE QUESTIONS section, an answer with no SAYS line), or if an
answer copies a version-3 fact or promise that `archive/08_CLAIMS_LEDGER_v3.txt` does not have. It cannot read a
version-3 `ledger.txt`. Without `markdown`, it keeps `process.html` as it is if that was built from the same
`process.md`, and stops if `process.md` has changed since.

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
(rule 6); fix it with another commit. The build checks only that list: any other edit goes live as written.

After such an edit the pages in the repository lag behind `ledger.txt` until someone runs the build and commits
them. The site does not lag, because Vercel builds its own.

## Rerunnable checks

`checks/` re-reads version 3's facts a machine can read, with Python 3 and nothing else: no packages, no account, no
key. (Two helpers for a member's AI need more: `agent.py lint` needs node, and `mcp_server.py` needs `pip install "mcp>=1.26,<2"`. Neither posts.)
Each takes its addresses and transactions from the fact's text, in `ledger.txt` if it is there and in
`archive/08_CLAIMS_LEDGER_v3.txt` if not, and from `fact-6-steps.txt`, so it tests what the text says, and prints
what it saw. `resolve.py` also names which WRONG IF lines tripped. None of them posts anything: a person reads the
output, compares it with the answer's WRONG IF lines, opens a link by hand, and posts (HOW TO CHECK AN ANSWER). Say
in your post whose script you ran and where it ran (the `Script:` line). A script run is a Saw only when none of the
answer's posters wrote the script and you opened one link by hand (Saw, in WORDS USED HERE), and rule 4 needs one of
the three closers to open every link by hand. Z wrote every script here and every version-3 fact, and an answer
copied from version 3 names its writer among its posters, so on such an answer these scripts show where to look
and count toward nothing (KNOWN BUGS 8).

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
| `python checks/lint.py` | The file against its own rules, run by the weekly turn before it commits (`--rev HEAD~1` after; `--prev FILE` against a saved copy, such as `archive/08_CLAIMS_LEDGER_v3.txt` on adoption day): every line of the earlier version still there unless CHANGES TO THE RULES archives it (I1), proposals, questions and answers numbered in order and each question opened the day rule 2 gives (I2), no SEEN item by one of its answer's posters or on a script one of them wrote (I3), none while STATUS says Proposed, before its answer's first day or in the future (I4), no checked answer changed and every CHANGED line naming who and when (I5), every SEEN item readable (I6), results and WRONG IF lines that exist (I7), every archive/ copy there with its hash (I9). Eight lines; there is no I8, since version 3's bonds are gone | seconds |
| `python checks/closers.py` | Who closes the answers: for every answer rule 4 has closed, its posters, its closers and the day, then the answers posted and closed per poster, the closes per closer and per set of closers, and the busiest set's and closer's share. A FLAG line when one set made at least half the closes, or one poster is on at least half the closed answers. A reading for the weekly turn to paste in the chat, not a rule (rule 9 keeps totals off the file and the pages): exit 2 while nothing has closed | seconds |

- The chain checks ask the public node https://api.mainnet-beta.solana.com. To ask another, your own for example,
  set `SOLANA_RPC` (`SOLANA_RPC=http://127.0.0.1:8899 python checks/fact6.py`). The public node turns away fast
  callers; the scripts wait and retry. `python checks/agent.py run 8 --rpc https://your-node` does the same for the
  helper, and its `Script:` line ends in `via <host>`: two members whose lines name one host read one source, and
  `lint` on both posts says so. The host only is named; a path or query can hold a key and is cut from the output. Some providers put an id in the host itself, and the host is printed: pick a node whose name you would post. A
  node that answers with a redirect is refused, not followed.
- `fact5.py` takes a copy of your own too, in the same form, which is how KNOWN BUGS 3 gets fixed:
  `python checks/fact5.py my-copy.json`. It prints the copy's SHA-256, so two people can tell whether they counted
  the same copy.
- `fact6.py` does not test "had received nothing from it by the end of 2026-10-14". Thousands of trades touched the
  fee account, too many for a public node; `resolve.py fact8` and `door2` read the two ways out instead.
- Never send the fee claim to see what happens. It pays the creator wallet and makes a WRONG IF line true.
- `python checks/test_checks.py` tests the scripts' own reading of the texts, offline.

## Records outside the group (rule 7)

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
(rule 8).

## Checking the history (rule 6)

`git log -p -- ledger.txt` shows every change to the ledger since the clean start of 2026-10-15; the history
before it was cut along with the drafts it described. From here on, earlier versions are in `archive/`, with the
SHA-256 the ledger cites for each one.


## One write path

A result, a proposal, a yes, an answer or a vote reaches the ledger one way: a post in the chat, which the weekly
turn copies into `ledger.txt` (rules 6 and 7). The site reads and prepares posts; it stores nothing and signs nobody in. A sign-in
(a one-time name claim) and a live record of seconds and checks were built for a second way and removed on 2026-10-15
before any rule came to depend on them: nothing on the site called the record, and the ledger counts only what the
chat shows. A second way to write would have given rule 10 a second thing only one person could run. The code is in git:
`git log --diff-filter=D -- api/claim.js` finds the commit that removed it.
