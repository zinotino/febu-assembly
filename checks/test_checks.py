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


def worked_data():
    """ledger.json's questions and answers for the worked version-5 ledger (checks/fixtures), as build.py writes them:
    Q1 answer 1 copies fact 2 (reads the node), posted by Laura, Zurandol wrote fact 2; Q2 answer 2 copies fact 5 (reads
    a link), posted by CrypticK, Zurandol wrote fact 5, nobody has checked it."""
    import sys
    from common import ROOT
    sys.path.insert(0, str(ROOT))
    import build
    title, secs = build.sections(text("checks/fixtures/ledger_v5_worked.txt"))
    return build.ledger_dict(title, secs, build.model(secs), more=True)


DATA = worked_data()
NOW = "2026-11-09"
FILLED = ("CHECK Q2 ANSWER 2 · HOLDS · lines 1,2 · Merc · 2026-11-09\nLine 1:\nSaw: none of the eight on 1-24\n"
          "Items: all 24\nLine 2:\nSaw: none\nItems: all 140\nNew: page 25 is in verse\n%s\nI opened the link myself.\n")
SCRIPT = ("Script: python checks/fact5.py by Zurandol said HOLDS on ledger d3e17658 at 2026-11-09T12:00Z via "
          "febu-assembly.vercel.app")
FILLED %= SCRIPT


def with_scripts(agent, outs):
    """agent.execute answering with fixed output, for a test that must not touch the network. Returns the undo."""
    real = agent.execute
    agent.execute = lambda num, say=None, rpc=None: (["python checks/x.py"], list(outs))
    return lambda: setattr(agent, "execute", real)


def test_agent_draft_waits_for_a_person():
    """A draft is held by the weekly page's own reading until a person fills it; it never says the link was opened."""
    import copy
    import shutil
    import agent
    assert shutil.which("node"), "lint needs node (test_claims.js does too)"
    assert agent.verdict_of(["x\nverdict: HOLDS\n"]) == "HOLDS" and agent.verdict_of(["no verdict here"]) is None
    assert agent.verdict_of(["verdict: HOLDS", "\nverdict (a, b): DOESN'T HOLD"]) == "DOESN'T HOLD"
    q2 = DATA["questions"][1]
    post = agent.draft_post(q2, q2["answers"][1], "Merc", NOW, "HOLDS", "Script: x")
    assert post.startswith("CHECK Q2 ANSWER 2 · HOLDS · lines 1,2 · Merc · 2026-11-09\n")
    assert "I opened the link" not in post and agent.lint(post, DATA, NOW)
    assert agent.lint(FILLED, DATA, NOW) == []
    held = lambda text: agent.lint(text, DATA, NOW)   # noqa: E731
    assert held(FILLED.replace("Saw: none\n", "Saw:\n"))                                   # a Saw: left empty
    assert held(FILLED.replace("Saw: none\n", "Saw: .\n"))                                 # a dot is not an answer
    assert held(FILLED.replace("New: page 25 is in verse", "New: ?"))
    assert held(FILLED.replace("Line 2:\nSaw: none\nItems: all 140\n", ""))               # line 2 named, nothing seen on it
    assert held(FILLED.replace("I opened the link myself.", "I opened the link in my dreams? no"))
    assert held(FILLED.replace("\nI opened the link myself.\n", "\n\nI opened the link myself.\n"))   # outside the post
    assert held(FILLED + "\nVOTE YES · version 5 · Merc · 2026-11-09\n")                  # lint reads check posts only
    assert held(FILLED.replace("· Merc ·", "· CrypticK ·"))                               # a poster checks their own answer
    assert held(FILLED.replace("ANSWER 2 ·", "ANSWER 3 ·"))                                # Q2 has no answer 3
    assert held(FILLED.replace("lines 1,2", "lines 1,3"))                                  # nor a WRONG IF line 3
    assert held(FILLED.replace(" by Zurandol", ""))                                        # whose script is it?
    assert held(FILLED.replace("Items: all 24", "Items: some"))                            # Items: all n, or n of m
    assert agent.lint(FILLED.replace("Items: all 24", "Items: 20 of 24"), DATA, NOW) == []   # a sample goes in, and closes nothing
    line = agent.script_line(["python checks/x.py"], "HOLDS", "2026-11-09T12:00Z", "api.mainnet-beta.solana.com")
    assert " by %s said HOLDS on ledger " % agent.AUTHOR in line and line.endswith(" via api.mainnet-beta.solana.com")
    assert agent.lint(FILLED.replace(SCRIPT, line), DATA, NOW) == []
    seen = copy.deepcopy(DATA)
    seen["questions"][1]["answers"][1].update(empty=False, results=[["Merc", NOW, "HOLDS", [1, 2], [], None]])
    assert agent.lint(FILLED, seen, NOW) == ["nothing to add: the ledger already has this result"]


