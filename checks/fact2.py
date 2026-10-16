"""Fact 2 from the chain: the creator wallet's $FEBU in the sale the ledger links, and its $FEBU now.

    python checks/fact2.py

Reads only. Prints what it saw, for a person to compare with the ledger and post; it posts nothing.
"""
from decimal import Decimal

from common import B58, RPC, entry, find, host_of, now, rpc, short, signers, token_changes, tx, when

fact = entry(2)
sale = find(r"solscan\.io/tx/(%s)" % B58, fact, "fact 2's sale")
wallet = find(r"solscan\.io/account/(%s)" % B58, fact, "fact 2's wallet")
mint = find(r"\$FEBU token,\s+(%s)" % B58, entry(1), "the $FEBU token in fact 1")
says = find(r"([\d,]+\.\d+) tokens", fact, "fact 2's amount")

r = tx(sale)
mine = [(a, b) for acct, owner, m, a, b in token_changes(r) if owner == wallet and m == mint]
held = rpc("getTokenAccountsByOwner", [wallet, {"mint": mint}, {"encoding": "jsonParsed"}])["value"]

print("Fact 2, read %s from %s" % (now(), host_of(RPC)))
print("The ledger says: the wallet sold all %s $FEBU in one transaction, and received none after it through 2026-10-14."
      % says)
print("Below: its $FEBU now. For $FEBU coming in after the sale, open its transfers (fact 1's link), filtered to $FEBU.")
print()
print("The sale, transaction %s" % short(sale))
print("  time              %s" % when(r["blockTime"]))
print("  failed            %s" % ("no" if r["meta"]["err"] is None else r["meta"]["err"]))
print("  signed by wallet  %s" % ("yes" if wallet in signers(r) else "no"))
if mine:
    print("  wallet's $FEBU    %s before, %s after" % ("{:,}".format(sum(a for a, _ in mine)),
                                                       "{:,}".format(sum(b for _, b in mine))))
else:
    print("  wallet's $FEBU    not in this transaction")
print()
print("The wallet's $FEBU now (%s)" % short(wallet))
if not held:
    print("  no $FEBU token account")
for a in held:
    print("  token account %s holds %s" % (short(a["pubkey"]), "{:,}".format(
        Decimal(a["account"]["data"]["parsed"]["info"]["tokenAmount"]["uiAmountString"]))))
