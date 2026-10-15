"""Resolvers for ledger facts 1, 3, 4, 8 and 9: scripts that say which WRONG IF lines tripped, tried on known-answer controls.

    python checks/resolve.py test9    fact 9: the real transaction, 2 real controls, 5 one-change copies, 4 lazy resolvers
    python checks/resolve.py fact8    fact 8's three lines on the live chain (about a minute)
    python checks/resolve.py door2    fact 8's other way out: was the vault paid out through pump's creator vault? (3 minutes)
    python checks/resolve.py fact1    fact 1: the creator wallet's $FEBU account in the window
    python checks/resolve.py fact3    fact 3: the phrase in the archived script, and the tweet id's time
    python checks/resolve.py fact4    fact 4: the book rotation over the scripture copy (Z's copy, KNOWN BUGS 3)
    python checks/resolve.py claimsim dry-run the fee claim from a stranger's address: does it need the creator to sign?
    python checks/resolve.py --test   offline checks of the pure parts

Reads ledger.txt and checks/common.py, so it tests what the ledger says. Public node, no key, read-only. Sends nothing:
claimsim and door2 only ask the node to dry-run a transaction. Posts nothing. An incomplete read is never HOLDS: it says
CAN'T TELL. A person reads the output, opens a link by hand, and posts.
"""
import base64
import copy
import datetime as dt
import hashlib
import json
import re
import sys
import urllib.request
import time
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))   # common.py and fact6.py sit beside this file
import common as c  # noqa: E402
from fact6 import rows  # noqa: E402

UTC = dt.timezone.utc
CREATOR_RUN_ROW_19 = "3RctBzwYbFMxSTTtCUUxunF1ruFLeqb6pijVy3zKQLDWp4etD9znKSdSCoAp4Em4QKTVBWJFNdXtr9LNfHgJnZJs"


# ---------- fact 9: one transaction, four lines ----------

def lines9(r, signer, vault, word):
    """The tripped state of each WRONG IF line of fact 9, read from one parsed transaction."""
    logs = " ".join(r["meta"]["logMessages"] or [])
    return {"signer is not %s" % c.short(signer): signer not in c.signers(r),
            "logs show no %s" % word: word not in logs,
            "%s not among its accounts" % c.short(vault): vault not in c.keys(r),
            "the transaction failed": r["meta"]["err"] is not None}


def verdict(tripped):
    return "DOESN'T HOLD" if any(tripped.values()) else "HOLDS"


def params9():
    f = c.entry(9)
    return (c.find(r"solscan\.io/tx/(%s)" % c.B58, f, "fact 9's transaction"),
            c.find(r"signer is (%s)" % c.B58, f, "fact 9's signer"),
            c.find(r"acts through is\s+(%s)" % c.B58, f, "fact 9's account"),
            c.find(r"logs show no (\w+)", f, "fact 9's log word"))


def mutants(r, signer, vault, word):
    """The real transaction with one thing changed each. Each must flip to DOESN'T HOLD on exactly that line."""
    out = {}
    m = copy.deepcopy(r)
    for k in m["transaction"]["message"]["accountKeys"]:
        if k["pubkey"] == signer:
            k["signer"] = False
    out["signer did not sign"] = m
    m = copy.deepcopy(r)
    m["meta"]["logMessages"] = [l.replace(word, "Other") for l in m["meta"]["logMessages"]]
    out["log word missing"] = m
    m = copy.deepcopy(r)
    for k in m["transaction"]["message"]["accountKeys"]:
        if k["pubkey"] == vault:
            k["pubkey"] = "1" * 44
    out["account missing"] = m
    m = copy.deepcopy(r)
    m["meta"]["err"] = {"InstructionError": [0, "Custom"]}
    out["transaction failed"] = m
    return out


LAZY = {   # each is a plausible shortcut: fewer lines, same shape of answer
    "always holds": lambda t: {},
    "logs only": lambda t: {k: v for k, v in t.items() if "logs" in k},
    "signer only": lambda t: {k: v for k, v in t.items() if "signer" in k},
    "forgot 'failed'": lambda t: {k: v for k, v in t.items() if "failed" not in k},
}