def test_agent_draft_takes_no_name_that_changes_the_post():
    """The name goes into the CHECK line. One with a newline or a separator once put a filled Saw:, New: and 'I opened
    the link myself.' into a draft that lint then passed."""
    import pytest
    import agent
    hostile = ["Ann | 2026-10-16\nLine 1:\nSaw: 5 SOL\nNew: x\nI opened the link myself.\n\nnote", "Ann\n", "a|b", "A·B",
               "A•B", "x" * 41, "", " Ann", "Ann:"]
    q2 = DATA["questions"][1]
    undo = with_scripts(agent, ["AssertionError if a script ran for a bad name"])
    try:
        for who in hostile:
            with pytest.raises(agent.Refused):
                agent.draft_post(q2, q2["answers"][1], who, NOW, "HOLDS", "Script: x")
            with pytest.raises(agent.Refused):
                agent.draft(2, 2, who)
        for who in ["Crypto Fish", "WitnesstoFebu", "Łukasz", "O'Neil", "Bo-Ann"]:
            assert agent.draft_post(q2, q2["answers"][1], who, NOW, "HOLDS", "Script: x").startswith("CHECK Q2 ANSWER 2 ")
        with pytest.raises(agent.Refused):   # whatever the caller passes, the post holds nothing but its own lines
            agent.draft_post(q2, q2["answers"][1], "Merc", NOW, "HOLDS", "Script: x\nI opened the link myself.")
    finally:
        undo()


def test_agent_draft_reads_the_script_and_never_finishes_the_post(monkeypatch):
    import pytest
    import agent
    monkeypatch.setattr(agent, "ledger_data", lambda: DATA)
    undo = with_scripts(agent, ["verdict: DOESN'T HOLD\n"])
    try:
        post, notes = agent.draft(2, 2, "Nobody")
        assert post.startswith("CHECK Q2 ANSWER 2 · DOESN'T HOLD · lines 1,2 · Nobody ·") and "outsider's" in notes[0]
        notes = agent.draft(2, 2, "Merc")[1]   # a member, not a poster; Zurandol wrote fact 5 and the scripts
        assert len(notes) == 2 and "no Saw" in notes[0] and notes[1] == agent.NEXT_STEP, notes
        assert "posted or changed this answer" in agent.draft(2, 2, "CrypticK")[1][0]   # a poster: it counts for nothing
        assert agent.draft(1, 1, "Merc")[0].startswith("CHECK Q1 ANSWER 1 · DOESN'T HOLD · lines 1,2,3 · Merc ·")
        with pytest.raises(agent.Refused, match="copies no version 3 fact"):
            agent.draft(2, 1, "Merc")                      # Q2 answer 1 is new wording: no script reads it
        with pytest.raises(agent.Refused, match="no Q9 answer 1"):
            agent.draft(9, 1, "Merc")
        assert agent.fact_of({"copies": ["PROMISE", 7]}) is None and agent.fact_of({"copies": None}) is None
        undo()
        undo = with_scripts(agent, ["verdict: CAN'T TELL (3 transactions unread)\n"])
        with pytest.raises(agent.Refused, match="CAN'T TELL"):
            agent.draft(1, 1, "Merc")
        undo()
        undo = with_scripts(agent, ["  a line   NOT SETTLED BY A SCRIPT\n\nverdict for what a script can settle: HOLDS\n"])
        post, notes = agent.draft(2, 2, "Merc")   # the script covers only part of the answer: no result is filled in
        assert post.startswith("CHECK Q2 ANSWER 2 · RESULT ·") and "HOLDS on ledger" in post
        assert any("unsettled" in n for n in notes), notes
        undo()
        undo = with_scripts(agent, ["verdict: HOLDS\n"])
        drafted = 0
        for q in DATA["questions"]:   # every answer with a script: the draft is held by lint and carries no attestation
            for a in q["answers"]:
                if agent.fact_of(a):
                    post = agent.draft(q["num"], a["num"], "Merc")[0]
                    assert "opened the link" not in post.lower() and agent.lint(post, DATA, NOW), (q["num"], a["num"])
                    drafted += 1
        assert drafted == 2
    finally:
        undo()


def test_agent_one_script_run_at_a_time_and_posts_read_as_text():
    import pytest
    import agent
    assert agent._busy.acquire(blocking=False)
    try:
        with pytest.raises(agent.Refused, match="still going"):
            agent.execute(1)
    finally:
        agent._busy.release()
    with pytest.raises(agent.Refused, match="no script"):
        agent.execute(7)
    import tempfile, os
    with tempfile.TemporaryDirectory() as d:
        for name, raw in (("u16.txt", "café".encode("utf-16")), ("u8.txt", b"\xef\xbb\xbfcaf\xc3\xa9")):
            path = os.path.join(d, name)
            open(path, "wb").write(raw)
            assert agent.read_post(path) == "café", name
        with pytest.raises(agent.Refused, match="cannot read"):
            agent.read_post(os.path.join(d, "missing.txt"))


