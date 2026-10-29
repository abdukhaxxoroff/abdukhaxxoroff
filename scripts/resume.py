"""Render the animated resume card (impact counters, career timeline, shipped apps) as resume_dark.svg / resume_light.svg.

    python scripts/resume.py

Everything shown comes from the lists below; edit them when the resume changes.
"""
from html import escape
from pathlib import Path

from build import CHAR_W, LOGIN, PAD, PANEL_CHARS, PANEL_X, THEMES

ROOT = Path(__file__).resolve().parent.parent

# (final label, label under it, function giving the label at progress 0..1)
IMPACT = [
    ("2M+", "users reached", lambda p: f"{2 * p:.1f}M"),
    ("15+", "apps shipped", lambda p: f"{round(15 * p)}"),
    ("1,000+", "drivers on LX1", lambda p: f"{round(1000 * p):,}"),
    ("+38%", "client revenue", lambda p: f"+{round(38 * p)}%"),
    ("-30%", "dispatcher workload", lambda p: f"-{round(30 * p)}%"),
]
# (dates, company, highlights), oldest first. The entry marked current gets a pulsing node.
JOBS = [
    ("May 2023 - Dec 2023", "RealSoft", ["Government service apps", "Face ID authentication", "Click & PayMe payments"]),
    ("Mar 2024 - Apr 2025", "SectorSoft", ["CRM for 1,500+ branches", "Sales $625K -> $860K", "LMS CRM for 5,000+ users"]),
    ("Feb 2025 - now", "LogistixOne", ["Logistics SaaS, 1,000+ drivers", "Live location, SSE + FCM", "AI dispatcher calls"]),
    ("Jul 2025 - Oct 2025", "Daryo.uz", ["News app, 2M+ users", "50% fewer backend calls", "CI/CD release pipelines"]),
]
CURRENT = "LogistixOne"
APPS = [
    "LX1 Driver · Logistics", "Daryo.uz · News", "ONUR Group · B2B CRM", "ONUR Agent · Sales CRM",
    "Fitrat · Education CRM", "Bozor App · Marketplace", "Bolalar Bog'chasi · Gov/Edu", "Ahrorjon Qori · Quran & Duas",
]
STACK = "Flutter · Dart · Kotlin · Swift · SSE/WebSocket · Firebase · Clean Architecture · CI/CD"

CYCLE = 12.0  # seconds; content plays once, holds, then fades out before looping
SMALL = 14
SMALL_W = CHAR_W * SMALL / 16
WIDTH = PANEL_X + int(PANEL_CHARS * CHAR_W) + PAD  # same width as the profile card


def kt(t):
    return f"{t / CYCLE:.4f}"


def fade_in(t, length=0.3):
    """Hidden until t seconds into the loop, then fades in and stays."""
    return (f'<animate attributeName="opacity" values="0;0;1;1" keyTimes="0;{kt(t)};{kt(t + length)};1" '
            f'dur="{CYCLE}s" repeatCount="indefinite"/>')


def visible_between(start, end=None):
    if end is None:
        return (f'<animate attributeName="opacity" values="0;1" keyTimes="0;{kt(start)}" calcMode="discrete" '
                f'dur="{CYCLE}s" repeatCount="indefinite"/>')
    return (f'<animate attributeName="opacity" values="0;1;0" keyTimes="0;{kt(start)};{kt(end)}" calcMode="discrete" '
            f'dur="{CYCLE}s" repeatCount="indefinite"/>')


def typed(uid, x, y, text, start, end, font_size=16, cls=None, cursor=None):
    """Reveal text one character at a time by growing a clip rectangle."""
    n = len(text)
    char_w = CHAR_W * font_size / 16
    widths = ";".join(["0"] + [f"{k * char_w:.1f}" for k in range(n + 1)])
    times = ";".join(["0"] + [kt(start + (end - start) * k / n) for k in range(n + 1)])
    cls_attr = f' class="{cls}"' if cls else ""
    out = f"""<clipPath id="{uid}"><rect x="{x}" y="{y - 20}" height="28" width="0">
  <animate attributeName="width" values="{widths}" keyTimes="{times}" calcMode="discrete" dur="{CYCLE}s" repeatCount="indefinite"/>
</rect></clipPath>
<text x="{x}" y="{y}" font-size="{font_size}px"{cls_attr} clip-path="url(#{uid})">{escape(text)}</text>"""
    if cursor:
        xs = ";".join([f"{x:.1f}"] + [f"{x + k * char_w:.1f}" for k in range(n + 1)])
        out += f"""
<g>
  <animate attributeName="opacity" values="1;0" keyTimes="0;0.5" calcMode="discrete" dur="1s" repeatCount="indefinite"/>
  <rect y="{y - 14}" width="{char_w:.1f}" height="18" fill="{cursor}" x="{x}">
    <animate attributeName="x" values="{xs}" keyTimes="{times}" calcMode="discrete" dur="{CYCLE}s" repeatCount="indefinite"/>
  </rect>
</g>"""
    return out


def section(y, title):
    rule = "─" * int((WIDTH - 2 * PAD) / CHAR_W - len(title) - 3)
    return f'<text x="{PAD}" y="{y}">─ {escape(title)} <tspan class="dim">{rule}</tspan></text>'