def test9():
    sig, signer, vault, word = params9()
    r = c.tx(sig)
    cases = [("the claimed transaction", r, signer, "HOLDS"),
             ("claim with one letter of the signer changed", r, signer[:-1] + ("A" if signer[-1] != "A" else "B"),
              "DOESN'T HOLD"),
             ("real: row 19, a creator-run claim", c.tx(CREATOR_RUN_ROW_19), signer, "DOESN'T HOLD")]
    cases += [("one change: " + n, m, signer, "DOESN'T HOLD") for n, m in mutants(r, signer, vault, word).items()]
    print("Fact 9, read %s from %s\n" % (c.now(), c.RPC))
    print("%-48s %-13s %-13s %s" % ("control", "expected", "honest", "  ".join(LAZY)))
    caught = {n: 0 for n in LAZY}
    for name, tx, sg, want in cases:
        t = lines9(tx, sg, vault, word)
        row = []
        for n, f in LAZY.items():
            ok = verdict(f(t)) == want
            caught[n] += not ok
            row.append(("pass" if ok else "FAIL").ljust(len(n)))
        print("%-48s %-13s %-13s %s" % (name, want, verdict(t), "  ".join(row)))
        for line, tripped in t.items():
            if tripped:
                print("%-48s   tripped: %s" % ("", line))
    print("\nhonest resolver wrong on any control:", sum(verdict(lines9(t, s, vault, word)) != w for _, t, s, w in cases))
    print("controls each lazy resolver fails:", caught)


# ---------- fact 8: one account, a window, three lines ----------
# ASSUMES: every payment out of the fee account passes through the creator wallet's wrapped-SOL token account (the claim
# instruction needs it to exist). The fee account has ~170 transactions a day, that token account 3 since 09-14. A scan of
# the fee account read 250 of 5,226 in 569 s on the public node. The control below tests the assumption on fact 6's 44 rows.
# ASSUMES: the window (2026-09-15 to the end of 2026-10-14), 09-22 00:00 UTC and the 3.8 to 4.1 band are typed in from the
# ledger's WRONG IF lines as of 2026-10-15. Only the addresses and the 11.12 floor are read from the ledger text, so a
# CHANGED line needs a matching edit here.
# ponytail: a payout that skipped that account would be missed; the 44-row control is the evidence, not a proof.
# It is not a proof because a second call, open to any payer, moves the vault to pump's creator vault instead (claimsim, run 6).
# `door2` reads that vault. A fact 8 signature should cover both commands.

ALPHA = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
P = 2 ** 255 - 19
D = -121665 * pow(121666, -1, P) % P
TOKEN = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
TOKEN_2022 = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"   # $FEBU is a Token-2022 mint
ATA_PROGRAM = "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
ROW_20 = "3rJRommVgnUg7c3YtR1cRLbN7ojdGRv428szwUMwawkXXS5N2NsMYpmyPPd7FvEM9L1DziB1pRmmEcqKKHTQ4cJU"


def b58d(s):
    n = 0
    for ch in s:
        n = n * 58 + ALPHA.index(ch)
    return n.to_bytes(32, "big")


def b58e(b):
    n, out = int.from_bytes(b, "big"), ""
    while n:
        n, r = divmod(n, 58)
        out = ALPHA[r] + out
    return "1" * (len(b) - len(b.lstrip(bytes(1)))) + out


def on_curve(b):
    """Is this 32-byte value a valid ed25519 point? (A program-derived address must not be.)"""
    y = int.from_bytes(b, "little") & (2 ** 255 - 1)
    x2 = (y * y - 1) * pow(D * y * y + 1, -1, P) % P
    return x2 == 0 or pow(x2, (P - 1) // 2, P) == 1


def derive_ata(owner, mint, program=TOKEN):
    seeds = b58d(owner) + b58d(program) + b58d(mint)
    for bump in range(255, -1, -1):
        h = hashlib.sha256(seeds + bytes([bump]) + b58d(ATA_PROGRAM) + b"ProgramDerivedAddress").digest()
        if not on_curve(h):
            return b58e(h)


def day(y, m, d, h=0):
    return int(dt.datetime(y, m, d, h, tzinfo=UTC).timestamp())


def sigs_since(account, t0):
    out, before = [], None
    while True:
        page = c.rpc("getSignaturesForAddress", [account, {"limit": 1000, **({"before": before} if before else {})}])
        out += [s for s in page if s["blockTime"] >= t0 and s["err"] is None]
        if not page or page[-1]["blockTime"] < t0:
            return out
        before = page[-1]["signature"]


def fee_change(sig, account):
    """(blockTime, balance before, balance after) of the account's WSOL in one transaction, or None if unread."""
    for _ in range(4):
        try:
            r = c.rpc("getTransaction", [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 1}])
        except SystemExit:
            time.sleep(5)
            continue
        if r:
            ch = [(a, b) for acct, _, m, a, b in c.token_changes(r) if acct == account]
            return r["blockTime"], *(ch[0] if ch else (Decimal(0), Decimal(0)))
    return None


