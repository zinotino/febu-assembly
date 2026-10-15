# Prior art for the Assembly ledger (2026-10-14)

Sources read: febu-assembly/ledger.txt (v2.1), tests.txt, docs/assembly/ASSEMBLY_SYSTEM_OUTLINE_20261014.md. Web searches 2026-10-14. Items marked (memory) come from background knowledge and were not re-verified today.

## The mechanism, restated

A public, append-only text file of numbered claims. A fact is a sentence, a public link, and WRONG IF lines saying what at the link would make it false; a promise is a dated commitment with the link anyone will open then and what the promiser loses. Those terms are fixed before anyone checks. An entry closes only when two of seven named members, neither the writer, each post what they actually saw and reach the same result unopposed; unresolved disagreement becomes CAN'T TELL after 30 days. Nothing is deleted, nothing is scored, and an AI may help read but never posts a verdict. The group holds no money: payments go person to person, a promise before and a transaction-link fact after. Rule changes and group acts need 7 days, four yeses, at most one objection; the file's hash goes outside the group weekly; any single-person step is a dated bug; the file states its own failure test. The extension routes $FEBU's creator fee to a 4-of-7 multisig under the same promise/fact discipline. In one line: a preregistered, link-backed claims register closed by two human witnesses, with no adjudicator.

## Survey (what it does / outlived founder? / the mechanism that decided it)

**Community Notes (2021).** Notes show only when raters who usually disagree both rate them helpful (bridging); algorithm and data are public. Survived the 2022 takeover; copied by Meta and TikTok (memory). Since July 2025 AI accounts write notes (eight bots wrote ~half of visible notes in early 2026) but only humans rate. **Durable:** bridging plus open code anyone can re-run.

**Wikipedia verifiability.** A claim needs a source a reader can check; unsourced claims get tagged or removed. Outlived Sanger (2002). Nupedia (seven-stage expert review) and Citizendium (credentialed approvers) stalled. **Durable:** near-free contribution, cheap reverts. **Killed the rivals:** a small approving pool.

**Kleros (2018).** Token-staked random jurors paid for voting with the majority; appeals double the jury. Founder still runs it; low volume, mostly curation. **Limit:** verdicts track expected majority, needs a token.

**UMA / Augur / Polymarket.** UMA: a bonded assertion stands unless disputed in a window; disputes go to a token vote. In March 2025 a whale swung Polymarket's $7M Ukraine-minerals market against Polymarket's own clarification. Augur's REP court faded as founders left (memory). **Lesson:** written resolution criteria survived; token courts are buyable or too slow.

**Metaculus / Good Judgment.** Pre-written resolution criteria plus a public, scored track record per forecaster. 10+ years, institutional. **Durable:** the score, which the Assembly forbids.

**Gitcoin / Optimism RetroPGF.** Gitcoin closed Grants Stack in May 2025 as financially unsustainable; quadratic funding was sybil-farmed throughout. Optimism's Citizens' House moved from voting on projects to voting on algorithms (Season 7: "too complex and unstable") and toward metrics. **Killer:** a money pool invites farming; human impact-judging did not scale.

**EAS / Hats.** EAS: tokenless schema registry for signed, revocable, never-deleted attestations; it records, decides nothing, and lasts. Hats: roles as revocable tokens with written eligibility rules; modest adoption.

**Zcash dev fund.** 20% of block reward to fixed orgs, then (NU6, 2024) 8% grants plus 12% lockbox, then (NU6.1, 2025) a coinholder-voted fund, now ~$95M and in an abolition fight (Oct 2026). Zooko stepped back (memory). **Lesson:** the held money generates every governance fight.

**Bitcoin BIPs / full nodes.** BIP editors are clerks; adoption is decided by what node operators run (2017 UASF, memory). Outlived Satoshi. **Durable:** acceptance by independent verifiers, not editors.

**Long Bets (2002).** Terms fixed at creation, escrow to charity, Long Now approves and adjudicates. Alive at low volume. **Durable:** an institution holds name and escrow. **Weak:** one adjudicator.

