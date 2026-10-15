# The system that pulls it together: priced resolvers, funded as experiments (2026-10-14)

Working paper for Z, written after Witness's tweet about a finite supply and halving, and Witness's offer to fund
experiments. It builds on ASSEMBLY_SYSTEM_OUTLINE_20261014.md (sections 6-12) and the simulations P187 and P190.
Theory on top of a simulation built on my guesses. Nothing here has been run on real people. No dollar figures: rule 5
forbids a post in the group's name from stating a price, and this is the file a post would be drawn from.

## 1. The thesis

Bitcoin does not pay for work. It pays for work that a stranger can verify for free. Miners show up because a hash
costs real effort to find and one step to check. The halving, the cap and the difficulty rule are tuning around that
one asymmetry, and they do nothing without it.

febu's whole record is the reverse: speech that costs nothing, and validation words with no validator behind them
(the -1 map: zero validator columns on any surface). The ideal system is the validator column febu never built, with
a price on it.

> A claim is payable only if it ships a resolver: a short script anyone can run against a public record that says
> which WRONG IF lines tripped. Writing one costs work. Running one costs nothing. Money attaches to that asymmetry
> and nowhere else.

That is the impure-boundary principle as a rule: the interior (what anyone says) is null, all signal is at the boundary
(a record nobody in the room controls), so only the boundary can carry money.

## 2. The map from Bitcoin

| Bitcoin | Here |
|---|---|
| A nonce that hashes under the target | A resolver that gets a held-out case right |
| The target, fixed by protocol | A held-out case, committed by hash before anyone starts: H(case, answer). The answer comes from the chain, not from the committer |
| Any node re-hashes in one step | Anyone runs the script |
| Block reward, capped supply | A funder's promise: total paid is at most F, stated up front |
| Halving | The payout ladder halves every K accepted resolvers |
| Difficulty adjustment | The ladder is indexed to the measured minutes per check and stops at the floor |
| Fees, once the subsidy is gone | Bounties posted by someone other than the funder |
| Miners need no name | Still names. A member signs every resolver and answers for it. An AI may draft it and never posts a result |

## 3. What this fixes in the simulation's open holes

- Rubber stamp (P187): an approve-everything resolver fails the held-out case when the answer is false. Approving is
  no longer free.
- Trivial-truth farm: a resolver for a claim that cannot be false has no WRONG IF case in the past data, so it has no
  control pair and is not payable. Easy entries are still allowed in the ledger, just not paid.