def touches(sig, account):
    for _ in range(4):
        try:
            r = c.rpc("getTransaction", [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 1}])
        except SystemExit:
            time.sleep(5)
            continue
        if r:
            return account in c.keys(r)
    return None


def fact8():
    f6, f8 = c.entry(6), c.entry(8)
    fee = c.find(r"solscan\.io/account/(%s)" % c.B58, f6, "fact 6's fee account")
    wallet = c.find(r"other than (%s)" % c.B58, f6, "fact 6's wallet")
    floor = Decimal(c.find(r"below\s+([\d.]+)\s+SOL", f8, "fact 8's floor"))
    t0, t_after, t_end, started = day(2026, 9, 14), day(2026, 9, 15), day(2026, 10, 15), time.time()
    ata = derive_ata(wallet, c.WSOL)
    r20 = c.tx(ROW_20)
    seen = [acct for acct, owner, m, a, b in c.token_changes(r20) if owner == wallet and m == c.WSOL and b > a]
    print("Fact 8, read %s from %s" % (c.now(), c.RPC))
    print("CONTROL, the derived WSOL account of %s is %s; fact 6's row 20 paid into %s: %s"
          % (c.short(wallet), c.short(ata), c.short(seen[0]) if seen else "?", "match" if seen == [ata] else "NO MATCH"))
    now_bal = Decimal(c.rpc("getTokenAccountBalance", [fee])["value"]["uiAmountString"])
    ends = sorted({s["signature"] for s in sigs_since(ata, t0)})
    fee_sigs = sigs_since(fee, t0)
    print("fee account %s holds %s. Since 2026-09-14 00:00 UTC: %d transactions on the creator's token account (to read), "
          "%d on the fee account (not read)" % (c.short(fee), now_bal, len(ends), len(fee_sigs)), flush=True)
    steps = [sig for _, _, _, sig in rows(c.text("fact-6-steps.txt"))[0]]
    with ThreadPoolExecutor(4) as pool:
        thru = list(pool.map(lambda s: touches(s, ata), steps))
        got = list(pool.map(lambda s: fee_change(s, fee), ends))
    print("CONTROL, the assumption: %d of fact 6's %d payments pass through that token account (%d unread)"
          % (thru.count(True), len(steps), thru.count(None)))
    missed = [s for s, g in zip(ends, got) if g is None]
    out = sorted((g[0], g[1] - g[2], s) for s, g in zip(ends, got) if g and g[2] < g[1])
    print("read %d, could not read %d, in %.0f s\n" % (len(ends) - len(missed), len(missed), time.time() - started))
    print("CONTROL, 09-14: expected exactly one payment out, fact 6 row 44 (6.868902687 SOL, 21:08)")
    for t, amt, s in out:
        if t < t_after:
            print("  %s  %s  %s" % (dt.datetime.fromtimestamp(t, UTC).strftime("%m-%d %H:%M"), amt, c.short(s)))
    since = [o for o in out if o[0] >= t_after]
    after = [o for o in since if o[0] < t_end]
    for t, amt, s in since:
        print("  PAYMENT OUT %s: %s  %s  %s" % ("in the window" if t < t_end else "after 10-14, outside the window",
                                               dt.datetime.fromtimestamp(t, UTC).strftime("%m-%d %H:%M"), amt, s))
    # The balance before 09-22's first transaction is its balance at 00:00 UTC.
    d22 = [s for s in fee_sigs if day(2026, 9, 22) <= s["blockTime"] < day(2026, 9, 23)]
    first, last = fee_change(d22[-1]["signature"], fee), fee_change(d22[0]["signature"], fee)
    lo, hi = first[1], last[2]
    print("\n09-22: %d transactions on the fee account; balance at 00:00 UTC %s, after the last %s" % (len(d22), lo, hi))
    lines = {"a payment out between 2026-09-15 and the end of 2026-10-14 shows": bool(after),
             "balance now below %s and no payment out explains it" % floor: now_bal < floor and not since,
             "balance at 00:00 UTC on 2026-09-22 outside 3.8-4.1": not (Decimal("3.8") <= lo <= Decimal("4.1"))}
    for line, tripped in lines.items():
        print("  %-62s %s" % (line, "TRIPPED" if tripped else "not tripped"))
    print("\nverdict:", verdict(lines) if not missed else "CAN'T TELL (%d transactions unread)" % len(missed))


