# The Assembly's system, outlined before we build more (2026-10-14)

For Z. Written against ledger version 2.1 (febu-assembly/ledger.txt), the four tests (tests.txt), the reward
simulation (tools/exp_stance, P187 and P190), the chat with Witness and Ksizzle, and the eleven scripture
problems in Z's table. Plain language, no scores, as the ledger asks.

## 1. The short answer on Bitcoin

We are not leaning on Bitcoin's infrastructure. We were, and version 2 cut it.

What version 1 took from Bitcoin and version 2 dropped: the checker draw from a block hash, sealed verdicts,
the hash chain, planted false claims as "proof of work". All gone, and the ledger says why: a long rulebook
written by one person is power over the people who have not read it.

What is left that touches Bitcoin at all:

| Piece | What it does | What happens if it vanishes |
|---|---|---|
| OpenTimestamps proofs in timestamps/ | Shows a file existed by the time of a Bitcoin block | Nothing. The Internet Archive copies and the posted hash still work. |
| Daily Internet Archive save | A dated copy outside the group | Nothing at check time; only rule 6's "somewhere the group does not control" gets weaker. |
| tests.txt, "Bitcoin's three properties" | An analogy to measure the ledger against | It is a yardstick, not a dependency. |

Nothing in the ledger reads a block, waits for a block, or breaks when a node is down. A member checks an entry
with a browser and a chat message. That is the right amount of Bitcoin: a free stamp on a text file.

The heavier lean is in the talk, not the code. "Proof of truth", "the ledger as proof of work", "approach it the
way Satoshi approached money". Those phrases pull toward building a machine that works without trusting anyone.
The Assembly is the opposite kind of system, and should say so:

- Bitcoin removes names. Anyone can mine, nobody has to be known, and the rule pays in its own money.
- The ledger requires names. Seven members, each result under a name, nothing paid, and the only cost of a
  broken promise is that BROKEN stays under your name for good.

That is not a weakness to engineer away. It is the design. Bitcoin's machinery exists for strangers with money
at stake who will cheat if they can. The Assembly is seven named people whose reputations with each other are
the stake. Importing Bitcoin's defenses into a group that does not have Bitcoin's threat gives the version 1
rulebook back. Keep the four tests as the yardstick. Drop "proof of truth" as a goal; what we have is a list
of claims that either closed under rule 3 or did not.

## 2. The eleven problems against the system

The ledger can only hold a problem that has a record a stranger can open (its own OPEN QUESTION says this).
Here is each of febu's eleven problems, what in the system meets it, and what does not.

