# Red team: ledger 2.1, the four tests, and the 4-of-7 fee vault (2026-10-14)

Against ledger 2.1, tests.txt, the system outline and the simulation results, whose findings are taken as
given. Not legal advice. VERIFY = not checked against the live Squads or pump.fun products. Ranked by
severity: ENDS the experiment, EMBARRASSES it, or ANNOYS.

---

## 1. One stranger can keep any entry from closing (ENDS, cost: zero)

Rule 3: an entry closes when two members agree "and nobody who posted what they saw disagrees". "Anyone,
member or not, can reopen it by posting what they saw." Rule 4: disagreement for 30 days becomes CAN'T TELL.

Scenario:
1. Crypto Fish and Laura post HOLDS on fact 2 with the amount they saw.
2. A throwaway account in the chat posts "DOESN'T HOLD, the wallet holds 12 $FEBU". A dust transfer of
   $FEBU to ApWpkd8 after 09-22 makes this literally true, for a fraction of a cent, because fact 2's WRONG
   IF says "the wallet holds any $FEBU now".
3. Fact 2 stays open. Day 30: CAN'T TELL.
4. Repeat on every entry. WHEN THIS HAS FAILED needs three closed entries in 30 days; it fires on schedule
   and the group "rewrites or stops".
5. Anything that did close, the same account reopens monthly. A reopened entry counts only posts made
   after reopening, so members re-check forever.

Rule 8's own bug: any one person holds a veto.

Cheapest fix (one line in rule 3, symmetric with closing): "A disagreement holds an entry open only when two
people other than the writer post the same different result and what they saw. A single post stays as a
SEEN line and does not block." Same for reopening. Also say in fact 2 whether $FEBU received after 09-22
counts.

## 2. Four keys can rewrite the vault, and the vault may not control the fee (ENDS)

