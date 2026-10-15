# Facts check for the CTO / Squads design (2026-10-14)

Scope: ASSEMBLY_SYSTEM_OUTLINE_20261014.md sections 6 and 8, ledger.txt v2.1. Chain reads: public RPC, `python -I`, pattern from febu-assembly/checks/common.py. No tracing past the payee.

## 1. Fee account BGa8RYiu... since 2026-09-22 00:00 UTC

**What the account is: CONFIRMED.** `getAccountInfo`: owned by the SPL Token program, a native WSOL token account. Its token authority is FwCYHHuANWju3iUxV87M9zxuJEUDfLFhhuGqgr5ULcfx, which I re-derived as the PumpSwap PDA `["creator_vault", ApWpkd8...]` under pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA. So it is the PumpSwap coin-creator vault ATA for wallet ApWpkd8, not a plain wallet.

**Balance now: CONFIRMED.** 11.125224593 SOL at 2026-10-14 19:07 UTC (`getBalance`). That includes 0.00203928 SOL token-account rent, so claimable is about 11.1232 SOL. The note's "about 11 SOL waiting" holds.

**Balance at 2026-09-22 00:00 UTC: CONFIRMED.** 3.873236909 SOL (post-balance of the last pre-cutoff tx, 2026-09-21 23:23:21 UTC, equal to the pre-balance of the first in-window tx).

**Net arrival since 09-22: +7.251987684 SOL** (11.125224593 - 3.873236909).

**Signatures since 09-22:** 6,583 (2,802 failed, 3,781 succeeded), paginated with `before`. Busiest days: 09-22 1,053 and 10-09 1,631; most days 30-500.

**Total arrived / total claimed out: PARTLY CONFIRMED.**
- Claimed out since 09-22: **0 SOL found.** I could not read all 3,781 successful txs: the public RPC throttled `getTransaction` to about 0.2 per second, hours for a full pass. Three narrower checks instead:
  1. 41 of the 6,583 txs also touch ApWpkd8. 40 are failed third-party txs with zero change. The 41st is the 09-22 17:52 UTC sale (ledger fact 2), which raised the account by +0.181665782 SOL (a creator fee paid in).
  2. A claim pays into ApWpkd8's WSOL ATA FAvzFneQDq9uWJZb6eMqNJupc7G7PTpeAqDUoy6AbryQ (derived locally). It has one tx since 09-22, at 09-22 17:53:59 UTC. That tx does not include BGa8, and its logs read `ClaimCashbackV2`, so it is not a claim from the fee account. The ATA's previous tx was 2026-09-14 21:08 UTC, matching the ledger's "nothing since 09-14".
  3. The balance rose from 3.873 to 11.125 SOL.
  Not proven: that no tx among the 3,781 removed SOL while others added more.
- Arrived: **7.251987684 SOL, assuming no outflow.** Per-transaction rows were not produced (see above). I did not inspect the pool account for unswept creator fees (see item 2).

**Side observation (public wallet only).** ApWpkd8 holds 3,223.710139844 SOL (`getBalance`, today). 787 txs since 09-22 reference it; the newest is 2026-10-14 11:55:57 UTC (failed). I did not check which it signed. The note says the creator "has not claimed since 09-14"; that is consistent with what I found. Whether the wallet counts as "abandoned" for pump.fun is not something I verified.

## 2. Fee mechanics

**Pull, not push, with a twist: CONFIRMED.**
- `docs/instructions/COLLECT_CREATOR_FEE.md`: creators accrue in a bonding-curve vault (Pump, `collect_creator_fee_v2`) and an AMM vault (PumpSwap, `collect_coin_creator_fee`).
- `docs/instructions/SWEEP_FEES.md`: newer trade instructions (`buy_v3`/`sell_v3`, `buy_v2`/`sell_v2` on PumpSwap) do not pay the creator fee per trade. They hold it in `Pool.creator_fees` until the permissionless `sweep_creator_fee`. So BGa8 holds only what old-style trades paid or sweeps moved. Not checked: how much sits unswept in the $FEBU pool, so the "stream" read from BGa8 may understate fees accrued.

**Claim instruction and program: CONFIRMED.** PumpSwap `collect_coin_creator_fee`. In pump_amm.json it has no signer; the doc calls it "permissionless: anyone can call it". It moves WSOL from the vault ATA to the coin creator's WSOL token account, which must exist. Sources: https://github.com/pump-fun/pump-public-docs/blob/main/docs/instructions/COLLECT_CREATOR_FEE.md and /idl/pump_amm.json. An older doc (PUMP_SWAP_CREATOR_FEE_README.md) says the creator must sign; the current IDL supersedes it.

**Recipient can be a Squads vault PDA: PARTLY CONFIRMED.** The doc requires only that the creator account is non-executable and not owned by the Pump Fees program. A Squads vault is a system-owned PDA, so it fits the stated rules. No pump.fun doc or IDL says a multisig/PDA is allowed and I found no worked example.

**How a CTO is executed: CONFIRMED (IDL).** pump.json `admin_cto` is signed by pump's `admin_set_creator_authority` key and takes `new_creator: Option<pubkey>`; `admin_cto_pool` needs pump's pool-authority PDA. pump.fun performs it, not the applicant.

## 3. The CTO application

