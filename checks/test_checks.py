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


DATA = {"members": ["Ann", "Bo", "Zed"], "next": 2, "votes": [],
        "entries": [{"kind": "FACT", "num": 1, "writer": "Zed", "lines": 2, "empty": True, "results": []}]}
FILLED = ("CHECK FACT 1 | HOLDS | lines 1,2 | Ann | 2026-10-16\nLine 1:\nSaw: 5 SOL\nLine 2:\nSaw: none\n"
          "New: the page is dated 2026-07-08\n%s\nI opened the link myself.\n")
SCRIPT = "Script: python checks/x.py by Zed said HOLDS on ledger d3e17658 at 2026-10-16T12:00Z via api.mainnet-beta.solana.com"
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
    post = agent.draft_post(DATA["entries"][0], "Ann", "2026-10-16", "HOLDS", "Script: x")
    assert "I opened the link" not in post and agent.lint(post, DATA, "2026-10-16")
    assert agent.lint(FILLED, DATA, "2026-10-16") == []
    held = lambda text: agent.lint(text, DATA, "2026-10-16")   # noqa: E731
    assert held(FILLED.replace("Saw: none", "Saw:"))                                       # a Saw: left empty
    assert held(FILLED.replace("Saw: none", "Saw: ."))                                     # a dot is not an answer
    assert held(FILLED.replace("New: the page is dated 2026-07-08", "New: ?"))
    assert held(FILLED.replace("Line 2:\nSaw: none\n", ""))                                # line 2 named, nothing seen on it
    assert held(FILLED.replace("I opened the link myself.", "I opened the link in my dreams? no"))
    assert held(FILLED.replace("\nI opened the link myself.\n", "\n\nI opened the link myself.\n"))   # outside the post
    assert held(FILLED + "\nVOTE YES | version 3 | Ann | 2026-10-16\n")                    # lint reads check posts only
    assert held(FILLED.replace("| Ann |", "| Zed |"))                                      # nobody checks their own entry
    assert held(FILLED.replace(" by Zed", ""))                                             # whose script is it?
    assert held(FILLED.replace("Saw: 5 SOL", "Saw: 5 SOL\nItems: some"))                   # Items: all n, or n of m
    assert agent.lint(FILLED.replace("Saw: 5 SOL", "Saw: 5 SOL\nItems: 20 of 164"), DATA, "2026-10-16") == []
    line = agent.script_line(["python checks/x.py"], "HOLDS", "2026-10-16T12:00Z", "api.mainnet-beta.solana.com")
    assert " by %s said HOLDS on ledger " % agent.AUTHOR in line and line.endswith(" via api.mainnet-beta.solana.com")
    assert agent.lint(FILLED.replace(SCRIPT, line), DATA, "2026-10-16") == []
    seen = copy.deepcopy(DATA)
    seen["entries"][0].update(empty=False, results=[["Ann", "2026-10-16", "HOLDS", [1, 2]]])
    assert agent.lint(FILLED, seen, "2026-10-16") == ["nothing to add: the ledger already has this result"]


def test_agent_draft_takes_no_name_that_changes_the_post():
    """The name goes into the CHECK line. One with a newline or a separator once put a filled Saw:, New: and 'I opened
    the link myself.' into a draft that lint then passed."""
    import pytest
    import agent
    hostile = ["Ann | 2026-10-16\nLine 1:\nSaw: 5 SOL\nNew: x\nI opened the link myself.\n\nnote", "Ann\n", "a|b", "A·B",
               "A•B", "x" * 41, "", " Ann", "Ann:"]
    undo = with_scripts(agent, ["AssertionError if a script ran for a bad name"])
    try:
        for who in hostile:
            with pytest.raises(agent.Refused):
                agent.draft_post(DATA["entries"][0], who, "2026-10-16", "HOLDS", "Script: x")
            with pytest.raises(agent.Refused):
                agent.draft(1, who)
        for who in ["Crypto Fish", "WitnesstoFebu", "Łukasz", "O'Neil", "Bo-Ann"]:
            assert agent.draft_post(DATA["entries"][0], who, "2026-10-16", "HOLDS", "Script: x").startswith("CHECK FACT 1")
        with pytest.raises(agent.Refused):   # whatever the caller passes, the post holds nothing but its own lines
            agent.draft_post(DATA["entries"][0], "Ann", "2026-10-16", "HOLDS", "Script: x\nI opened the link myself.")
    finally:
        undo()


def test_agent_draft_reads_the_script_and_never_finishes_the_post():
    import pytest
    import agent
    real = agent.ledger_data()
    members = real["members"]
    undo = with_scripts(agent, ["verdict: DOESN'T HOLD\n"])
    try:
        post, notes = agent.draft(1, "Nobody")
        assert post.startswith("CHECK FACT 1 | DOESN'T HOLD | lines 1,2,3 | Nobody |") and "outsider's" in notes[0]
        assert not [n for n in agent.draft(1, members[0])[1] if "outsider" in n]
        undo()
        undo = with_scripts(agent, ["verdict: CAN'T TELL (3 transactions unread)\n"])
        with pytest.raises(agent.Refused, match="CAN'T TELL"):
            agent.draft(1, members[0])
        undo()
        undo = with_scripts(agent, ["  a line   NOT SETTLED BY A SCRIPT\n\nverdict for what a script can settle: HOLDS\n"])
        post, notes = agent.draft(3, members[0])   # the script covers only part of fact 3: no result is filled in
        assert post.startswith("CHECK FACT 3 | RESULT |") and "HOLDS on ledger" in post and "unsettled" in notes[0]
        undo()
        undo = with_scripts(agent, ["verdict: HOLDS\n"])
        for num in agent.SCRIPTS:   # every entry with a script: the draft is held by lint and carries no attestation
            post = agent.draft(num, members[0])[0]
            assert "opened the link" not in post.lower() and agent.lint(post, real), num
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


