# The ledger's weak problems: extensions and alternatives (2026-10-14)

Written against ledger version 2.1, tests.txt, the system outline (sections 1-9) and the reward simulations (P187, P190). Every rule below can be pasted into ledger.txt and goes through rule 7. None adds a token, score or pool, or lets an AI post a result. To keep the rules on one screen, most belong under HOW AN ENTRY IS WRITTEN, not THE RULES; section D adds about eight lines.

## A. Mechanisms for the weak and absent problems

Key for "changes": the tests are G (gains), L (losses), B (bailout) and D (decision). Bitcoin's three properties are P1 (work that cannot be faked), P2 (anyone can check cheaply) and P3 (the rule itself pays).

### Problem 2: debt and financial illusion

**2a. Bonds without a pool.**
> IF BROKEN names an amount in SOL or $FEBU and where it goes. It goes either to the person the promise was made to, who then cannot post a result on it, or to Solana's incinerator, 1nc1nerator11111111111111111111111111111111, where nobody can spend it. Whoever has not paid a forfeit by 7 days after BROKEN posts no new promise until they have.

- **Record:** the forfeit transaction on any explorer, linked as a FACT.
- **Cost:** none until a promise breaks. Then about 5 minutes for the payer and 5 for a checker.
- **How it fails:** nothing holds the bond in advance, so paying the forfeit is voluntary. A member who refuses keeps BROKEN and the unpaid forfeit under their name, and that is the only enforcement. Enough among seven named people, not among strangers.
- **Where the forfeit goes:** never to the checkers. If BROKEN paid the people who call it, they would have a reason to call it, and rule 3 is built on checkers gaining nothing. The incinerator is the default because a loss that profits nobody cannot be farmed.
- **Changes:** L, from a word to money. B a little: an empty promise now costs something. P1 partly: a promise with money behind it is harder to fake. P3 is unchanged.
- **A held-in-advance version:** the promiser sends the bond to the 4-of-7 vault before the date, and the vault returns it on KEPT or burns it on BROKEN. That collects the forfeit, but needs the vault voted in and turns four signers into a court. Adopt it only after someone refuses to pay.

**2b. No price.**
> No entry, and no post in the group's name, states or implies a price for $FEBU. A promise whose KNOWN BY is a price is not entered. Any post asking people to trade $FEBU says that each trade pays a fee to ApWpkd8 until KNOWN BUGS 5 closes.

- **Record:** the ledger itself. A stranger searches it for "price".
- **Cost:** nothing to keep. About a minute to read a draft post before it goes out.
- **How it fails:** members talk price in their own names, which this rule cannot reach.
- **Changes:** G, because the fee to the wallet that sold gets disclosed instead of quietly fed. B: no more costless announcements about value. None of the three properties.

Judgment: 2b is the cheapest addition here and closes the outline's "investment pitch" risk. Do 2b now and 2a with the first promise.

### Problem 3: repeating history and futile cycles

**3a. Every change cites what it repeats.**
> A rule change quotes the wording it replaces, links the archived version, and names which of febu's eleven problems it addresses. If it brings back wording from any earlier version, it says so and links that version.

- **Record:** archive/ and its hashes. A stranger can diff two versions and see whether a change went back to old wording without saying so.
- **Cost:** about 5 minutes per rule change, and changes are rare.
- **How it fails:** it becomes box-ticking ("addresses: 1"). It catches unannounced returns, not deliberate ones.
- **Changes:** D a little, because a change cannot quietly undo an earlier decision. P2: going back is now visible from the file alone.

**3b. A WRONG line, under the writer's own name.**
> Anyone who posted a result or wrote an entry that later proves wrong adds a dated WRONG line under it, in their own name, saying what they missed. Z'S PREDICTIONS THAT FAILED becomes the first set of WRONG lines.

- **Record:** the entry. The WRONG line sits next to the SEEN lines that disagreed with it.
- **Cost:** a few minutes, only when someone is wrong.
- **How it fails:** nobody writes their own. Then the next weekly checker writes it for them, marked "added by".
- **Changes:** L, because being wrong becomes a line of its own and not just a disagreement. Also covers problem 4.

Judgment: remembering is not learning, and no rule makes people learn. 3a makes a repeat visible to a stranger; that is as far as a text file goes.

### Problem 4: human limits and arrogance

