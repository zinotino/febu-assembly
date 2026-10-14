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
| `timestamps/` | OpenTimestamps proofs that `ledger.txt` and the archive files existed by a Bitcoin block. |
| `api/archive.js` | Asks the Internet Archive to save `ledger.txt` once a day. |
| `checks/` | Scripts that re-read facts 2, 5 and 6 from public sources, for anyone to run. |
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

Next to every solscan.io link on the ledger page, the build adds the same record on explorer.solana.com, so no
check rests on one explorer (known bug 4). `ledger.txt` itself keeps only the links it has.

An edit made on github.com changes `ledger.txt` but not the pages. Until someone runs the build and pushes,
the ledger page shows the old text, and its hash check reports a different SHA-256.

## Publishing

Every push to `main` redeploys the Vercel project `febu-ledger`. There is no build step: Vercel serves the
files as committed. https://febu-assembly.vercel.app forwards the Assembly's addresses to that project
(`febu-host`'s `vercel.json`), so the links stay the same and `ledger.txt` arrives byte for byte. After a
push, download https://febu-assembly.vercel.app/ledger.txt and check that its SHA-256 is the one the build
printed.

## Rerunnable checks

`checks/` re-reads the facts a machine can read, with Python 3 and nothing else: no packages, no account, no key.
Each takes its addresses and transactions from `ledger.txt` and `fact-6-steps.txt`, so it tests what the ledger
says, and prints what it saw. None of them posts anything or gives a verdict: a person reads the output, compares
it with the entry's WRONG IF lines, and posts (HOW TO CHECK AN ENTRY). Say in your post that you ran a script.

| Script | Reads | Takes |
|---|---|---|
| `python checks/fact2.py` | Fact 2: the creator wallet's $FEBU before and after the sale the ledger links, and whether it holds any $FEBU now | seconds |
| `python checks/fact5.py` | Fact 5: on how many of pages 1-24 and 25-164 each of the eight words appears, in the scripture copy behind the fact's link | seconds |
| `python checks/fact6.py` | Fact 6: adds up the 44 rows, then re-reads every row's transaction and step 1's trade | a minute or two |

- The chain checks ask the public node https://api.mainnet-beta.solana.com. To ask another, your own for example,
  set `SOLANA_RPC` (`SOLANA_RPC=http://127.0.0.1:8899 python checks/fact6.py`). The public node turns away fast
  callers; the scripts wait and retry.
- `fact5.py` takes a copy of your own too, in the same form, which is how KNOWN BUGS 3 gets fixed:
  `python checks/fact5.py my-copy.json`. It prints the copy's SHA-256, so two people can tell whether they counted
  the same copy.
- `fact6.py` does not test "has received nothing from it since". Thousands of trades have touched the fee account
  since 2026-09-14, too many for a public node; step 2's link shows its payments out.
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

Z adds them on GitHub: Settings, Collaborators, Add people, role Write. They then clone, edit, build and push
the same way Z does. On Vercel's free plan a collaborator's push deploys only because this repository is
public. Anyone else can propose a change as a pull request, or copy the whole thing and run it their own way
(rule 7).

## Checking the history (rule 2)

`git log -p -- ledger.txt` shows every change to the ledger since it moved here on 2026-10-14. Earlier
versions are in `archive/`, with the SHA-256 the ledger cites for each one.
