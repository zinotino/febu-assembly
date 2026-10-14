"""Draw assets/card.png, the 1200x630 picture a chat shows when someone pastes a link to the Assembly (build.py's
meta_tags names it). It repeats the front page's own sentence in the site's own look: navy bar, silver window, the
yellow note. Nothing on it changes with the ledger (no counts, no status), so it never goes stale.

    python make_card.py          needs Pillow and Windows' Consolas (any bold monospace TTF works: pass its path)
"""
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
FONT = sys.argv[1] if len(sys.argv) > 1 else "C:/Windows/Fonts/consolab.ttf"
W, H = 1200, 630
NAVY, INK, SILVER, SILVER_LT, NOTE = "#1f1a8c", "#111111", "#c0c0c0", "#d4d0c8", "#ffffe1"
LINES = ("A claim costs a link", "and a line that would", "prove it wrong.")
LAST = "A check costs a click."


def bevel(d, box, up=True, width=2):
    """The den's raised (or sunken) edge: light on two sides, dark on the other two."""
    x0, y0, x1, y1 = box
    lo, hi = ("#ffffff", "#404040") if up else ("#404040", "#ffffff")
    for k in range(width):
        d.line([(x0 + k, y0 + k), (x1 - k, y0 + k)], fill=lo)
        d.line([(x0 + k, y0 + k), (x0 + k, y1 - k)], fill=lo)
        d.line([(x0 + k, y1 - k), (x1 - k, y1 - k)], fill=hi)
        d.line([(x1 - k, y0 + k), (x1 - k, y1 - k)], fill=hi)


def main():
    img = Image.new("RGB", (W, H), "#00002b")
    d = ImageDraw.Draw(img)
    rnd = random.Random(14)                       # the same stars every time
    for _ in range(260):
        x, y = rnd.randrange(W), rnd.randrange(H)
        d.point((x, y), fill=rnd.choice(("#9fb0ff", "#ffffff", "#5a6bd8")))

    x0, y0, x1, y1 = 70, 60, 1130, 570            # the window, with its shadow
    d.rectangle((x0 + 12, y0 + 12, x1 + 12, y1 + 12), fill="#000014")
    d.rectangle((x0, y0, x1, y1), fill=SILVER_LT, outline="#000000", width=1)
    bevel(d, (x0 + 1, y0 + 1, x1 - 1, y1 - 1))

    bar_h = 58                                    # title bar: the site's navy to blue sweep
    for x in range(x0 + 5, x1 - 4):
        t = (x - x0) / (x1 - x0)
        d.line([(x, y0 + 5), (x, y0 + 5 + bar_h)], fill=(int(0 + 16 * t), int(0 + 132 * t), int(128 + 80 * t)))
    d.text((x0 + 22, y0 + 5 + bar_h / 2), "febu assembly", font=ImageFont.truetype(FONT, 32), fill="#ffffff", anchor="lm")
    bx = x1 - 5 - 46                              # a close box that does nothing, as on the site's windows
    d.rectangle((bx, y0 + 12, bx + 38, y0 + 5 + bar_h - 7), fill=SILVER)
    bevel(d, (bx, y0 + 12, bx + 38, y0 + 5 + bar_h - 7))
    d.text((bx + 19, y0 + 5 + bar_h / 2 - 2), "x", font=ImageFont.truetype(FONT, 26), fill="#000000", anchor="mm")

    big = ImageFont.truetype(FONT, 62)
    y = y0 + 5 + bar_h + 36
    for line in LINES:
        d.text((x0 + 56, y), line, font=big, fill=NAVY)
        y += 70
    d.text((x0 + 56, y + 14), LAST, font=big, fill=INK)

    ny0, ny1 = y1 - 92, y1 - 28                   # the yellow "note" strip
    d.rectangle((x0 + 56, ny0 + 4, x1 - 56 + 4, ny1 + 4), fill="#000000")
    d.rectangle((x0 + 56, ny0, x1 - 56, ny1), fill=NOTE, outline="#000000", width=2)
    d.text((x0 + 80, (ny0 + ny1) / 2), "A public ledger of claims about febu. Anyone can check.",
           font=ImageFont.truetype(FONT, 26), fill=INK, anchor="lm")

    out = ROOT / "assets" / "card.png"
    img.save(out, optimize=True)
    print("wrote %s (%d bytes)" % (out, out.stat().st_size))


if __name__ == "__main__":
    main()
