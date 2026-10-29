"""Record one loop of each SVG's animation in Chrome and save it as an animated WebP."""
import io
import re
import sys
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
SVGS = [ROOT / name for name in ("dark_mode.svg", "light_mode.svg", "resume_dark.svg", "resume_light.svg")]
FRAME_MS = 50


def attrs(svg):
    """Width, height and loop length (data-cycle, in ms) from the root <svg> tag."""
    head = svg.read_text(encoding="utf-8")[:600]

    def number(name):
        return int(re.search(rf'{name}="(\d+)"', head)[1])

    return number("width"), number("height"), number("data-cycle")


def main():
    channel = sys.argv[1] if len(sys.argv) > 1 else "chrome"  # the GitHub runner and most Macs already have Chrome
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=channel)
        for svg in SVGS:
            width, height, cycle_ms = attrs(svg)
            page = browser.new_page(viewport={"width": width, "height": height})
            page.goto(svg.as_uri(), wait_until="networkidle")
            page.evaluate("document.documentElement.pauseAnimations()")

            frames = []
            for i in range(cycle_ms // FRAME_MS):
                page.evaluate(
                    """async (t) => {
                        document.documentElement.setCurrentTime(t);
                        await new Promise(requestAnimationFrame);
                    }""",
                    i * FRAME_MS / 1000,
                )
                frames.append(Image.open(io.BytesIO(page.screenshot())))

            out = svg.with_suffix(".webp")
            # Lossless keeps the text crisp; minimize_size + a long keyframe interval lets the encoder
            # store only the few pixels that change between frames (eyes, status dot, cursor).
            frames[0].save(out, save_all=True, append_images=frames[1:], duration=FRAME_MS, loop=0,
                           lossless=True, minimize_size=True, kmax=200, method=6)
            print(f"Saved {out} ({out.stat().st_size // 1024} KB)")
            page.close()
        browser.close()


if __name__ == "__main__":
    main()
