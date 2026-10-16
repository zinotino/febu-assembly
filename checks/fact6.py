"""Fact 6 from the chain: re-add fact-6-steps.txt's 44 rows, then re-read each row's transaction, and step 1's trade.

    python checks/fact6.py

Reads only, about 50 requests to a public node (a minute or two). Prints what it saw, for a person to compare with
the ledger and post; it posts nothing.
"""
import re
from decimal import Decimal

from common import B58, RPC, WSOL, entry, find, host_of, keys, now, sol_change, short, signers, text, token_changes, tx, when

ROW = re.compile(r"^\s*(\d+)\s+(\d{4}-\d\d-\d\d \d\d:\d\d)\s+(\d+(?:\.\d+)?)\s+(?:https://solscan\.io/tx/)?(%s)" % B58, re.M)
TOTAL = re.compile(r"^\s*total\s+(\d+(?:\.\d+)?)\s*$", re.M)


def rows(steps):
    """[(row number, 'date time', SOL as Decimal, signature)] and the total line, as the steps file has them."""
    got = [(int(n), d, Decimal(sol), sig) for n, d, sol, sig in ROW.findall(steps)]
    total = TOTAL.search(steps)
    return got, Decimal(total.group(1)) if total else None


def arrived(r, wallet, amount):
    """How the row's amount reached the wallet: as WSOL in a token account it owns, or as SOL (adding back the network
    fee when the wallet paid it). "none" when nothing left the fee account; "less" when the wallet is not even in
    the transaction."""
    if not amount:
        return "none"
    if sum(b - a for _, owner, m, a, b in token_changes(r) if owner == wallet and m == WSOL) == amount:
        return "WSOL"
    if wallet not in keys(r):
        return "less"
    got = sol_change(r, wallet) + (Decimal(r["meta"]["fee"]) / 10 ** 9 if keys(r)[0] == wallet else 0)
    return "SOL" if got == amount else "SOL+more" if got > amount else "less"


def main():
    steps, fact = text("fact-6-steps.txt"), entry(6)
    fee_account = find(r"solscan\.io/account/(%s)" % B58, fact, "fact 6's fee account")
    wallet = find(r"other than (%s)" % B58, fact, "fact 6's wallet")
    ledger_total = find(r"add up to ([\d,]+\.\d+)", fact, "fact 6's total")
    sale = find(r"STEP 1.*?solscan\.io/tx/(%s)" % B58, steps.replace("\n", " "), "step 1's trade")
    table, total = rows(steps)

    print("Fact 6, read %s from %s" % (now(), host_of(RPC)))
    print("Fee account %s, creator wallet %s" % (short(fee_account), short(wallet)))
    print()
    r = tx(sale)
    ch = token_changes(r)
    payouts = [a - b for _, _, m, a, b in ch if m == WSOL and b < a]
    fee = sum((b - a for acct, _, _, a, b in ch if acct == fee_account), Decimal(0))
    said = ("the pool paid out %s WSOL; the fee account got %s (%.3f%% of it)" % (max(payouts), fee,
            fee / max(payouts) * 100) if payouts else "no WSOL left any account; the fee account got %s" % fee)
    print("Step 1, the trade %s at %s: %s" % (short(sale), when(r["blockTime"]), said))
    print()
    print("Step 3, every row:")
    print("  row  time on chain            SOL in the row   out of the fee account  same  arrived as  signed by wallet")
    seen = []
    for n, d, sol, sig in table:
        r = tx(sig)
        out = sum((a - b for acct, _, _, a, b in token_changes(r) if acct == fee_account), Decimal(0))
        seen.append((n, d, sol, r, out, arrived(r, wallet, out)))
        print("  %3d  %s  %15s  %22s  %-4s  %-10s  %s%s" % (   # SOL has 9 places, so .9f rounds nothing
            n, when(r["blockTime"]), sol, format(out, ".9f"), "yes" if out == sol else "NO", seen[-1][5],
            "yes" if wallet in signers(r) else "no", "" if r["meta"]["err"] is None else "  FAILED %s" % r["meta"]["err"]))

    nums = [n for n, *_ in table]
    pick = lambda test: [n for n, d, sol, r, out, how in seen if test(d, sol, r, out, how)] or ["none"]
    print()
    print("Step 4 and the rest, in sum:")
    print("  rows in the file                    %d, numbered %s" % (
        len(nums), "1 to %d" % len(nums) if nums == list(range(1, len(nums) + 1)) else nums))
    print("  the SOL column adds up to           %s (the file's total line: %s; the ledger: %s)"
          % (sum(sol for _, _, sol, _ in table), total, ledger_total))
    print("  out of the fee account, not = row   %s" % ", ".join(map(str, pick(lambda d, sol, r, out, how: out != sol))))
    print("  time on chain, not the row's minute %s" % ", ".join(map(str, pick(
        lambda d, sol, r, out, how: when(r["blockTime"])[:16] != d))))
    print("  failed transactions                 %s" % ", ".join(map(str, pick(
        lambda d, sol, r, out, how: r["meta"]["err"] is not None))))
    print("  not signed by the wallet            %s" % ", ".join(map(str, pick(
        lambda d, sol, r, out, how: wallet not in signers(r)))))
    for how, said in (("SOL", "arrived as SOL, exactly"), ("SOL+more", "arrived as SOL, plus more"),
                      ("WSOL", "arrived as WSOL in its account"), ("less", "arrived short of the row"),
                      ("none", "nothing left the fee account")):
        print("  %-35s %s" % (said, ", ".join(map(str, pick(lambda d, sol, r, out, h: h == how)))))
    print()
    print("Not read here: whether anything left the fee account from 2026-09-15 to the end of 2026-10-14. Thousands")
    print("of trades touched it; resolve.py fact8 and door2 read the two ways out instead (fact 8's NOTE).")


if __name__ == "__main__":
    main()