def test_rpc_option_takes_a_node_and_keeps_its_key_out_of_what_is_printed(monkeypatch):
    """--rpc is the person's own node: https (http only on this machine), no whitespace, and a path or query in its
    address, which can be an API key, is cut from the output and never reaches a post."""
    import pytest
    import agent
    for good in ("https://api.mainnet-beta.solana.com", "https://x.example/k/SECRET?api-key=SECRET", "http://127.0.0.1:8899",
                 "http://localhost:8899", "http://[::1]:8899"):
        assert agent.check_rpc(good) == good
    for bad in ("http://example.com", "ftp://x.example", "https://", "x", "", "https://a b.example", "https://x.example:99999",
                "file:///etc/passwd", "javascript:alert(1)", "https://x.example/a\nb", "https://x.example/k/SEC\x01RET",
                "https://x.example/k/SECRET”", "https://user:SECRET@x.example", "https://a|b.example/",
                "https://x.example%0a/", "https://x.example﻿/", "https://[", "https://[::1", "https://x.example／a",
                "http://[::2]:8899", "https://x.example:99999/k"):
        with pytest.raises(agent.Refused, match="--rpc takes"):
            agent.check_rpc(bad)
    assert agent.host_of("https://x.example:8443/k/SECRET?a=SECRET") == "x.example:8443" and agent.host_of("x") == "unknown"
    assert agent.host_of("http://[::1]:8899/") == "[::1]:8899" and agent.host_of("https://x.example%0a/") == "unknown"
    assert agent.options(["--as", "Ann", "--rpc", "https://x.example"], ("--as", "--rpc")) == {"--as": "Ann", "--rpc": "https://x.example"}
    assert agent.options([], ("--rpc",)) == {}
    for words in (["--rpc"], ["--rpc="], ["--rpc=https://x.example"], ["--rcp", "https://x.example"], ["--rpc", "a", "--rpc", "b"],
                  ["--as", "Ann"], ["Smith"]):   # none of these may run on the default node
        with pytest.raises(agent.Refused):
            agent.options(words, ("--rpc",))
    for argv in (["run", "1", "--rpc"], ["run", "1", "--rpc="], ["run", "1", "--rpc=https://x.example"], ["run", "1", "--rpc", ""],
                 ["draft", "1", "--as", "Ann", "--rpc", ""], ["draft", "1", "--as", "Laura", "Smith"], ["draft", "1", "--rpc", "https://x.example"]):
        with pytest.raises(SystemExit):   # refused before any script runs
            agent.main(["agent.py"] + argv)
    with pytest.raises(agent.Refused, match="reads a link"):
        agent.execute(3, rpc="https://x.example")   # fact 3 reads the Internet Archive: there is no node to change
    with pytest.raises(agent.Refused, match="--rpc takes"):
        agent.execute(1, rpc="http://example.com")

    node, seen = "https://x.example/k/SECRET", {}

    class Done:
        returncode, stderr = 0, ""
        stdout = "read %s ok\nverdict: HOLDS\n" % node

    def fake(cmd, **kw):
        seen.update(kw)
        return Done
    monkeypatch.setattr(agent.subprocess, "run", fake)
    cmds, outs = agent.execute(1, rpc=node)
    assert seen["env"]["SOLANA_RPC"] == node and "SECRET" not in outs[0] and "read https://x.example ok" in outs[0]
    Done.returncode, Done.stderr = 1, "answered HTTP 429 from %s" % node
    with pytest.raises(agent.Refused) as e:
        agent.execute(1, rpc=node)
    assert "SECRET" not in str(e.value) and "https://x.example" in str(e.value)
    Done.returncode, Done.stderr = 1, "POST /k/SECRET HTTP/1.1 refused"   # an error that echoes only the path
    with pytest.raises(agent.Refused) as e:
        agent.execute(1, rpc=node)
    assert "SECRET" not in str(e.value)


def test_solana_rpc_is_checked_like_rpc_and_no_key_leaks(monkeypatch):
    """SOLANA_RPC is how the MCP server sets the node. One with user:key@ once put the key in an InvalidURL error, and a
    typo with no :// came back whole in a traceback. Both are refused now, before any script runs, with no address in the
    message. A node that echoes its key alone has it cut, and one that answers with a redirect is refused, not followed."""
    import http.server
    import threading
    import pytest
    import agent
    import common
    ran = []
    monkeypatch.setattr(agent.subprocess, "run", lambda *a, **k: ran.append(a))
    for bad in ("https://user:KEYSECRET@127.0.0.1/x", "https//host.example/KEYSECRET", "KEYSECRET", "https://x.example:٨٠/"):
        monkeypatch.setattr(common, "RPC", bad)
        with pytest.raises(agent.Refused, match="SOLANA_RPC takes") as e:
            agent.execute(2)
        assert "KEYSECRET" not in str(e.value) and "٨" not in str(e.value) and not ran
    monkeypatch.setattr(common, "RPC", "https://api.mainnet-beta.solana.com")
    assert agent.check_rpc(common.RPC, "SOLANA_RPC") == common.RPC
    url = "https://mainnet.example/v2/?api-key=abcdef-123456"
    assert agent.redact("invalid api key abcdef-123456 for %s" % url, url) == "invalid api key <cut> for https://mainnet.example"
    assert agent.redact("x KEYSECRET y", "KEYSECRET") == "x <cut> y"

    class Moved(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            self.send_response(302)
            self.send_header("Location", "http://127.0.0.1:9/elsewhere")
            self.end_headers()

        def log_message(self, *a):
            pass
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Moved)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        monkeypatch.setattr(common, "RPC", "http://127.0.0.1:%d/" % srv.server_address[1])
        with pytest.raises(SystemExit, match="answered HTTP 302"):
            common.rpc("getSlot", [])
    finally:
        srv.shutdown()


def test_script_line_names_its_source(monkeypatch):
    import agent
    monkeypatch.setattr(agent, "ledger_data", lambda: DATA)
    undo = with_scripts(agent, ["verdict: HOLDS\n"])
    try:
        line = agent.run_entry(1, rpc="https://x.example:8443/k/SECRET")[1]
        assert line.endswith(" via x.example:8443") and "SECRET" not in line
        assert agent.run_entry(1)[1].endswith(" via " + agent.host_of(agent.common.RPC))
        assert agent.run_entry(3)[1].endswith(" via web.archive.org")   # a link fact: the host its own link names
        post, notes = agent.draft(1, 1, "Merc", rpc="https://x.example/k/SECRET")   # Q1 answer 1 copies fact 2: the node
        assert "no Saw" in notes[0]   # Zurandol wrote fact 2 and the scripts
        assert "Script: python checks/x.py by %s said HOLDS on ledger" % agent.AUTHOR in post
        assert post.count("via x.example") == 1
        assert "SECRET" not in post
    finally:
        undo()
    assert {agent.source_of(n) for n in agent.RPC_FACTS} == {agent.host_of(agent.common.RPC)}
    assert agent.source_of(7) == "unknown" and agent.source_of(5) != "unknown" and agent.source_of(4) != "unknown"