- Who plants the false claims (P190's open question): nobody does. A held-out case is a past chain fact with a known
  answer, committed by hash. The committer cannot be fooled about it and cannot judge it. Reality plants.
- AI checks are cheap to produce and hard to verify (outline section 7): not for a script. Reading AI prose is hard;
  executing deterministic code against an RPC is one command. The AI's output becomes checkable by running it.
- Sybils: payment goes to a resolver that reproduces, not to an account. Ten accounts reproducing the same script is
  still one resolver.

What it does not fix: a resolver can be wrong in the same way for every model that drafts it (P190: a 10% shared blind
spot broke every holding design). The held-out case and a person reading about 30 lines are the defence, and E3 below
measures how much that defence is worth.

## 4. How it fits version 3 without a rule change

- Witness's money is a PROMISE (WILL pay, BY, KNOWN BY the payment transaction, IF BROKEN a $FEBU bond). Rule 5 as
  written: wallet to wallet, promise kept. No vault, no pool, no treasury, the group pays nobody.
- The bounty's condition is mechanical: the resolver passes the committed case and two other members post SEEN lines
  that ran it and got the same output. Witness judges nothing. If the condition is met and Witness does not pay,
  that is BROKEN and the bond burns. That is the enforcement the sim said was missing, a loss that can be collected.
- Rule 5 says the only token used is $FEBU. So the payout is $FEBU, or the group changes rule 5 under rule 7. Paying
  in $FEBU means buying it, and every buy pays a fraction to the creator vault, which `ApWpkd8` can claim (KNOWN BUGS
  5). The experiment would fund its own subject. Disclose it in the promise.
- A resolver today prints what it saw and a person compares (checks/fact6.py says so). A resolver for payment also
  prints which WRONG IF lines tripped. That is a small change to common.py, not a new system.

## 5. The funding ladder

F is Witness's total. K accepted resolvers per epoch. The payout per accepted resolver starts at r0 and halves each
epoch, so after j epochs the total is K * r0 * (2 - 2^(1-j)), and never more than 2 * K * r0 = F. The cap is arithmetic,
not a treasury. The early premium pays whoever writes resolvers while nobody knows if the idea works, which is the
real reason Bitcoin front-loads.

The limit: the simulation's holding band was pay at 2.5 to 7.5 times a check's cost. That is a factor of 3, under two
halvings. So the ladder must be indexed to the measured cost (the 30-day minutes), and it stops at the floor instead of
decaying below it. Example in made-up units: check cost 0.4, so the band is 1 to 3; r0 = 3, K = 10; epoch 1 pays 30,
epoch 2 pays 15, epoch 3 would pay 0.75, under the floor, so stop. Total 45, and the third epoch needs a new promise
or does not happen.

After the floor the subsidy is gone and the question is Bitcoin's own: does a fee market exist. That is E5.

## 6. The dev wallet

`ApWpkd8` is the creator and dev wallet. Read on 10-14, 19:07 UTC: it holds 3,223.71 SOL, has transactions to that
day, and has not claimed its creator fee since 09-14 (11.125 SOL waiting, about 10 SOL a month arriving). Anyone may
trigger the claim, and it pays the creator, not the sender. From the 10-09 pass: 0 $FEBU since the 09-22 exit, and
since 10-01 mostly swaps of other tokens, 7 times a fixed ~3.96 SOL buy followed about two minutes later by a sell.

What it is for the system:
- The subject. Every money claim febu made is a claim about this wallet: the buyback, the chest, the jobs, the fee.
  Resolvers about it need no one's word, and nobody in the group can move it.
- The one fixed reference. The 10-08 call believed a recurring ~900k-token buy; the 10-09 chain pass refuted it from
  the signatures. Under this system that claim would have shipped with a resolver or stayed unpaid.
- Febu's only unforgeable identity left. The X account is suspended and the sites are frozen. A signature from this wallet
  over a ledger entry's hash is the one answer from febu a stranger can verify. The ledger can leave a standing
  invitation for it. It cannot send anything to the wallet.

What it must not be:
- A purse. The group has no key and takes none. Claiming its fee makes the group an heir and a treasury (red team 3).
- A recipient. A dust $FEBU transfer to it makes fact 2's WRONG IF literally true (red team 1). Nothing in this
  system sends to it, including a message.
- A bettor's counterparty. Whoever can move the wallet can win any bet on it, which is job #004 again. Forecasts about
  it carry no payout that depends on the outcome; the funded prize goes to calibration against the base rate, small
  and capped, and anyone who could act on the wallet says so first.

## 7. The experiments Witness could fund

Each states the number that would count against it, before it runs. All thresholds are my guesses from the sim.

| # | Question | Cost | Counts against if |
|---|---|---|---|
| E0 | Do seven people check at all, unpaid? | 0 (the 30-day dry run) | fewer than three closed entries in 30 days |
| E1 | Is writing a resolver much harder than reproducing one? | one small bounty | median minutes to reproduce are over a fifth of minutes to write |
| E2 | Does the held-out case catch lazy resolvers? | one case, committed by hash | fewer than a quarter of submitted resolvers fail it (the sim needed 25 to 50 percent planted) |
| E3 | How shared is the AI blind spot? | 3 models draft the same 20 resolvers | the models fail the same way on more than a tenth |
| E4 | Does pay move reproduction? | two arms, 1x and 3x on the same task | reproduction rates match; pay is not the lever, so stop paying |
| E5 | Once the subsidy stops, does anyone post a bounty? | 0 | no unfunded bounty in 30 days (zero strangers is a result too) |

Order: E0 now, then E1 and E2 together on one claim about the dev wallet (the fee unclaimed since 09-14 is already
fact 8), then E3 and E4, then E5. A failed E1 or E2 stops the rest. That is the cheapest way to find out the whole
design is wrong.

## 8. What is still unsolved

- Most of febu's claims have no record a script can read (27.9% are ungateable by the earlier measure). They stay
  unpaid in the ledger and the system says nothing about them.
- Resolver correctness is a person reading code. Two people agreeing in advance can still bless a bad script. The
  held-out case narrows it. It does not close it.
- The multipolar trap, as in outline section 11. A priced resolver does not change what anyone wants. It makes one kind
  of defection (an unverifiable claim collecting money) cost more.
- Funding in $FEBU sends part of every buy to the wallet under study. Funding in SOL breaks rule 5. Pick one in the
  promise and say which.
