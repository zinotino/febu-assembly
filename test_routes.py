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
            return ("redirect", r["status"], r["headers"]["Location"]), headers
        if "dest" in r:
            return ("rewrite", r["dest"]), headers
        # continue: true with only headers: keep matching
    return ("404",), headers


def csp(host, path):
    return "Content-Security-Policy" in serve(host, path)[1]


def test():
    # the den: root, its files and its app routes get no Assembly CSP, and unknown paths reach the app
    for p in ["/", "/index.html", "/scripture.html", "/favicon.ico", "/assets/shim.js",
              "/assets/index-C4UKkDq2.js", "/assets/community.json", "/library/scripture"]:
        assert not csp(DEN, p), p
    assert serve(DEN, "/")[0] == ("file", "/index.html")
    assert serve(DEN, "/library/scripture")[0] == ("rewrite", "/index.html")
    assert serve(DEN, "/scripture.html")[0] == ("file", "/scripture.html")

    # every page and text file the Assembly serves keeps its CSP on both domains
    pages = [f for f in FILES if re.fullmatch(r"[a-z0-9-]+\.(html|txt|ics)", f)
             and f not in {"index.html", "scripture.html"}]
    assert {"febu-assembly.html", "process.html", "tests.html", "ledger.txt", "how.txt", "assembly.ics"} <= set(pages), pages
    for host in (DEN, LEDGER):
        for p in pages:
            assert csp(host, "/" + p), (host, p)
            assert serve(host, "/" + p)[0] == ("file", "/" + p), (host, p)
        for p in ["/assets/claims.js", "/assets/how-it-connects.svg", "/archive/x.txt", "/api/claim"]:
            assert csp(host, p), (host, p)
    assert not csp(DEN, "/api/keepalive")
    for host in (DEN, LEDGER):                      # the live record: its pretty URLs reach the function, with the headers
        assert serve(host, "/api/entries/3/check")[0] == ("rewrite", "/api/entries?num=$1&act=$2"), host
        assert csp(host, "/api/entries/3/second"), host
    assert CFG["functions"]["api/entries.js"]["includeFiles"] == "ledger.txt"

    # the old domain keeps its behaviour
    assert serve(LEDGER, "/")[0] == ("rewrite", "/febu-assembly.html")
    assert serve(LEDGER, "/nope")[0] == ("404",)
    assert serve(LEDGER, "/z")[0] == ("404",) and serve(DEN, "/z")[0] == ("rewrite", "/index.html")   # no findings page
    assert serve(LEDGER, "/findings.html")[0] == ("404",) and serve(DEN, "/findings.html")[0] == ("rewrite", "/index.html")
    for h in (DEN, LEDGER):
        assert serve(h, "/start")[0] == ("redirect", 308, "/febu-assembly.html#check")

    assert [c["path"] for c in CFG["crons"]] == ["/api/archive", "/api/claim?name=Zurandol", "/api/keepalive"]
    assert CFG["buildCommand"] == "python3 build.py" and CFG["outputDirectory"] == "."
    print("routes ok:", len(pages), "assembly files x 2 hosts, den paths, old-domain behaviour")


if __name__ == "__main__":
    test()
