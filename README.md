# febu Assembly: the ledger

The febu Assembly's ledger of promises and facts about febu, the texts that go with it, and the script that
turns them into the Assembly's pages on https://febu-assembly.vercel.app (assembly, the ledger, four tests).

| File | What it is |
|---|---|
| `ledger.txt` | The ledger. Edit this one. It is served byte for byte, and its SHA-256 is the hash in rule 6. |
| `fact-6-steps.txt` | Fact 6 as four steps, each a link, with all 44 payments. |
| `tests.txt` | The four tests. Reading, not the experiment: served at `/tests.html`, not linked from the front page. |
| `process.md` | The whole process in one file: the ledger, the scripts, money, the 30-day clock and its stop rule, the decisions waiting. Adds no rule; where it and `ledger.txt` differ, the ledger wins. Shown as the "the process" tab (`process.html`, needs the `markdown` package, otherwise the committed page is kept while `process.md` is unchanged). |
| `claims.sql`, `api/claim.js`, `api/_claims.js`, `claims.py` | The one-time name claim: the table, the function, its pure part, the script that issues codes. Setup below. |
| `live.sql`, `api/entries.js`, `api/_record.js`, `live/` | The live record: the two tables (seconds and checks), the function, its pure rules, and `live/server.py`, its local twin that runs on one machine with SQLite. `live/live.js` and `live.css` are the ledger page's forms. Setup under "The live record" below. |
| `paid.md` | The shape for a member who wants to pay for scripts: their own promise, the cap, two tests of its own. Not linked from the site, not part of the vote. |
| `archive/` | Empty at the clean start of 2026-10-15. Each later change to `ledger.txt` puts the text before it here, word for word. Add to it; never edit or delete. |
| `timestamps/` | OpenTimestamps proofs that `ledger.txt` and the archive files existed by a Bitcoin block. None yet: stamp the clean-start text first (see "Records outside the group"). |
| `api/archive.js` | Asks the Internet Archive to save `ledger.txt` once a day. |
| `checks/` | Scripts that re-read facts 1 to 6, 8 and 9 from public sources, for anyone to run. |
| `build.py` | Write the pages from the texts. `test_build.py` tests the people page and how the build reads SEEN lines (rule 3). |
| `assets/` | The pages' stylesheets, and `claims.js`: tap to copy, hash checks, and the member flows below. Written by hand. `node test_claims.js` tests its reading of a pasted chat. |
| `assets/card.png`, `make_card.py` | The 1200x630 picture a chat shows when someone pastes a link (every page names it in its `og:image` tag). `make_card.py` draws it; it holds nothing that changes with the ledger, so redraw it only to change the look. |
| `febu-assembly.html`, `ledger.html`, `how.html`, `process.html`, `tests.html`, `people.html`, `weekly.html`, `write.html`, `assembly.ics` | Written by `build.py`. Don't edit them by hand. |


## One project

This repo is the whole of the Assembly: the pages, the ledger, the claim and record API, and the unofficial archive of imfebu.com (the "den"). It replaces two repos and two project names that were easy to confuse:

| Old name | What it was | Now |
|---|---|---|
| `febu-host` (private GitHub repo) | The den, the scripture reader, the members page, and a proxy to this repo | Folded in here on 2026-10-15; the repo is archived. Every current file is here byte for byte. Only superseded page renders, the dropped draw page and earlier den bundles exist solely in its history. |
| Vercel project `febu-assembly` | Deployed from `febu-host` | Deploys from this repo. https://febu-assembly.vercel.app is the front door. |
| Vercel project `febu-ledger` | This repo, under another project name | A second address for the same files, kept only until after the 2026-10-22 vote. `ledger.txt`'s own lines and the daily Internet Archive capture cite https://febu-ledger.vercel.app/ledger.txt, and changing the ledger's text restarts rule 7's seven days. After the vote: a dated CHANGED line moves the citation to https://febu-assembly.vercel.app/ledger.txt, `api/archive.js` captures that address too, the old project is deleted, and its routes in `vercel.json` and `test_routes.py` go with it. Nothing new points at it. |

| Path | What it is |
|---|---|
| `/` , `index.html`, `assets/index-*.js`, `assets/index-reconstructed.css`, `assets/shim.js`, `assets/community.json`, `assets/scripture.json` | The den: the 2026-08-14 imfebu front end, patched to talk to our Supabase. Its app routes (`/library/scripture` and the rest) fall back to `index.html`. See `DEN.md`. |
| `scripture.html` | Plain-text scripture reader. |
| `api/keepalive.js` | A daily read so the free Supabase project is not paused. |
| `test_routes.py` | Checks `vercel.json`: the Assembly's security headers sit on the Assembly's files only (the den needs inline styles and Supabase), `/` is the den here and the front page on the old domain, unknown paths reach the den. |

**One address.** Sign-in (the name claim, seconds and checks) and the den share https://febu-assembly.vercel.app, so they share browser storage: a script that runs in the den can read a member's token. What keeps one in from the other:

