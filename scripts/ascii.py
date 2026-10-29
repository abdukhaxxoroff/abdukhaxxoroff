"""Turn a picture into the ASCII portrait used on the profile card.

    python scripts/ascii.py                      # your GitHub avatar
    python scripts/ascii.py photo.jpg --invert   # a photo with a dark subject on a light background

Writes assets/portrait.txt. After regenerating, check the EYES position in build.py.
"""
import argparse
import io
from pathlib import Path

import requests
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
RAMP = " ░▒▓█"
# Monospace glyphs at 16px are ~9.6px wide on a 20px line, so a cell is about twice as tall as wide.
CELL_ASPECT = 20 / 9.6


def load(source):
    if source:
        return Image.open(source)
    data = requests.get("https://github.com/abdukhaxxoroff.png?size=400", timeout=30).content
    return Image.open(io.BytesIO(data))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("image", nargs="?", help="image path (defaults to the GitHub avatar)")
    parser.add_argument("--cols", type=int, default=54)
    parser.add_argument("--crop", type=int, nargs=4, metavar=("L", "T", "R", "B"), default=(70, 45, 330, 375),
                        help="crop box in pixels of a 400x400 image")
    parser.add_argument("--invert", action="store_true", help="make dark areas dense instead of light ones")
    args = parser.parse_args()

    image = ImageOps.exif_transpose(load(args.image)).convert("L").resize((400, 400))
    image = image.crop(args.crop)
    if args.invert:
        image = ImageOps.invert(image)
    rows = round(args.cols * image.height / image.width / CELL_ASPECT)
    image = image.resize((args.cols, rows), Image.Resampling.BOX)

    lines = []
    for y in range(rows):
        line = "".join(RAMP[min(image.getpixel((x, y)) * len(RAMP) // 256, len(RAMP) - 1)] for x in range(args.cols))
        lines.append(line.rstrip())
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()

    out = ROOT / "assets" / "portrait.txt"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nSaved {out} ({len(lines)} rows)")


if __name__ == "__main__":
    main()