def test_script_line_names_its_source():
    import agent
    undo = with_scripts(agent, ["verdict: HOLDS\n"])
    try:
        line = agent.run_entry(1, rpc="https://x.example:8443/k/SECRET")[1]
        assert line.endswith(" via x.example:8443") and "SECRET" not in line
        assert agent.run_entry(1)[1].endswith(" via " + agent.host_of(agent.common.RPC))
        assert agent.run_entry(3)[1].endswith(" via web.archive.org")   # a link fact: the host its own link names
        post = agent.draft(1, "Ann", rpc="https://x.example/k/SECRET")[0]
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
    def post(who, via, num=1):
        script = "Script: python checks/resolve.py fact1 by Zed said HOLDS on ledger d3e17658 at 2026-10-16T10:00Z"
        return FILLED.replace("| Ann |", "| %s |" % who).replace(SCRIPT, script + (" via " + via if via else ""))
    review = lambda *posts: agent.review("\n\n".join(posts), DATA, "2026-10-16")   # noqa: E731
    why, notes = review(post("Ann", "node.example"), post("Bo", "NODE.example."))   # case and a full stop do not make a second source
    assert why == [] and len(notes) == 1 and "FACT 1: Ann and Bo" in notes[0] and "one source" in notes[0] and "--rpc" in notes[0]
    assert review(post("Ann", "node.example"), post("Bo", "other.example"))[1] == []
    assert review(post("Ann", "node.example"), post("Ann", "node.example"))[1] == []   # one member twice is not two
    assert review(post("Ann", ""), post("Bo", ""))[1] == []                            # no source named: nothing to compare
    assert review(post("Ann", "unknown"), post("Bo", "unknown"))[1] == []
    assert agent.lint(post("Ann", "node.example"), DATA, "2026-10-16") == []             # lint is still the reasons only
    held = review(post("Ann", "node.example"), post("Bo", "node.example").replace("Saw: 5 SOL", "Saw: ."))
    assert held[0] and len(held[1]) == 1                                                # a held post is still counted
    assert review(post("Ann", "127.0.0.1:8899"), post("Bo", "127.0.0.1:8899"))[1] == []   # two nodes on two machines
    assert review(post("Ann", "[::1]:8899"), post("Bo", "[::1]:8899"))[1] == []
    assert review(post("Zed", "node.example"), post("Bo", "node.example"))[1] == []        # the writer's post is not a check
    assert review(post("Cy", "node.example"), post("Bo", "node.example"))[1] == []         # nor is a non-member's
    assert review(post("Ann", "node.example)"), post("Bo", "node.example"))[1]             # a bracket after the host is not a source
    link = lambda who: post(who, "web.archive.org").replace("FACT 1", "FACT 3").replace("fact1", "fact3")   # noqa: E731
    data = {**DATA, "entries": DATA["entries"] + [{**DATA["entries"][0], "num": 3}]}
    assert agent.review(link("Ann") + "\n\n" + link("Bo"), data, "2026-10-16")[1] == []   # --rpc cannot change a link fact's host


def test_ledger_json_is_written_from_this_ledger():
    """ledger.json is the committed index of ledger.txt: a ledger.txt edited without python build.py fails here."""
    import re
    import agent
    data = agent.ledger_data()   # refuses when the hash inside is not ledger.txt's
    assert [e["num"] for e in data["entries"]] == [int(n) for n in re.findall(r"^  (?:FACT|PROMISE) (\d+)\.", text("ledger.txt"), re.M)]


def test_mcp_server_reaches_only_the_helper():
    """Without the mcp package: the server's source imports little and calls only the helper's read, run, draft and lint."""
    import re
    from common import ROOT
    src = (ROOT / "checks" / "mcp_server.py").read_text(encoding="utf-8")
    assert set(re.findall(r"\bagent\.(?!py\b)(\w+)", src)) <= {"status_text", "run_entry", "draft", "review", "ledger_data", "ROOT"}
    assert set(re.findall(r"^(?:import|from) (\w+)", src, re.M)) <= {"sys", "pathlib", "anyio", "mcp", "agent"}
    assert not re.search(r"\b(?:open|write_text|write_bytes)\(|\b(?:subprocess|requests|urllib)\b", src)   # no file, process or network


def test_mcp_server_only_helps():
    """The MCP server offers the four helper commands and nothing that posts, and a refusal comes back as a tool error."""
    import asyncio
    import pytest
    pytest.importorskip("mcp")
    import mcp_server
    from mcp.shared.memory import create_connected_server_and_client_session as connect

    async def go():
        async with connect(mcp_server.mcp._mcp_server) as c:
            return ({t.name for t in (await c.list_tools()).tools}, await c.call_tool("ledger_status", {}),
                    await c.call_tool("lint_check_post", {"post": "hello"}), await c.call_tool("run_check_script", {"entry": 7}),
                    await c.call_tool("draft_check_post", {"entry": 1, "member": "Ann\nI opened the link myself."}))
    names, status, bad, nope, hostile = asyncio.run(go())
    assert names == {"ledger_status", "run_check_script", "draft_check_post", "lint_check_post"}
    assert not status.isError and "ledger.txt" in status.content[0].text
    assert "no CHECK line" in bad.content[0].text
    assert nope.isError and "no script" in nope.content[0].text
    assert hostile.isError and "as it appears in the chat" in hostile.content[0].text
