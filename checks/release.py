"""Is the file the site serves the file the post names? Anyone can run this; it needs no key and posts nothing.

    python checks/release.py                          the live site against this repo
    python checks/release.py --posted d3e17658        also: does the hash in a post match what is served?
    python checks/release.py --site http://127.0.0.1:8000 --no-archive
    python checks/release.py --test                   offline checks of the pure parts

What it compares, and what each answer means:
  served bytes   ledger.txt fetched as is and fetched with gzip: the same SHA-256 once decoded. A proxy or an edge
                 that rewrote the file would show here.
  the repo       the same SHA-256 as ledger.txt in this checkout and in git HEAD (when git is there).
  the page       the hash ledger.html prints for ledger.txt is the one the file has.
  the post       the hash a post gave (--posted, 8 or more hex digits) is the served file, or else which archived
                 version it is: a post can be true of an earlier version and stale for this one.
  headers        what the file is served as (type, charset, nosniff, content-security-policy).
  the archive    the Internet Archive's captures of ledger.txt: does one have the served file's content?
  OpenTimestamps timestamps/*.ots: a proof that is only PENDING is a calendar's promise, not yet a Bitcoin block;
                 and whether the served file has a proof at all.
An incomplete read is never OK: it says CAN'T TELL, and the line says what to open by hand.
"""
import argparse
import gzip
import hashlib
import http.client
import json
import re
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://febu-assembly.vercel.app"
OTS_MAGIC = b"\x00OpenTimestamps\x00\x00Proof\x00\xbf\x89\xe2\xe8\x84\xe8\x92\x94"
OTS_BITCOIN = bytes.fromhex("0588960d73d71901")
OTS_PENDING = bytes.fromhex("83dfe30d2ef90c8e")
OK, WARN, FAIL, CANT = "OK", "WARN", "FAIL", "CAN'T TELL"


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def capture_with(caps, site, served, get=None):
    """The timestamp of the newest Internet Archive capture whose content is the served file, or None. The index's own
    'digest' is a SHA-1 over the bytes the Archive stored, which is the gzip copy the site sent, so it never equals the
    plain file's: compare content instead, from each capture's id_ copy (the file as saved), unpacked."""
    get = get or fetch
    for ts, _digest, _status in reversed(caps):
        status, _, copy = get("https://web.archive.org/web/%sid_/%s/ledger.txt" % (ts, site), gz=True)
        if status == 200 and copy[:2] == b"\x1f\x8b":     # still packed: the header did not say so
            try:
                copy = gzip.decompress(copy)
            except OSError:
                continue
        if status == 200 and sha256(copy) == served:
            return ts
    return None


def parse_ots(raw):
    """(sha256 of the stamped file as hex or None, anchored in a Bitcoin block, only pending)."""
    digest = None
    n = len(OTS_MAGIC)
    if raw.startswith(OTS_MAGIC) and raw[n:n + 2] == b"\x01\x08" and len(raw) >= n + 34:
        digest = raw[n + 2:n + 34].hex()
    anchored = OTS_BITCOIN in raw
    return digest, anchored, (OTS_PENDING in raw and not anchored)


def printed_hash(html, path):
    """The SHA-256 ledger.html prints beside a file's name (build.py: data-sha-of)."""
    m = re.search(r'data-sha-of="%s"[^>]*>([0-9a-f]{64})<' % re.escape(path), html)
    return m.group(1) if m else None