def test_lint_notes_two_checks_that_read_one_source():
    """Two members who each opened the link are two checks; two Script: lines that name one host are one witness. The
    note holds nothing back: it is for the people reading the week."""
    import agent
    def post(who, via):   # on Q1 answer 1, which copies fact 2: its script reads the node
        script = "Script: python checks/resolve.py fact2 by Zurandol said HOLDS on ledger d3e17658 at 2026-11-09T10:00Z"
        return ("CHECK Q1 ANSWER 1 · HOLDS · lines 1,2,3 · %s · 2026-11-09\nLine 1:\nSaw: 23,843,803.61\nItems: all 1\n"
                "Line 2:\nSaw: none left\nItems: all 1\nLine 3:\nSaw: none in\nItems: all 1\nNew: the fee payer\n%s\n"
                "I opened the link myself.\n") % (who, script + (" via " + via if via else ""))
    review = lambda *posts: agent.review("\n\n".join(posts), DATA, NOW)   # noqa: E731
    why, notes = review(post("Merc", "node.example"), post("Ksizzle", "NODE.example."))   # case and a full stop: one source
    assert why == [] and len(notes) == 1, (why, notes)
    assert "Q1 answer 1: Ksizzle and Merc" in notes[0] and "one source" in notes[0] and "--rpc" in notes[0]
    assert review(post("Merc", "node.example"), post("Ksizzle", "other.example"))[1] == []
    assert len(review(post("Merc", "node.example:443"), post("Ksizzle", "node.example"))[1]) == 1   # https's own port
    assert review(post("Merc", "node.example"), post("Merc", "node.example"))[1] == []   # one member twice is not two
    assert review(post("Merc", ""), post("Ksizzle", ""))[1] == []                        # no source named: nothing to compare
    assert review(post("Merc", "unknown"), post("Ksizzle", "unknown"))[1] == []
    assert agent.lint(post("Merc", "node.example"), DATA, NOW) == []                     # lint is still the reasons only
    held = review(post("Merc", "node.example"), post("Ksizzle", "node.example").replace("Saw: none in", "Saw: ."))
    assert held[0] and len(held[1]) == 1                                                # a held post is still counted
    assert review(post("Merc", "127.0.0.1:8899"), post("Ksizzle", "127.0.0.1:8899"))[1] == []   # two nodes, two machines
    assert review(post("Merc", "[::1]:8899"), post("Ksizzle", "[::1]:8899"))[1] == []
    assert review(post("Laura", "node.example"), post("Ksizzle", "node.example"))[1] == []   # a poster's post is no check
    assert review(post("Cy", "node.example"), post("Ksizzle", "node.example"))[1] == []      # nor is a non-member's
    assert review(post("Merc", "node.example)"), post("Ksizzle", "node.example"))[1]         # a bracket is not a source
    link = lambda who: FILLED.replace("· Merc ·", "· %s ·" % who)   # noqa: E731  Q2 answer 2 copies fact 5: a link
    assert review(link("Merc"), link("Ksizzle")) == ([], [])          # --rpc cannot change a link fact's host


