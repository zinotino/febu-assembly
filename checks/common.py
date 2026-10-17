"""What the checks share: the ledger's own text, and one public Solana RPC (no key, read-only).

The addresses and transactions come from the ledger's text and fact-6-steps.txt, not from these scripts, so a check
tests what the ledger says. Version 3's facts are kept word for word in archive/08_CLAIMS_LEDGER_v3.txt (version 5 asks
questions instead, and an answer may copy a fact), so a fact is read from ledger.txt if it is there and from that copy
if not. To ask another node, your own for example, set SOLANA_RPC:
    SOLANA_RPC=http://127.0.0.1:8899 python checks/fact6.py
"""
import datetime as dt
import http.client
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RPC = os.environ.get("SOLANA_RPC", "https://api.mainnet-beta.solana.com")
WSOL = "So11111111111111111111111111111111111111112"
B58 = r"[1-9A-HJ-NP-Za-km-z]{32,90}"


def text(name):
    return (ROOT / name).read_bytes().replace(b"\r\n", b"\n").decode("utf-8")


V3 = "archive/08_CLAIMS_LEDGER_v3.txt"


def entry(num):
    """FACT num: its header line and the lines indented under it, from ledger.txt, or from version 3's archive copy."""
    for name in ("ledger.txt", V3):
        m = (ROOT / name).exists() and re.search(r"^  FACT %d\. .*\n(?:(?:    .*)?\n)*" % num, text(name), re.M)
        if m:
            return m.group()
    raise SystemExit("neither ledger.txt nor %s has a FACT %d" % (V3, num))


def find(pattern, where, what):
    m = re.search(pattern, where)
    if not m:
        raise SystemExit("could not find %s in the ledger's text" % what)
    return m.group(1)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):   # refused, not followed: what the check names as its node is what it read
        return None


OPEN = urllib.request.build_opener(_NoRedirect).open
HOST = re.compile(r"[A-Za-z0-9.:\[\]-]+")


def host_of(url):
    """The host of an address, with its port if it has one, and nothing else: a path or query can hold a key, and this goes
    into a post line, so anything but letters, digits and . : - [ ] reads as unknown."""
    try:
        p = urllib.parse.urlparse(url)
        host = ("[%s]" % p.hostname if p.hostname and ":" in p.hostname else p.hostname or "") + (":%d" % p.port if p.port else "")
    except ValueError:
        return "unknown"
    return host if HOST.fullmatch(host) else "unknown"


def redact(text, url):
    """The node's address cut to scheme and host in a script's output: its user:password@, path, query or fragment can hold
    an API key, and so can an address that does not parse. Each part of 6 or more characters is cut too, longest first: a
    node may echo the key alone ("invalid api key ..."), a request line, or the HTTP library a port it could not read."""
    url = url or ""
    m = re.match(r"[A-Za-z]+://(?:([^/?#]*)@)?[^/?#]*", url)
    if not m:
        return text.replace(url, "<cut>") if len(url) >= 6 else text
    text = text.replace(url, "%s://%s" % (url.split(":", 1)[0], host_of(url)))
    user, rest = m.group(1) or "", url[m.end():]
    for part in sorted({rest, user, *re.split(r"[/?#&=@:;]", user + "/" + rest)}, key=len, reverse=True):
        if len(part) >= 6:
            text = text.replace(part, "<cut>")
    return text


def rpc(method, params):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    last = None
    try:
        req = urllib.request.Request(RPC, body, {"Content-Type": "application/json", "User-Agent": "curl/8"})
    except ValueError:   # not an address at all, and urllib's message repeats it whole: it may be the key itself
        raise SystemExit(redact("%s: SOLANA_RPC %s is not the address of a node" % (method, RPC), RPC)) from None
    for attempt in range(6):
        if attempt:
            time.sleep(3 * attempt)   # the public node's "slow down" passes after a few seconds
        try:
            r = json.load(OPEN(req, timeout=60))
        except urllib.error.HTTPError as err:
            if err.code < 500 and err.code != 429:   # refused, not busy: asking again will not help
                raise SystemExit(redact("%s: %s answered HTTP %d" % (method, RPC, err.code), RPC))
            last = "HTTP %d" % err.code
            continue
        except (OSError, ValueError, http.client.HTTPException) as err:   # no connection, or a cut-off or non-JSON body
            last = repr(err)
            continue
        if "error" in r and r["error"].get("code") in (429, -32429):
            last = r["error"]
            continue
        if "error" in r:
            raise SystemExit(redact("%s: %s" % (method, r["error"]), RPC))
        return r["result"]
    raise SystemExit(redact("%s: no answer from %s after 6 tries (last: %s)" % (method, RPC, last), RPC))


def tx(sig):
    time.sleep(0.4)   # the public node allows a few requests a second
    # version 1: the creator wallet moved to v1 transactions on 2026-09-20
    r = rpc("getTransaction", [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 1}])
    if r is None:
        raise SystemExit(redact("%s does not know transaction %s" % (RPC, sig), RPC))
    return r


def when(t):
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def keys(r):
    return [k["pubkey"] for k in r["transaction"]["message"]["accountKeys"]]


def signers(r):
    return [k["pubkey"] for k in r["transaction"]["message"]["accountKeys"] if k.get("signer")]


def token_changes(r):
    """[(token account, owner, mint, before, after)] from the transaction's own balance lists. An account missing from one
    list was opened or closed in the transaction: 0 there. A listed balance with no amount or owner raises KeyError: a
    field the node left out is not a zero, and not someone else's account."""
    k = keys(r)
    pre = {b["accountIndex"]: b for b in r["meta"]["preTokenBalances"]}
    post = {b["accountIndex"]: b for b in r["meta"]["postTokenBalances"]}
    amt = lambda b: Decimal(b["uiTokenAmount"]["uiAmountString"]) if b else Decimal(0)
    return [(k[i], (post.get(i) or pre[i])["owner"], (post.get(i) or pre[i])["mint"], amt(pre.get(i)),
             amt(post.get(i))) for i in sorted(set(pre) | set(post))]


def sol_change(r, who):
    i = keys(r).index(who)
    return Decimal(r["meta"]["postBalances"][i] - r["meta"]["preBalances"][i]) / 10 ** 9


def short(s):
    return s[:8] + "..."