**4a. The failure test as a promise.**
> PROMISE 7 (the group, date adopted). WILL: at least three entries close under rule 3, at least one written by someone other than Z. BY: 30 days after adoption. KNOWN BY: ledger.txt. IF BROKEN: we rewrite this or stop, said in the chat and in this file.

- **Record:** ledger.txt on that date, plus its Internet Archive copy.
- **Cost:** none until the date. Then about 10 minutes for two checkers.
- **How it fails:** the group extends the date. Rule 2 means the extension shows as a new line, and the withdrawal rule makes a late extension count as BROKEN.
- **Changes:** D, because the group's claim about itself gets the same treatment as anyone's. P1: the claim "this works" becomes checkable.

**4b. A stranger's check.**
> Each month the weekly checker invites one person outside the seven to check one OPEN entry, chosen by them, not by the writer. Their post goes under the entry as SEEN (outside). It can reopen an entry but cannot close one. If nobody accepts, the month says so.

- **Record:** the stranger's post somewhere readable without an account (a GitHub issue, a pastebin, an archived copy of a tweet; an X link alone is not enough). The SEEN line links it.
- **Cost:** about 15 minutes a month for whoever's turn it is.
- **How it fails:** nobody accepts, or the "stranger" is a friend. The month's line records the first. The second is the RISKS WE ACCEPT ring with one more person in it.
- **Changes:** P1 directly, because it is the only mechanism here that makes someone outside look. It weakens the "fake lasts until somebody looks" risk. Covers problem 10 too.

Judgment: 4a costs nothing and should go first, since the outline already drafted it. 4b is the best answer here to "nothing makes anyone look".

### Problem 5: war, diplomacy, broken agreements

**5a. Agreements are two promises.**
> An agreement with anyone outside the group is entered as two promises, one for each side, and goes in only if the other side has posted its half where anyone can open it. An agreement the other side never posted is not one.

- **Record:** the outsider's own public post, linked as KNOWN BY.
- **Cost:** about 10 minutes per agreement, and agreements are rare.
- **How it fails:** outsiders will not post. Then there is no agreement in the record, which is true.
- **Changes:** D, because nobody can claim a deal on the group's behalf. B, because a one-sided "we have a partner" announcement cannot happen. Witness's marketing budget is the first case.