def test_swap_test_notes_a_reading_that_would_fit_another_answer():
    """Saw: and New: that use none of an answer's own words, or more of another's, or that two answers share, are a frame."""
    import agent
    ans = lambda num, says, wrong_if: {"num": num, "says": says, "wrong_if": [wrong_if]}   # noqa: E731
    data = {"questions": [
        {"num": 1, "answers": [ans(1, "the wallet bought nothing between 2026-09-29 and 2026-10-09", "ApWpkd8 signed a swap"),
                               ans(2, "the wallet sold 23,843,803.61 tokens on 2026-09-22", "the sale moves another amount")]},
        {"num": 2, "answers": [ans(1, "2,939.10 SOL arrived in 44 payments", "a payment goes somewhere else")]}]}
    one = {"questions": [{"num": 1, "answers": data["questions"][0]["answers"][:1]}]}
    post = lambda q, a, text, who="Ann": {"q": q, "a": a, "who": who, "text": text}   # noqa: E731
    reading = post(1, 1, "opened the swap list, ApWpkd8 signed nothing in the window")
    assert agent.swap_notes([reading], data) == []                                                     # own words: a reading
    none = agent.swap_notes([post(1, 1, "looked fine, matches what the answer says")], data)
    assert len(none) == 1 and "none of this answer's words" in none[0] and "Q1 answer 1 (Ann)" in none[0]
    other = agent.swap_notes([post(1, 1, "the sale moved 23,843,803.61 tokens, a different amount")], data)
    assert len(other) == 1 and "more of Q1 answer 2's own words" in other[0]
    same = "everything looked right to me, nothing odd, nothing missing, nothing unusual anywhere"
    twin = agent.swap_notes([post(1, 1, same), post(2, 1, same, "Bo")], data)
    assert any("nearly the same" in n for n in twin)                                                   # one text, two answers
    assert not any("nearly the same" in n for n in agent.swap_notes([post(1, 1, same), post(1, 1, same, "Bo")], data))   # one answer twice is not a swap
    assert agent.swap_notes([post(1, 1, "anything")], one) == []                                       # one answer: nothing to swap with
    assert agent.swap_notes([post(1, 1, "")], data) == [] and agent.swap_notes([post(1, 1, ".")], data) == []   # lint holds an empty one
    assert agent.swap_notes([post(9, 9, "looked fine")], data) == []                                   # an answer the ledger lacks
    # a date is the most answer-specific thing a reading has; a plural and a figure without its comma are the same words
    dated = {"questions": [{"num": 1, "answers": [ans(1, "bought nothing between 2026-09-29 and 2026-10-09", "the transaction is a swap"),
                                                  ans(2, "sold 23,843,803.61 tokens on 2026-09-22", "the transaction moves more")]}]}
    assert agent.swap_notes([post(1, 1, "checked 2026-09-29 to 2026-10-09 and the transactions show nothing")], dated) == []
    assert agent.swap_notes([post(1, 2, "I saw the sale of 23843803.61 tokens on 2026-09-22")], dated) == []
    assert len(agent.swap_notes([post(1, 1, "the sale of 23,843,803.61 tokens on 2026-09-22 is there")], dated)) == 1
    # end to end through review(): the node reader hands each post's Saw:/New: text to swap_notes
    chat = FILLED.replace("Saw: none of the eight on 1-24", "Saw: looked fine, matches the answer")
    q2 = DATA["questions"][1]
    other_q = {**DATA["questions"][0], "answers": [{**DATA["questions"][0]["answers"][0], "says": "sold 23,843,803.61 tokens",
                                                   "wrong_if": ["a swap"]}]}
    mine = {**q2, "answers": [{**a, "says": "bought nothing 2026-09-29", "wrong_if": ["a buy"]} if a["num"] == 2 else a
                              for a in q2["answers"]]}
    why, notes = agent.review(chat, {**DATA, "questions": [other_q, mine]}, NOW)
    assert any("Q2 answer 2 (Merc)" in n and "none of this answer's words" in n for n in notes), (why, notes)


def test_ledger_json_is_written_from_this_ledger():
    """ledger.json is the committed index of ledger.txt: a ledger.txt edited without python build.py fails here."""
    import agent
    agent.ledger_data()   # refuses when the hash inside is not ledger.txt's


def test_mcp_server_reaches_only_the_helper():
    """Without the mcp package: the server's source imports little and calls only the helper's read, run, draft and lint."""
    import re
    from common import ROOT
    src = (ROOT / "checks" / "mcp_server.py").read_text(encoding="utf-8")
    assert set(re.findall(r"\bagent\.(?!py\b)(\w+)", src)) <= {"status_text", "run_entry", "draft", "review", "ledger_data", "ROOT"}
    assert set(re.findall(r"^(?:import|from) (\w+)", src, re.M)) <= {"sys", "pathlib", "anyio", "mcp", "agent"}
    assert not re.search(r"\b(?:open|write_text|write_bytes)\(|\b(?:subprocess|requests|urllib)\b", src)   # no file, process or network


def test_mcp_server_only_helps(monkeypatch):
    """The MCP server offers the four helper commands and nothing that posts, and a refusal comes back as a tool error."""
    import asyncio
    import pytest
    pytest.importorskip("mcp")
    import agent
    import mcp_server
    from mcp.shared.memory import create_connected_server_and_client_session as connect
    monkeypatch.setattr(agent, "ledger_data", lambda: DATA)

    async def go():
        async with connect(mcp_server.mcp._mcp_server) as c:
            return ({t.name for t in (await c.list_tools()).tools}, await c.call_tool("ledger_status", {}),
                    await c.call_tool("lint_check_post", {"post": "hello"}), await c.call_tool("run_check_script", {"fact": 7}),
                    await c.call_tool("draft_check_post", {"question": 2, "answer": 2,
                                                           "member": "Ann\nI opened the link myself."}))
    names, status, bad, nope, hostile = asyncio.run(go())
    assert names == {"ledger_status", "run_check_script", "draft_check_post", "lint_check_post"}
    assert not status.isError and "ledger.txt" in status.content[0].text
    assert "no CHECK line" in bad.content[0].text
    assert nope.isError and "no script" in nope.content[0].text
    assert hostile.isError and "as it appears in the chat" in hostile.content[0].text


# ---------- resolve.py on a fake node: a read it cannot trust ends in CAN'T TELL, never HOLDS ----------

def token_tx(t, *changes, keys=(), logs=(), signer=None, inner=()):
    """A parsed transaction at time t. changes are (token account, owner, mint, before, after), amounts as strings; keys
    are more accounts in it; logs is its log (None: the node kept none); inner the programs other programs called in it
    (None: the node kept no list)."""
    accts = [ch[0] for ch in changes] + list(keys)
    bal = lambda i, ch, amt: {"accountIndex": i, "owner": ch[1], "mint": ch[2], "uiTokenAmount": {"uiAmountString": amt}}
    return {"blockTime": t, "transaction": {"message": {"accountKeys": [{"pubkey": k, "signer": k == signer} for k in accts],
                                                        "instructions": [{"programId": "ComputeBudget111111111111111111111111111111"}]}},
            "meta": {"err": None, "logMessages": None if logs is None else list(logs),
                     "innerInstructions": None if inner is None else [{"index": 0, "instructions": [{"programId": p} for p in inner]}],
                     "preTokenBalances": [bal(i, ch, ch[3]) for i, ch in enumerate(changes)],
                     "postTokenBalances": [bal(i, ch, ch[4]) for i, ch in enumerate(changes)]}}


