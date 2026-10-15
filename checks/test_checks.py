"""The checks' own logic, offline: python checks/test_checks.py (or pytest). The chain reads need a node and are not
tested here."""
from decimal import Decimal

from common import B58, WSOL, entry, find, text
from fact5 import on_page
from fact6 import arrived, rows


def test_word_rule():
    page = {"title": "The Jester", "ascii_art": None, "body": "majesty, slaughter and onslaught, indebted, mocking"}
    assert on_page("jest", page) and on_page("mock", page)
    assert not on_page("laugh", page) and not on_page("debt", page)
    assert not on_page("jest", {"title": "", "body": "majesty"})


def test_steps_rows_add_up():
    got, total = rows(text("fact-6-steps.txt"))
    assert [n for n, *_ in got] == list(range(1, 45))
    assert sum(sol for _, _, sol, _ in got).quantize(total) == total == Decimal("2939.095965")


def test_whole_number_row_is_read():
    got, total = rows("    1  2026-07-09 05:48   70  %s\n       total   70\n" % ("1" * 88))
    assert [(n, sol) for n, _, sol, _ in got] == [(1, Decimal(70))] and total == Decimal(70)


def fake_tx(keys, sol, wsol=None, fee=5000):
    """A parsed transaction: keys[0] pays the fee; sol gives each key's lamport change; wsol is (owner, before,
    after) for one WSOL token account."""
    pre = [10 ** 12] * len(keys)
    meta = {"fee": fee, "preBalances": pre, "postBalances": [p + s for p, s in zip(pre, sol)],
            "preTokenBalances": [], "postTokenBalances": []}
    if wsol:
        owner, a, b = wsol
        meta["preTokenBalances"] = [{"accountIndex": len(keys), "owner": owner, "mint": WSOL,
                                     "uiTokenAmount": {"uiAmountString": a}}]
        meta["postTokenBalances"] = [{"accountIndex": len(keys), "owner": owner, "mint": WSOL,
                                      "uiTokenAmount": {"uiAmountString": b}}]
        keys = keys + ["wsol-account"]
    return {"transaction": {"message": {"accountKeys": [{"pubkey": k, "signer": i == 0} for i, k in enumerate(keys)]}},
            "meta": meta}


def test_arrived():
    one = Decimal(1)
    assert arrived(fake_tx(["W", "X"], [10 ** 9 - 5000, 0]), "W", one) == "SOL"   # the wallet paid the fee
    assert arrived(fake_tx(["W"], [2 * 10 ** 9 - 5000]), "W", one) == "SOL+more"
    assert arrived(fake_tx(["A", "X"], [0, 0], ("W", "0", "1")), "W", one) == "WSOL"
    assert arrived(fake_tx(["A", "X"], [0, 0], ("W", "0", "0.5")), "W", one) == "less"   # the wallet signed nothing
    assert arrived(fake_tx(["A", "X"], [0, 0]), "W", Decimal(0)) == "none"   # nothing left the fee account


def test_ledger_links_found():
    assert find(r"solscan\.io/tx/(%s)" % B58, entry(2), "sale").startswith("51ekPPgz")
    assert find(r"other than (%s)" % B58, entry(6), "wallet").startswith("ApWpkd8t")
    assert find(r"\$FEBU token,\s+(%s)" % B58, entry(1), "mint").endswith("pump")


if __name__ == "__main__":
    for name, f in list(globals().items()):
        if name.startswith("test_"):
            f()
    print("ok")