**Preregistration.** Hypotheses fixed before data; Registered Reports (2013) accept at that stage; trial registration enforced by journal editors (2005) and US law (2007) (memory). **Durable:** outside enforcement. **Failure:** COMPare (2015-16) found widespread outcome switching because nobody compared registry to paper (memory).

**IETF.** "Rough consensus and running code"; RFC 7282 says objections are answered, not counted. 38 years, rotating chairs. **Durable:** running code is an external test.

**Debian (constitution 1998).** General Resolutions with discussion periods, yearly-elected leader, 3:1 to amend the constitution, assets held by SPI. Founder left 1996. **Durable:** person-independent procedure plus a legal asset holder.

**"Proof of truth" / "credibility ledger".** No established system by either name: a scored-claims manifesto, a ZK prover network, pre-launch tokens, a personal habit, credibility-score patents. Closest crypto analog: TruQuest, an Ethereum promise tracker planned on EAS, with no evidence of use. I found no DAO promises registry with pre-registered falsification lines and named human sign-off.

## Mechanism table

| Assembly mechanism | Nearest prior art | Same | Different |
|---|---|---|---|
| SAYS + public LINK, no account needed | Wikipedia verifiability | Claim must point to a source anyone can open | Assembly never removes an unsourced claim; it stays OPEN |
| WRONG IF fixed before checking | Preregistration; Metaculus/Polymarket resolution criteria | Falsification terms locked before outcome | Applied to facts about the present, not only predictions |
| Two non-writer members post what they saw | Code review "non-author approves"; two-person rule | Writer cannot close own claim | Requires the observation itself, not just approval; no diversity requirement (Community Notes requires disagreeing raters) |
| Bare HOLDS counts for nothing | Community Notes requires sources in notes | Evidence over assent | Applied to the verifier, not the claimant |
| CAN'T TELL after 30 days | Community Notes "needs more ratings"; Polymarket 50-50 | Honest non-result | No escalation court, by design |
| Nothing removed, changes are new dated lines | Wikipedia history; EAS revocation; Certificate Transparency | Append-only | Plain text, human-readable, no software needed |
| Hash posted outside, OpenTimestamps, daily archive copy | Certificate Transparency gossip; Bitcoin anchoring | External witness of the file's state | Same, cheaper |
| No scores | Opposite of Metaculus, Good Judgment, Kleros, CN rater helpfulness | n/a | Deliberate; drops the main durability tool of forecasting sites |
| AI may help, never posts a result | Community Notes since 2025: AI writes, humans rate | Human holds the verdict | Assembly is stricter: AI cannot even author the claim's check |
| Promise: WILL / BY / KNOWN BY / IF BROKEN | Long Bets; UMA assertion | Terms fixed in advance, public resolution source | No stake, no adjudicator; loss is a word under a name |
| No new promise to pay while in default | Credit default exclusion; UMA bond forfeiture | Default blocks further credit | Reputational only |
| 7 days, 4 yeses, at most 1 object | Debian GR; IETF last call | Waiting period, supermajority | Counts objections (IETF says answer them); same bar for rules and acts (Debian raises it for the constitution) |
| Anyone may copy and run it | Forks: Debian, Bitcoin, open-sourced CN algorithm | Exit right | Same |
| Single-person steps are bugs with dates | BIP editors as clerks; Debian's anti-single-point design | Remove discretionary chokepoints | Written as a dated public bug list; I found no direct precedent |
| Written failure condition | Sunset clauses; startup kill criteria | Pre-stated end test | Applied to the institution itself, in its own rules |
| 4-of-7 multisig, promise before / fact after | Safe treasuries + Snapshot; Zcash grants committee; Optimism Grants Council | Multi-signer custody, public spending proposals | Small; but it is a pool, which rule 5 forbids |

## Verdict

**Narrowly novel (I found no precedent for these four in combination, and only weak precedent for each alone):**
1. Preregistered falsification lines (WRONG IF) attached to *present-tense facts* in a group's working record, not just to predictions or studies.
2. A verifier must state the observation (the number, words or date) and which WRONG IF lines they tested. Assent alone is void.
3. A dated public register of every step only one person can do, treated as bugs.
4. The institution's own failure test, written into its rules with a number and date, applied to itself.

