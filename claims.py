"""Issue and list the one-time claim codes (claims.sql, api/claim.js). Needs SUPABASE_URL and SUPABASE_SERVICE_KEY
in the environment; it writes neither anywhere, and the codes are printed once and stored only as hashes.

    python claims.py issue           a code for every name on the ledger's Member line that has no row yet
    python claims.py reissue NAME    a fresh code for one name (a lost device): the old claim is cleared
    python claims.py list            each name: claimed when, wrong codes so far
"""
import hashlib
import json
import os
import secrets
import sys
import urllib.parse
import urllib.request

import build

ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"                  # no 0, o, 1, l or i: the code is read out of a DM
TABLE = "/rest/v1/assembly_claims"


def code():
    return "-".join("".join(secrets.choice(ALPHABET) for _ in range(4)) for _ in range(4))


def norm(c):                                                  # as api/_claims.js normalises what is typed
    return "".join(ch for ch in c.lower() if ch.isalnum())


def hsh(s):
    return hashlib.sha256(s.encode()).hexdigest()


def db(path, method="GET", body=None):
    url, key = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        sys.exit("set SUPABASE_URL and SUPABASE_SERVICE_KEY in the environment first (never in a file here)")
    req = urllib.request.Request(url + TABLE + path, method=method, data=json.dumps(body).encode() if body else None,
                                 headers={"apikey": key, "Authorization": "Bearer " + key,
                                          "Content-Type": "application/json", "Prefer": "return=representation"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read() or b"[]")


def members():
    text = build.raw_text(build.LEDGER).decode("utf-8")
    return build.member_names(build.sections(text)[1])


def issue(names):
    have = {r["name"] for r in db("?select=name")}
    for n in names:
        if n in have:
            print("%-16s has a row already (reissue to replace it)" % n)
            continue
        c = code()
        db("", "POST", {"name": n, "code_hash": hsh(norm(c))})
        print("%-16s %s" % (n, c))


def reissue(name):
    c = code()
    rows = db("?name=eq." + urllib.parse.quote(name), "PATCH",
              {"code_hash": hsh(norm(c)), "token_hash": None, "claimed_at": None, "failed": 0})
    if not rows:
        sys.exit("no row for %s; issue first" % name)
    print("%-16s %s   (the old claim is cleared)" % (name, c))


def listing():
    for r in db("?select=name,claimed_at,failed,issued_at&order=name"):
        print("%-16s %s   wrong codes: %d   issued %s" % (
            r["name"], ("claimed " + r["claimed_at"][:10]) if r["claimed_at"] else "not claimed", r["failed"],
            r["issued_at"][:10]))


def selfcheck():
    c = code()
    assert len(c) == 19 and c.count("-") == 3 and set(norm(c)) <= set(ALPHABET), c
    assert norm("AB12-CD34") == "ab12cd34" and len(hsh("x")) == 64


if __name__ == "__main__":
    selfcheck()
    cmd = sys.argv[1:2]
    if cmd == ["issue"]:
        issue(members())
    elif cmd == ["reissue"] and len(sys.argv) == 3:
        reissue(sys.argv[2])
    elif cmd == ["list"]:
        listing()
    else:
        sys.exit(__doc__)