Scenario A, collusion: four members (or one person holding four of the seven names, see #6) approve a config
transaction: remove the other three, threshold 1. Next block, drain. Rule 7's seven days live in the chat;
the chain does not know about them. The other three learn from the explorer.

Scenario B, the seat outside the vault: section 8's diagram has the CTO form naming the vault as recipient.
It does not say which wallet becomes the coin's admin on pump.fun, the one that can re-split the fee across
up to ten wallets. If that admin is the Phantom wallet of whoever filled in the form, that one person can
move the fee away from the vault any day, and the multisig is decoration. pump.fun's site signs in with a
wallet message, which a Squads vault generally cannot sign (VERIFY).

Scenario C, social engineering: Merc proposes "claim pump.fun fees", an instruction nobody here has seen.
It pays Merc's second wallet. Three others sign on a busy evening: "we've waited a week". That is the
predicted fast-path pressure.

Scenario D: a drainer takes Laura's Phantom key. It is one of four, but it can propose routine-looking
transactions. Three lost keys plus one quiet member lock the funds for good (accepted in the outline).

Cheapest fixes, all set once at creation (VERIFY each in the Squads app before anything is sent to it):
- Config authority: none (an autonomous multisig), so membership changes only by the members' threshold.
- Time lock: 7 days on every transaction, config changes included. This puts rule 7 on chain: any member,
  or any stranger watching the address, has seven days to see a theft coming and say so. It also kills the
  fast path, since shortening the time lock waits seven days itself.
- Every proposal is a PROMISE entry first, naming the Squads transaction number and the exact balance
  changes ("vault -0.5 SOL, wallet X +0.5 SOL"). Sign only if the simulation shows those numbers.
- Before applying for the CTO, show in a FACT that the pump.fun admin seat itself can be the vault. If it
  cannot, the admin is one person and the vault adds nothing: see #3.
- Each signer uses a fresh wallet used for nothing else (also fixes the exposure in #8).

The time lock makes four patient colluders visible, not stopped. Say so under RISKS WE ACCEPT.

## 3. Taking the fee makes the group febu's heir and breaks rule 5 (ENDS the checker role)

Rule 5 says "No pool and no treasury." A vault that receives a fee stream is a treasury. Section 8 lists
three rule changes; it does not list the removal of rule 5's first sentence, which is what it requires.

Scenario:
1. CTO granted. The vault receives every $FEBU trade's creator fee.
2. Every member now earns more when $FEBU trades more. Facts about febu (1, 2, 6 and any new one) are
   written by people paid by $FEBU volume. A finding that excites traders pays them.
3. A critic: "The group that documented febu taking 2,939 SOL in fees now takes the same fees." True.
4. Section 8 step 5 claims "the 11 SOL already waiting" as a signing test. That SOL accrued while the seat
   was the original creator's. Claiming it is taking money accrued to the person the group publishes facts
   about. The worst possible first transaction.
5. The original operator (active through 09-22, launched $benchcoin 09-03) objects, or resumes claiming
   before the form is decided. pump.fun refuses on "any reasonable dispute". Or it grants, then later
   revokes, changes its terms, or shuts down, alone, outside every rule here. That part is UNFIXABLE by
   anyone: pump.fun is a single point of control the group cannot list as its own
   bug with a fix date.

Cheapest fix within every constraint: KNOWN BUGS 5 is "trades pay the wallet that sold". It is fixed by the
fee leaving that wallet, not by the fee arriving at the group. Apply, if at all, to send the fee to an
address nobody can spend from (Solana's incinerator), or ask whether it can accrue unclaimed under a seat
nobody holds (VERIFY pump.fun accepts either). No vault, no heir, no tax question, and #2 and #7 disappear.
Under any design, never claim fees that accrued before the CTO.

If the group wants the money: UNFIXABLE UNDER CONSTRAINTS. "No pool and no treasury" has to go, and the
group has to accept that it stops being an independent checker of $FEBU. Both belong in the rule 7 post.

## 4. Z leaves, and KNOWN BUGS 1 does not cover it (ENDS slowly)

Bug 1's fix is "a second member can edit it too". That is one more person on GitHub. It leaves:
- The repo under Z's account (zinotino/febu-assembly), and the Vercel project and subdomain under Z's
  Vercel account. A second GitHub editor gets no Vercel.
- The definition of Hash: "ledger.txt as the group site serves it". Site down, no defined hash.
- The daily Internet Archive save is run by Z's site, so it stops with it.
- build.py, checks/, timestamps and all six facts are Z's; nobody else has to be able to run anything.

Scenario: Z goes quiet for two months. Nobody can merge SEEN lines, rule 6 has no file to hash, and the
ledger forks into seven chat memories.

Cheapest fixes, no new rules:
- Every member clones the repo and posts their latest commit id. Seven full histories.
- Move the repo to a GitHub organization with three owners; same for Vercel, or stop relying on it.
- Reword Hash: "the SHA-256 of ledger.txt in any copy; the copy whose hash was last posted outside the group
  is the current one." The site becomes one copy among many.

## 5. The record cannot tell a check from a rubber stamp (EMBARRASSES; partly UNFIXABLE)

Scenarios:
1. Copying: "look before you read anyone else's post" cannot be enforced in a shared chat. The second checker
   copies the first's number ("23,843,803.61") and posts HOLDS. Indistinguishable in the record.
2. AI SEEN line: a member gives the entry to a browsing model, which opens the link and writes "Saw: Swap
   23,843,803.614015 febu for 18.893241316 WSOL, tested both WRONG IF lines, HOLDS". The member posts it
   without opening anything. The rule says the person answers; the record looks the same.
3. Two friends close a false fact (RISKS WE ACCEPT); if checks are ever paid, easy true ones for pay.

Cheapest fix for 1 and 3: "Your post names one thing on the page that is not in the entry and not in any
earlier post" (a block number, a fee amount, a second timestamp). Two independent openings give two different
details; a copy gives none. A reader can see the difference in the record, years later.

2 is UNFIXABLE UNDER CONSTRAINTS. The AI can produce the extra detail too. Telling a person from an AI at
check time needs proctoring or identity checks, and "an AI may help you find something" would have to go.
Write under RISKS WE ACCEPT: "A SEEN line shows who answers for a result, not who opened the link."

## 6. The member list is the soft target (ENDS slowly, or ENDS via #2)

Scenarios:
1. Sybil inside: one person already holds two of the seven names; nothing today shows otherwise. Rule 3 needs
   "two members other than its writer", so that person closes any entry alone. Four names take the vault.
   Cost: getting past the group once, at adoption.
2. Stacking: four members vote in four new ones (two objections suffice to block, but only if made). The
   newcomers then outvote the originals on everything, the vault's signers included.
3. Fossilization: there is no rule for leaving. Members drift off and rule 7 needs four yeses forever. Once
   four of seven are quiet, no rule can change, nobody can be added to replace them, and any vault is locked.
   This is the most likely way the group ends in year two.

Cheapest fixes:
- "A member who has posted nothing in the chat for 90 days is listed as quiet and does not count until they
  post again." Rule 7's four is four of the members not quiet. (A vault's signer list does not follow this
  rule: one more reason for #3.)

Sybil itself is UNFIXABLE UNDER CONSTRAINTS: proving seven names are seven people needs identity checks,
which this project rules out (never identify private individuals). Write it under RISKS WE ACCEPT.

## 7. SOL in, "$FEBU only", and the buyback trap (EMBARRASSES, possible legal exposure)

Rule 5: "The only token used here is $FEBU." The fee arrives in SOL.

Scenario:
1. Honoring rule 5, the group posts PROMISE 9: "on 2026-12-01 the vault buys $FEBU with the claimed SOL",
   public seven days ahead under rule 7.
2. Anyone, members included, buys early and sells into the vault's buy: insiders trading ahead of their own
   announcement.
3. It is the buyback febu talked about and never did (fact 1), on a public schedule: price support.
4. Later the vault pays a member 0.5 SOL for a closed check. The money rises with $FEBU volume. To a holder
   who has read Witness's "demand growing against supply", members are being paid from trading in a token
   they talk up. That is the moment a payment looks like an investment return.

Cheapest fix, in rule 5's wording: "The group never buys or sells $FEBU and never says what its price will
do. Money is paid in what it arrived in." With #3's no-vault fix the section disappears.

## 8. Legal and regulatory exposure (EMBARRASSES to ENDS)

Not advice. What a careful person would put to a lawyer before section 8 step 3:
- Seven people with no entity jointly receiving income and spending it by vote may be treated as a general
  partnership in many places, each member answerable for the whole.
- Who reports the vault's income for tax, and when? Seven people, possibly seven jurisdictions.
- Taking a token's trading fee while publishing about it and announcing what the money will do is the shape
  regulators examine for promoter and market-manipulation questions.
- pump.fun's terms put securities, money-transmission and tax duties on the fee recipient.
- Signer wallets are public in the multisig config, linking each member's history to the group (#2's
  fresh wallets fix this).
- Rule 2's "[removed]" is defeated by rule 6: the daily Internet Archive copies and the word-for-word
  archive/ versions keep the original. Fix: personal information is never posted; if it slips in, the site
  owner asks the Archive to exclude that copy, written down as the one exception.

Partnership and tax are UNFIXABLE UNDER CONSTRAINTS while the group receives money; "no treasury" (and the
unwritten "no entity") would have to go. Not receiving the fee (#3) makes most of this moot.

## 9. Time (ANNOYS now, ENDS at ten years)

- 1 year: solscan changes its URL filters (`?flow=out#transfers` in fact 6 is page state, not an address).
  The Vercel subdomain lasts as long as Z's account.
- 3 years: half the members are quiet (#6); pump.fun's fee program has changed. The chat platform dies, and
  rule 6's "every SEEN line has its post in the chat" becomes uncheckable: SEEN lines are the file's word.
- 10 years: most links are dead; rule 1 demands they open, with no status for a link that died after
  closing. The CAN'T TELL pile only grows; nobody reads 400 entries.

Cheapest fixes:
- #5's extra detail makes each SEEN line a witness statement that outlives its link.
- "LINK DEAD (date)" as a dated line; the entry keeps its result, "closed while the link worked".
- Each chain fact gives the bare signature or address on its own line, for any future explorer.
- Whoever has the rule 6 turn exports the chat into the repo once a month.

## 10. Smaller breaks (ANNOY)

- "WRONG IF ... never changed", yet facts 1, 2, 5 and 6 have CHANGED lines that changed it. Fix: at adoption,
  re-post facts 1-6 as final; any later change is a new entry number.
- Facts 4 and 5 are checked against Z's own copy, so closing them certifies only that copy. Fix: SAYS begins
  "In the copy Z saved, ...".
- Two friends can pass the failure test by closing a trivial fact a third wrote. Accept.

---

## Summary

The three attacks that matter most:
1. Rule 3 lets one stranger keep any entry from closing and reopen any closed one, for free (#1).
2. The vault has no on-chain wait, four keys can rewrite it, and pump.fun's admin seat may sit outside it (#2).
3. Taking the fee is a treasury under rule 5 and makes the checker febu's paid heir, with partnership and
   tax exposure (#3, #8).

The three cheapest fixes worth adopting now:
1. Rule 3: a disagreement or reopening needs two people posting the same different result, as closing does.
2. Each SEEN post names one thing on the page that is not in the entry or in any earlier post.
3. KNOWN BUGS 5: send the fee where nobody can spend it, or do not apply; never claim pre-CTO fees. If a vault
   ever exists: no config authority, 7-day time lock, fresh signer wallets.
