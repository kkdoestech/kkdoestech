"""Generate animated glitch repo cards: assets/cards/<repo>.svg

Each card is a small SVG with CSS/SMIL animation (GitHub plays these in READMEs):
colour-cycling border, red/cyan split title that jitters, horizontal slices that
jump sideways, flashing noise bars and scanlines. Every card runs on its own
timing so they glitch out of sync.

Repo text is baked in below; edit REPOS (or re-run with fresh data) when it changes.

Usage:  python tools/make_cards.py
"""

import textwrap
from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(__file__).resolve().parent.parent / "assets" / "cards"
USER = "kkdoestech"

BG = "#0D0D0D"
BLUE, DEEP_BLUE, RED, GREEN, YELLOW, CYAN = "#00A8FF", "#0047FF", "#FF1F3D", "#39FF14", "#FFD300", "#00E5FF"
PY = "#3572A5"

# name, description, language, stars, accent colour, glitch period (s), tag
REPOS = [
    ("lieng-stealer",
     "Real-time Game Theory Optimal (GTO) decision solver and dynamic EV engine for Vietnamese Liêng.",
     "Python", 1, RED, 2.6, "0x01"),
    ("matchoracle-honest",
     "Honest rebuild of MatchOracle (EPL predictor): leak-free features, a pre-registered protocol that "
     "never tunes on the test season, trust reports, a prediction ledger, a terminal dashboard, and a "
     "21-chapter course.",
     "Python", 0, BLUE, 3.4, "0x02"),
    ("m6rec-pytorch",
     "A PyTorch-based text-to-text recommender system implementing the M6-Rec paradigm. Transforms user "
     "behavioral clickstreams and item metadata into structured natural language prompts.",
     "Python", 0, GREEN, 3.0, "0x03"),
    ("stealer-recreation",
     "Poker preflop steal-range EV calculator — a from-scratch recreation inspired by @GanjinZero's stealer.",
     "Python", 0, YELLOW, 3.8, "0x04"),
]

W, H = 400, 150
SANS = "'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif"
MONO = "Consolas, 'Courier New', monospace"


def wrap(text, width=54, lines=3):
    out = textwrap.wrap(text, width)
    if len(out) > lines:
        out = out[:lines]
        out[-1] = out[-1][: width - 1].rstrip() + "…"
    return out


