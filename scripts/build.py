"""Fetch GitHub stats and render the neofetch-style profile card as dark_mode.svg and light_mode.svg.

Needs a GitHub token in GH_TOKEN (the workflow passes ACCESS_TOKEN or the built-in GITHUB_TOKEN).
Locally:  GH_TOKEN=$(gh auth token) python scripts/build.py
"""
import os
from datetime import datetime, timezone
from html import escape
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
LOGIN = "abdukhaxxoroff"

# Edit these rows to change what the card says. "{uptime}" and the stats keys are filled in from the API.
INFO = [
    ("Name", "Abduazim Abduqahhorov"),
    ("Uptime", "{uptime}"),
    ("Host", "Tashkent, Uzbekistan"),
    ("Kernel", "Flutter Developer"),
    ("Company", "Omnitech"),
    ("Languages.Programming", "Dart, Kotlin, Python"),
    ("Frameworks", "Flutter"),
    ("Platforms", "Android, iOS"),
    ("Focus", "Mobile apps, clean UI"),
]
CONTACT = [
    ("Timezone", "UZT (UTC+5)", None),
    ("GitHub", "github.com/abdukhaxxoroff", "https://github.com/abdukhaxxoroff"),
]
QUOTE = "// Talk is cheap. Show me the code."

# Where the eyes sit inside the hood in assets/portrait.txt: (row, left column, right column), 0-based.
EYES = (11, 21, 32)
EYE_WIDTH = 3

THEMES = {
    "dark": {
        "bg": "#161b22", "text": "#c9d1d9", "key": "#ffa657", "value": "#a5d6ff",
        "dim": "#616e7f", "eye": "#3fb950", "status": "#3fb950",
    },
    "light": {
        "bg": "#f6f8fa", "text": "#24292f", "key": "#953800", "value": "#0a3069",
        "dim": "#8c959f", "eye": "#1a7f37", "status": "#1a7f37",
    },
}

FONT = 16
CHAR_W = 9.63  # DejaVu Sans Mono / Menlo advance at 16px
LINE_H = 20  # portrait line height
ROW_H = 28  # info panel row height
PAD = 30
PANEL_X = 600
PANEL_CHARS = 58
CYCLE = "6s"  # blink loop; every other animation divides it so the WebP loops seamlessly


def graphql(query, variables):
    token = os.environ["GH_TOKEN"]
    response = requests.post(
        "https://api.github.com/graphql",
        json={"query": query, "variables": variables},
        headers={"Authorization": f"bearer {token}"},
        timeout=60,
    )
    response.raise_for_status()
    body = response.json()
    if "errors" in body:
        raise RuntimeError(body["errors"])
    return body["data"]