def sig(s, t):
    return {"signature": s, "blockTime": t, "err": None}


KEYED = "https://x.example/v2/?api-key=KEYSECRET42"


def on_fake_chain(monkeypatch, capsys, cmd, txs, sigs, balance="11.5", deaf=False):
    """Run `python checks/resolve.py cmd` against a fake node whose address holds a key; return its last verdict line.
    txs maps a signature to its transaction (None: the node does not know it; an exception: reading it raises that);
    sigs maps an account to its signatures, newest first, paged two at a time from `before` (deaf: a node that ignores
    `before`). No run may print the key."""
    import collections
    import resolve
    asked = collections.Counter()

    def rpc(method, params):
        if method == "getTokenAccountBalance":
            return {"value": {"uiAmountString": balance}}
        if method == "getSignaturesForAddress":
            asked[params[0]] += 1
            assert asked[params[0]] < 50, "paged forever"
            got = sigs.get(params[0], [])
            at = 0 if deaf or "before" not in params[1] else [s["signature"] for s in got].index(params[1]["before"]) + 1
            return got[at:at + 2]
        got = txs.get(params[0])
        if isinstance(got, BaseException):
            raise got
        return got
    monkeypatch.setattr(resolve.c, "RPC", KEYED)
    monkeypatch.setattr(resolve.c, "rpc", rpc)
    monkeypatch.setattr(resolve.time, "sleep", lambda s: None)
    try:
        resolve.main(cmd)
    except SystemExit:
        pass
    out = capsys.readouterr().out
    assert "KEYSECRET42" not in out
    said = [ln for ln in out.splitlines() if ln.startswith("verdict")]
    return said[-1] if said else out


def test_resolve_fact8_says_cant_tell_on_a_read_it_cannot_trust(monkeypatch, capsys):
    """Fact 8 on a fake chain where it holds, then with one thing broken each: a control payment the node does not know,
    a control that does not match, 09-22 read without the fee account's balance or not at all, a signature with no block
    time, a payment out whose amount the node left out. Each must say CAN'T TELL, never HOLDS."""
    import copy
    import resolve
    wallet = find(r"other than (%s)" % B58, entry(6), "wallet")
    fee = find(r"solscan\.io/account/(%s)" % B58, entry(6), "fee account")
    ata = resolve.derive_ata(wallet, WSOL)
    steps = [s for *_, s in rows(text("fact-6-steps.txt"))[0]]
    d14, d22, oct1 = resolve.day(2026, 9, 14, 21), resolve.day(2026, 9, 22), resolve.day(2026, 10, 1)
    paid = lambda t, a, b: token_tx(t, (fee, "pool", WSOL, a, b), (ata, wallet, WSOL, "0", "1"))
    txs = {**{s: token_tx(d14, keys=[ata]) for s in steps}, resolve.ROW_20: token_tx(d14, (ata, wallet, WSOL, "0", "1")),
           steps[-1]: paid(d14, "7", "0.131"),   # row 44, the one payment out on 09-14
           "open": token_tx(d22 + 60, (fee, "pool", WSOL, "3.9", "4.5")),   # read in the wrong order, 09-22 opens at 4.5
           "close": token_tx(d22 + 3600, (fee, "pool", WSOL, "4.5", "5.0")), "pay": paid(oct1, "11", "0.5")}
    sigs = {ata: [sig(steps[-1], d14)], fee: [sig("close", d22 + 3600), sig("open", d22 + 60), sig(steps[-1], d14)]}
    paying = {**sigs, ata: [sig("pay", oct1), *sigs[ata]]}
    assert on_fake_chain(monkeypatch, capsys, "fact8", txs, sigs) == "verdict: HOLDS"
    assert on_fake_chain(monkeypatch, capsys, "fact8", txs, paying) == "verdict: DOESN'T HOLD"

    def broken(edit, s=sigs):
        t, g = copy.deepcopy(txs), copy.deepcopy(s)
        edit(t, g)
        return on_fake_chain(monkeypatch, capsys, "fact8", t, g)
    cases = {"a control payment the node does not know": lambda t, g: t.update({steps[0]: None}),
             "row 20 paid another account": lambda t, g: t.update({resolve.ROW_20: token_tx(d14, ("x", wallet, WSOL, "0", "1"))}),
             "09-14 shows no payment out": lambda t, g: t.update({steps[-1]: token_tx(d14, keys=[ata, fee])}),
             "09-22's first transaction lists no fee balance": lambda t, g: t.update({"open": token_tx(d22 + 60, keys=[fee])}),
             "09-22's first transaction does not read": lambda t, g: t.update({"open": SystemExit("HTTP 500")}),
             "no transaction read on 09-22": lambda t, g: g.update({fee: g[fee][2:]}),
             "a signature with no block time": lambda t, g: g[fee][0].update({"blockTime": None}),
             "the node refuses row 20 and names its own key": lambda t, g: t.update({resolve.ROW_20: SystemExit("HTTP 401 " + KEYED)})}
    for name, edit in cases.items():
        assert broken(edit).startswith("verdict: CAN'T TELL"), name
    # an amount the node left out is not a balance of zero: here it would hide the payment out
    gone = lambda t, g: t["pay"]["meta"]["preTokenBalances"][0]["uiTokenAmount"].pop("uiAmountString")
    assert broken(gone, paying).startswith("verdict: CAN'T TELL")
    assert "the same page twice" in on_fake_chain(monkeypatch, capsys, "fact8", txs, sigs, deaf=True)   # it ignores `before`


