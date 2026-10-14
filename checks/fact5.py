"""Fact 5 from the scripture copy: how many pages each of its eight words is on, in pages 1-24 and in pages 25-164.

    python checks/fact5.py                 the copy behind fact 5's link
    python checks/fact5.py my-copy.json    a copy you saved yourself (KNOWN BUGS 3), in the same form

A page counts when a word on it starts with the word ("jester", "laughing"), not when the word only sits inside
another ("majesty", "slaughter"), as fact 5 says. Title, picture and text all count. Prints what it saw, for a
person to compare with the ledger and post; it posts nothing.
"""
import hashlib
import json
import re
import sys
import urllib.parse
import urllib.request

from common import entry, find, now

WORDS = ("jest", "hollow", "false", "mock", "laugh", "theater", "spectacle", "debt")   # fact 5's eight, in its order


def on_page(word, page):
    shown = "\n".join(page.get(k) or "" for k in ("title", "ascii_art", "body"))
    return re.search(r"\b" + word, shown, re.I) is not None


def main():
    link = find(r"LINK\s+(https://\S+)", entry(5), "fact 5's link")
    src = sys.argv[1] if len(sys.argv) > 1 else urllib.parse.urljoin(link, "assets/scripture.json")   # what the page loads
    if src.startswith("https://"):
        raw = urllib.request.urlopen(urllib.request.Request(src, headers={"User-Agent": "curl/8"}), timeout=60).read()
    else:
        raw = open(src, "rb").read()
    pages = json.loads(raw)
    nums = sorted(p["page_number"] for p in pages)
    early = [p for p in pages if p["page_number"] <= 24]
    late = [p for p in pages if 25 <= p["page_number"] <= 164]

    print("Fact 5, read %s from %s" % (now(), src))
    print("The copy: SHA-256 %s, %d pages, numbered %s" % (hashlib.sha256(raw).hexdigest(), len(pages),
          "1 to %d" % len(nums) if nums == list(range(1, len(nums) + 1)) else nums))
    print()
    print("  word        on pages 1-24   on pages 25-164")
    for w in WORDS:
        print("  %-10s  %13d   %15d" % (w, sum(on_page(w, p) for p in early), sum(on_page(w, p) for p in late)))
    hits = ["%s on page %d" % (w, p["page_number"]) for w in WORDS for p in early if on_page(w, p)]
    print()
    print("In pages 1-24: %s" % ("; ".join(hits) if hits else "none of the eight words"))


if __name__ == "__main__":
    main()
