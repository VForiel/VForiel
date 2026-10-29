"""Draw the language spectrum of VForiel's public repositories (assets/spectrum-dark.svg, assets/spectrum-light.svg).

Each language is an emission line: its height follows its share of the code, its position is fixed by its name, so
the spectrum only changes when the code does. Jupyter notebooks are left out: their size is mostly cell outputs.
Run: GITHUB_TOKEN=... python scripts/spectrum.py   (the weekly workflow does it)
"""

import datetime
import json
import os
import urllib.request
import zlib
from pathlib import Path

USER = "VForiel"
EXCLUDED = {"Jupyter Notebook"}
ASSETS = Path(__file__).resolve().parent.parent / "assets"
THEMES = {
    "dark": {"background": "#0b0e14", "border": "#2d3140", "text": "#ebe6dc", "muted": "#80838f", "line": "#e2c482"},
    "light": {"background": "#f8f5ee", "border": "#d1ccc2", "text": "#1a2233", "muted": "#737780", "line": "#21438d"},
}
WIDTH, HEIGHT = 1200, 240
LEFT, RIGHT, BASE, TOP = 48, 1152, 186, 108
ROWS = (62, 86)  # baselines of the two label rows
MONO = "'IBM Plex Mono', ui-monospace, 'SF Mono', Menlo, Consolas, monospace"
QUERY = """
query($login: String!) { user(login: $login) { repositories(first: 100, privacy: PUBLIC, isFork: false,
  ownerAffiliations: OWNER) { totalCount nodes { languages(first: 30) { edges { size node { name } } } } } } }
"""


def fetch_languages() -> tuple[int, dict[str, int]]:
    """Number of public repositories and bytes of code per language."""
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {os.environ['GITHUB_TOKEN']}"},
    )
    with urllib.request.urlopen(request) as response:
        repositories = json.load(response)["data"]["user"]["repositories"]
    sizes: dict[str, int] = {}
    for repository in repositories["nodes"]:
        for edge in repository["languages"]["edges"]:
            name = edge["node"]["name"]
            if name not in EXCLUDED:
                sizes[name] = sizes.get(name, 0) + edge["size"]
    return repositories["totalCount"], sizes


def wavelength(name: str) -> float:
    """Fixed position of a language on the spectrum, between 0 and 1."""
    return 0.04 + 0.92 * (zlib.crc32(name.encode()) % 1000) / 999


def spectrum(c: dict[str, str], repositories: int, sizes: dict[str, int], today: str) -> str:
    total = sum(sizes.values())
    ranked = sorted(sizes.items(), key=lambda item: -item[1])
    largest = ranked[0][1]
    parts = []

    # Axis with ticks, like a spectrograph read-out.
    parts.append(f'<line x1="{LEFT}" y1="{BASE}" x2="{RIGHT}" y2="{BASE}" class="axis"/>')
    for k in range(11):
        x = LEFT + k * (RIGHT - LEFT) / 10
        parts.append(f'<line x1="{x}" y1="{BASE}" x2="{x}" y2="{BASE + 5}" class="axis"/>')

    labelled = []
    for rank, (name, size) in enumerate(ranked):
        x = LEFT + wavelength(name) * (RIGHT - LEFT)
        # Square root, so that small languages stay visible next to Python.
        height = 6 + (BASE - TOP - 6) * (size / largest) ** 0.5
        width = 3 if rank < 6 else 1.5
        parts.append(
            f'<rect x="{x - width / 2:.1f}" y="{BASE - height:.1f}" width="{width}" height="{height:.1f}" '
            f'class="emission" opacity="{0.45 + 0.55 * (size / largest) ** 0.5:.2f}"/>'
        )
        if rank < 6:
            labelled.append((x, name, 100 * size / total, BASE - height))

    # Labels of the six main lines, above the spectrum: second row when they would overlap the first.
    labelled.sort()
    row_end = [-1e9, -1e9]
    texts = []
    for x, name, share, top in labelled:
        text = f"{name} {share:.0f} %" if share >= 1 else f"{name} <1 %"
        half = 4.9 * len(text)
        row = 0 if x - half > row_end[0] + 12 else 1
        x_text = max(x, row_end[row] + 12 + half)
        row_end[row] = x_text + half
        texts.append(f'<text x="{x_text:.1f}" y="{ROWS[row]}" class="label" text-anchor="middle">{text}</text>')
        parts.append(
            f'<path d="M{x_text:.1f} {ROWS[row] + 5} V{ROWS[1] + 8} L{x:.1f} {TOP - 2} V{top - 3:.1f}" class="leader"/>'
        )
    parts.extend(texts)  # drawn last, so that their outline hides the leaders passing behind them

    lines = "\n  ".join(parts)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" width="{WIDTH}" height="{HEIGHT}" role="img" aria-labelledby="title">
  <title id="title">Languages of {repositories} public repositories: {", ".join(f"{n} {100 * s / total:.0f} %" for n, s in ranked[:6])}</title>
  <style>
    .label {{ font: 400 16px {MONO}; fill: {c["text"]}; stroke: {c["background"]}; stroke-width: 6px;
              paint-order: stroke; }}
    .caption {{ font: 400 15px {MONO}; fill: {c["muted"]}; letter-spacing: 0.5px; }}
    .axis {{ stroke: {c["muted"]}; stroke-width: 1; }}
    .emission {{ fill: {c["line"]}; }}
    .leader {{ fill: none; stroke: {c["muted"]}; stroke-width: 1; stroke-dasharray: 2 3; }}
  </style>
  <rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{HEIGHT - 1}" rx="8" fill="{c["background"]}" stroke="{c["border"]}"/>
  <text x="{LEFT}" y="30" class="caption">EMISSION SPECTRUM · {repositories} PUBLIC REPOSITORIES · BYTES OF CODE, NOTEBOOKS EXCLUDED</text>
  <text x="{RIGHT}" y="30" class="caption" text-anchor="end">{today}</text>
  {lines}
  <text x="{LEFT}" y="{BASE + 32}" class="caption">{len(sizes)} languages detected</text>
</svg>
"""


if __name__ == "__main__":
    repositories, sizes = fetch_languages()
    today = datetime.date.today().isoformat()
    ASSETS.mkdir(exist_ok=True)
    for name, colors in THEMES.items():
        (ASSETS / f"spectrum-{name}.svg").write_text(
            spectrum(colors, repositories, sizes, today), encoding="utf-8", newline="\n"
        )