| # | Problem (pages) | What meets it | What does not |
|---|---|---|---|
| 1 | Corrupt leaders and false authority (18) | Nobody approves anything (WHAT THIS IS). Nobody checks their own entry (rule 3). Anything only one person can do is a listed bug with a date (rule 8). Rule changes wait 7 days (rule 7). | The file and the site are Z's (KNOWN BUGS 1). Until a second member can edit, the ledger has a leader. |
| 2 | Debt and financial illusion (17) | No pool, no treasury, no new token (rule 5). A promise to pay names amount, currency, date; the payment is a transaction link; nobody who owes may promise again. | Every $FEBU trade pays a fee to the wallet that sold out (KNOWN BUGS 5). This is the system's largest contradiction with the scripture, and it is the problem febu wrote about second most. |
| 3 | Repeating history and futile cycles (15) | Nothing is removed; every version is archived with its hash; failed predictions stay listed. The ledger remembers. | Remembering is not learning. No mechanism makes anyone read the archive. Febu's scripture had perfect memory too and repeated itself. |
| 4 | Human limits and arrogance (14) | WRONG IF is written before anyone checks and never changed. Z's five failed predictions are in the file. WHEN THIS HAS FAILED names the day we admit it. | Six facts, all by Z, none checked. The claim "this works" is itself unchecked. |
| 5 | War, diplomacy, broken agreements (14) | Promises have a date, a link anyone will open, and a stated loss. Withdrawn in the last 7 days counts as BROKEN. Anything told to outsiders goes in as a promise first. | The loss for a broken promise is a word under a name. Tests.txt already calls this weak. No promise exists yet. |
| 6 | Technological dependence and obsolescence (12) | ledger.txt is plain text, served byte for byte; anyone may copy it and run it their own way (rule 7). The checks in checks/ run without a key. | We depend on Vercel, GitHub, Supabase, solscan.io, the Internet Archive, and Z's machine. KNOWN BUGS 1 and 4 are this problem, named. |
| 7 | Digital illusion and machine imitation (9) | "An AI may help you find something on the page. It never posts a result." A person answers for every verdict. This is already Ksizzle's pair. | Nothing tells human from AI at sign-up. The ledger accepts this: it asks who answers, not what wrote. |
| 8 | Hidden systems and surveillance (9) | Every link opens for anyone without asking the poster (rule 1). The hash is posted outside the group (rule 6). Personal information is "[removed]" (rule 2). Chain tracing stops at the payee; never identify private individuals (Z's constraints). | The group chat is on a platform whose admin can delete messages (KNOWN BUGS 2). The weekly copy is the fix. |
| 9 | Hollow law and justice (9) | Eight rules on one screen. Old wording stays. No court: the link decides, and a disagreement ends in CAN'T TELL after 30 days (rule 4), not in a ruling. | A rule nobody applies is hollow. Zero entries have closed. |
| 10 | Misinformation and lost shared truth (4) | The core of the thing: SAYS, LINK, WRONG IF, SEEN. A result that only says HOLDS counts for nothing; you post what you saw. | Two members who agree in advance can close a false fact until someone looks (RISKS WE ACCEPT). |
| 11 | Environment and infrastructure neglect (3) | Nothing. | Out of scope, and the ledger should say so rather than stretch. |

What the table shows:

- The ledger is strongest on 1, 8, 9 and 10: authority, hiddenness, law, shared truth. Those are the problems a
  public checkable list is for.
- It is honest but weak on 2, 4 and 5: money, arrogance, agreements. Those need stakes, and rule 5 forbids the
  group from holding any. The simulation found the same thing from the other side: every paying design needed
  money held somewhere, and whoever holds it is test 4 (decision by one party) again.
- It does not touch 3, 6 or 11, and the OPEN QUESTION already asks the group to name a record for 3 and 7 or
  say there is none.

Witness's "multipolar trap" point stands against us as much as against Bitcoin. The ledger does not change
anyone's incentives. It makes defection visible and permanent among seven people. That is all it does, and
the write-up should claim no more.

## 3. The system in layers, built against proposed

| Layer | What it is | State |
|---|---|---|
| 0. The record | ledger.txt, archive/, SHA-256, Internet Archive copies, OpenTimestamps proofs | Built, live at febu-ledger.vercel.app. Local main has commits not pushed. |
| 1. Checking | Rule 3, SEEN lines, WRONG IF fixed before checking, the weekly two-way check (rule 6) | Written. Zero entries checked. This is the unproven part and the only part that matters. |
| 2. Promises and payment | WILL / BY / KNOWN BY / IF BROKEN, payment wallet to wallet in $FEBU | Written. No promise exists. |
| 3. Reward layer | Pay for checking, person+AI pair, planted claims | Proposed only (draft post). The simulation says it cannot hold under rule 5. Not built, and should not be. |
| The pages | febu-assembly.html, ledger.html, tests.html, findings.html, people.html, built by build.py from the texts | Built. They are a view of layer 0, nothing more. |
| febu-host | The 08-14 den copy with its own Supabase community, members.html, scripture reader | Separate instrument: an archive of febu's site. Not part of the Assembly's rules. |

The live surface on Vercel is layer 0 and its pages. That is the cheap, reversible part: text files and a
script that renders them. Publishing the pages is not adopting the rules; STATUS says proposed, and rule 7
says how it becomes real.

## 4. Did we jump the gun?

On the build, no. What exists is a text file, a renderer, three rerunnable checks and two free timestamp
services. Nothing is irreversible and nothing is in anyone's name but Z's.

On the design, partly. Three things are ahead of the evidence:

1. Six facts, all Z's, none closed. The ledger's own failure test (three closed entries within 30 days, at
   least one not by Z) has not started because nothing is adopted. Until one entry closes under rule 3, we do
   not know whether checking is a thing people do.
2. The reward layer is being designed before a single check has been timed. The draft post already says the
   right thing: pay nobody, run 30 days, measure minutes per check and how many entries have a record.
3. The chat is adding goals faster than the ledger can test them: proof of truth, a credibility ledger, a
   prediction ledger, person+AI pairs, a marketing budget. Two of those already exist inside version 2.1 and
   need no build: a prediction is a PROMISE entry (WILL, BY, KNOWN BY), and the pair is the Saw definition.

What to say to the group: the system is version 2.1 as written. The experiment is whether seven people will
check each other's links. Everything else waits for that answer.

## 5. What to do before publishing more

- Freeze the rules at 2.1. No reward layer, no new ledger, no new token. Say so in the chat so the design stops
  moving while people read it.
- Push the local commits that make checking cheaper (checks/, the second explorer links, the people page).
  Those lower the cost of layer 1, which is the only layer that is untested.
- Ask for one entry from someone other than Z. Witness's four ifs ("a working system, people taking part, a
  role for $FEBU, demand against supply") are three promises and a price; invite Witness to write the first
  three as PROMISE 7, 8, 9 with dates.
- Make the group's own claim an entry. PROMISE: "By 2026-11-14 three entries have closed under rule 3, at least
  one written by someone other than Z. KNOWN BY: ledger.txt. IF BROKEN: we rewrite this or stop." That is
  WHEN THIS HAS FAILED, written so it can come back false and be checked like anything else.
- Decide KNOWN BUGS 5 before any promise to pay in $FEBU, because every such payment sends a fee to the wallet
  in facts 2 and 6. Problem 2 in the table is febu's second-biggest theme and this is where the system
  contradicts it.
- Answer the OPEN QUESTION in the chat: name a public record for repeating history, machine imitation and
  human arrogance, or write "none" under each. Problems 6 and 11 can be added to that list.

## 6. $FEBU as the paying system (added the same day, after Z's question)

The purse. The "large purse" is febu's, not ours. The creator wallet took 2,939 SOL of fees and sold every
$FEBU it had. The Assembly has no key to it and never will. What the Assembly could have is the fee stream
going forward: every $FEBU trade pays a fee, and pump.fun's community-takeover form can redirect that fee to
a new wallet. That stream is the one piece of money that arrives by rule, with nobody deciding to send it,
which is the Bitcoin property tests.txt marked NO. It is small now (July 2,634 SOL, August 268, September 37,
about 11 SOL unclaimed) and it only grows if people trade.

Where the money would come from, in order of how real it is:
1. Members' own $FEBU, paid wallet to wallet (rule 5 as written). Real today.
2. Witness's marketing budget. Real if Witness writes it as a promise with an amount and a date.
3. The redirected fee stream. Real only after the group applies in its own name (rule 7) and pump.fun agrees.
4. Price going up. Not a source. Nobody can promise a price, and the ledger must not imply one.

Who holds it. Source 3 needs a wallet, and a wallet held by one person is rule 8's bug. The plain fix is a
multisig (Squads on Solana) that pays only when four of seven members sign. Four of seven is already rule 7's
number. Every payment out of it is a promise first and a fact after, with the transaction as the link.

What to pay for. The simulation (P187, P190) says: do not pay per contribution, it gets farmed; pay a flat
amount for a check that posts what the checker saw, and make a wrong check cost something. The fee stream
is the "outside money" every holding design needed. The loss side still needs people to put $FEBU at risk,
and that is a rule change the group has to want.

Can wallets be funded for contributions? Technically, yes, in one transaction each. The hard part was never
the transfer. It is who decides a contribution was worth paying, which is test 4 (decision by one party)
unless the deciding is rule 3's two checks plus four signatures.

The issues, plainly:
- The fee stream may be close to nothing. September paid 37 SOL and the engines stopped. Measure it before
  anyone plans around it.
- Paying for contributions recreates febu's job #004: an insider deciding who gets paid. Pay for checks, by
  rule, or do not pay.
- Price talk turns a checking group into an investment pitch. Keep Witness's fourth "if" out of every promise.
- The takeover application is done in the group's name and may be refused. Write it as a promise with a date
  so a refusal is a recorded outcome, not a quiet failure.
- Four-of-seven signing is slow. That is the point, but the first time a payment waits a week people will
  ask for a faster path, and the faster path is one person with a key.
- Tax and identity are each member's own. The ledger records transactions; it does not advise.

The order to build it:
1. Thirty days unpaid, as the draft post says. Time the checks, count the closed entries.
2. Decide KNOWN BUGS 5 by rule 7: apply for the fee, or write that we will not.
3. If the fee comes, a Squads multisig, four of seven, as the receiving wallet. Its address goes on the ledger
   page and nowhere else.
4. First payments: flat, small, for closed checks only, each one a promise entry before and a fact entry
   after.
5. Rerun the simulation with the real numbers from step 1 before changing the amounts.

## 7. AI checkers as a network, and the CTO (added after Z's third question)

Nodes, not miners. Bitcoin has two kinds of participant. Miners do expensive work that is cheap to verify.
Full nodes verify everything and are paid nothing; people run them because they want to trust nobody. An AI
check is the reverse of mining: cheap to produce, hard to verify, and two models can agree and both be wrong.
The simulation measured this: a 10% shared blind spot tripled the false claims accepted, and drawing models by
lot did no better than everyone using one model. So compute is not the scarce thing here. A person who opened
the link and answers for the result is. The ledger already puts the AI in the right seat: it reads the 164
pages or the 44 rows; the person signs.

What "contributing compute" means honestly: running the checks. checks/fact2.py, fact5.py and fact6.py
re-derive three facts from public sources with no key. Anyone who runs one on their own machine is a full node.
A local model fits the same way: it reads the page text so the check is cheaper, and its output goes nowhere
except in front of the person. The release shape is one script per fact, and a SEEN line may say "ran
checks/factN.py, got X". That is the whole architecture, and it is already half built.

What not to build: a network of models that post results. That is febu's own machine, validation words with
no validator, rebuilt by us. The −1 map found zero validator columns on every febu surface; an AI checker
network would be one more surface emitting "verified" as content. Rule: an AI never posts a result. Keep it.

Where proof of work would matter: if the group opens to strangers. Names stop fakes among seven people. Among
strangers, compute does not (one person, forty AIs, the simulation's +4.75 a round); only something at risk
does. That is a later problem and a rule change.

The CTO. Yes, it is the one path to money that arrives by rule. But "route the fees to the protocol" has no
protocol to route to. There is a text file, seven people, and a wallet somebody holds. An on-chain program
that pays "when two members post SEEN" cannot see the chat; it would need a person to tell it, and that
person is test 4 again. The honest version is the four-of-seven multisig in section 6, with every payment a
promise before and a fact after.

Before applying, the group should know two things:
1. The size of the stream. One link, fact 6's fee account, tells whether anything has arrived since 09-22. If
   it is a trickle, the CTO still fixes KNOWN BUGS 5 (every trade stops paying the wallet that sold), which
   answers test 1 on its own.
2. What it makes the group. The day the Assembly receives febu's creator fee, it stops being a group checking
   febu and becomes febu's heir. Scripture problem 1 is false authority; inheriting the fee is the shortest
   way to become one. That is a rule 7 decision, posted for 7 days, and the post should say it plainly.

Order: measure the stream; post the question of inheritance; if yes, apply as a promise with a date; set up
the multisig only when pump.fun answers.

## 8. The fee structure, drawn (added after Z's fourth question)

What pump.fun actually does (its docs and its 2025-07-18 announcement, read 2026-10-14):
- The creator fee is a cut of every trade, paid in SOL, never in the coin.
- It accrues to a fee account and is claimed by whoever holds the fee seat. Fees never expire. Fact 6's 44
  payments are those claims.
- A CTO is a form. pump.fun decides on its own, by email, and says it refuses when there is any reasonable
  dispute about who deserves the fee.
- After a takeover the new admin can split the fee across up to ten wallets by percentage.

The architecture, four boxes and three arrows:

    traders ──(fee, in SOL)──> creator vault ──(claim, anyone may trigger)──> Squads vault ──(promise, then fact)──> a member
                                    ^
                          pump.fun's CTO sets the creator here

| Box | What it is | Who controls it |
|---|---|---|
| Creator vault | A PumpSwap account derived from the creator's address, where the fee accrues (fact 6's BGa8 account is its WSOL account) | pump.fun's program; pump.fun's own key changes the creator |
| Squads vault | A 4-of-7 multisig; the seven members' Phantom wallets are the signers | Four members, any four |
| The claim | A permissionless instruction (collect_coin_creator_fee) that moves the accrued SOL to the creator. Nobody signs; anyone may send it. | Nobody |
| A payment | A vault transaction to one member's wallet | Four signatures, and a PROMISE entry before it, a FACT entry with the transaction link after |

(Corrected after the 10-14 fact check, section 9: the claim needs no signature; four signatures are for paying out only.)

Is a multisig and surrounding integrations the answer? The multisig, yes. The surrounding integrations, no.
Three things are the whole system: the Squads app, pump.fun's form, and ledger entries. No payout bot, no
treasury dashboard, no governance token, no program on chain. Every one of those would be a thing only its
maintainer understands, which is rule 8's bug and version 1's mistake. Four people clicking sign in Phantom
is the mechanism, and the ledger is the only record.

Rule changes it needs (rule 7, seven days, four yeses):
- Rule 5 says the only token used is $FEBU. The fee arrives in SOL. Either the group pays in SOL as received,
  or it buys $FEBU with it as a posted promise. Buying is a buyback, which is the thing febu claimed and did
  not do (fact 1); do not do it quietly.
- A new rule: the vault exists, four of seven sign, its signers are exactly the member list, nothing leaves it
  without a promise before and a fact after. The vault's address goes on ledger.txt and ledger.html only.
- KNOWN BUGS 5 closes with a promise: applied on this date, known by pump.fun's written answer and by the fee
  account's claims going to the vault.

Issues, plainly:
- pump.fun refuses disputed takeovers. The creator has not claimed since 09-14, but the operator may still be
  active elsewhere, and a single objection ends it. The application should state the record (facts 2 and 6)
  and nothing about who febu is.
- The application is one person with an email. Bug 1 again, for the length of the application. Name the
  person in the promise entry.
- The vault must be able to sign pump.fun's claim instruction. Squads vaults can execute arbitrary
  instructions, but nobody here has done this one. The first claim is the test. Try it on the 11 SOL already
  waiting before planning around the stream.
- Four of seven also means: if four members go quiet, the money is locked for good. That is accepted, and
  should be written down as accepted.
- The fee split to ten wallets looks like a way to pay members by rule. It pays seats, not work, so it is a
  dividend, which is scripture problem 2 arriving through our own door. Leave it off.
- The stream may be a trickle. Measure first. A trickle is still worth the takeover: it stops every trade
  paying the wallet that sold.
- pump.fun's terms put securities, AML and tax on whoever receives the fee. The Assembly is seven people with
  no entity. Each member's own problem, said once.

First steps, in order:
1. Open fact 6's fee-account link. Has anything arrived since 09-22? Post the number.
2. Post the inheritance question and the three rule changes above. Seven days.
3. On four yeses: create the Squads multisig, 4 of 7, seven Phantom addresses. Vault address to the ledger.
4. Submit the form with the vault as recipient. PROMISE 7: applied, date, known by.
5. When pump.fun answers, FACT: the answer. If yes, claim the waiting SOL as the signing test. FACT: the
   transaction.
6. Nothing pays anyone until the thirty unpaid days are done and the simulation has real numbers.

## 9. After review (four agents, 2026-10-14 evening)

Four reports, in docs/assembly/review_20261014/: facts.md (chain and docs checked), prior_art.md (what exists already),
red_team.md (ten attacks, ranked), architecture.md (rules for the weak problems). What follows is what they
agree on, where they disagree, and what I take from them. Their reports are model output; the chain numbers
were read from the public RPC, the rest from pump.fun's and Squads' own pages, and each report says what it
could not confirm.

### What the fact check changed

| The note said | What is true | Source |
|---|---|---|
| The vault must sign the claim | The claim is permissionless. Anyone may send it; the SOL goes to the creator. Four signatures are needed only to pay out. | PumpSwap IDL, collect_coin_creator_fee |
| The stream may be a trickle | +7.25 SOL arrived in the 22 days since 09-22, about 10 SOL a month. Balance now 11.125 SOL. Newer trades hold fees in the pool until swept, so this understates it. | RPC, 10-14 19:07 UTC |
| The fee seat is set by the form | The form starts it; pump.fun's own key runs admin_cto(new_creator). The fee split (up to 10 wallets) can be set once, then locks. A wrong address may be unfixable. | pump.fun docs, 2026 statements |
| Squads is cheap and safe | 0.1 SOL to create, ~0.005 per action; the program is immutable; losing signers below threshold has no recovery path. | Squads docs, chain |
| Fact 6's account is "the fee account" | It is the WSOL token account of the PumpSwap creator vault for ApWpkd8. | Derived on chain |

Also from the chain, and it matters for the application: the creator wallet holds 3,223.71 SOL and has
transactions as recent as 2026-10-14. It is not dormant. It has simply not claimed its 11 SOL since 09-14.
Not checked: whether pump.fun accepts an off-curve address (a Squads vault, or the incinerator) as the new
creator. No documented case of a CTO fee going to a multisig was found. The form's fields are unverified.

### Is it novel

Narrowly, in four places, and the prior-art survey names them: WRONG IF lines fixed before checking, for facts
about the present and not just predictions; a result that counts only with what the checker saw and which lines
they tested; every step only one person can do listed as a dated bug; and a failure test for the group written
into its own rules. Each is an old idea moved somewhere new (preregistration, show-your-work, a single-point
audit, a sunset clause). Everything else is Wikipedia, Certificate Transparency, Debian and the IETF, and that
is a compliment: the survey rates those parts equal to their originals. Two parts rate worse. The two-witness
close is weaker than Community Notes, which requires agreement between people who usually disagree. And the
multisig is a pool, which rule 5 forbids, and every prior system that held money (Zcash, Gitcoin, UMA,
Optimism) spent most of its governance on the money.

What the systems that lasted ten years share: a procedure that outlived the founder, contribution open to
strangers at near-zero cost, rotating roles, more than one party holding the name and the servers, outside
users who need the output, and the right to copy and run it separately. The ledger has the copy right and the
procedure on paper. It lacks a holder other than Z, and it lacks outside users, because febu has stopped.

### Where it breaks

The red team's top three, in its order:
1. Rule 3 gives any stranger a veto. One disagreeing post blocks closing and anyone may reopen, so a throwaway
   account can push every entry to CAN'T TELL and trip WHEN THIS HAS FAILED. A dust transfer of $FEBU to the
   creator wallet makes fact 2's WRONG IF literally true. Costs nothing. Fix: disagreeing or reopening needs
   two people posting the same different result, the same bar as closing.
2. The vault as drawn. Four signers can change the config and remove the other three the same day; rule 7's
   seven days do not exist on chain. The note never says who becomes the coin's pump.fun admin, the role that
   can set the fee split, and if that is one person's wallet the vault is decoration. Fix, if a vault ever
   exists: no config authority, a 7-day time lock on every transaction, fresh signer wallets, and a FACT
   showing the vault itself can be the admin before applying.
3. Taking the fee makes the group febu's paid heir, and a fee stream is a treasury, which rule 5 forbids. The
   note's rule changes never said "remove no treasury". Claiming the 11 SOL that accrued under the original
   creator's seat would be the worst possible first transaction. The red team calls keeping the money
   unfixable under the constraints: "no treasury" and the checker's independence would both have to go.

And one it ranks sixth that I would move up: there is no rule for leaving. Once four members go quiet, no rule
can change and no vault can pay. That is the likeliest death in year two.

### The decision the reviews converge on

Take the money out, or take it only as forfeits. Three independent readings landed there:
- The prior-art survey: every durable system without a treasury survived its founder; every one with a
  treasury spent itself governing it.
- The red team: a fee to the group is a treasury and a conflict of interest, unfixable under the rules.
- The architecture report: the only money that cannot be farmed is a loss that profits nobody.

So the version that is most distinct from everything surveyed, and most likely to be here in ten years, is:

- Apply for the CTO, naming as the new creator an address nobody can spend from. KNOWN BUGS 5 only needs the
  fee to stop reaching the wallet that sold. It never needed the fee to reach us. Nobody claims the 11 SOL
  that accrued before. (Unverified: whether pump.fun accepts such an address. If not, the fallback is "we will
  not apply", written as the bug's close.)
- The only money in the group's name is a forfeit: IF BROKEN names an amount, paid to the incinerator or to
  the person the promise was made to, who then posts no result on it. Nobody who owes a forfeit posts a new
  promise. No vault, no pool, no claim, no heir.
- Checking stays unpaid. The simulation already said paying checkers needs outside money and a collectable
  loss. Thirty days unpaid will say whether seven people check without it.

What this gives up: Witness's "a role for $FEBU" shrinks to a unit of forfeit and a unit of private payment
between members. The stream, about 10 SOL a month, goes nowhere. That is the cost of staying a checker.

If the group wants the vault anyway, it is a rule 7 decision that says in its own words: rule 5 loses "no
treasury", the group becomes the coin's fee recipient while publishing facts about it, and the red team's five
conditions apply. The post should say all of that.

### Rule changes to propose (each through rule 7)

1. Rule 3: a disagreement or a reopening needs two people posting the same different result and what they
   saw, the same bar as closing. (Red team 1.)
2. HOW TO CHECK AN ENTRY: each SEEN post names one thing on the page that is not in the entry or in any
   earlier post. (Red team 5. This is the one way the record can tell a check from a copy.)
3. Rule 6: the ledger is the file matching the last posted hash, wherever it is served; the weekly checker
   makes that week's changes from that file. (Architecture C. This closes KNOWN BUGS 1 and the founder test.)
4. WORDS USED HERE, Member: a member who has posted nothing in 90 days stops counting toward rule 3, rule 7
   and the weekly turn until they post again. (Red team 6.)
5. IF BROKEN names an amount in SOL or $FEBU and where it goes: the incinerator, or the person the promise was
   made to, who then posts no result on it. Nobody posts a new promise until their forfeits are paid.
   (Architecture 2a.)
6. No entry, and no post in the group's name, states or implies a price for $FEBU. Any post asking people to
   trade it says each trade pays a fee to the wallet in facts 2 and 6 until KNOWN BUGS 5 closes.
   (Architecture 2b.)
7. PROMISE 7 is the group's own failure test, as drafted in section 5.
8. A dated WRONG line under any entry or result that proves wrong, in the writer's own name; after 7 days the
   weekly checker adds it, marked "added by". Z'S PREDICTIONS THAT FAILED become the first.
9. An objection under rule 7 says what would change the objector's mind. (Prior art, IETF.)
10. OUT OF SCOPE: environment, febu's problem 11. DEPENDS ON: each outside service with a second and the date
    it was last tried; a second untried for 90 days is a KNOWN BUG.

Ten changes is more than one screen. Proposals 1, 3, 4 and 7 are the ones that decide whether the thing
survives; the rest can follow in a second round.

### The multisig Z found (added the same evening, dossier P191)

Z's other session found a 20-address Squads multisig, threshold 2 of 11, whose member keys signed transactions
in both the febu creator wallet's history and the LIZARD dev wallet's. Read on the public RPC: it is pump.fun's
own admin multisig. The instructions it ran are platform-admin calls (AdminSetCreator, DistributeCreatorFees,
ResetFeeSharingConfig), and its vault address UqN2p5bA sits inside pump.fun's Global config. Both coins appear
in its history because pump.fun ran fee operations on both, as it does for any coin. It is not a febu to
LIZARD link.

What it means for this design:
- The CTO is executed by that multisig. The fee seat the group would hold depends on a 2-of-11 wallet at
  pump.fun that can reset any coin's creator at will. The red team's "single point of control" now has an
  address and a threshold, and it is looser than the 4-of-7 proposed here. Worth one line in tests.txt test 4
  and in KNOWN BUGS 5.
- On 07-22 that multisig reassigned the creator of a coin ApWpkd8 had made six hours earlier, and on 07-17 it
  split 3.685 SOL of creator fees in half between ApWpkd8 and a second wallet. Creator reassignment and fee
  splits are routine platform operations, not a sign of anything about febu.
- It is a live example of what a pooled multisig becomes: 20 addresses, any two can act. The ledger's "no
  treasury" is the opposite choice, made on purpose.

### Still open

- Whether a stranger should be able to close an entry. Prior art says small approving pools killed Nupedia
  and Citizendium; the red team says sybils are unfixable without identity. The architecture report's middle
  path: a stranger's check once a month that can reopen but not close.
- A SEEN line written by an AI and signed by a person who never opened the link cannot be told from a real
  check. All three reviews say so. The rule stays; the record cannot enforce it.
- Facts 4 and 5 rest on Z's copy of the scripture (KNOWN BUGS 3). Unchanged.
- The fee stream's true size, since new-style trades hold fees in the pool until swept.

## 10. The return-or-burn vault (added after Z's question on idle funds)

Unspendable and waiting cannot both be true. The nearest honest thing: a Squads 4-of-7 with a 7-day time lock
on every transaction including config changes, no config authority, fresh signer wallets. Nothing moves unless
four act and a week passes in public. That is rule 7 on chain.

Its money is the members' own (the fee is unavailable while the creator wallet is active). Its purpose leaves
nothing to govern: money enters as a bond behind a promise and leaves in two directions only, back to the
depositor on KEPT or to the incinerator on BROKEN. Signers execute what rule 3 closed; they decide nothing. A
stranger verifies the history by checking every outgoing transaction went to one of two places. Optional: the
idle balance in a native stake account, rewards by protocol, unstaking ~2 days, never called yield.

Rule text to propose when the first money promise is written:
  5. Money moves wallet to wallet, as promises kept. The group's vault holds bonds only: a bond returns to
     its depositor on KEPT and goes to the incinerator on BROKEN, and nothing else leaves it. Four of seven
     sign, and every transaction waits 7 days in public before it runs. No pool for pay. The group makes no
     new token.

Accepted, not fixed: four quiet members lock it forever; holding bonds is custody by seven people with no
entity; a bond returned is a decision rule 3 made, and two colluding checkers could free one.

Order: survival rules and PROMISE 7 first with no vault; the vault only with the first bonded promise.

Second pass, same evening (is it optimized?):
- The vault is not needed until someone refuses to pay a forfeit. Bonds start voluntary: the promiser burns
  their own SOL on BROKEN and posts the transaction as a fact; "no new promise until paid" is the enforcement.
  Trigger for the vault: the first unpaid forfeit, not the first bonded promise.
- Drop staking: choosing a validator is a decision (test 4) and adds an operational part.
- One forfeit destination, the incinerator. Paying the counterparty gives someone a reason to want BROKEN.
- Burden not yet priced: returning a bond needs four signatures and seven days, so a kept promise waits about
  two weeks for its money, if four people sign. Keep bonds small; the rule 6 checker proposes returns weekly.
- Seven fresh keys for years; lose four and the vault is permanent. Say so before anyone deposits.
- The 90-day quiet rule can leave fewer than four active members, so rule 7 can never pass again. Word it:
  "four yeses, or every active member if fewer than five are active", and note that this lets a small active
  core change the rules.
- A lone disagreement is recorded as a NOTE under the entry, which stays closed. Keeps the signal, removes the
  veto.
- First round of changes: the four survival rules and PROMISE 7 only. First month's entries: the three
  cheapest one-link facts, including the platform-multisig fact (P191), which is about pump.fun, not febu.
- Untested assumption: that holders want this. Test inside the thirty days: Witness's budget as a promise to
  put the link in front of holders, then a fact counting whether any stranger reopened an entry.

## 11. The answer to Witness's question (late, after re-reading the chat)

Satoshi's move: making a thing costs real work, checking it costs nothing, and the rule itself pays in the
thing protected, so nobody at the top decides. Febu's eleven problems share one disease: speech that costs
nothing, and febu is its purest specimen (diagnosis without mechanism, a validator narrated, a prize unpaid, a
buyback claimed). The Satoshi move applied to that is proof of work for claims: a claim costs a WRONG IF line,
a public link and a bond; a check costs a click; a broken promise burns its bond by rule. Prediction is the
claim with the highest cost, and the ledger already holds it (WILL, BY, KNOWN BY).

$FEBU's role, found at last: the bond. It is burnable and the promiser values it. Then every serious claim is
demand for the coin and every broken promise removes supply, with no treasury, no heir and no price talk.
This passes the four tests more cleanly than the vault: nobody paid, the promiser alone loses, nothing issued
or removed, two checkers and a link decide. Cost to disclose: buying $FEBU to bond pays a fee to the wallet
that sold (KNOWN BUGS 5).

Not solved: the multipolar trap (Bitcoin did not either); scaling past named people; paying anyone to look.

## 12. One line for Witness

Bitcoin removed the need to trust named people. The ledger does the reverse: it makes trust among seven named
people checkable by a stranger with a browser. It borrows one thing from Bitcoin, a free stamp that a file
existed by a certain block, and nothing else.