def test_release_hashes():
    from release import capture_with, sha256
    import gzip
    assert sha256(b"") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    # an Archive capture is judged by its content, not by the index's SHA-1 over the stored (gzip) bytes
    ledger = b"THE LEDGER\n" * 50
    saved = {"20261015": gzip.compress(ledger), "20261014": b"an older draft", "20261013": ledger}
    caps = [["20261013", "x", "200"], ["20261014", "y", "200"], ["20261015", "z", "200"]]
    get = lambda url, gz=False: (200, {}, saved[url.split("/web/")[1][:8]])
    assert capture_with(caps, "https://s.example", sha256(ledger), get) == "20261015"            # newest first, packed copy unpacked
    assert capture_with(caps[:2], "https://s.example", sha256(ledger), get) == "20261013"        # skips the older draft
    assert capture_with(caps[1:2], "https://s.example", sha256(ledger), get) is None
    assert capture_with(caps, "https://s.example", sha256(ledger), lambda u, gz=False: (404, {}, b"")) is None


def test_ots_pending_and_anchored():
    from release import OTS_BITCOIN, OTS_MAGIC, OTS_PENDING, parse_ots
    d = bytes(range(32))
    base = OTS_MAGIC + b"\x01\x08" + d
    assert parse_ots(base + OTS_PENDING + b"xx") == (d.hex(), False, True)    # a calendar's promise only
    assert parse_ots(base + OTS_BITCOIN + b"xx") == (d.hex(), True, False)    # in a block
    assert parse_ots(b"junk") == (None, False, False)


def test_release_printed_hash():
    from release import printed_hash
    h = "a" * 64
    html = '<dd><code class="tok" data-sha-of="ledger.txt" data-name="ledger.txt" title="tap to copy">%s</code></dd>' % h
    assert printed_hash(html, "ledger.txt") == h and printed_hash(html, "archive/x.txt") is None


def test_release_against_a_local_site():
    """The repo served as it is: no line fails; and a post that names an earlier version is told which one."""
    import functools
    import http.server
    import threading
    from release import FAIL, ROOT, archive_hashes, run, sha256
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a, **k):
            pass
    handler = functools.partial(Quiet, directory=str(ROOT))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        site = "http://127.0.0.1:%d" % srv.server_address[1]
        assert not [w for s, w in run(site, "", archive=False) if s == FAIL]
        current = sha256((ROOT / "ledger.txt").read_bytes())
        older = next(((h, n) for h, n in archive_hashes().items() if h != current), None)
        if older:  # archive/ holds an earlier version: the post is told which one
            rows = run(site, older[0][:8], archive=False)
            assert any(s == FAIL and older[1] in w and "earlier version" in w for s, w in rows), rows
        rows = run(site, "00000000", archive=False)  # a hash that is no version at all
        assert any(s == FAIL and "matches no archived version" in w for s, w in rows), rows
    finally:
        srv.shutdown()


def test_agent_draft_waits_for_a_person():
    """A draft is held by the weekly page's own reading until a person fills it; it never says the link was opened."""
    import shutil
    import agent
    assert shutil.which("node"), "lint needs node (test_claims.js does too)"
    data = {"members": ["Ann", "Bo", "Zed"], "next": 2, "votes": [],
            "entries": [{"kind": "FACT", "num": 1, "writer": "Zed", "lines": 2, "empty": True, "results": []}]}
    assert agent.verdict_of(["x\nverdict: HOLDS\n"]) == "HOLDS" and agent.verdict_of(["no verdict here"]) is None
    assert agent.verdict_of(["verdict: HOLDS", "\nverdict (a, b): DOESN'T HOLD"]) == "DOESN'T HOLD"
    post = agent.draft_post(data["entries"][0], "Ann", "2026-10-16", "HOLDS", "Script: x")
    assert "I opened the link" not in post and agent.lint(post, data, "2026-10-16")
    done = (post.replace("Line 1:\nSaw:", "Line 1:\nSaw: 5 SOL").replace("Line 2:\nSaw:", "Line 2:\nSaw: none")
            .replace("New:", "New: the page is dated 2026-07-08") + "I opened the link myself.\n")
    assert agent.lint(done, data, "2026-10-16") == []
    assert agent.lint(done.replace("Saw: none", "Saw:"), data, "2026-10-16")          # a Saw: left empty
    assert agent.lint(done.replace("| Ann |", "| Zed |"), data, "2026-10-16")         # nobody checks their own entry
