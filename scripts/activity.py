"""Draw the key numbers of VForiel (assets/activity-dark.svg, assets/activity-light.svg).

Totals only, no curve over time. Same colours and layout rules as the spectrum.
Run: GITHUB_TOKEN=... python scripts/activity.py   (the weekly workflow does it)
"""

import datetime
import json
import os
import urllib.request

from spectrum import ASSETS, MONO, THEMES, USER

WIDTH, HEIGHT = 1200, 170
LEFT, RIGHT = 48, 1152
QUERY = """
query($login: String!) { user(login: $login) { createdAt
  repositories(privacy: PUBLIC, isFork: false, ownerAffiliations: OWNER) { totalCount }
  contributionsCollection { totalPullRequestContributions totalIssueContributions
    contributionCalendar { totalContributions } } } }
"""


def fetch_numbers() -> list[tuple[int, str]]:
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {os.environ['GITHUB_TOKEN']}"},
    )
    with urllib.request.urlopen(request) as response:
        user = json.load(response)["data"]["user"]
    repositories = user["repositories"]
    collection = user["contributionsCollection"]
    created = datetime.date.fromisoformat(user["createdAt"][:10])
    return [
        ((datetime.date.today() - created).days // 365, "years on GitHub"),
        (repositories["totalCount"], "public repos"),
        (collection["contributionCalendar"]["totalContributions"], "contributions, 1 year"),
        (collection["totalPullRequestContributions"], "pull requests"),
        (collection["totalIssueContributions"], "issues"),
    ]


def card(c: dict[str, str], numbers: list[tuple[int, str]], today: str) -> str:
    column = (RIGHT - LEFT) / len(numbers)
    parts = []
    for i, (value, label) in enumerate(numbers):
        x = LEFT + i * column
        if i:
            parts.append(f'<line x1="{x - 16:.1f}" y1="70" x2="{x - 16:.1f}" y2="140" class="axis" opacity="0.4"/>')
        parts.append(f'<text x="{x:.1f}" y="110" class="big">{value}</text>')
        parts.append(f'<text x="{x:.1f}" y="136" class="caption">{label}</text>')
    body = "\n  ".join(parts)
    summary = ", ".join(f"{value} {label}" for value, label in numbers)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" width="{WIDTH}" height="{HEIGHT}" role="img" aria-labelledby="title">
  <title id="title">{summary}</title>
  <style>
    .big {{ font: 400 44px {MONO}; fill: {c["text"]}; }}
    .caption {{ font: 400 15px {MONO}; fill: {c["muted"]}; letter-spacing: 0.5px; }}
    .axis {{ stroke: {c["muted"]}; stroke-width: 1; }}
  </style>
  <rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{HEIGHT - 1}" rx="8" fill="{c["background"]}" stroke="{c["border"]}"/>
  <text x="{LEFT}" y="36" class="caption">SURVEY · PUBLIC ACTIVITY</text>
  <text x="{RIGHT}" y="36" class="caption" text-anchor="end">{today}</text>
  {body}
</svg>
"""


if __name__ == "__main__":
    numbers = fetch_numbers()
    today = datetime.date.today().isoformat()
    ASSETS.mkdir(exist_ok=True)
    for name, colors in THEMES.items():
        (ASSETS / f"activity-{name}.svg").write_text(card(colors, numbers, today), encoding="utf-8", newline="\n")