def test_resolve_door2_counts_a_log_it_cannot_see_whole_as_unread(monkeypatch, capsys):
    """Door 2 greps each transaction's log for the call. A log the node did not keep, or cut short without the word, cannot
    show the call is absent, unless the transaction never runs pAMM, whose instruction the call is: the node keeps every
    instruction even when it cuts the log. Nor can a dry run that names the call and then fails, as one on a wrong vault does."""
    import resolve
    word = "Program log: Instruction: TransferCreatorFeesToPumpV2"
    dry = {"run": (None, [word], {})}
    monkeypatch.setattr(resolve, "payer", lambda: "1" * 32)
    monkeypatch.setattr(resolve, "simulate", lambda payer, ixs, watch=(): dry["run"])
    wallet = find(r"other than (%s)" % B58, entry(6), "wallet")
    pcv = resolve.to_pump_v2(wallet, find(r"solscan\.io/account/(%s)" % B58, entry(6), "fee account"))[0]
    oct1, cut = resolve.day(2026, 10, 1), ["Program log: Instruction: Buy", "Log truncated"]
    swap = token_tx(oct1, logs=["Program log: Instruction: Buy"], inner=[resolve.PAMM])

    def door2(b, before=(sig("older", resolve.day(2026, 9, 10)),)):
        return on_fake_chain(monkeypatch, capsys, "door2", {"a": swap, "b": b}, {pcv: [sig("a", oct1 + 60), sig("b", oct1), *before]})
    assert door2(swap) == "verdict: HOLDS"
    assert door2(token_tx(oct1, logs=[word], inner=[resolve.PAMM])) == "verdict: DOESN'T HOLD"
    assert door2(token_tx(oct1, logs=[word, "Log truncated"], inner=[resolve.PAMM])) == "verdict: DOESN'T HOLD"   # the call shows
    assert door2(token_tx(oct1, logs=cut, inner=[resolve.PUMP])) == "verdict: HOLDS"   # cut short, but pAMM never ran
    for b in (token_tx(oct1, logs=None, inner=[resolve.PAMM]), token_tx(oct1, logs=cut, inner=[resolve.PAMM]),
              token_tx(oct1, logs=cut, inner=None), token_tx(oct1, logs=[], inner=[resolve.PAMM]), {**swap, "meta": None}):
        assert door2(b).startswith("verdict: CAN'T TELL"), b
    assert door2(swap, before=()).startswith("verdict: CAN'T TELL")   # a node whose history stops inside the window
    assert on_fake_chain(monkeypatch, capsys, "door2", {}, {}).startswith("verdict: CAN'T TELL")   # or that shows none at all
    dry["run"] = ({"InstructionError": [0, {"Custom": 2006}]}, [word, "Program log: AnchorError: ConstraintSeeds"], {})
    assert door2(swap).startswith("verdict: CAN'T TELL")


def test_resolve_fact1_gates_its_verdict_on_its_controls(monkeypatch, capsys):
    """Fact 1 on a fake chain where it holds, then with a control failing (the sale left from another account; the 08-14
    inflow is not where the window rule expects it), a creating transaction whose log the node cut short or kept none of,
    and a buy in the window whose balance has no owner. None of them may say HOLDS."""
    import copy
    import resolve
    create, wallet = find(r"solscan\.io/tx/(%s)" % B58, entry(1), "create"), find(r"signer is\s+(%s)" % B58, entry(1), "wallet")
    mint, sale = find(r"\$FEBU token,\s+(%s)" % B58, entry(1), "mint"), find(r"solscan\.io/tx/(%s)" % B58, entry(2), "sale")
    ata = resolve.derive_ata(wallet, mint, resolve.TOKEN_2022)
    aug14, oct1 = resolve.day(2026, 8, 14, 12), resolve.day(2026, 10, 1)
    txs = {create: token_tx(resolve.day(2026, 7, 8), keys=[wallet, mint], signer=wallet,
                            logs=["Program log: Instruction: InitializeMint2"]),
           sale: token_tx(resolve.day(2026, 9, 22), (ata, wallet, mint, "100", "0")),
           "in": token_tx(aug14, (ata, wallet, mint, "0", "100")), "buy": token_tx(oct1, (ata, wallet, mint, "0", "5"))}
    sigs, buying = {ata: [sig("in", aug14)]}, {ata: [sig("buy", oct1), sig("in", aug14)]}
    assert on_fake_chain(monkeypatch, capsys, "fact1", txs, sigs) == "verdict: HOLDS"
    assert on_fake_chain(monkeypatch, capsys, "fact1", txs, buying) == "verdict: DOESN'T HOLD"

    def broken(edit, s=sigs):
        t = copy.deepcopy(txs)
        edit(t)
        return on_fake_chain(monkeypatch, capsys, "fact1", t, s)
    cut = ["Program log: Instruction: Create", "Log truncated"]
    cases = {"the sale left from another account": lambda t: t.update({sale: token_tx(1, ("x", wallet, mint, "100", "0"))}),
             "the 08-14 inflow came on 08-20": lambda t: t["in"].update({"blockTime": resolve.day(2026, 8, 20)}),
             "the creating log cut short": lambda t: t[create]["meta"].update({"logMessages": cut}),
             "no creating log kept": lambda t: t[create]["meta"].update({"logMessages": None})}
    for name, edit in cases.items():
        assert broken(edit).startswith("verdict: CAN'T TELL"), name
    no_owner = lambda t: t["buy"]["meta"]["postTokenBalances"][0].pop("owner")
    assert broken(no_owner, buying).startswith("verdict: CAN'T TELL")