- Every path that is not an Assembly file gets a content-security policy (the first route in `vercel.json`): scripts from this address only, no inline script, no `javascript:` links, connections to this address and the one Supabase project only. A post that smuggles in a script, an event handler or a `javascript:` link does nothing. Checked in a browser on 2026-10-15: with the policy on, the den's home, library and community pages load with no violations, and an inline script and a `javascript:` link are both refused.
- The den's bundle puts raw HTML into the page in two places only, both react-tweet's rendering of a tweet's own text, and in one theme script the policy blocks. The count of 16 this file used to give was the string `dangerouslySetInnerHTML` appearing in React's own code. Posts and comments are drawn as text.
- Not covered: a bug in the bundle's own code that a post can steer into running, which the policy does not stop; and the token is still stored in the browser and never expires (KNOWN BUGS 6). If either worries you, the den goes, and nothing else changes.

`test_routes.py` checks both policies on every path. Environment variables (set in Vercel, never in the repo): `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `ASSEMBLY_SALT` (one value, kept), `ASSEMBLY_STRANGERS`, `CRON_SECRET`, all in the `febu-assembly` project, the first four for Production only. Until they are moved there from `febu-ledger`, `/api/claim` and `/api/entries` answer 503 on this address.

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

Every push to `main` redeploys the Vercel projects built from this repo (`febu-assembly`, and `febu-ledger` until it is retired). Vercel first runs `python3 build.py` (the
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
| `python checks/release.py --posted 90e674d3` | The release: the served `ledger.txt` against this checkout and git, the hash a post names (and which archived version it is, if not the served file), the headers, the Internet Archive's captures, and whether each timestamp proof is pending or in a block. CAN'T TELL when a read is incomplete | seconds |

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

**Three daily crons** (`crons` in `vercel.json`), none of which takes input or changes anything: `/api/archive` (below);
`/api/keepalive`, one read of the den's `site_stats` with the publishable key; and `/api/claim?name=Zurandol`, one read
of the claim table through the function. The last two exist so the free Supabase project is never idle long enough to
pause. On the den's address the claim read answers 503 ("not set up"), as it should.

**The Internet Archive, every day.** `api/archive.js` runs once a day (the `crons` entry in `vercel.json`; on
Vercel's free plan it fires some time between 04:00 and 05:00 UTC) and asks the Archive to save
https://febu-ledger.vercel.app/ledger.txt. Nobody has to do anything. Every copy, with its date and time:
https://web.archive.org/web/*/https://febu-ledger.vercel.app/ledger.txt. To hash a copy, put `id_` after its date
in the address, so you get the file as it was saved rather than the Archive's page around it. The Archive sends it
compressed, so let your tool unpack it:

```bash
curl -s --compressed https://web.archive.org/web/<YYYYMMDDhhmmss>id_/https://febu-ledger.vercel.app/ledger.txt | sha256sum
```

**OpenTimestamps.** `timestamps/` holds proofs that a file existed by the time of a Bitcoin block. A proof holds
the file's SHA-256 and nothing else, so it shows nothing about who made it. Each is named after what it proves: `timestamps/ledger-<first 8 characters of the SHA-256>.txt.ots` for a
version of `ledger.txt`, and `timestamps/<name>.ots` for `archive/<name>`. There are none yet; the first to
make is the clean-start `ledger.txt`.

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


## The one-time name claim

A name on the Member line belongs to whoever enters its invite code first on the front page; that browser then
holds a token, and the panel says "Claimed <date>, on this device". It marks a device, not a post: the chat, checked
by the weekly turn, still decides who posted what (KNOWN BUGS 6). Without the setup below the panel says claims are
not switched on and everything else works as before.

### Switching it on

Each step is Z's: they need the service key. Steps 1 to 3 were done on 2026-10-15 in the `febu-ledger` project; what is left is to set the same variables in `febu-assembly` (the one address). `python claims.py status` reads the live
endpoint, needs no key, and names the first step still missing.

Use a Supabase project of the Assembly's own (the free plan allows two), not febu-host's. The service key sits in the
build environment of a public repository, so whoever can push to `main` can read it, and on febu-host's project it
would open the community's posts and uploads too.

1. Create the project. In its SQL editor run `claims.sql` once: one table, row-level security on, no policies, and
   nothing granted to the public roles.
2. In the febu-assembly Vercel project set `SUPABASE_URL` (the project URL) and `SUPABASE_SERVICE_KEY` (the service role
   key: never the publishable one, never in this repository) for Production only, so a preview deployment never sees
   them. Redeploy. `python claims.py status` should now say "ON, no codes yet".
3. On your machine, with the same two variables in the shell for that one session, run `python claims.py issue`. It
   prints one message per member, with their code and their own link, once; only hashes are stored. DM each member
   their message. The codes are not written to a file.
4. `python claims.py list` shows who has claimed and how many wrong codes were tried. `python claims.py reissue Laura`
   clears a claim and prints a new message, for a lost device.
5. Adding a member: change the Member line by rule 7, rebuild, and run `python claims.py issue` again. It prints a
   message only for a name with no row.

What the claim protects and what it does not:
- It marks a device. A lost or shared device holds the name until someone reissues it, and only Z can (KNOWN BUGS 6).
- A code is 16 characters of 31, about 79 bits, and the right code is never turned away. Five wrong codes in a row
  turn wrong guesses away for ten minutes, so nobody can lock a name by guessing at it.
- Anyone who can push to `main` can read the key at build time, and whoever controls `api/claim.js` can mint any
  member's identity: sign-in trust is as strong as write access to this repository. Add a collaborator only if you
  would give them the key, keep the variables to the Production environment, and if you can, protect `main` (require a
  review; CODEOWNERS on `api/`, `build.py`, `vercel.json`, `claims.py` and `claims.sql`). That slows the browser-edit
  flow in "A second editor", which is the trade.
- The den's scripts share this address's browser storage with the token; see "One address" for what stands between them.
  The messages `claims.py` prints link https://febu-assembly.vercel.app/febu-assembly.html.
- Losing the claims table costs seven reissued codes and nothing else. The record's own durable copies are the exported
  SEEN lines in `ledger.txt`, the git history, the daily Internet Archive capture and the Bitcoin timestamps.
- The site sends a strict content-security policy (`vercel.json`): its own scripts and styles only, no connections
  elsewhere, no framing. The token lives in the browser, so that policy is what protects it from a page script.
- A daily request to `/api/claim` (`vercel.json`) keeps a free Supabase project from pausing after a week.

`node test_api.js` runs the endpoint against a fake database.

### The live record

Members second an entry or post a check from the ledger page; a stranger may post a check. Seconds and checks go to two
tables (`live.sql`) through `api/entries.js`; the entries, their writers, due dates and the Member line are read from
`ledger.txt` as deployed, so nothing is copied and a new entry is there as soon as the site is. The rules (rules 3 and
4, a second before any check, the limits below) are `api/_record.js`, a pure file with no database in it.
`node test_entries.js` runs them and the function against a fake database; with python on the path it also checks that
this reader and `build.py`'s read `ledger.txt` and the banned notation the same way.

**Who is posting.** A member sends the token the name claim left on the device (`Authorization: Bearer`); the name
comes from `assembly_claims`, not from what was typed. A token the table does not know is a 401. It is never treated as a
stranger, and neither is a claim table that does not answer (502).

**The stranger lane. Off for now.** The record is an internal tool for the seven members until the abuse question is
settled: a stranger's words would be kept for good (rule 2) and nobody could remove them. Do not set `ASSEMBLY_STRANGERS`
in either Vercel project. With `ASSEMBLY_STRANGERS=1` and `ASSEMBLY_SALT` both set, a post with no `Authorization` header
may be a check, never a second, under a name that is not a member's and holds none as a word (plain ASCII, however spaced or capitalised it is
written). Rule 3 already says what that is worth: two people, member or not, posting the other result reopen a closed
entry or split an open one, and only two members close one. The row keeps a salted hash of the poster's address
(`x-forwarded-for`), never shows it, and takes one check per source per entry, five per source per day and six from
outside the seven per entry. Without the salt the lane stays off: an unsalted hash of an address can be undone by trying
every address. A person with several addresses gets past all of this; the ledger lists that under RISKS WE ACCEPT.

**Rule 2.** The two tables refuse UPDATE and DELETE with triggers (`live.sql`), so a result stays once written. That
includes "[removed]" for personal information, until someone needs it. Two posts at the same moment cannot both land on
one place: each check takes the next place number, the table takes each place once, and the second poster is told to
post again.

Setup, after the claim's own (same project, same two environment variables); every step is Z's:

1. In the same Supabase project, run `live.sql` once in the SQL editor: two tables, row-level security on, no policies,
   nothing granted to the public roles, and the two triggers.
2. Nothing else switches the record on: with the table there and `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` set (the
   claim's), `GET /api/entries` answers. Members can post as soon as they have claimed a name.
3. Leave this step undone for now (see "The stranger lane"). To let strangers post checks too, set both `ASSEMBLY_STRANGERS` to `1` and `ASSEMBLY_SALT` to a long random string
   (for example `python -c "import secrets; print(secrets.token_hex(24))"`; never in this repository) for Production
   only, and redeploy. Change or unset either to close the lane. Changing the salt makes earlier sources unrelated to
   later ones, which resets the per-day limit and nothing else.
4. The ledger page does not load `live/live.js` and `live/live.css` yet. Add the two tags the local server adds (`LIVE_HEAD`
   in `live/server.py`) to the page `build.py` writes, rebuild, and push. Until then the function is reachable and nothing
   on the site calls it.

Not done on the site: the export of the record's SECONDED and SEEN lines into `ledger.txt` (`python live/server.py
export`) reads the local SQLite file, not these tables. Until it is ported, a check posted on the site shows on the ledger
page and in `GET /api/entries`, and goes into `ledger.txt` by hand, the way the weekly turn adds a SEEN line.

`live/server.py` is the same record on one machine, with SQLite and no sign-in unless `ASSEMBLY_CLAIMS_URL` is set to the
site's `/api/claim` (then it also takes `ASSEMBLY_STRANGERS=1`, with a salt kept in `live/salt`, not in git); `python
live/test_live.py` tests it. The two keep the same rules; change one and change the other.