def impact(top, theme):
    gap = 16
    tile_w = (WIDTH - 2 * PAD - gap * (len(IMPACT) - 1)) / len(IMPACT)
    steps = 24
    out = []
    for i, (final, label, at) in enumerate(IMPACT):
        x = PAD + i * (tile_w + gap)
        start = 1.4 + i * 0.12
        duration = 1.4
        out.append(f'<g opacity="0">{fade_in(start - 0.2)}'
                   f'<rect x="{x:.1f}" y="{top}" width="{tile_w:.1f}" height="96" fill="none" stroke="{theme["dim"]}" stroke-opacity="0.5"/>'
                   f'<text x="{x + 16:.1f}" y="{top + 78}" font-size="{SMALL}px" class="dim">{escape(label)}</text></g>')
        # One text per step, each shown only during its slice of the count-up; ease-out so it settles gently.
        for k in range(steps + 1):
            progress = 1 - (1 - k / steps) ** 3
            value = final if k == steps else at(progress)
            t0 = start + duration * k / steps
            t1 = None if k == steps else start + duration * (k + 1) / steps
            out.append(f'<text x="{x + 16:.1f}" y="{top + 50}" font-size="34px" font-weight="bold" class="value" opacity="0">'
                       f'{visible_between(t0, t1)}{escape(value)}</text>')
    return "\n".join(out)


def timeline(top, theme):
    col_w = (WIDTH - 2 * PAD) / len(JOBS)
    x0, x1 = PAD + col_w / 2, WIDTH - PAD - col_w / 2
    line_y = top + 40
    start, end = 3.2, 5.4
    length = x1 - x0
    out = [f'<line x1="{x0:.1f}" y1="{line_y}" x2="{x1:.1f}" y2="{line_y}" stroke="{theme["dim"]}" stroke-width="2" '
           f'stroke-dasharray="{length:.1f}" stroke-dashoffset="{length:.1f}">'
           f'<animate attributeName="stroke-dashoffset" values="{length:.1f};{length:.1f};0;0" '
           f'keyTimes="0;{kt(start)};{kt(end)};1" dur="{CYCLE}s" repeatCount="indefinite"/></line>']
    for i, (dates, company, highlights) in enumerate(JOBS):
        cx = x0 + i * length / (len(JOBS) - 1)
        reached = start + (end - start) * i / (len(JOBS) - 1)
        color = theme["status"] if company == CURRENT else theme["key"]
        pulse = ""
        if company == CURRENT:
            pulse = (f'<circle cx="{cx:.1f}" cy="{line_y}" r="7" fill="none" stroke="{color}" stroke-width="2">'
                     f'<animate attributeName="r" values="7;16" dur="1.5s" repeatCount="indefinite"/>'
                     f'<animate attributeName="stroke-opacity" values="0.8;0" dur="1.5s" repeatCount="indefinite"/></circle>')
        lines = "".join(
            f'<text x="{cx:.1f}" y="{line_y + 70 + j * 22}" font-size="{SMALL}px">{escape(h)}</text>'
            for j, h in enumerate(highlights)
        )
        out.append(f"""<g opacity="0" text-anchor="middle">{fade_in(reached)}
  <text x="{cx:.1f}" y="{line_y - 18}" font-size="{SMALL}px" class="dim">{escape(dates)}</text>
  {pulse}<circle cx="{cx:.1f}" cy="{line_y}" r="7" fill="{color}"/>
  <text x="{cx:.1f}" y="{line_y + 40}" font-weight="bold" fill="{color}">{escape(company)}</text>
  {lines}
</g>""")
    return "\n".join(out)


def apps(top):
    out = []
    x, y = PAD, top
    for i, name in enumerate(APPS):
        label = f"[ {name} ]"
        width = len(label) * SMALL_W
        if x + width > WIDTH - PAD:
            x, y = PAD, y + 30
        out.append(f'<text x="{x:.1f}" y="{y}" font-size="{SMALL}px" opacity="0">{fade_in(5.6 + i * 0.18, 0.2)}'
                   f'<tspan class="dim">[ </tspan><tspan class="value">{escape(name)}</tspan><tspan class="dim"> ]</tspan></text>')
        x += width + 14
    return "\n".join(out), y


def render(theme_name):
    theme = THEMES[theme_name]
    y = PAD + 20
    parts = [typed("cmd", PAD, y, f"{LOGIN}@github ~ $ cat resume.log", 0.2, 1.3, cursor=theme["text"])]

    y += 46
    parts.append(f'<g opacity="0">{fade_in(1.2)}{section(y, "Impact")}</g>')
    parts.append(impact(y + 22, theme))

    y += 22 + 96 + 46
    parts.append(f'<g opacity="0">{fade_in(3.0)}{section(y, "Experience")}</g>')
    parts.append(timeline(y + 14, theme))

    y += 14 + 40 + 70 + 44 + 46
    parts.append(f'<g opacity="0">{fade_in(5.4)}{section(y, "Shipped apps")}</g>')
    app_svg, last = apps(y + 34)
    parts.append(app_svg)

    y = last + 46
    parts.append(f'<g opacity="0">{fade_in(7.0)}{section(y, "Stack")}</g>')
    y += 32
    parts.append(typed("stack", PAD, y, STACK, 7.2, 8.6, SMALL + 1, cls="value"))

    height = y + PAD
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}" data-cycle="{int(CYCLE * 1000)}"
     font-family="'DejaVu Sans Mono', Menlo, Consolas, monospace" font-size="16px">
<style>
text, tspan {{ white-space: pre; }}
.key {{ fill: {theme["key"]}; }}
.value {{ fill: {theme["value"]}; }}
.dim {{ fill: {theme["dim"]}; }}
</style>
<rect width="{WIDTH}" height="{height}" fill="{theme["bg"]}"/>
<g fill="{theme["text"]}">
  <animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.94;0.98;1" dur="{CYCLE}s" repeatCount="indefinite"/>
{chr(10).join(parts)}
</g>
</svg>
"""


def main():
    for name in THEMES:
        path = ROOT / f"resume_{name}.svg"
        path.write_text(render(name), encoding="utf-8")
        print(f"Saved {path}")


if __name__ == "__main__":
    main()