# ---------- fact 1: a wallet bought no $FEBU in a window ----------
# ASSUMES: a swap that gets the wallet $FEBU credits its associated token account (Token-2022), so that account's
# transaction list holds every buy. Control: it is the account fact 2's sale moved $FEBU out of.
# ASSUMES: the window (09-29 to 10-09, whole days) is typed in from the ledger's WRONG IF as of 2026-10-14; only the
# addresses are read from the ledger text.
# ponytail: a buy credited to some other token account the wallet owns would be missed.

def fact1():
    f1 = c.entry(1)
    create = c.find(r"solscan\.io/tx/(%s)" % c.B58, f1, "fact 1's creating transaction")
    wallet = c.find(r"signer is\s+(%s)" % c.B58, f1, "fact 1's wallet")
    mint = c.find(r"\$FEBU token,\s+(%s)" % c.B58, f1, "the $FEBU token")
    start, end = day(2026, 9, 29), day(2026, 10, 10)   # "between 2026-09-29 and 2026-10-09", both days whole
    started = time.time()
    r = c.tx(create)
    logs = " ".join(r["meta"]["logMessages"])
    ata = derive_ata(wallet, mint, TOKEN_2022)
    sale = c.tx(c.find(r"solscan\.io/tx/(%s)" % c.B58, c.entry(2), "fact 2's sale"))
    seen = [a for a, owner, m, _, _ in c.token_changes(sale) if owner == wallet and m == mint]
    print("Fact 1, read %s from %s" % (c.now(), c.RPC))
    print("CONTROL, the derived $FEBU account of %s is %s; fact 2's sale moved $FEBU out of %s: %s"
          % (c.short(wallet), c.short(ata), c.short(seen[0]) if seen else "?", "match" if seen == [ata] else "NO MATCH"))
    sigs = sigs_since(ata, day(2026, 7, 8))
    got = []
    for s in sigs:
        t = c.tx(s["signature"])
        got.append((t["blockTime"], sum((b - a for _, owner, m, a, b in c.token_changes(t) if owner == wallet and m == mint),
                                        Decimal(0)), s["signature"]))
    print("%d successful transactions on that account since 2026-07-08, read in %.0f s:" % (len(got), time.time() - started))
    for t, d, s in sorted(got):
        print("  %s  %+.2f $FEBU  %s" % (dt.datetime.fromtimestamp(t, UTC).strftime("%m-%d %H:%M"), d, c.short(s)))
    gets = lambda a, b: any(a <= t < b and d > 0 for t, d, _ in got)   # the window rule the claim's third line uses
    first_in = min(t for t, d, _ in got if d > 0 and t > day(2026, 7, 9))
    print("CONTROL, the window rule: a window holding the 08-14 inflows trips: %s; one starting at an inflow's own second "
          "trips: %s; one ending at it does not: %s" % (gets(day(2026, 8, 13), day(2026, 8, 15)), gets(first_in, first_in + 60),
                                                      not gets(first_in - 60, first_in)))
    lines = {"that transaction does not create $FEBU": "InitializeMint" not in logs or mint not in c.keys(r),
             "ApWpkd8 did not sign it": wallet not in c.signers(r),
             "the wallet shows a swap 09-29..10-09 in which it gets $FEBU": any(start <= t < end and d > 0 for t, d, _ in got)}
    for line, tripped in lines.items():
        print("  %-62s %s" % (line, "TRIPPED" if tripped else "not tripped"))
    print("\nverdict:", verdict(lines))


# ---------- facts 3 and 4: one archived file, one rule over the scripture copy ----------

def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "curl/8"}), timeout=90).read()


def fact3():
    f = " ".join(c.entry(3).split())
    url = c.find(r"(https://web\.archive\.org/web/\d{14}if_/\S+)", f, "fact 3's archived script")
    phrase = c.find(r"Search the page for: (.+?) Febu's", f, "fact 3's phrase")
    tid = int(c.find(r"tweet id (\d+)", f, "fact 3's tweet id"))
    said = c.find(r"turns that id into (\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)", f, "fact 3's tweet time")
    stamp = c.find(r"web/(\d{14})if_", url, "the archive's stamp")
    saved = c.find(r"saved (\d{4}-\d\d-\d\d \d\d:\d\d) UTC", f, "fact 3's save time")
    made = dt.datetime.fromtimestamp(((tid >> 22) + 1288834974657) / 1000, UTC).strftime("%Y-%m-%d %H:%M:%S")
    page = get(url).decode("utf-8", "replace")
    print("Fact 3, read %s" % c.now())
    print("the copy is %d bytes; its stamp %s-%s-%s %s:%s matches 'saved %s': %s" % (len(page), stamp[:4], stamp[4:6], stamp[6:8],
          stamp[8:10], stamp[10:12], saved, "yes" if "%s-%s-%s %s:%s" % (stamp[:4], stamp[4:6], stamp[6:8], stamp[8:10], stamp[10:12]) == saved else "NO"))
    print("tweet id %d is %s UTC by the snowflake rule; the ledger says %s" % (tid, made, said))
    lines = {"the phrase is not in that copy": phrase.lower() not in page.lower()}
    for line, tripped in lines.items():
        print("  %-62s %s" % (line, "TRIPPED" if tripped else "not tripped"))
    print("  %-62s %s" % ("a febu tweet naming UBEF from before 01:43 turns up", "NOT SETTLED BY A SCRIPT (needs febu's tweets)"))
    print("\nverdict for what a script can settle:", verdict(lines))