- **Criteria: CONFIRMED (primary).** @Pumpfun, 2025-07-18: "there needs to be indisputable proof that the community wouldn't survive without the CTO lead(s)... if there's a reasonable conflict about who deserves the Creator Fees, then the Creator Fees WON'T be redirected"; pump.fun will not intervene in disputes. Eligible: bonding curve or PumpSwap. https://x.com/Pumpfun/status/1946290150859997678
- **Process: CONFIRMED.** Applicants complete the form; the team emails from cto@pump.fun only; unsolicited mail hurts the application. https://x.com/Pumpfun/status/1946290156455260281
- **Form URL: NOT CONFIRMED.** The link is an attachment I could not retrieve; no current pump.fun docs page found.
- **What the form asks: NOT CONFIRMED.** Not documented where I could reach.
- **Split to up to 10 wallets: CONFIRMED (secondary).** Jan 2026: creators and CTO admins "allocate specific percentages of fees to up to 10 wallets". Read via https://www.tradingview.com/news/cointelegraph:41ebfb523094b:0-pump-fun-says-creator-fees-may-have-skewed-incentives-plans-revamp/ and https://bravenewcoin.com/insights/pump-fun-introduces-creator-fee-sharing-system-to-rebalance-platform-incentives (the Cointelegraph URL itself returned 404).
- **Single-use limits: CONFIRMED, missing from the note.** (a) `CREATOR_FEE_SHARING.md`: `update_fee_shares_v2` "can only be called once per sharing_config (the admin is revoked after)". (b) Sept 2026 report quoting pump.fun: after a CTO "the new Coin Admin will be granted one update to the existing configuration before it is locked again" (https://www.mitrade.com/au/insights/news/live-news/article-3-2074250-20260910). (c) March 2026: each token gets one chance to redirect creator fees, then locked (https://cointelegraph.com/news/pump-fun-creator-fee-cap-update-memecoin-model); the article does not say whether it covers CTOs. A wrong vault address may be unfixable.
- **Discretion:** pump.fun decides "at its sole discretion" (BloFin, 2026-10-06, secondary).

## 4. Squads v4

- **Phantom as signer: CONFIRMED.** Docs list Phantom; Ledger Connect unsupported, use via Phantom. https://docs.squads.so/main/llms-full.txt
- **Arbitrary instructions from the vault: CONFIRMED.** TX Builder takes custom instructions for any program; vault transactions execute "atomically via CPI" once Approved, by a member with Executor permission. Same file.
- **Threshold change: PARTLY CONFIRMED.** Done in Settings as a transaction; only Voters count; changing it cancels all Active/Ready transactions. With no config authority, config changes go through normal member votes. The docs do not say outright that the change is voted at the old threshold; that is the implication.
- **Signers below threshold permanently: PARTLY CONFIRMED.** Docs warn a maximum threshold "may lead to access issues if control over one wallet is lost". I found no recovery path for an autonomous multisig; that is inference. With 4-of-7, four lost members lock the vault.
- **Cost: CONFIRMED with one conflict.** Costs page and getting-started: one-time 0.1 SOL Squads deployment fee + 0.001 SOL funding + about 0.0018 SOL rent (about 0.103 SOL). One search snippet said 0.05 SOL; the pages I read say 0.1. Network fees per action: change threshold 0.0042, add member 0.0037, remove member 0.0044, token withdrawal 0.0051 SOL. "Squads doesn't charge fees on other transactions." https://docs.squads.so/main/frequently-asked-questions/costs-of-using-squads
- **Program immutable: CONFIRMED on chain.** SQDS4ep65T869zMMBKyuUq6aD6EgTu8psMjkvj52pCf, ProgramData Fy3YMJCvwbAXUgUM5b91ucUVA3jYzwWLHL3MwBqKsh8n, `authority: null` (RPC, 2026-10-14). Docs say v4 immutable since Nov 2024 (https://x.com/SquadsProtocol/status/1859947607671607443); audits by OtterSec, Certora, Neodyme plus two formal verifications. No admin key exists to hold.

## 5. Any CTO fee redirected to a multisig

**NOT CONFIRMED: none found.** Searches turned up no documented case of a pump.fun CTO fee going to a Squads or other multisig.

## Things the design note gets wrong or leaves out

1. Section 8 says the claim is "a vault transaction ... Four signatures" and that the vault must sign pump.fun's claim. The claim has no signer; anyone can trigger it. Four signatures apply only to paying out of the vault, so the "first claim is the test" step tests nothing about signing.
2. "Accrues to a fee account": it is the PumpSwap vault ATA, and new-style trades leave fees in the pool until a permissionless sweep. Measure the pool's unswept amount before judging the stream.
3. The stream is not nothing: BGa8 rose by +7.25 SOL since 09-22 (11.125 SOL now). The ledger's "nothing paid out since 09-14" holds as far as I could check.
4. The 10-wallet split and the CTO config are single-use; the note does not say a wrong address may lock.
5. Squads costs 0.1 SOL to deploy (about 0.103 SOL all in), not an unstated small amount.
6. "pump.fun's CTO form names the vault": the form's fields and URL are unverified.
7. Not checked: whether pump.fun's tooling accepts an off-curve PDA as `new_creator`, and how it handles the WSOL ATA owned by one.
