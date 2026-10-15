# The Assembly: the whole process in one place (2026-10-15)

Start here. This file says how the parts fit: the ledger, the scripts that check it, money, and the 30 days that decide
whether to keep it. It adds no rule. The rules are `ledger.txt` (https://febu-ledger.vercel.app/ledger.txt), and where
this file and the ledger differ, the ledger wins. Anything marked **proposed** counts only after a rule 7 vote. Three
things are up for that vote now, all by 2026-10-22 (section 10).

## 0. The process in five lines

1. Anyone writes a claim as an entry: what it says, a link anyone can open, and what would prove it wrong.
2. Two members who did not write it open the link and post what they saw. The same result twice closes it.
3. Each week one member copies the week's results into the file and posts its hash somewhere the group does not control.
4. Nobody is paid to check and the group holds no money. A promise may name a $FEBU bond, burned by its writer if they
   break it.
5. The whole thing runs as a 30-day test on the seven members, with the result that would end it written down first.

Everything below is detail on one of those five lines, or an add-on that changes none of them.

## 1. Why it exists

febu ran every step of a pipeline except the check. 164 pages, numbered without a gap, so nothing was ever refused; the
one checker in its story, UBEF, was "removed", in the first person. Then the writing stopped (09-19) and the bag was sold
(09-22).

The ledger is that missing step and nothing more. What anyone says is worth nothing until it meets a record nobody in
the group controls: a transaction, an archived page, a dated file. All the weight sits at that edge, so every part of
the process exists to put a claim in front of a public record and keep the check honest.

Why anyone takes part, with nobody paid: a writer gets a fact anyone can cite without trusting them, once two others
close it. A promiser gets believed: a date and a bond count for more than a chat message. A checker gets something to
rely on without taking anyone's word. If that is not enough for seven people, PROMISE 7 breaks and the minutes say what
pay would cost.

## 2. The shape: one core, two add-ons, one clock

| Part | What it is | State | What turns it on |
|---|---|---|---|
| **Core: the ledger** | Entries, checks, promises, bonds, the weekly turn, rule changes, known bugs (rules 1-8) | Version 3, proposed, live at febu-ledger.vercel.app. Nothing checked yet | Rule 7: 7 days, four yeses, at most one "object". Vote by 2026-10-22 |
| **Add-on A: scripts** | A short program that reads a claim's record and says which WRONG IF lines tripped | Runs on facts 1-6, 8 and 9 (`checks/`, beside the ledger) | Helps anyone today. Counts as a check only after the Saw line (section 5) |
| **Add-on B: a member's money** | A member who wants to pay for work does it by their own promise, with a bond | Witness has spoken of funding experiments; no promise posted. Shape drafted | Only if a member posts that promise. Changes nothing in the core |
| **The clock** | Five steps from now to a dated keep, change or stop | Steps 1 and 2 done | Section 7 |

The add-ons sit on the core. Neither can change a rule, and the core runs the same with both off. The site's pages are
built from `ledger.txt` and add nothing.

## 3. The core: an entry's life

### Writing it

```
FACT n. (who, date)                     PROMISE n. (who, date)
  SAYS      one sentence                  WILL       what they will do
  LINK      links anyone can open         BY         the date
  WRONG IF  what would show it false      KNOWN BY   the link anyone will open then
  SEEN      results, as they come         IF BROKEN  the bond in $FEBU, or none
                                          SEEN       results, on or after the date
```

- Every part of SAYS needs a WRONG IF line that would catch it. If SAYS claims more, cut SAYS.
- Every link opens for anyone, without asking the person who posted it.
- Nobody approves an entry or judges whether it is worth having. One nobody needs goes unchecked and stays OPEN.
- A forecast of something nobody here does ("the sun will rise tomorrow") is neither. It goes in the chat.
- Anything the group tells outsiders about what will happen goes in first, as a promise.
- **A habit, not yet a rule: a WRONG IF line must not be something a stranger can make true.** "Holds none now" and
  "nothing out after 09-14" can be tripped by anyone, with a dust transfer or the permissionless fee claim. End-date
  them: "by the end of 2026-10-14". The scripts found this; facts 2, 6 and 8 carry CHANGED lines that fix it.

### Before anyone checks

- The writer may correct SAYS or WRONG IF with a dated CHANGED line while SEEN says "nobody yet". Never after.
- **Proposed for round two:** a second. Before anyone checks, someone other than the writer says they want it checked
  and that its WRONG IF lines test what it says. If adopted, it stays optional: a second that every entry must wait for
  is an approval, and nobody approves an entry.

### Checking it

1. Open the link. You need no account.
2. Look for what the entry says is there before reading anyone else's post about it.
3. Post: the entry number, what you saw, which WRONG IF lines you tested, **one thing on the page nobody has written
   yet**, and your result. A post that only says HOLDS counts for nothing. Add the minutes it took: not a rule, but E1
   and any pay floor are measured from them.
4. Your post goes under the entry as a SEEN line.

Nobody checks their own entry. An entry in the group's name has a writer: the member who proposed it. An AI may help
you look; it never posts a result.

### How it ends

```
OPEN ──two members, same result──▶ HOLDS / DOESN'T HOLD   (a fact)
  ▲                                KEPT / BROKEN          (a promise)
  │                                       │
  └──two people, member or not, post ─────┘   reopened; it closes again the same way,
     the same different result                counting only posts made after it reopened

one person disagrees       ──▶  a NOTE under the entry; the entry stays as it was
30 days without closing    ──▶  CAN'T TELL
```

"The same result" means the same word on the same WRONG IF lines. Nothing is removed. A wrong fact stays, marked
DOESN'T HOLD, under its writer's name: that is a fact's whole cost. A fact never carries a bond.

### Promises

- A promise can be withdrawn up to 7 days before its date. Withdrawn later, it counts as BROKEN.
- The bond is optional. The promiser picks the amount in $FEBU, with no minimum, and a reader weighs the promise by it.
- **On BROKEN:** within 7 days the promiser sends the bond to the incinerator or burns it, and the transaction is the
  link. It is burned, not paid to the person promised, who would then have a reason to want BROKEN. Unpaid, the entry
  says UNPAID. Whoever owes a bond posts no new promise until it is paid. No contract holds bonds in advance, so that
  is all the enforcement there is.
- A promise to pay names the amount, what it is paid in, and the date. The payment itself is a fact.

## 4. The people and the record around the entries

### Who can do what

| Who | Can | Cannot |
|---|---|---|
| Anyone, no account | Read everything, run any script, add an entry, reopen an entry together with a second person | Close an entry, vote |
| A member: CrypticK, Crypto Fish, Ksizzle, Laura, Merc, WitnesstoFebu, Zurandol | All of the above; close an entry with another member; vote under rule 7; take the weekly turn | Check their own entry |
| The writer | Correct the entry with a CHANGED line until the first check | Check or close it |
| An AI | Help a person find things on a page; draft a script | Post a result |

A member silent in the chat for 90 days stops counting for rules 3, 6 and 7 until they post again. Witness is one of
the seven, with one vote: not a gate, and nothing waits on Witness. A live record page, where results would be posted
straight into the ledger, is a prototype and not public. Before anyone else reaches it, it needs sign-in limited to the
seven, because a typed name lets one person act as seven.

### The weekly turn (rule 6)

Each week the next member in the list order starts from the file whose hash was last posted, checks both ways (every
result posted in the chat that week is in the file; every SEEN line in the file has its chat post), adds what is
missing, and posts the new file's SHA-256 somewhere the group does not control. A turn not done by the end of its week
passes on. The ledger is whichever copy matches the last posted hash, wherever it is served.

### The outside record

Four things nobody in the group controls: the GitHub history, the hash posted outside the chat, a daily Internet
Archive capture, and an OpenTimestamps proof in a Bitcoin block. None of them stops an edit. Together they make every
edit visible, with a date nobody in the group set. Bitcoin is used for that stamp and nothing else.

### Rules and bugs (rules 7 and 8)

- A rule changes, and anything is done in the group's name, only after 7 days in the chat, four yeses from active
  members (every active member, if fewer than five are active) and at most one "object". The old wording is archived
  with its hash first.
- An objection says what would change the objector's mind. A habit for now, proposed as a rule in round two.
- Anything only one person can do is a bug, listed under KNOWN BUGS with a fix-by date. Bugs 1 to 3 are due 2026-11-14;
  4 is fixed on the site; 5 has a proposed close (section 6).
- Anyone may copy the file and run it their own way.

## 5. Add-on A: scripts

A script does the reading for a claim a public record settles. Writing one is work; running one is one command. That
gap is the whole reason to have them.

**Where they fit.** Five of the nine entries settle this way (1, 2, 6, 8, 9); fact 3 half; facts 4 and 5 run, but on
Z's copy of the scripture (KNOWN BUGS 3); PROMISE 7 is people. The entries were picked because they could be checked,
so five of nine is a ceiling, not an average.

**What makes a script signable:**

1. It reads the addresses from the ledger's own text, not from values typed into it.
2. It opens with an `ASSUMES` block in plain words, one line per assumption.
3. It is tried on controls first: one copy of the real record per WRONG IF line, each with one thing changed, each of
   which it must call wrong. Anyone can make these on the spot, and the script's writer cannot see them in advance.
4. Its output says which WRONG IF lines tripped.

The person signs the script, its ASSUMES block and the controls' output. A script without ASSUMES is not signable.
Running catches loud failures; only a control catches a wrong assumption, which is why ASSUMES comes first.

**What running them taught:**

- Refuting is cheap: one witness does it. Confirming that nothing happened is expensive unless the flow has a quiet
  end. Fact 8 read 3 transactions where the obvious way needed 5,226.
- A script reads what is written, not what was meant. Fact 8's "at any time on 09-22" was false as worded; 00:00 UTC
  was meant.
- The fee claim is permissionless, and a second call anyone can send skips the account fact 8 reads. Fact 8 needs both
  reads, `resolve.py fact8` and `resolve.py door2`.
- **Never send the fee claim to see what happens.** It pays the dev wallet and makes a WRONG IF line true.

**What it needs from the rules:** one line, **proposed** under rule 7, in WORDS USED HERE:

> Saw: you opened the link yourself, or you ran the entry's script yourself and opened one link by hand. An AI may
> help you find something on the page or write the script. It never posts a result.

Without it, scripts still help people look, but a script run cannot close an entry. With it, two closers may run the
same script, and then its mistakes are made twice. What keeps them two checks is the link each opens by hand and the
one new thing each names; E3 (section 7) tests whether that is enough.

Scripts live in `checks/` in the ledger's repository, https://github.com/zinotino/febu-assembly/tree/main/checks. They
rest on one free node that keeps history (api.mainnet-beta.solana.com); until there is a second, the explorer link
opened by hand is the second source.

## 6. Money: all of it

### In the core

- **The group holds nothing.** No pool, no vault, no treasury, no new token. Money moves wallet to wallet, as promises
  kept.
- **The only money in the core is bonds**, burned by whoever broke the promise.
- **No price.** No entry and no post in the group's name states or implies a price for $FEBU, "demand" and "supply"
  included.
- **$FEBU's catch (KNOWN BUGS 5).** Every $FEBU trade pays a fee to the wallet that created it and sold out, including
  a buy made to post a bond. Any post asking people to trade $FEBU says where the fee goes. Proposed close: the group
  does not apply to take over the fee (pump.fun's own multisig runs takeovers, fact 9). Decided when version 3 is
  adopted.

### The dev wallet, ApWpkd8

The subject, never a purse.

- **The subject.** Every money claim febu made is a claim about it. It is also febu's last unforgeable identity: a
  signature from it over an entry's hash would be the one answer from febu a stranger can verify. That invitation can
  stand; nothing is sent to the wallet, not even a message.
- **Not a purse.** Nobody claims its fee: that would make the group a treasury and febu's heir.
- **Not a recipient.** A dust transfer can trip a WRONG IF line; fact 2's could, before its fix.
- **Not a counterparty.** Nothing pays out on what it does next, because whoever can move it would win. Anyone who can
  move it says so in one dated line.

### Add-on B: a member pays for work

Exists only if a member offers money. The group still pays nobody.

- The offer is that member's own **PROMISE 10**, with a bond: WILL pay X $FEBU for each script that passes its controls
  and that two other members reproduce. Terms met and not paid is BROKEN, and the bond burns.
- **Pay goes to scripts others reproduced, never to a verdict.** The funder picks what is looked at, never what is found.
- **Admissible only if** a record settles it and no WRONG IF line can be made true by a stranger for less than the pay.
  Otherwise the pay buys the event.
- **Capped.** The funder states a total F and pays in rounds of K scripts, each round half the last, so the total never
  passes F. It stops at a floor tied to the measured minutes per check instead of decaying below it.
- **Guardrails.** Every bounty is public for 7 days first; anyone may post a competing one; no single spec takes more
  than a third of F.
- **Not covered:** creative work (a book, a video). No record settles whether it is good, so it would need its own track.
- **The funder answers four questions first:** scope; money (PROMISE 10, with a bond); subjects (up to three things a
  record settles); and the stop rule, written before anything runs. E4 and E5 (section 7) are a starting point for it.

## 7. The clock: from now to a decision

| Step | Who decides | Done when | Stops if |
|---|---|---|---|
| 1. Scripts run on every entry a script can settle | Z | Done: everything holds except fact 8's third line, false as worded. Runs, not checks | — |
| 2. Z fixes facts 2, 6 and 8, fills the three holes, and posts | Z | Done: CHANGED lines and the three holes are in the ledger as served | — |
| 3. The vote week, to 2026-10-22 | The members; the six who did not write the entries check | Facts 3, 8 and 9 checked, with minutes; version 3, the Saw line and the stop rule have had their 7 days | Version 3 does not pass: rewrite it |
| 4. Thirty days after adoption, unpaid | People, not the simulation | E0 to E3 each have a measured number | E1 or E2 fails: the script track stops |
| 5. The stop rule decides | The members | A dated ledger line: keep, change or stop | This step is the stop |

**The tests, each with its failing number fixed before it runs:**

| Test | Question | Cost | Counts against it if | Then |
|---|---|---|---|---|
| E0 = **PROMISE 7** | Do seven people check, unpaid? | Nothing | Fewer than three entries closed in 30 days, or Z wrote every one | BROKEN: rewrite the ledger or stop |
| E1 | Is writing a script much harder than reproducing one? | Nothing; volunteers are timed | Reproducing takes over a fifth of the writing time | Scripts stay helpers (the Saw line's script half lapses); add-on B never opens; E3 to E5 do not run |
| E2 | Do one-change copies catch lazy scripts? | Nothing; for each script, make its lazy versions: one that always says HOLDS, and one per WRONG IF line with that line left out | Any lazy version gets every copy for its entry right | Same as E1 |
| E3 | Do AI-drafted scripts share a blind spot? | Nothing; three models each draft a script for every entry that has one (five today), from the entry text alone. Runs only if the Saw line passed | On any entry, all three drafts say HOLDS on the same one-change copy | Two script runs no longer close an entry: one of the two closers opens every link by hand |
| E4 | Does pay change how often scripts get reproduced? | Add-on B only | 1x and 3x pay give the same rate | Stop paying |
| E5 | Once pay stops, does anyone post a bounty? | Add-on B only | None in 30 days | No market. Zero strangers is a result too |

The members vote on E0 to E3 with version 3, so the table is in force when the 30 days start. Adopting it adopts its
last column: when a test fails, that line applies with no second vote, so a failed test cannot be argued away
afterwards. E4 and E5 belong to add-on B; a funder writes them into their own promise. Every threshold comes from a
simulation built on guesses, which is why they are tests.

E3's remedy is the old way of checking. A miss all three drafts share is caught here by a copy, but it predicts the
misses no copy covers, and two closers whose scripts share one would close a false fact. A person reading ASSUMES might
share the miss and leaves no record; opening every link by hand leaves the one new thing on the page.

## 8. Lines that never move

- Nothing is removed. Every change is a new dated line. Only personal information may become "[removed]".
- Nobody checks their own entry.
- An AI never posts a result.
- No treasury, no new token, no price.
- No totals, no rankings, no scores. What stands under a name is what happened, entry by entry.
- Nothing is sent to the dev wallet, its fee is not claimed, and no fee claim is sent as a test.
- Nobody tries to identify private individuals. Chain tracing stops at the payee.
- Full wallet addresses appear only in `ledger.txt` and `ledger.html`.

## 9. What it cannot do

- Hold a claim with no public record. Three of febu's problems (repeating history, machines that imitate, human
  arrogance) have none yet: that is the ledger's OPEN QUESTION.
- Settle what a link means. It settles what a link shows; interpretation stays in the chat.
- Tell one person from two names, or a real check from an AI-written one a person signed without looking, beyond the
  "one new thing" rule.
- Tell two runs of one script from two checks, beyond the link each closer opens by hand. E3 measures how much that
  matters.
- Beat two people who agree in advance. They can close a false fact, or hold an entry open, until someone else looks.
- Keep out easy entries. One anyone could get right without looking can be posted and closed; it counts toward PROMISE 7
  and shows nothing, and it stays under its writer's name for anyone to read. The full list is RISKS WE ACCEPT.
- Make anyone look, or pay anyone to. If the seven do not check, PROMISE 7 breaks, and that is the honest result.
- Stop an edit. It makes one visible.
- Escape the multipolar trap. Scripts make one kind of cheating cost more, and that is all.

## 10. Decisions waiting, in order

Done before this was posted, by Z: the scripts re-run (section 7, step 1); facts 2, 6 and 8 fixed by CHANGED lines; the
three holes filled (section 11).

| # | Decision | Who | How |
|---|---|---|---|
| 1 | Adopt version 3 as served, with the KNOWN BUGS 5 close | Members | Rule 7, by 2026-10-22 |
| 2 | The Saw line for scripts (section 5) | Members | Rule 7, the same week |
| 3 | The stop rule: E0 to E3 and what each failure does (section 7) | Members | Rule 7, the same week, so it holds from the first of the 30 days |
| 4 | Round two: a dated WRONG line for anything later shown wrong; objections say what would change one's mind; a rule for leaving; OUT OF SCOPE and DEPENDS ON lines; WRONG IF lines a stranger cannot make true; the optional second; sign-in for the live record | Members | Rule 7, after round one |
| 5 | Whether a stranger can ever close an entry (today: can reopen with a second person, cannot close) | Members | Open |
| 6 | The OPEN QUESTION: a record for each of the three problems, or "none" | Anyone | Chat, then entries |
| 7 | KNOWN BUGS 1 to 3 | Each member | By 2026-11-14 |
| 8 | Add-on B, with its own stop rule | A member who wants to pay | Only if offered |

The vote closes 2026-10-22, not 10-21: the three holes changed rule text, and rule 7 counts 7 days from the post that
shows the text. A "yes" already written stands unless its writer takes it back.

## 11. What became of what you have seen

| What you have seen | What became of it |
|---|---|
| The reward-layer proposal in the V3 post: pay for checking, a person and an AI as one unit, planted false claims (Ksizzle's shape) | Pay for checking is dropped: every paying design in the simulation needed money held somewhere, and rule 5 forbids that. The pair stays as the Saw definition: an AI helps, a person posts. Planted claims became one-change copies, which test a script without putting a lie on a list people cite |
| V3's "no vault, no pay, no takeover" | Unchanged. The only money in the core is bonds, burned. A member who wants to pay does it by their own promise (add-on B) |
| Witness's four questions to the group (bond size, burning, why take part, the sun) | Answered in `how.txt`, and in the ledger's rule 1 and Bond |
| Witness's offer to fund experiments, and the halving | Add-on B. The halving is its cap. It pays for scripts others reproduced, never for a verdict, and nothing in the core waits on it. Its four questions are the funder's, not the group's |
| Version 3 as first served | Three holes filled before any check: an entry in the group's name has a writer (without one, nobody could close PROMISE 7); an unpaid bond shows UNPAID after 7 days; a weekly turn not done passes on. Also, WRONG IF may change by a CHANGED line until the first check and never after: the text said "never changed", while facts 1, 2 and 6 had already changed theirs before any check |
| The vote on version 3 by 2026-10-21 | By 2026-10-22, together with the Saw line and the stop rule (section 10) |
| Facts 2, 6 and 8 as first written | CHANGED before any check. Fact 8's third line was false as worded ("at any time on 09-22"); the others had lines a stranger could make true |
| PROMISE 7 (WHEN THIS HAS FAILED) | E0 in the stop rule: one test, one row |
| `tests.txt`: gains, losses, bailout, decision, and the founder test | Unchanged. It is how to judge the core, not a step in it. The founder test passes once a second member has done a weekly turn (KNOWN BUGS 1) |

The reasoning behind these lines is in Z's working papers: a design outline, a paper on paying for scripts, four
reviews, and two simulations built on guesses. They are not public. Where a line here rests on one, it says so, and
nothing here needs them to be read.