def fetch(url, gz=False):
    req = urllib.request.Request(url, headers={"User-Agent": "curl/8", "Accept-Encoding": "gzip" if gz else "identity"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            status, headers, body = r.status, r.headers, r.read()
    except urllib.error.HTTPError as err:
        status, headers, body = err.code, err.headers, err.read()
    except (OSError, http.client.HTTPException) as err:
        return None, {}, repr(err).encode()
    if headers.get("Content-Encoding", "").lower() == "gzip":
        body = gzip.decompress(body)
    return status, headers, body


def archive_hashes():
    return {sha256(p.read_bytes()): "archive/" + p.name for p in sorted((ROOT / "archive").glob("*.txt"))}


def check_ots(served_sha):
    """One line per proof, then whether the served file is stamped."""
    rows, stamped = [], set()
    for p in sorted((ROOT / "timestamps").glob("*.ots")):
        digest, anchored, pending = parse_ots(p.read_bytes())
        if digest:
            stamped.add(digest)
        state = "anchored in a Bitcoin block" if anchored else "PENDING (a calendar's promise, not yet a block)" if pending else "unreadable"
        rows.append((OK if anchored else WARN, "%s: %s" % (p.name, state)))
    if served_sha:
        rows.append((OK, "the served file has a proof") if served_sha in stamped else
                    (WARN, "the served file (%s) has no proof in timestamps/" % served_sha[:8]))
    return rows


def run(site, posted, archive=True):
    out = []
    add = lambda status, what: out.append((status, what))
    local_raw = (ROOT / "ledger.txt").read_bytes()
    local = sha256(local_raw)
    add(OK if b"\r" not in local_raw else FAIL, "ledger.txt in this checkout: %s, %d bytes, %s" % (
        local, len(local_raw), "LF only" if b"\r" not in local_raw else "has CR: the hash depends on the checkout"))
    try:
        head = subprocess.run(["git", "show", "HEAD:ledger.txt"], cwd=str(ROOT), capture_output=True, check=True).stdout
        add(OK if sha256(head) == local else FAIL, "git HEAD's ledger.txt is %s the working file" % (
            "the same as" if sha256(head) == local else "NOT"))
    except (OSError, subprocess.CalledProcessError):
        add(CANT, "git HEAD not readable here; run git show HEAD:ledger.txt | sha256sum")

    status, headers, body = fetch(site + "/ledger.txt")
    served = None
    if status != 200:
        add(CANT, "%s/ledger.txt answered %s (%s); open it by hand and run sha256sum" % (site, status, body[:80]))
    else:
        served = sha256(body)
        add(OK if served == local else FAIL, "served ledger.txt: %s, %d bytes, %s this checkout" % (
            served, len(body), "the same as" if served == local else "NOT the same as"))
        gstatus, gheaders, gbody = fetch(site + "/ledger.txt", gz=True)
        if gstatus == 200:
            add(OK if sha256(gbody) == served else FAIL, "decoded gzip copy %s the plain copy (Content-Encoding: %s)" % (
                "equals" if sha256(gbody) == served else "DIFFERS from", gheaders.get("Content-Encoding", "none")))
        ctype = headers.get("Content-Type", "")
        add(OK if "charset" in ctype.lower() else WARN, "Content-Type: %s%s" % (ctype or "(none)", "" if "charset" in ctype.lower() else " (no charset: a browser guesses)"))
        add(OK if headers.get("X-Content-Type-Options", "").lower() == "nosniff" else WARN, "X-Content-Type-Options: %s" % headers.get("X-Content-Type-Options", "(none)"))
        add(OK if headers.get("Content-Security-Policy") else WARN, "Content-Security-Policy: %s" % ("set" if headers.get("Content-Security-Policy") else "(none)"))

    hstatus, _, html = fetch(site + "/ledger.html")
    if hstatus == 200 and served:
        said = printed_hash(html.decode("utf-8", "replace"), "ledger.txt")
        add(OK if said == served else FAIL if said else CANT, "ledger.html prints %s for ledger.txt" % (said or "no hash"))
    elif served:
        add(CANT, "ledger.html answered %s; read the hash it prints and compare" % hstatus)

    if posted:
        p = posted.lower().strip()
        if not re.fullmatch(r"[0-9a-f]{8,64}", p):
            add(FAIL, "--posted needs 8 to 64 hex digits")
        elif served and served.startswith(p):
            add(OK, "the posted hash %s is the served file" % p)
        else:
            was = next((name for h, name in archive_hashes().items() if h.startswith(p)), None)
            add(FAIL if served else CANT, "the posted hash %s is %s%s" % (
                p, "not the served file" if served else "not compared (nothing served was read)",
                "; it is %s: the post is true of an earlier version" % was if was else "; it matches no archived version"))

    cstatus, cdx = None, b""
    if archive:
        cstatus, _, cdx = fetch("https://web.archive.org/cdx/search/cdx?url=%s/ledger.txt&output=json&fl=timestamp,digest,statuscode&limit=-5"
                                % site.split("://", 1)[-1])
    if cstatus == 200 and served:
        try:
            caps = json.loads(cdx)[1:]
        except ValueError:
            caps = None
        if caps is None:
            add(CANT, "the Internet Archive's index answered something that is not JSON")
        elif not caps:
            add(WARN, "the Internet Archive has no capture of %s/ledger.txt" % site)
        else:
            have = capture_with(caps, site, served)
            add(OK if have else WARN, "the Internet Archive's last %d captures %s the served file (newest %s%s)" % (
                len(caps), "include" if have else "do not include", caps[-1][0], "; %s has it" % have if have else ""))
    else:
        add(CANT, "the Internet Archive's index not read; open https://web.archive.org/web/*/%s/ledger.txt" % site.split("://", 1)[-1])

    out.extend(check_ots(served or local))
    return out


def main(argv):
    if "--test" in argv:
        import test_checks
        for name in sorted(n for n in dir(test_checks) if n.startswith("test_release") or n.startswith("test_ots")):
            getattr(test_checks, name)()
            print("ok", name)
        return 0
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--site", default=SITE)
    ap.add_argument("--posted", default="")
    ap.add_argument("--no-archive", action="store_true", help="skip the Internet Archive lookup")
    args = ap.parse_args(argv)
    rows = run(args.site.rstrip("/"), args.posted, archive=not args.no_archive)
    for status, what in rows:
        print("%-10s %s" % (status, what))
    bad = [w for s, w in rows if s == FAIL]
    print("\n%d line(s) FAIL, %d WARN, %d CAN'T TELL" % (len(bad), sum(s == WARN for s, _ in rows), sum(s == CANT for s, _ in rows)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