def fetch_stats():
    user = graphql(
        """query($login: String!) {
          user(login: $login) {
            createdAt
            followers { totalCount }
            repositoriesContributedTo(contributionTypes: [COMMIT, PULL_REQUEST, REPOSITORY]) { totalCount }
          }
        }""",
        {"login": LOGIN},
    )["user"]

    repos, stars, cursor = 0, 0, None
    while True:
        page = graphql(
            """query($login: String!, $cursor: String) {
              user(login: $login) {
                repositories(ownerAffiliations: OWNER, isFork: false, first: 100, after: $cursor) {
                  totalCount
                  nodes { stargazerCount }
                  pageInfo { hasNextPage endCursor }
                }
              }
            }""",
            {"login": LOGIN, "cursor": cursor},
        )["user"]["repositories"]
        repos = page["totalCount"]
        stars += sum(node["stargazerCount"] for node in page["nodes"])
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]

    # contributionsCollection spans at most one year, so walk the account's lifetime year by year.
    created = datetime.fromisoformat(user["createdAt"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    commits = contributions = 0
    for year in range(created.year, now.year + 1):
        start = max(created, datetime(year, 1, 1, tzinfo=timezone.utc))
        end = min(now, datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc))
        collection = graphql(
            """query($login: String!, $from: DateTime!, $to: DateTime!) {
              user(login: $login) {
                contributionsCollection(from: $from, to: $to) {
                  totalCommitContributions
                  restrictedContributionsCount
                  contributionCalendar { totalContributions }
                }
              }
            }""",
            {"login": LOGIN, "from": start.isoformat(), "to": end.isoformat()},
        )["user"]["contributionsCollection"]
        commits += collection["totalCommitContributions"] + collection["restrictedContributionsCount"]
        contributions += collection["contributionCalendar"]["totalContributions"]

    return {
        "uptime": uptime(created, now),
        "repos": repos,
        "contributed": user["repositoriesContributedTo"]["totalCount"],
        "stars": stars,
        "commits": commits,
        "contributions": contributions,
        "followers": user["followers"]["totalCount"],
    }


def uptime(start, now):
    months = (now.year - start.year) * 12 + now.month - start.month
    if now.day < start.day:
        months -= 1
    anchor_month = start.month + months
    anchor = start.replace(year=start.year + (anchor_month - 1) // 12, month=(anchor_month - 1) % 12 + 1)
    days = (now - anchor).days
    years, months = divmod(months, 12)

    def plural(n, unit):
        return f"{n} {unit}{'' if n == 1 else 's'}"

    return f"{plural(years, 'year')}, {plural(months, 'month')}, {plural(days, 'day')}"


def tspan(text, cls=None, **attrs):
    attributes = "".join(f' {k}="{v}"' for k, v in attrs.items())
    if cls:
        attributes += f' class="{cls}"'
    return f"<tspan{attributes}>{escape(text)}</tspan>"


def info_row(y, key, value, link=None):
    """'. Key: ......... value' padded with dots so every value ends on the same column."""
    dots = max(PANEL_CHARS - len(key) - len(value) - 5, 1)
    parts = [tspan(". ", "dim", x=PANEL_X, y=y)]
    *path, last = key.split(".")
    for segment in path:
        parts += [tspan(segment, "key"), "."]
    parts += [tspan(last, "key"), ":", tspan(" " + "." * dots + " ", "dim")]
    value_span = tspan(value, "value")
    parts.append(f'<a href="{escape(link)}" target="_blank">{value_span}</a>' if link else value_span)
    return "".join(parts)


def section(y, title):
    rule = "─" * (PANEL_CHARS - len(title) - 3)
    return tspan(f"─ {title} {rule}", x=PANEL_X, y=y)


def portrait(lines, top, theme):
    # Pin every glyph to the grid with an explicit x list, so block characters stay aligned
    # even if the fallback font gives them a different advance width.
    rows = []
    for i, line in enumerate(lines):
        if not line:
            continue
        xs = " ".join(f"{PAD + c * CHAR_W:.1f}" for c in range(len(line)))
        rows.append(f'<text x="{xs}" y="{top + i * LINE_H}">{escape(line)}</text>')
    return f'<g fill="{theme["text"]}" font-size="{FONT}px">\n' + "\n".join(rows) + "\n</g>"


def eyes(top, theme):
    row, left, right = EYES
    y = top + row * LINE_H

    def pair(char):
        return "".join(
            f'<text x="{PAD + col * CHAR_W:.1f}" y="{y}">{char * EYE_WIDTH}</text>' for col in (left, right)
        )

    # Two copies of the eyes: open for most of the loop, swapped for "closed" for a split second.
    return f"""<g fill="{theme["eye"]}" filter="url(#glow)">
  <g>
    <animate attributeName="opacity" values="1;0;1" keyTimes="0;0.92;0.96" calcMode="discrete" dur="{CYCLE}" repeatCount="indefinite"/>
    {pair("▄")}
  </g>
  <g opacity="0">
    <animate attributeName="opacity" values="0;1;0" keyTimes="0;0.92;0.96" calcMode="discrete" dur="{CYCLE}" repeatCount="indefinite"/>
    {pair("▁")}
  </g>
</g>"""


def render(theme_name, stats, lines):
    theme = THEMES[theme_name]
    rows = []
    y = PAD + 20

    rows.append(tspan(f"{LOGIN}@github", x=PANEL_X, y=y) + " " + tspan("─" * (PANEL_CHARS - len(LOGIN) - 8), "dim"))
    y += ROW_H
    status_y = y
    rows.append(info_row(y, "Status", "  Running (stable)"))
    for key, value in INFO:
        y += ROW_H
        rows.append(info_row(y, key, value.format(**stats)))

    y += ROW_H * 1.5
    rows.append(section(y, "Contact"))
    for key, value, link in CONTACT:
        y += ROW_H
        rows.append(info_row(y, key, value, link))

    y += ROW_H * 1.5
    rows.append(section(y, "GitHub Stats"))
    y += ROW_H
    rows.append(info_row(y, "Repos", f"{stats['repos']} {{Contributed: {stats['contributed']}}} | Stars: {stats['stars']}"))
    y += ROW_H
    rows.append(info_row(y, "Commits", f"{stats['commits']:,} | Followers: {stats['followers']}"))
    y += ROW_H
    rows.append(info_row(y, "Contributions", f"{stats['contributions']:,}"))

    y += ROW_H * 1.5
    prompt_y = y
    rows.append(tspan(QUOTE, "dim", x=PANEL_X, y=y))

    portrait_top = PAD + 16
    height = int(max(y, portrait_top + len(lines) * LINE_H) + PAD)
    width = PANEL_X + int(PANEL_CHARS * CHAR_W) + PAD
    # Status dot sits where the two spaces before "Running" are.
    dot_x = PANEL_X + (PANEL_CHARS - len("  Running (stable)")) * CHAR_W + 6
    cursor_x = PANEL_X + (len(QUOTE) + 1) * CHAR_W

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"
     font-family="'DejaVu Sans Mono', Menlo, Consolas, monospace" font-size="{FONT}px">
<style>
text, tspan {{ white-space: pre; }}
.key {{ fill: {theme["key"]}; }}
.value {{ fill: {theme["value"]}; }}
.dim {{ fill: {theme["dim"]}; }}
</style>
<defs>
  <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
    <feGaussianBlur stdDeviation="2.5" result="blur"/>
    <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
</defs>
<rect width="{width}" height="{height}" fill="{theme["bg"]}"/>

{portrait(lines, portrait_top, theme)}
{eyes(portrait_top, theme)}

<circle cx="{dot_x:.1f}" cy="{status_y - 5}" r="8" fill="none" stroke="{theme["status"]}" stroke-width="2" opacity="0.5"/>
<circle cx="{dot_x:.1f}" cy="{status_y - 5}" r="4" fill="{theme["status"]}">
  <animate attributeName="opacity" values="1;0.3;1" dur="3s" repeatCount="indefinite"/>
</circle>

<text fill="{theme["text"]}">
{chr(10).join(rows)}
</text>

<rect x="{cursor_x:.1f}" y="{prompt_y - 14}" width="{CHAR_W:.1f}" height="18" fill="{theme["text"]}">
  <animate attributeName="opacity" values="1;0" keyTimes="0;0.5" calcMode="discrete" dur="1s" repeatCount="indefinite"/>
</rect>
</svg>
"""


def main():
    lines = (ROOT / "assets" / "portrait.txt").read_text(encoding="utf-8").splitlines()
    stats = fetch_stats()
    print(stats)
    for name in THEMES:
        path = ROOT / f"{name}_mode.svg"
        path.write_text(render(name, stats, lines), encoding="utf-8")
        print(f"Saved {path}")


if __name__ == "__main__":
    main()