def card(name, desc, lang, stars, accent, period, tag):
    desc_lines = "".join(
        f'<tspan x="22" dy="{0 if i == 0 else 18}">{escape(line)}</tspan>' for i, line in enumerate(wrap(desc))
    )
    title = escape(name)
    star = (f'<g transform="translate(120 122)" fill="none" stroke="{YELLOW}" stroke-width="1.4">'
            f'<path d="M7 0.8l1.9 3.9 4.3.6-3.1 3 .7 4.3L7 10.6l-3.8 2 .7-4.3-3.1-3 4.3-.6z"/></g>'
            f'<text x="140" y="134" class="meta">{stars}</text>') if stars else ""
    bars = "".join(
        f'<rect class="bar" x="{x}" y="{y}" width="{w}" height="{h}" fill="{c}" style="animation-delay:{d}s"/>'
        for x, y, w, h, c, d in [
            (30, 18, 70, 3, GREEN, 0.1), (250, 64, 110, 2, RED, 0.5), (60, 104, 40, 4, YELLOW, 0.9),
            (300, 118, 60, 3, CYAN, 1.3), (180, 30, 30, 5, accent, 1.7), (12, 84, 90, 2, BLUE, 2.1),
        ]
    )
    p = period
    return f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<style>
  .title {{ font: 700 18px {SANS}; }}
  .desc {{ font: 400 12.5px {SANS}; fill: #E6E6E6; }}
  .meta {{ font: 400 12px {SANS}; fill: #CFCFCF; }}
  .tag {{ font: 700 11px {MONO}; fill: {GREEN}; animation: flicker {p * 0.7:.2f}s steps(1) infinite; }}
  .main {{ animation: jitter {p}s steps(1) infinite; }}
  .gr {{ fill: {RED}; opacity: .85; animation: ghostR {p}s steps(1) infinite; }}
  .gc {{ fill: {CYAN}; opacity: .85; animation: ghostC {p}s steps(1) infinite; }}
  .s1 {{ animation: slice1 {p}s steps(1) infinite; }}
  .s2 {{ animation: slice2 {p * 1.3:.2f}s steps(1) infinite; }}
  .bar {{ opacity: 0; animation: flash {p}s steps(1) infinite; }}
  @keyframes jitter {{
    0%, 82%, 100% {{ transform: translate(0, 0); }}
    84% {{ transform: translate(-3px, 1px); }} 87% {{ transform: translate(4px, -1px); }}
    90% {{ transform: translate(-2px, 0); }} 93% {{ transform: translate(2px, 1px); }} 96% {{ transform: translate(0, 0); }}
  }}
  @keyframes ghostR {{
    0%, 82%, 100% {{ transform: translate(1.5px, 0); }}
    84% {{ transform: translate(6px, -1px); }} 88% {{ transform: translate(-4px, 1px); }} 92% {{ transform: translate(9px, 0); }}
  }}
  @keyframes ghostC {{
    0%, 82%, 100% {{ transform: translate(-1.5px, 0); }}
    84% {{ transform: translate(-6px, 1px); }} 88% {{ transform: translate(5px, -1px); }} 92% {{ transform: translate(-8px, 0); }}
  }}
  @keyframes slice1 {{
    0%, 80%, 100% {{ transform: translateX(0); }}
    81% {{ transform: translateX(-18px); }} 85% {{ transform: translateX(12px); }} 89% {{ transform: translateX(-6px); }} 92% {{ transform: translateX(0); }}
  }}
  @keyframes slice2 {{
    0%, 70%, 100% {{ transform: translateX(0); }}
    72% {{ transform: translateX(22px); }} 76% {{ transform: translateX(-10px); }} 80% {{ transform: translateX(0); }}
  }}
  @keyframes flash {{
    0%, 80%, 100% {{ opacity: 0; }} 82% {{ opacity: .9; }} 86% {{ opacity: 0; }} 90% {{ opacity: .8; }} 94% {{ opacity: 0; }}
  }}
  @keyframes flicker {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: .25; }} 55% {{ opacity: 1; }} 80% {{ opacity: .5; }} }}
</style>
<defs>
  <linearGradient id="border" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="{BLUE}"/><stop offset=".35" stop-color="{RED}"/>
    <stop offset=".65" stop-color="{YELLOW}"/><stop offset="1" stop-color="{GREEN}"/>
    <animateTransform attributeName="gradientTransform" type="rotate" values="0 .5 .5;360 .5 .5" dur="{p * 1.5:.2f}s" repeatCount="indefinite"/>
  </linearGradient>
  <pattern id="scan" width="4" height="3" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="#000" opacity=".35"/></pattern>
  <clipPath id="band1"><rect x="0" y="40" width="{W}" height="16">
    <animate attributeName="y" values="38;96;60;20;112" dur="{p * 1.1:.2f}s" calcMode="discrete" repeatCount="indefinite"/></rect></clipPath>
  <clipPath id="band2"><rect x="0" y="100" width="{W}" height="9">
    <animate attributeName="y" values="100;24;76;130;50" dur="{p * 1.7:.2f}s" calcMode="discrete" repeatCount="indefinite"/></rect></clipPath>
  <g id="content">
    <g transform="translate(22 22)" fill="{accent}">
      <path d="M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 .75.75v12.5a.75.75 0 0 1-.75.75h-2.5a.75.75 0 0 1 0-1.5h1.75v-2h-8a1 1 0 0 0-.71 1.71.75.75 0 0 1-1.07 1.05A2.5 2.5 0 0 1 2 11.5Zm10.5-1h-8a1 1 0 0 0-1 1v6.71A2.5 2.5 0 0 1 4.5 9h8ZM5 12.25a.25.25 0 0 1 .25-.25h3.5a.25.25 0 0 1 .25.25v3.25a.25.25 0 0 1-.4.2l-1.45-1.09a.25.25 0 0 0-.3 0L5.4 15.7a.25.25 0 0 1-.4-.2Z"/>
    </g>
    <text x="46" y="36" class="title gr">{title}</text>
    <text x="46" y="36" class="title gc">{title}</text>
    <text x="46" y="36" class="title" fill="{accent}">{title}</text>
    <text x="{W - 16}" y="24" class="tag" text-anchor="end">[{tag}]</text>
    <text y="64" class="desc">{desc_lines}</text>
    <circle cx="28" cy="130" r="6" fill="{PY}"/>
    <text x="40" y="134" class="meta">{escape(lang)}</text>
    {star}
  </g>
</defs>

<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="8" fill="{BG}"/>
<g class="main"><use xlink:href="#content" href="#content"/></g>
<g clip-path="url(#band1)"><g class="s1"><rect width="{W}" height="{H}" fill="{BG}"/><use xlink:href="#content" href="#content"/></g></g>
<g clip-path="url(#band2)"><g class="s2"><rect width="{W}" height="{H}" fill="{BG}"/><use xlink:href="#content" href="#content"/></g></g>
{bars}
<rect width="{W}" height="{H}" rx="8" fill="url(#scan)"/>
<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="8" fill="none" stroke="url(#border)" stroke-width="2"/>
</svg>
"""


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for repo in REPOS:
        path = OUT / f"{repo[0]}.svg"
        path.write_text(card(*repo), encoding="utf-8")
        print(f"wrote {path} ({path.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