Each is an old idea (preregistration, show-your-work, single-point audit, sunset clause) moved somewhere new; the novelty is the packaging: one screen, no token, no adjudicator.

**Reinventions, rated:**
- Link-backed claims: Wikipedia. *Equal.*
- Append-only log with an external hash: Certificate Transparency and OpenTimestamps. *Equal and cheaper.*
- Pre-fixed resolution terms: Long Bets and Metaculus. *Better* for facts, because there is no adjudicator. *Worse* for promises, because there is no stake.
- Two-witness close: code review. *Worse than Community Notes*, which requires agreement across people who usually disagree. (Collusion is already under RISKS WE ACCEPT.)
- 7-day supermajority: Debian and IETF. *Equal.* Slightly worse than IETF because objections are counted rather than answered.
- Fork right: *equal.*
- The multisig extension: Safe/Snapshot treasuries. *Equal mechanically.* It reverses rule 5, and every crypto precedent above that held money (Zcash, Gitcoin, UMA, Optimism) spent most of its governance energy on that money. The outline's "febu's heir" warning is backed by the record.

**Durable mechanisms worth borrowing that fit the constraints (plain language, no token, no scores, no single-person step, no AI decision):**
1. **A bridging rule (Community Notes), scoreless version:** "The two checkers who close an entry may not be the same two who closed the writer's last closed entry."
2. **Answer objections instead of counting them (IETF RFC 7282):** an "object" must say what would change the objector's mind. (WRONG IF for decisions).
3. **Entrench the core rules (Debian 3:1):** changing rules 3 or 7 needs more than ordinary acts, for example six yeses.
4. **Stage-1 review of WRONG IF (Registered Reports):** before any SEEN counts, any member may post "WRONG IF does not test SAYS" and the entry waits for a rewrite.
5. **Outcome-switch audit (the COMPare failure):** rule 6's weekly check should also confirm that no WRONG IF line changed after its first SEEN.
6. **Clerk-only editors (BIP model):** two or three members with write access whose only job is transcribing chat posts into SEEN lines. Fixes KNOWN BUGS 1 without granting judgment.
7. **Let non-members close entries:** Nupedia and Citizendium died of a small approval pool; let any stranger's SEEN line count if it names what they saw.

**What the 10+ year survivors share** (Wikipedia, Debian, IETF, Bitcoin, Long Bets, Metaculus/GJ, preregistration):

| Shared trait | Assembly |
|---|---|
| Written procedure that outlived its founder | Has it on paper; untested, and the file is Z's (KNOWN BUGS 1) |
| Contribution open to strangers at near-zero cost | Partial: strangers can reopen, only 7 members can close |
| Rotating or elected roles, nobody indispensable | Has the rule 6 rotation; nothing else rotates yet |
| An institution or many independent operators holding name, servers and assets (WMF, SPI, ISOC, Long Now, node operators) | Lacks: one person, Vercel, GitHub |
| An outside party that needs the output (readers, shipping software, journals, law, traders) | Lacks: the subject (febu) has stopped. The ledger has no consumer outside the seven |
| Fork right | Has it |
| Either no money held, or money held by a legal entity under procedure | Has "no money held" today; the multisig would move it to "money held, no entity" |

Bottom line: a careful recombination, better than most crypto attempts because it holds no token and no court. What would keep it alive is what it borrows least: an open contributor pool, an outside reader, an institutional host. What the prior art says would kill it is the money in the extension. Its stated experiment, whether seven people will check each other's links, is the right first test: every survivor above first proved people would do the boring check unpaid.

## Sources

rstreet.org (AI writers on Community Notes, 2026); indicator.media (8 AI bots write 50%); theblock.co/post/348171 and decrypt.co/311634 (UMA whale); cointelegraph.com (Zcash dev fund 2028 debate); zechub.wiki (development fund); gov.gitcoin.co/t/20333 (Grants Stack sunset); gov.optimism.io/t/10024 (Retro Funding S8); longbets.org/rules; github.com/TruQuest/TruQuest; github.com/smartcontracts/eas-contracts; cityam.com (Proof-of-Truth); blog.succinct.xyz; antoinebuteau.com (credibility ledger).