def fact4():
    f = " ".join(c.entry(4).split())
    link = c.find(r"(https://\S+/scripture\.html)", f, "fact 4's link")
    books = re.findall(r"\d+-\d+ (THE [A-Z ]+?)(?:,| then)", f)
    pages = json.loads(get(link.replace("scripture.html", "assets/scripture.json")).decode("utf-8"))
    sha = hashlib.sha256(get(link.replace("scripture.html", "assets/scripture.json"))).hexdigest()
    off = [(p["page_number"], p["book"]) for p in pages if p["book"].strip().upper() != books[((p["page_number"] - 1) // 4) % len(books)]]
    print("Fact 4, read %s; the copy: %d pages, SHA-256 %s" % (c.now(), len(pages), sha))
    print("the eight books, read from the ledger: %s" % ", ".join(books))
    lines = {"any page sits in a book the rotation does not predict": bool(off) or len(books) != 8,
             "the copy does not have pages 1 to 164": [p["page_number"] for p in pages] != list(range(1, 165))}
    for line, tripped in lines.items():
        print("  %-62s %s" % (line, "TRIPPED" if tripped else "not tripped"))
    print("pages off the rotation:", off or "none")
    print("\nverdict (on this copy, KNOWN BUGS 3):", verdict(lines))


# ---------- the fee claim: does it need the creator's signature? (simulated, nothing sent) ----------
# ASSUMES: simulateTransaction with sigVerify off runs the program with the signer flags exactly as written in the message
# (control 4 checks that), and the pAMM instruction's account list is the one in the creator's own claim, row 19.
# No key is used at all: the signature slots hold zeros, the fee payer is a public address whose key nobody here has.

PAMM = "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA"   # PumpSwap, the program that holds the creator fee
SYSTEM = "11111111111111111111111111111111"


@lru_cache(None)
def payer():
    """The fee payer of a recent trade on the fee account: a stranger's funded, system-owned wallet. Picked at run time,
    so no third party's address is written into this file; only its balance is read, and it is printed shortened."""
    fee = c.find(r"solscan\.io/account/(%s)" % c.B58, c.entry(6), "fact 6's fee account")
    for s in c.rpc("getSignaturesForAddress", [fee, {"limit": 20}]):
        if s["err"] is None:
            k = c.signers(c.tx(s["signature"]))[0]
            info = c.rpc("getAccountInfo", [k, {"encoding": "base64"}])["value"]
            if info and info["owner"] == SYSTEM and info["lamports"] > 50_000_000:
                return k
    raise SystemExit("no funded stranger among the fee account's last 20 transactions; run it again later")


def pda(seeds, program):
    for bump in range(255, -1, -1):
        h = hashlib.sha256(b"".join(seeds) + bytes([bump]) + b58d(program) + b"ProgramDerivedAddress").digest()
        if not on_curve(h):
            return b58e(h)


def shortvec(n):
    out = b""
    while True:
        b, n = n & 0x7F, n >> 7
        if not n:
            return out + bytes([b])
        out += bytes([b | 0x80])


def build_tx(payer, ixs):
    """A legacy transaction with zeroed signatures. ixs: [(program, [(key, signer, writable)], data bytes)]."""
    metas = {payer: [True, True]}
    for prog, accts, _ in ixs:
        for k, s, w in accts:
            m = metas.setdefault(k, [False, False])
            m[0], m[1] = m[0] or s, m[1] or w
        metas.setdefault(prog, [False, False])
    keys = [k for g in ((1, 1), (1, 0), (0, 1), (0, 0)) for k, (s, w) in metas.items() if (int(s), int(w)) == g]
    n_sig = sum(metas[k][0] for k in keys)
    ro_signed = sum(metas[k][0] and not metas[k][1] for k in keys)
    ro_unsigned = sum(not metas[k][0] and not metas[k][1] for k in keys)
    msg = bytes([n_sig, ro_signed, ro_unsigned]) + shortvec(len(keys)) + b"".join(b58d(k) for k in keys) + bytes(32)
    msg += shortvec(len(ixs))
    for prog, accts, data in ixs:
        msg += bytes([keys.index(prog)]) + shortvec(len(accts)) + bytes(keys.index(k) for k, _, _ in accts) + shortvec(len(data)) + data
    return shortvec(n_sig) + bytes(64 * n_sig) + msg


def simulate(payer, ixs, watch=()):
    """(err, logs, {account: token amount after}) from the node's dry run. Changes nothing on chain."""
    opts = {"encoding": "base64", "sigVerify": False, "replaceRecentBlockhash": True, "commitment": "confirmed"}
    if watch:
        opts["accounts"] = {"encoding": "jsonParsed", "addresses": list(watch)}
    v = c.rpc("simulateTransaction", [base64.b64encode(build_tx(payer, ixs)).decode(), opts])["value"]
    after = {}
    for a, got in zip(watch, v.get("accounts") or []):
        d = (got or {}).get("data")
        after[a] = d["parsed"]["info"]["tokenAmount"]["uiAmountString"] if isinstance(d, dict) and "parsed" in d else (
            "%.9f SOL" % (got["lamports"] / 1e9) if got else None)
    return v["err"], v.get("logs") or [], after


def needs_signature(err, logs):
    blob = json.dumps(err) + " ".join(logs)
    return any(w in blob for w in ("MissingRequiredSignature", "AccountNotSigner", "must sign", "missing required signature"))


def claimsim():
    f6 = c.entry(6)
    fee = c.find(r"solscan\.io/account/(%s)" % c.B58, f6, "fact 6's fee account")
    wallet = c.find(r"other than (%s)" % c.B58, f6, "fact 6's wallet")
    real = [i for i in c.tx(CREATOR_RUN_ROW_19)["transaction"]["message"]["instructions"] if i["programId"] == PAMM]
    assert len(real) == 1, "row 19 should hold exactly one pAMM instruction"
    real = real[0]
    acct = real["accounts"]
    collect_data = b58d_any(real["data"])
    PAYER = payer()
    print("The fee claim, simulated %s. Nothing is sent; no key is used; the fee payer is %s, a recent trader."
          % (c.now(), c.short(PAYER)))
    print("template: row 19's own pAMM instruction, %d accounts, data %s (the 8-byte tag for collect_coin_creator_fee)" % (len(acct), collect_data.hex()))
    ata = derive_ata(wallet, c.WSOL)
    ev = pda([b"__event_authority"], PAMM)
    vault_auth = pda([b"creator_vault", b58d(wallet)], PAMM)
    for name, mine, theirs in (("fee account", fee, acct[4]), ("creator", wallet, acct[2]), ("creator's WSOL account", ata, acct[5]),
                               ("event authority", ev, acct[6]), ("vault authority", vault_auth, acct[3])):
        print("  %-24s derived or read from the ledger %s the real claim's" % (name, "MATCHES" if mine == theirs else "DOES NOT MATCH"))
        assert mine == theirs, name
    create = (ATA_PROGRAM, [(PAYER, True, True), (ata, False, True), (wallet, False, False), (c.WSOL, False, False),
                            (SYSTEM, False, False), (TOKEN, False, False)], bytes([1]))   # createIdempotent: the account is closed now

    def collect(signer, vault_auth_key=vault_auth):
        a = [(c.WSOL, False, False), (TOKEN, False, False), (wallet, signer, False), (vault_auth_key, False, False), (fee, False, True),
             (ata, False, True), (ev, False, False), (PAMM, False, False)]
        return (PAMM, a, collect_data)

    def show(label, err, logs, after):
        verdict_ = "needs a signature" if needs_signature(err, logs) else ("RAN TO THE END" if err is None else "failed otherwise")
        print("  %-52s %s%s" % (label, verdict_, "   (%s)" % json.dumps(err)[:70] if verdict_ == "failed otherwise" else ""))
        return verdict_, err, logs, after

    def filler(i):
        return b58e(hashlib.sha256(b"febu claim sim filler %d" % i).digest())

    before = c.rpc("getTokenAccountBalance", [fee])["value"]["uiAmountString"]
    print("\nthe fee account holds %s WSOL now\n" % before)
    t1 = show("1 creator signs (as in its own claims)", *simulate(PAYER, [create, collect(True)], [ata, fee]))
    t2 = show("2 nobody signs for the creator (a stranger's claim)", *simulate(PAYER, [create, collect(False)], [ata, fee]))
    t3 = show("3 as 2, vault authority swapped for another address", *simulate(PAYER, [create, collect(False, PAYER)], [ata, fee]))
    stranger = b58e(hashlib.sha256(b"febu claim sim: an address nobody holds a key for").digest())
    pay = (2).to_bytes(4, "little") + (1_000_000).to_bytes(8, "little")   # system transfer; 1,000,000 lamports clears the rent floor
    t4a = show("4a harness: a transfer whose 'from' does not sign", *simulate(PAYER, [(SYSTEM, [(stranger, False, True), (PAYER, False, True)], pay)]))
    t4b = show("4b harness: the same transfer, 'from' signs", *simulate(PAYER, [(SYSTEM, [(PAYER, True, True), (stranger, False, True)], pay)]))
    # pAMM's update_creator_fee_config: its IDL gives `admin` the signer flag. Not signing must fail on the flag; signing gets past the flag
    cfg = bytes([61, 175, 160, 249, 66, 66, 136, 175, 1]) + bytes(8)
    admin, gcfg = filler(0), pda([b"global_config"], PAMM)
    t5 = show("5 control: pAMM's update_creator_fee_config, admin not signing", *simulate(PAYER, [(PAMM, [(admin, False, True), (gcfg, False, True), (SYSTEM, False, False), (ev, False, False), (PAMM, False, False)], cfg)]))
    t5b = show("5b control: the same, admin signing (fails later, on who the admin is)", *simulate(PAYER, [(PAMM, [(admin, True, True), (gcfg, False, True), (SYSTEM, False, False), (ev, False, False), (PAMM, False, False)], cfg)]))
    print("\nlogs of run 2:")
    for ln in t2[2][-12:]:
        print("   ", ln[:150])
    print("   err:", json.dumps(t2[1]))
    print("after run 2, the watched accounts' WSOL:", t2[3])
    checks = {"1 ran (the template and the encoder are right)": t1[0] == "RAN TO THE END",
              "3 failed, and not for a signature (the program does read the accounts)": t3[0] == "failed otherwise",
              "4a needs a signature, 4b does not (a missing signer shows with sigVerify off)": t4a[0] == "needs a signature" and t4b[0] == "RAN TO THE END",
              "5 pAMM refuses a missing signer it declares, and 5b gets past it (so run 2's pass is not the program skipping the check)": t5[0] == "needs a signature" and t5b[0] == "failed otherwise"}
    for k, ok in checks.items():
        print("  control %-72s %s" % (k, "ok" if ok else "FAILED"))
    if not all(checks.values()):
        print("\nCAN'T TELL: a control failed, so run 2 says nothing.")
    elif t2[0] == "RAN TO THE END":
        print("\nPERMISSIONLESS: with the creator not signing, the claim runs. A stranger can make an open-ended 'payment out' line true.")
    elif t2[0] == "needs a signature":
        print("\nSIGNED BY THE CREATOR: with the creator not signing, the program refuses. A stranger cannot trip that line this way.")
    else:
        print("\nCAN'T TELL: run 2 failed for another reason (see the logs).")
    # a second door: the IDL lists a pay-out of the same vault to pump's creator vault that skips the creator's WSOL account
    pcv, v2 = to_pump_v2(wallet, fee)
    t6 = show("\n6 a stranger sends the vault to pump's creator vault (v2)", *simulate(PAYER, [v2], [fee, pcv]))
    print("   pump's creator vault %s held %.9f SOL before" % (pcv, c.rpc("getBalance", [pcv])["value"] / 1e9))
    print("   after run 6: the fee vault's WSOL and pump's creator vault:", t6[3])
    print("   the log names the instruction:", [ln for ln in t6[2] if "Instruction:" in ln][:1], "(door2 greps for this)")
    if t6[0] == "RAN TO THE END":
        print("   so a payment out of the fee account can happen without touching the creator's WSOL account. Fact 8's script cannot see it.")


PUMP = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"   # pump.fun's bonding-curve program; it holds the creator's other vault


def to_pump_v2(wallet, fee):
    """pAMM's transfer_creator_fees_to_pump_v2 (IDL, pump-fun/pump-public-docs): any payer, the creator does not sign."""
    pcv = pda([b"creator-vault", b58d(wallet)], PUMP)
    a = [(payer(), True, True), (c.WSOL, False, False), (TOKEN, False, False), (SYSTEM, False, False), (ATA_PROGRAM, False, False),
         (wallet, False, False), (pda([b"creator_vault", b58d(wallet)], PAMM), False, True), (fee, False, True), (pcv, False, True),
         (derive_ata(pcv, c.WSOL), False, True), (pda([b"__event_authority"], PAMM), False, False), (PAMM, False, False)]
    return pcv, (PAMM, a, bytes([1, 33, 78, 185, 33, 67, 44, 92]))


def door2():
    """Did anyone pay the fee vault out through pump's creator vault since 09-14? That path skips the creator's WSOL
    account, which fact 8's script reads. Every transaction on pump's creator vault is read; one unread means CAN'T TELL."""
    wallet = c.find(r"other than (%s)" % c.B58, c.entry(6), "fact 6's wallet")
    fee = c.find(r"solscan\.io/account/(%s)" % c.B58, c.entry(6), "fact 6's fee account")
    pcv, v2 = to_pump_v2(wallet, fee)
    word = "TransferCreatorFeesToPump"
    # control: the same search finds the instruction in a dry run of it
    assert any(word in ln for ln in simulate(payer(), [v2])[1]), "the search word is not in the dry run's log"
    # the window is fact 8's, typed in as of 2026-10-15: from 09-14 (a day early, to be safe) to the end of 2026-10-14
    sigs = [s for s in sigs_since(pcv, day(2026, 9, 14)) if s["blockTime"] < day(2026, 10, 15)]
    seen = hits = unread = 0
    for s in sigs:
        try:
            logs = c.tx(s["signature"])["meta"].get("logMessages") or []
        except SystemExit:
            unread += 1
            continue
        seen += 1
        hits += any(word in ln for ln in logs)
    print("Door 2, read %s: pump's creator vault %s" % (c.now(), pcv))
    print("%d transactions on it from 2026-09-14 to the end of 2026-10-14 (newest %s), %d read, %d unread, %d name %s" % (
        len(sigs), c.when(sigs[0]["blockTime"]) if sigs else "none", seen, unread, hits, word))
    print("\nverdict:", "CAN'T TELL" if unread else verdict({"a payment went out through pump's creator vault in the window": hits > 0}))


def b58d_any(s):
    n = 0
    for ch in s:
        n = n * 58 + ALPHA.index(ch)
    return n.to_bytes((n.bit_length() + 7) // 8, "big")


# ---------- offline checks ----------

def selftest():
    t = {"signer is not X": False, "logs show no Y": True}
    assert verdict(t) == "DOESN'T HOLD" and verdict({"a": False}) == "HOLDS"
    w = "ApWpkd8tpPTdTFNihoYuF5en8Y27TQn4LAQTvvmf8faG"   # a real wallet: on the curve; a derived address is not
    assert b58e(b58d(w)) == w and on_curve(b58d(w)) and not on_curve(b58d(derive_ata(w, c.WSOL)))
    r = {"transaction": {"message": {"accountKeys": [{"pubkey": "S", "signer": True}, {"pubkey": "V", "signer": False}]}},
         "meta": {"logMessages": ["Program log: Instruction: AdminSetCreator"], "err": None}}
    assert verdict(lines9(r, "S", "V", "AdminSetCreator")) == "HOLDS"
    for name, m in mutants(r, "S", "V", "AdminSetCreator").items():
        assert verdict(lines9(m, "S", "V", "AdminSetCreator")) == "DOESN'T HOLD", name
    assert all(verdict(f(lines9(m, "S", "V", "AdminSetCreator"))) == "HOLDS"
               for m in [mutants(r, "S", "V", "AdminSetCreator")["transaction failed"]] for f in [LAZY["forgot 'failed'"]])
    assert shortvec(0) == b"\x00" and shortvec(127) == b"\x7f" and shortvec(128) == b"\x80\x01" and shortvec(300) == b"\xac\x02"
    assert b58d_any("ToNg27JNfmT") == bytes([160, 57, 89, 42, 181, 139, 43, 66])   # the collect tag, as on chain
    raw = build_tx(w, [(PAMM, [(c.WSOL, False, False), (w, False, True), (SYSTEM, True, False)], b"\x01\x02")])
    assert raw[0] == 2 and raw[1:129] == bytes(128)               # 2 signers (payer, SYSTEM here), zeroed
    assert raw[129:132] == bytes([2, 1, 2])                       # header: 2 signed, 1 read-only signed, 2 read-only unsigned
    print("ok")


if __name__ == "__main__":
    {"test9": test9, "fact8": fact8, "fact1": fact1, "fact3": fact3, "fact4": fact4, "claimsim": claimsim, "door2": door2,
     "--test": selftest}[sys.argv[1] if len(sys.argv) > 1 else "--test"]()
