#!/usr/bin/env python
"""
draw.py -- the checker draw, the verdict lock and the chain for the claims ledger
(08_CLAIMS_LEDGER.txt: THE DRAW, SEALED VERDICTS, THE RECORD).

Everything here can be done by hand with a block explorer, a hex converter, a calculator and any "sha256 online" page.
This only saves the arithmetic.

  python draw.py find "2026-10-12 15:00"
        the draw block for a claim posted at that UTC time (asks mempool.space, so it needs the internet)
  python draw.py order <block hash> <proposer> <record keeper> <name> <name> ...
        the seat order for one claim. Give everyone in the pool, plus the proposer and the record keeper.
  python draw.py lock WRONG
        a verdict line with a private word made for you, and its lock. Add your own word after the verdict to use that.
  python draw.py close CHAIN.txt 6 RIGHT 2026-10-20
        add a closed entry to the chain and print the hash to post
  python draw.py chain CHAIN.txt
        check a copy of the chain and print its newest hash
  python draw.py --test
        offline self-check against the examples printed in the ledger
"""
import hashlib, json, os, secrets, sys, urllib.error, urllib.request
from datetime import datetime, timezone

SEATS = ("checker 1", "checker 2", "re-checker 1", "re-checker 2", "tie-breaker")
VERDICTS = ("RIGHT", "WRONG", "CANTTELL", "KEPT", "BROKEN")
WAIT = 2 * 60 * 60      # Bitcoin refuses a block dated more than two hours ahead, so a block dated this late did not exist yet
API = "https://mempool.space/api"
SEP = " | "


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def order(block_hash, members, proposer, keeper):
    """Everyone except the proposer and the record keeper, in drawn order. The first five take SEATS."""
    h = block_hash.strip().lower()
    if len(h) != 64 or any(c not in "0123456789abcdef" for c in h):
        raise ValueError("a block hash is 64 characters, 0-9 and a-f")
    low = [m.lower() for m in members]
    if len(set(low)) != len(low):
        raise ValueError("two members have the same name")
    for who in (proposer, keeper):
        if who.lower() not in low:
            raise ValueError("%s is not on the member list" % who)
    names = sorted((m for m in members if m.lower() not in (proposer.lower(), keeper.lower())), key=str.lower)
    x, out = int(h[-12:], 16), []
    while names:
        x, r = divmod(x, len(names))
        out.append(names.pop(r))
    return out


def lock(verdict, word=None):
    if verdict not in VERDICTS:
        raise ValueError("the verdict is one of: " + ", ".join(VERDICTS))
    word = word or secrets.token_hex(6)
    if len(word) < 8 or not word.isalnum():
        raise ValueError("the private word is at least 8 letters or digits, with no spaces")
    line = "%s %s" % (verdict, word)
    return line, sha(line)


def chain_check(lines):
    """Every line must number itself in order and carry the hash of the line before. Returns the newest hash."""
    prev = "start"
    for i, line in enumerate(lines, 1):
        f = line.split(SEP)
        if len(f) != 5:
            raise ValueError("line %d does not have five parts" % i)
        if f[0] != str(i):
            raise ValueError("line %d is numbered %s" % (i, f[0]))
        if f[2] not in VERDICTS:
            raise ValueError("line %d has the result %s" % (i, f[2]))
        if f[4] != prev:
            raise ValueError("line %d does not carry the hash of line %d, so something before it was changed, removed or moved" % (i, i - 1))
        prev = sha(line)
    return prev


def chain_add(lines, entry, result, date):
    prev = chain_check(lines)
    if result not in VERDICTS:
        raise ValueError("the result is one of: " + ", ".join(VERDICTS))
    if SEP.strip() in entry or not entry.strip():
        raise ValueError("the entry is a number or a short name, with no | in it")
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise ValueError("the date is written like 2026-10-20")
    return SEP.join((str(len(lines) + 1), entry.strip(), result, date, prev))