def test_resolve_fact9_reads_no_line_from_a_log_it_cannot_see_whole():
    import pytest
    import resolve
    r = token_tx(0, keys=["S", "V"], signer="S", logs=["Program log: Instruction: AdminSetCreator"])
    assert resolve.verdict(resolve.lines9(r, "S", "V", "AdminSetCreator")) == "HOLDS"
    r["meta"]["logMessages"].append("Log truncated")   # cut short after the word: the word still shows
    assert resolve.verdict(resolve.lines9(r, "S", "V", "AdminSetCreator")) == "HOLDS"
    for logs in (None, [], ["Program log: Instruction: Other", "Log truncated"]):   # a run always logs its first invoke
        r["meta"]["logMessages"] = logs
        with pytest.raises(SystemExit, match="whole log"):
            resolve.lines9(r, "S", "V", "AdminSetCreator")


def test_resolve_reads_the_copy_it_names_not_where_a_redirect_points():
    """The archive answers a stamp it has no copy of with a redirect to the nearest copy. Following it would check another
    copy than the ledger names, so get() refuses it."""
    import http.server
    import threading
    import urllib.error
    import pytest
    import resolve

    class Moved(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(302 if self.path == "/named" else 200)
            if self.path == "/named":
                self.send_header("Location", "/nearest")
            self.end_headers()
            self.wfile.write(b"" if self.path == "/named" else b"another copy")

        def log_message(self, *a):
            pass
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Moved)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        base = "http://127.0.0.1:%d" % srv.server_address[1]
        assert resolve.get(base + "/nearest") == b"another copy"
        with pytest.raises(urllib.error.HTTPError, match="302"):
            resolve.get(base + "/named")
    finally:
        srv.shutdown()


def test_resolve_fact4_hashes_the_copy_it_checks(monkeypatch, capsys):
    """Fact 4 printed the SHA-256 of a second download, not of the copy it checked: a copy that changed in between showed
    a hash that names neither."""
    import hashlib
    import json
    import re
    import resolve
    books = re.findall(r"\d+-\d+ (THE [A-Z ]+?)(?:,| then)", " ".join(entry(4).split()))
    checked = json.dumps([{"page_number": n, "book": books[(n - 1) // 4 % 8]} for n in range(1, 165)]).encode()
    copies = [checked, checked + b" "]
    monkeypatch.setattr(resolve, "get", lambda url: copies.pop(0))
    resolve.fact4()
    out = capsys.readouterr().out
    assert hashlib.sha256(checked).hexdigest() in out and "verdict (on this copy, KNOWN BUGS 3): HOLDS" in out


def test_no_key_in_what_the_checks_print(monkeypatch, capsys):
    """A direct run (not through agent.py) with SOLANA_RPC holding a key: the key is in no error and no header line. The
    node refuses (HTTP 401); the HTTP library echoes an address it cannot parse; fact 2 and fact 6 name the node they read.
    resolve.py's runs are checked in on_fake_chain."""
    import http.server
    import runpy
    import threading
    from pathlib import Path
    import pytest
    import common
    import fact6

    class Refuse(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            self.send_response(401)
            self.end_headers()

        def log_message(self, *a):
            pass
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Refuse)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        monkeypatch.setattr(common, "RPC", "http://127.0.0.1:%d/v2/?api-key=KEYSECRET42" % srv.server_address[1])
        with pytest.raises(SystemExit, match="answered HTTP 401") as e:
            common.rpc("getSlot", [])
        assert "KEYSECRET42" not in str(e.value)
    finally:
        srv.shutdown()
    monkeypatch.setattr(common.time, "sleep", lambda s: None)
    monkeypatch.setattr(common, "RPC", "https://user:KEYSECRET42@x.example/")   # InvalidURL: "nonnumeric port: 'KEYSECRET42@..."
    with pytest.raises(SystemExit, match="no answer") as e:
        common.rpc("getSlot", [])
    assert "KEYSECRET42" not in str(e.value)
    monkeypatch.setattr(common, "RPC", "KEYSECRET42")   # no scheme: urllib's ValueError repeats it whole
    with pytest.raises(SystemExit) as e:
        common.rpc("getSlot", [])
    assert "KEYSECRET42" not in str(e.value)

    key = "https://x.example/v2/?api-key=KEYSECRET42"
    monkeypatch.setattr(common, "RPC", key)
    monkeypatch.setattr(fact6, "RPC", key)   # fact 6 took the name when it was imported
    monkeypatch.setattr(common, "rpc", lambda method, params: {"value": []} if method == "getTokenAccountsByOwner"
                        else token_tx(0, keys=["W"], signer="W"))
    runpy.run_path(str(Path(common.__file__).parent / "fact2.py"))

    def stop(method, params):
        raise SystemExit("stop")
    monkeypatch.setattr(common, "rpc", stop)
    with pytest.raises(SystemExit, match="stop"):   # fact 6 stops at its first read, after its header
        fact6.main()
    out = capsys.readouterr().out
    assert "Fact 2, read" in out and "Fact 6, read" in out and "x.example" in out and "KEYSECRET42" not in out