Judgment: 5a plus 2a (bonds are this problem's loss side). Without a stake, problem 5 stays a word under a name.

### Problem 6: technological dependence and obsolescence

**6a. The copy of record.**
> The ledger is the file whose SHA-256 was last posted under rule 6, wherever it is served. The weekly checker updates it that week, starting from that file, and posts the new hash. Any member may serve a copy, and none is the original.

- **Record:** the posted hashes, plus the Internet Archive copies of each served copy.
- **Cost:** 30 to 45 minutes once every seven weeks per member, about 5 minutes a week on average. Each of the seven needs write access somewhere, which is one setup session per member.
- **How it fails:** members who cannot use git miss their turn. The fix is that the turn can be done in GitHub's web editor. A missed turn is marked by the next checker.
- **Changes:** D, because it closes KNOWN BUGS 1 and fixes the founder test. Covers problem 1 too.

**6b. DEPENDS ON, with a second for each.**
> DEPENDS ON lists every outside service the ledger needs. Each has a second one and the date someone last served or checked the file through that second. A second untried for 90 days goes under KNOWN BUGS.

  Vercel, second GitHub Pages. GitHub, second a Codeberg mirror. solscan.io, second explorer.solana.com. web.archive.org, second archive.today. The chat, second the rule 6 copy in this file.

- **Record:** the second's URL serving a file with the same hash, and the same transaction on the second explorer.
- **Cost:** about 15 minutes a month.
- **How it fails:** the dates go stale. The 90-day trigger makes that a listed bug, not a silent one.
- **Changes:** P2, because a check survives one site dying. Closes KNOWN BUGS 4.

Judgment: 6a matters most (section C). 6b is cheap.

### Problem 11: environment and infrastructure neglect

**11a. Say it is out of scope.**
> OUT OF SCOPE: environment (febu's problem 11). Nothing here makes a record a stranger could open for it. The only infrastructure this ledger keeps is its own (DEPENDS ON).

- **Record:** the line itself.
- **Cost:** none.
- **How it fails:** it does not. It is an honest refusal.
- **Changes:** none of the four tests or the three properties.

Judgment: do not stretch (3 pages of 164). The part the group can hold, its own infrastructure, is 6a and 6b.

## B. Three whole-architecture alternatives

**B1. No money, ever.** Rule 5 becomes "no money moves in the group's name, ever". KNOWN BUGS 5 closes as "we will not apply". Members may still pay each other privately, but that is not a ledger matter.
*Gains:* problem 2 is answered by staying out. Nothing to hold means no test-4 holder, and the group never becomes febu's heir (outline section 7). It is the simplest rules.
*Loses:* L stays weak for good. P3 stays NO. The fee keeps going to the wallet that sold.
*Survives the founder:* the best of the three. There is nothing to hand over except a text file.

**B2. Bonds only, no fee.** No vault and no takeover. The only money is bonds (2a): a promiser's own SOL or $FEBU, burned on BROKEN. Checkers are never paid.
*Gains:* L becomes real money, and problems 2 and 5 move from weak to covered. No holder, no pool, no inheritance question. Burning profits nobody, so it cannot be farmed.
*Loses:* making a promise costs something, so fewer promises get made. The simulation found every holding design needed outside money to pay checkers, and this has none, so checking stays volunteer work. P3 is still NO. Forfeits can only be collected if the promiser pays.
*Survives the founder:* yes. Nothing is held.

**B3. A federation of copies.** Each member keeps their own ledger.txt, a copy under rule 7. The group's ledger is every entry that appears word for word in at least four copies, each with its SEEN lines. A stranger can compute this by opening four files and comparing them.
*Gains:* no keeper, no shared host, no bug 1. Problems 1 and 6 are covered by construction. Leaving takes one copy away, not the record.
*Loses:* readability. A stranger reads seven files instead of one, or trusts a script that computes the overlap, and that script is one person's tool (rule 8). Copies drift. Wording disputes become identical-text disputes. It costs more minutes per week: each member syncs their copy.
*Survives the founder:* yes, by design. 6a gets most of this for a fraction of the cost.

Recommendation among these: none of them as a replacement. Version 2.1 plus 2a is B2 with the vault question left open. Plus 6a, that is B3's durability without the merge cost.

## C. Durability

In ten years the text will still exist: plain text, the Internet Archive's daily saves and OpenTimestamps make sure of that. The question is whether anyone can still add to it. The one thing that decides that is **whether the right to update the file belongs to a host or to a rule.** Today it belongs to a host: Z's repository and Z's site. If Z stops, the file freezes, as febu's writing did on 09-19.

The simplest rule that fixes it is 6a. The ledger is whatever file matches the last hash posted under rule 6, and the weekly turn holds the pen. Then no host is the original. Any member, or after the group has gone any stranger running a copy under rule 7, can carry on from the last archived file, and a reader can tell which copy continues the record by checking one hash.

Also: a ledger that ends honestly stays readable. PROMISE 7 (4a) means the last line explains why the lines stop.

## D. The three smallest additions, in order

**1. The copy of record** (problems 6 and 1, KNOWN BUGS 1, the founder test). Goes in rule 6:
> 6. Each week a different member checks both ways: every result posted in the chat that week is in this file, and every SEEN line in this file has its post in the chat. That member also makes the week's changes, starting from the file whose hash was last posted, and posts the new file's SHA-256 somewhere the group does not control. The ledger is the file that matches the last posted hash, wherever it is served.

The first time it runs, it requires all seven members to have write access, or a host of their own.

**2. The failure test as an entry, plus WRONG lines** (problems 4 and 3). Add PROMISE 7 as drafted in 4a, and add one line under HOW AN ENTRY IS WRITTEN:
> Anyone whose entry or result proves wrong adds a dated WRONG line under it, in their own name, saying what they missed. If they do not within 7 days, the weekly checker adds it, marked "added by".

**3. Losses with a destination, and no price** (problems 2 and 5). Replace the IF BROKEN definition with:
> IF BROKEN names an amount in SOL or $FEBU, paid to the incinerator 1nc1nerator11111111111111111111111111111111 or to the person the promise was made to, who then posts no result on it. Nobody posts a new promise until their forfeits are paid. No entry states or implies a price for $FEBU.

These three cover 6, 1, 4, 3, 2 and 5, leave 11 out of scope in one line (11a), and add about eight lines to the file. Together they move L from "weak" toward money, D from "Z's file" to "the hash's file", and P1 toward real stakes. P3 stays NO, and the file should go on saying so.