def read_chain(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [ln.rstrip("\r\n") for ln in f if ln.strip()]


def _get(path):
    with urllib.request.urlopen(urllib.request.Request(API + path, headers={"User-Agent": "draw.py"}), timeout=30) as r:
        return r.read().decode()


def find(posted_utc):
    """The lowest block whose time is at least two hours after the claim was posted. None if it has not been mined yet."""
    try:
        t = int(datetime.strptime(posted_utc, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).timestamp())
    except ValueError:
        raise ValueError('the time is written like "2026-10-12 15:00", in UTC')
    height = json.loads(_get("/v1/mining/blocks/timestamp/%d" % t))["height"]     # the newest block when the claim was posted
    while True:
        height += 1
        try:
            blk = json.loads(_get("/block/" + _get("/block-height/%d" % height).strip()))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            raise
        if blk["timestamp"] >= t + WAIT:
            return blk


def _refuses(fn):
    try:
        fn()
    except ValueError:
        return True
    return False


def _test():
    members = ["Ada", "Ben", "Cal", "Dot", "Eli", "Fay", "Gus"]
    h = "000000000000000000009be34d563b691ec3f0b2935e88ec56ceace95b11755c"      # block 971,119, the example in the ledger
    got = order(h, members, "Ada", "Gus")
    assert got == ["Dot", "Eli", "Cal", "Fay", "Ben"], got
    assert sorted(got) == ["Ben", "Cal", "Dot", "Eli", "Fay"]                       # a permutation, proposer and keeper left out
    assert order(h.upper(), [m.upper() for m in members], "ada", "gus") == [g.upper() for g in got]   # case does not matter
    assert order(h[:-1] + "0", members, "Ada", "Gus") != got                         # one character of the hash changes the draw
    assert lock("WRONG", "walnut7731") == ("WRONG walnut7731", "fd548234041d9e55167c3109916ff23e5b3210a94d6cdc13ea7325c883377cb5")
    line, digest = lock("RIGHT")                                                     # a made word: long enough, different each time
    assert sha(line) == digest and len(line.split()[1]) >= 8 and lock("RIGHT")[0] != line

    one = chain_add([], "example-A", "RIGHT", "2026-11-02")                          # the two example lines in the ledger
    two = chain_add([one], "example-B", "WRONG", "2026-11-05")
    assert one == "1 | example-A | RIGHT | 2026-11-02 | start", one
    assert two == "2 | example-B | WRONG | 2026-11-05 | " + EXAMPLE_HASH_1, two
    assert chain_check([one, two]) == EXAMPLE_HASH_2
    assert chain_check([]) == "start"
    changed = one.replace("RIGHT", "WRONG")
    for bad in (lambda: chain_check([changed, two]),          # a result rewritten
                lambda: chain_check([two]),                    # a line removed
                lambda: chain_check([two, one]),               # lines moved
                lambda: chain_add([one], "x | y", "RIGHT", "2026-11-05"), lambda: chain_add([one], "7", "MAYBE", "2026-11-05"),
                lambda: chain_add([one], "7", "RIGHT", "Nov 5"),
                lambda: order("abc", members, "Ada", "Gus"), lambda: order(h, members, "Zed", "Gus"),
                lambda: order(h, members + ["ada"], "Ada", "Gus"), lambda: lock("MAYBE", "walnut7731"), lambda: lock("RIGHT", "short"),
                lambda: find("yesterday")):
        assert _refuses(bad), "bad input was accepted"
    print("ok")


EXAMPLE_HASH_1 = "f3e91ada72d5de2777b5bacd52c08382f3efa5cd21dc8a5308b6fdf7a6d03ccb"
EXAMPLE_HASH_2 = "867359db3e16470c6f67a685868c501ed3d1f3da0567320870c93d9d4cacc3f8"


def main(a):
    if a[:1] == ["--test"]:
        return _test()
    try:
        if a[:1] == ["find"] and len(a) == 2:
            blk = find(a[1])
            if blk is None:
                print("The draw block has not been mined yet. Try again later.")
            else:
                when = datetime.fromtimestamp(blk["timestamp"], timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                print("draw block %d\ntime       %s\nhash       %s" % (blk["height"], when, blk["id"]))
        elif a[:1] == ["order"] and len(a) >= 5:
            for i, name in enumerate(order(a[1], a[4:], a[2], a[3])):
                print("%-13s %s" % (SEATS[i] if i < len(SEATS) else "spare", name))
        elif a[:1] == ["lock"] and len(a) in (2, 3):
            line, digest = lock(*a[1:])
            print("keep private:  %s\npost the lock: %s" % (line, digest))
        elif a[:1] == ["close"] and len(a) == 5:
            line = chain_add(read_chain(a[1]), a[2], a[3], a[4])
            with open(a[1], "a", encoding="utf-8", newline="\n") as f:
                f.write(line + "\n")
            print("added:        %s\npost its hash: %s" % (line, sha(line)))
        elif a[:1] == ["chain"] and len(a) == 2:
            lines = read_chain(a[1])
            print("%d lines, all in order\nnewest hash: %s" % (len(lines), chain_check(lines)))
        else:
            print(__doc__)
    except ValueError as e:
        sys.exit("Not done: %s." % e)
    except (urllib.error.URLError, TimeoutError) as e:
        sys.exit("Could not reach mempool.space (%s). Look the block up on any explorer and use 'order'." % e)


if __name__ == "__main__":
    main(sys.argv[1:])
