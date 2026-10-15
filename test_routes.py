"""Check vercel.json's routes the way Vercel reads them: first match wins, `continue` keeps going,
`handle: filesystem` serves a real file, `has`/`missing` test the host. Run: python test_routes.py"""
import json, os, re, subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(ROOT, "vercel.json"), encoding="utf-8"))
FILES = set(subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).split("\n")) - {""}
LEDGER, DEN = "febu-ledger.vercel.app", "febu-assembly.vercel.app"


def is_file(path):
    p = path.lstrip("/")
    return p in FILES or (p == "" and "index.html" in FILES)


def conds_ok(route, host):
    for c in route.get("has", []):
        if not re.fullmatch(c["value"], host):
            return False
    for c in route.get("missing", []):
        if re.fullmatch(c["value"], host):
            return False
    return True


def serve(host, path):
    """-> ('file', path) | ('rewrite', dest) | ('redirect', status, location) | ('404',), plus the headers set on the way."""
    headers, cur = {}, path
    for r in CFG["routes"]:
        if r.get("handle") == "filesystem":
            if is_file(cur):
                return ("file", "/index.html" if cur == "/" else cur), headers
            continue
        m = re.fullmatch(r["src"], cur)
        if not m or not conds_ok(r, host):
            continue
        if "headers" in r:
            headers.update(r["headers"])
        if "status" in r:
            loc = re.sub(r"\$(\d)", lambda g: m.group(int(g.group(1))), r["headers"]["Location"])
            return ("redirect", r["status"], loc), headers
        if "dest" in r:
            return ("rewrite", r["dest"]), headers
        # continue: true with only headers: keep matching
    return ("404",), headers


def csp(host, path):
    """The Assembly's own policy (no inline anything), not the den's."""
    h = serve(host, path)[1].get("Content-Security-Policy", "")
    return bool(h) and "unsafe-inline" not in h


def den_csp(host, path):
    """The policy every other path gets: no inline or injected script, no javascript: links, connections to ourselves
    and the one Supabase project only. It is what keeps the den's scripts away from a member's token."""
    h = serve(host, path)[1].get("Content-Security-Policy", "")
    return ("script-src 'self';" in h
            and "unsafe-inline" in h.split("style-src")[1].split(";")[0]
            and "connect-src 'self' https://tytebptpuiiemuxlaeab.supabase.co" in h)


def test():
    # the den: root, its files and its app routes get the den's CSP (scripts from ourselves only), and unknown paths reach the app
    for p in ["/", "/index.html", "/scripture.html", "/favicon.ico", "/assets/shim.js",
              "/assets/index-C4UKkDq2.js", "/assets/community.json", "/library/scripture"]:
        assert not csp(DEN, p) and den_csp(DEN, p), p
    assert serve(DEN, "/")[0] == ("file", "/index.html")
    assert serve(DEN, "/library/scripture")[0] == ("rewrite", "/index.html")
    assert serve(DEN, "/scripture.html")[0] == ("file", "/scripture.html")
    # the den's policy has no inline script: a den page that still carries one renders as an empty shell
    for f in ("index.html", "scripture.html"):
        src = open(os.path.join(ROOT, f), encoding="utf-8").read()
        assert not re.search(r"<script(?![^>]*src=)[^>]*>", src), f + " has an inline script"

    # every page and text file the Assembly serves keeps its CSP
    pages = [f for f in FILES if re.fullmatch(r"[a-z0-9-]+\.(html|txt|ics)", f)
             and f not in {"index.html", "scripture.html"}]
    assert {"febu-assembly.html", "process.html", "tests.html", "ledger.txt", "how.txt", "assembly.ics"} <= set(pages), pages
    for p in pages:
        assert csp(DEN, "/" + p), p
        assert serve(DEN, "/" + p)[0] == ("file", "/" + p), p
    for p in ["/assets/claims.js", "/assets/how-it-connects.svg", "/archive/x.txt", "/api/claim"]:
        assert csp(DEN, p), p
    assert not csp(DEN, "/api/keepalive") and den_csp(DEN, "/api/keepalive")
    assert serve(DEN, "/api/entries/3/check")[0] == ("rewrite", "/api/entries?num=$1&act=$2")   # the live record's pretty URLs
    assert csp(DEN, "/api/entries/3/second")
    assert CFG["functions"]["api/entries.js"]["includeFiles"] == "ledger.txt"
    assert serve(DEN, "/z")[0] == ("rewrite", "/index.html")                                     # no findings page
    assert serve(DEN, "/findings.html")[0] == ("rewrite", "/index.html")
    assert serve(DEN, "/start")[0] == ("redirect", 308, "/febu-assembly.html#check")

    # the old domain serves nothing: every path is a 308 to the same path on the one address
    ONE = "https://" + DEN
    assert serve(LEDGER, "/")[0] == ("redirect", 308, ONE + "/febu-assembly.html")
    for p in pages + ["api/claim", "api/entries", "archive/08_CLAIMS_LEDGER_v3.txt", "assets/claims.js", "nope"]:
        assert serve(LEDGER, "/" + p)[0] == ("redirect", 308, ONE + "/" + p), p
    assert not any("febu-ledger" in str(x) for x in serve(DEN, "/")[0])

    assert [c["path"] for c in CFG["crons"]] == ["/api/archive", "/api/claim?name=Zurandol", "/api/keepalive"]
    assert CFG["buildCommand"] == "python3 build.py" and CFG["outputDirectory"] == "."
    print("routes ok:", len(pages), "assembly files, den paths, old domain redirects everything")


if __name__ == "__main__":
    test()
