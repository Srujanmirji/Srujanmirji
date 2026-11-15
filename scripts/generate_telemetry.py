#!/usr/bin/env python3
"""
Generates zero-downtime cyberpunk SVG telemetry visuals for Srujanmirji's GitHub profile:
1. profile-3d-contrib/profile-night-rainbow.svg — Isometric 3D contribution matrix from live GitHub GraphQL data
2. assets/developer-telemetry.svg — System Stats, Language Telemetry, Streak & 52-Week Activity Wave
"""

import json
import math
import os
import subprocess
import sys
from collections import Counter
from datetime import datetime

USERNAME = os.environ.get("GITHUB_USER", "Srujanmirji")

GRAPHQL_QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
      totalCount
      nodes {
        name
        isPrivate
        stargazerCount
        primaryLanguage { name color }
      }
    }
    contributionsCollection {
      totalCommitContributions
      restrictedContributionsCount
      totalPullRequestContributions
      totalIssueContributions
      totalRepositoriesWithContributedCommits
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            contributionCount
            date
          }
        }
      }
    }
  }
}
"""


def fetch_github_data(username: str) -> dict:
    cached = "/tmp/gh_stats.json"
    if os.path.exists(cached) and not os.environ.get("FORCE_FETCH"):
        with open(cached, "r", encoding="utf-8") as f:
            return json.load(f)["data"]["user"]

    token = os.environ.get("GITHUB_TOKEN")
    if token:
        import urllib.request

        req = urllib.request.Request(
            "https://api.github.com/graphql",
            data=json.dumps({"query": GRAPHQL_QUERY, "variables": {"login": username}}).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "User-Agent": "Srujanmirji-Profile-Telemetry",
            },
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))["data"]["user"]

    out = subprocess.check_output(
        ["gh", "api", "graphql", "-f", f"query={GRAPHQL_QUERY}", "-F", f"login={username}"],
        text=True,
    )
    return json.loads(out)["data"]["user"]


def compute_streaks(days: list[dict]) -> tuple[int, int, int]:
    longest = 0
    current = 0
    active_days = 0
    running = 0
    for d in days:
        c = d["contributionCount"]
        if c > 0:
            active_days += 1
            running += 1
            if running > longest:
                longest = running
        else:
            running = 0

    # Current streak (allow today to be 0 if yesterday was >0)
    curr = 0
    for i in range(len(days) - 1, -1, -1):
        if days[i]["contributionCount"] > 0:
            curr += 1
        elif i == len(days) - 1:
            continue
        else:
            break
    return curr, longest, active_days


def generate_3d_contrib_svg(user_data: dict, out_path: str) -> None:
    cal = user_data["contributionsCollection"]["contributionCalendar"]
    total_contrib = cal["totalContributions"]
    weeks = cal["weeks"][-36:]  # Last 36 weeks for crisp isometric clarity
    all_days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    _, longest_streak, active_days = compute_streaks(all_days)
    peak_day = max((d["contributionCount"] for d in all_days), default=1)

    # Isometric projection parameters
    # Grid of 36 weeks (columns) x 7 days (rows)
    origin_x = 215.0
    origin_y = 215.0
    dx_w = 21.5
    dy_w = 4.2
    dx_d = -11.5
    dy_d = 9.2
    cube_r = 7.2

    bars_svg = []
    for w_idx, week in enumerate(weeks):
        for d_idx, day in enumerate(week["contributionDays"]):
            count = day["contributionCount"]
            cx = origin_x + w_idx * dx_w + d_idx * dx_d
            cy = origin_y + w_idx * dy_w + d_idx * dy_d

            if count == 0:
                h = 4.0
                top_fill = "#111936"
                left_fill = "#0a1024"
                right_fill = "#070b1a"
                stroke = "#26335e"
                glow_attr = ""
            else:
                ratio = min(1.0, math.pow(count / max(peak_day, 12), 0.62))
                h = 12.0 + ratio * 108.0
                if ratio > 0.68:
                    top_fill = "url(#topPeak)"
                    left_fill = "url(#leftPeak)"
                    right_fill = "url(#rightPeak)"
                    stroke = "#ff94ec"
                    glow_attr = ' filter="url(#glow)"'
                elif ratio > 0.35:
                    top_fill = "url(#topMid)"
                    left_fill = "url(#leftMid)"
                    right_fill = "url(#rightMid)"
                    stroke = "#7df9ff"
                    glow_attr = ""
                else:
                    top_fill = "url(#topLow)"
                    left_fill = "url(#leftLow)"
                    right_fill = "url(#rightLow)"
                    stroke = "#38bdf8"
                    glow_attr = ""

            top_y = cy - h
            # Isometric diamond top + left & right vertical faces
            r = cube_r
            ry = cube_r * 0.54
            top_pts = f"{cx:.1f},{top_y - ry:.1f} {cx + r:.1f},{top_y:.1f} {cx:.1f},{top_y + ry:.1f} {cx - r:.1f},{top_y:.1f}"
            left_pts = f"{cx - r:.1f},{top_y:.1f} {cx:.1f},{top_y + ry:.1f} {cx:.1f},{cy + ry:.1f} {cx - r:.1f},{cy:.1f}"
            right_pts = f"{cx + r:.1f},{top_y:.1f} {cx:.1f},{top_y + ry:.1f} {cx:.1f},{cy + ry:.1f} {cx + r:.1f},{cy:.1f}"

            bars_svg.append(
                f'    <g{glow_attr}>'
                f'<polygon points="{left_pts}" fill="{left_fill}"/>'
                f'<polygon points="{right_pts}" fill="{right_fill}"/>'
                f'<polygon points="{top_pts}" fill="{top_fill}" stroke="{stroke}" stroke-width="0.45" stroke-opacity="0.75"/>'
                f"</g>"
            )

    bars_joined = "\n".join(bars_svg)
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="440" viewBox="0 0 1200 440" role="img" aria-labelledby="title desc">
  <title id="title">3D Developer Contribution Matrix — Srujan Mirji</title>
  <desc id="desc">Live 3D isometric contribution skyline generated from Srujan Mirji's GitHub activity ({total_contrib} annual contributions).</desc>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#040711"/>
      <stop offset="0.55" stop-color="#090f24"/>
      <stop offset="1" stop-color="#050814"/>
    </linearGradient>
    <linearGradient id="edge" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#00f5ff" stop-opacity="0.8"/>
      <stop offset="0.5" stop-color="#7c5cff" stop-opacity="0.65"/>
      <stop offset="1" stop-color="#ff4fd8" stop-opacity="0.8"/>
    </linearGradient>
    <linearGradient id="topLow" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#00e5ff"/><stop offset="1" stop-color="#2563eb"/></linearGradient>
    <linearGradient id="leftLow" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#0284c7"/><stop offset="1" stop-color="#0f172a"/></linearGradient>
    <linearGradient id="rightLow" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#1d4ed8"/><stop offset="1" stop-color="#090d1f"/></linearGradient>

    <linearGradient id="topMid" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#00f5ff"/><stop offset="1" stop-color="#a855f7"/></linearGradient>
    <linearGradient id="leftMid" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#0891b2"/><stop offset="1" stop-color="#1e1b4b"/></linearGradient>
    <linearGradient id="rightMid" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#6d28d9"/><stop offset="1" stop-color="#170f36"/></linearGradient>

    <linearGradient id="topPeak" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#7df9ff"/><stop offset="0.5" stop-color="#d946ef"/><stop offset="1" stop-color="#ff4fd8"/></linearGradient>
    <linearGradient id="leftPeak" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#00d2ff"/><stop offset="1" stop-color="#3b0764"/></linearGradient>
    <linearGradient id="rightPeak" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#c026d3"/><stop offset="1" stop-color="#240a3d"/></linearGradient>

    <filter id="glow" x="-60%" y="-60%" width="220%" height="220%">
      <feGaussianBlur stdDeviation="4" result="b"/>
      <feFlood flood-color="#ff4fd8" flood-opacity="0.55"/>
      <feComposite in2="b" operator="in"/>
      <feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse">
      <path d="M32 0H0V32" fill="none" stroke="#7c72ff" stroke-opacity="0.07"/>
    </pattern>
  </defs>

  <rect x="3" y="3" width="1194" height="434" rx="26" fill="url(#bg)" stroke="url(#edge)" stroke-width="1.5"/>
  <rect x="3" y="3" width="1194" height="434" rx="26" fill="url(#grid)"/>

  <!-- Header HUD -->
  <g font-family="Arial, Helvetica, sans-serif">
    <text x="48" y="54" fill="#effcff" font-size="22" font-weight="800" letter-spacing="3.5">3D CONTRIBUTION SKYLINE</text>
    <circle cx="54" cy="80" r="4" fill="#00f5b8">
      <animate attributeName="opacity" values="1;0.25;1" dur="1.8s" repeatCount="indefinite"/>
    </circle>
    <text x="68" y="84" fill="#8f9bb8" font-size="11.5" font-family="monospace" letter-spacing="1.3">LIVE ISOMETRIC COMMIT MATRIX • LAST 36 WEEKS TELEMETRY</text>
  </g>

  <!-- Live Stat Pills (Top Right) -->
  <g font-family="monospace" transform="translate(650, 32)">
    <rect x="0" y="0" width="165" height="54" rx="12" fill="#0b1329" stroke="#00f5ff" stroke-opacity="0.45"/>
    <text x="16" y="21" fill="#7f91b8" font-size="10" letter-spacing="1">ANNUAL OUTPUT</text>
    <text x="16" y="42" fill="#00f5ff" font-size="20" font-weight="700">{total_contrib:,}</text>

    <rect x="180" y="0" width="160" height="54" rx="12" fill="#0b1329" stroke="#a879ff" stroke-opacity="0.45"/>
    <text x="196" y="21" fill="#7f91b8" font-size="10" letter-spacing="1">ACTIVE DAYS</text>
    <text x="196" y="42" fill="#c8a8ff" font-size="20" font-weight="700">{active_days} days</text>

    <rect x="355" y="0" width="150" height="54" rx="12" fill="#0b1329" stroke="#ff4fd8" stroke-opacity="0.45"/>
    <text x="371" y="21" fill="#7f91b8" font-size="10" letter-spacing="1">PEAK STREAK</text>
    <text x="371" y="42" fill="#ff7ae2" font-size="20" font-weight="700">{longest_streak}d</text>
  </g>

  <!-- Isometric Base Platform Lines -->
  <g fill="none" stroke="#7767ff" stroke-opacity="0.22" stroke-width="1">
    <path d="M120 278L910 418L1020 330L230 190Z"/>
  </g>

  <!-- 3D Isometric Contribution Bars -->
  <g>
{bars_joined}
  </g>

  <!-- Bottom HUD Footer -->
  <path d="M45 402H1155" stroke="url(#edge)" stroke-opacity="0.55"/>
  <text x="48" y="422" fill="#6f7ea3" font-size="10.5" font-family="monospace">INTENSITY: LOW [CYAN] → HIGH [VIOLET] → PEAK [MAGENTA GLOW]</text>
  <text x="1152" y="422" text-anchor="end" fill="#6f7ea3" font-size="10.5" font-family="monospace">SRUJAN MIRJI // CODE × PRODUCT × MOTION × INTELLIGENCE</text>
</svg>
"""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg)


def generate_telemetry_dashboard_svg(user_data: dict, out_path: str) -> None:
    repos = user_data["repositories"]["nodes"]
    total_repos = user_data["repositories"]["totalCount"]
    cc = user_data["contributionsCollection"]
    total_commits = cc["totalCommitContributions"] + cc["restrictedContributionsCount"]
    total_prs = cc["totalPullRequestContributions"]
    contributed_repos = cc["totalRepositoriesWithContributedCommits"]
    cal = cc["contributionCalendar"]
    total_contrib = cal["totalContributions"]
    weeks = cal["weeks"]
    all_days = [d for w in weeks for d in w["contributionDays"]]
    curr_streak, longest_streak, active_days = compute_streaks(all_days)

    # Weekly totals for the 52-week wave chart
    weekly_totals = [sum(d["contributionCount"] for d in w["contributionDays"]) for w in weeks[-52:]]
    max_week = max(weekly_totals + [1])
    peak_week_val = max(weekly_totals)

    # Language breakdown across owned non-fork repos
    lang_counts = Counter(r["primaryLanguage"]["name"] for r in repos if r.get("primaryLanguage"))
    top_langs = lang_counts.most_common(5)
    total_lang_repos = sum(c for _, c in top_langs) or 1
    lang_colors = {
        "TypeScript": "#00F5FF",
        "JavaScript": "#FACC15",
        "Python": "#A879FF",
        "HTML": "#FF4FD8",
        "CSS": "#38BDF8",
        "Swift": "#FB7185",
        "Kotlin": "#34D399",
        "Java": "#F97316",
    }

    # Build multi-segment language bar (width 460)
    bar_x = 580.0
    bar_w = 540.0
    lang_rects = []
    lang_labels = []
    cur_x = bar_x
    for idx, (lang, cnt) in enumerate(top_langs):
        pct = cnt / total_lang_repos
        seg_w = max(18.0, round(pct * bar_w, 1))
        if idx == len(top_langs) - 1:
            seg_w = round(bar_x + bar_w - cur_x, 1)
        color = lang_colors.get(lang, "#7C5CFF")
        lang_rects.append(
            f'    <rect x="{cur_x:.1f}" y="198" width="{ max(2.0, seg_w - 3):.1f}" height="10" rx="4" fill="{color}"/>'
        )
        cur_x += seg_w
        lx = 580 + idx * 112
        lang_labels.append(
            f'    <circle cx="{lx}" cy="228" r="4.5" fill="{color}"/>'
            f'<text x="{lx + 10}" y="232" fill="#d4dfff" font-size="11.5" font-family="monospace">{lang} {round(pct*100)}%</text>'
        )

    # Build 52-week activity spline/polyline points
    chart_x0 = 76.0
    chart_x1 = 1136.0
    chart_y0 = 335.0
    chart_y1 = 485.0
    n_pts = len(weekly_totals)
    pts = []
    dots = []
    for i, val in enumerate(weekly_totals):
        px = chart_x0 + (i / max(1, n_pts - 1)) * (chart_x1 - chart_x0)
        py = chart_y1 - (val / max_week) * (chart_y1 - chart_y0)
        pts.append((px, py, val))
        if val >= peak_week_val * 0.45 or i == n_pts - 1:
            dots.append(
                f'    <circle cx="{px:.1f}" cy="{py:.1f}" r="4" fill="#ff4fd8" stroke="#ffffff" stroke-width="1.2"/>'
            )
        elif i % 4 == 0:
            dots.append(f'    <circle cx="{px:.1f}" cy="{py:.1f}" r="2.5" fill="#00f5ff"/>')

    line_path = "M " + " L ".join(f"{px:.1f} {py:.1f}" for px, py, _ in pts)
    area_path = line_path + f" L {chart_x1:.1f} {chart_y1:.1f} L {chart_x0:.1f} {chart_y1:.1f} Z"

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="550" viewBox="0 0 1200 550" role="img" aria-labelledby="title desc">
  <title id="title">Srujan Mirji — Developer Telemetry &amp; Contribution Activity</title>
  <desc id="desc">GitHub telemetry card displaying {total_contrib} annual contributions, {total_commits} commits, {total_prs} pull requests, {total_repos} repositories, and a 52-week contribution activity graph.</desc>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#050814"/>
      <stop offset="0.5" stop-color="#080e22"/>
      <stop offset="1" stop-color="#050712"/>
    </linearGradient>
    <linearGradient id="cardBg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#0a1126" stop-opacity="0.95"/>
      <stop offset="1" stop-color="#070c1b" stop-opacity="0.95"/>
    </linearGradient>
    <linearGradient id="edge" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#00f5ff" stop-opacity="0.8"/>
      <stop offset="0.5" stop-color="#7c5cff" stop-opacity="0.65"/>
      <stop offset="1" stop-color="#ff4fd8" stop-opacity="0.8"/>
    </linearGradient>
    <linearGradient id="waveArea" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#00f5ff" stop-opacity="0.42"/>
      <stop offset="0.6" stop-color="#7c5cff" stop-opacity="0.18"/>
      <stop offset="1" stop-color="#070b16" stop-opacity="0.0"/>
    </linearGradient>
    <linearGradient id="waveLine" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#00f5ff"/>
      <stop offset="0.55" stop-color="#a879ff"/>
      <stop offset="1" stop-color="#ff4fd8"/>
    </linearGradient>
    <pattern id="grid" width="30" height="30" patternUnits="userSpaceOnUse">
      <path d="M30 0H0V30" fill="none" stroke="#7c72ff" stroke-opacity="0.065"/>
    </pattern>
  </defs>

  <rect x="3" y="3" width="1194" height="544" rx="26" fill="url(#bg)" stroke="url(#edge)" stroke-width="1.5"/>
  <rect x="3" y="3" width="1194" height="544" rx="26" fill="url(#grid)"/>

  <!-- LEFT CARD: CORE GITHUB TELEMETRY -->
  <rect x="36" y="32" width="496" height="226" rx="18" fill="url(#cardBg)" stroke="#00f5ff" stroke-opacity="0.32"/>
  <text x="64" y="68" fill="#00f5ff" font-size="15" font-family="Arial, Helvetica, sans-serif" font-weight="800" letter-spacing="2.4">01 // SYSTEM TELEMETRY</text>
  <text x="498" y="68" text-anchor="end" fill="#6d7da3" font-size="11" font-family="monospace">@Srujanmirji</text>

  <g font-family="monospace" font-size="13">
    <text x="64" y="108" fill="#9fb0d6">Annual Contributions</text>
    <text x="315" y="108" text-anchor="end" fill="#ffffff" font-weight="700" font-size="15">{total_contrib:,}</text>

    <text x="64" y="138" fill="#9fb0d6">Commits (12 Months)</text>
    <text x="315" y="138" text-anchor="end" fill="#00f5ff" font-weight="700" font-size="15">{total_commits:,}</text>

    <text x="64" y="168" fill="#9fb0d6">Pull Requests Merged</text>
    <text x="315" y="168" text-anchor="end" fill="#c8a8ff" font-weight="700" font-size="15">{total_prs}</text>

    <text x="64" y="198" fill="#9fb0d6">Public &amp; Private Repos</text>
    <text x="315" y="198" text-anchor="end" fill="#ff7ae2" font-weight="700" font-size="15">{total_repos}</text>

    <text x="64" y="228" fill="#9fb0d6">Active Repo Footprint</text>
    <text x="315" y="228" text-anchor="end" fill="#5eead4" font-weight="700" font-size="15">{contributed_repos} repos</text>
  </g>

  <!-- Grade / Status Ring on Right of Left Card -->
  <g transform="translate(425, 152)">
    <circle cx="0" cy="0" r="54" fill="none" stroke="#182342" stroke-width="9"/>
    <circle cx="0" cy="0" r="54" fill="none" stroke="url(#waveLine)" stroke-width="9" stroke-dasharray="305 340" stroke-linecap="round" transform="rotate(-90)"/>
    <text x="0" y="-2" text-anchor="middle" fill="#ffffff" font-family="Arial, Helvetica, sans-serif" font-size="24" font-weight="900">S+</text>
    <text x="0" y="18" text-anchor="middle" fill="#00f5ff" font-family="monospace" font-size="10" letter-spacing="1.2">SHIPPING</text>
  </g>

  <!-- RIGHT CARD: VELOCITY, STREAKS & LANGUAGE DISTRIBUTION -->
  <rect x="552" y="32" width="612" height="226" rx="18" fill="url(#cardBg)" stroke="#a879ff" stroke-opacity="0.35"/>
  <text x="580" y="68" fill="#c8a8ff" font-size="15" font-family="Arial, Helvetica, sans-serif" font-weight="800" letter-spacing="2.4">02 // CADENCE &amp; STACK TELEMETRY</text>
  <text x="1134" y="68" text-anchor="end" fill="#00f5b8" font-size="11" font-family="monospace">● VERIFIED GRAPHQL</text>

  <!-- 3 Stat Boxes inside Right Card -->
  <g font-family="monospace">
    <rect x="580" y="88" width="170" height="76" rx="12" fill="#0d1630" stroke="#00f5ff" stroke-opacity="0.3"/>
    <text x="598" y="113" fill="#8596bd" font-size="10.5">PEAK WEEKLY BURST</text>
    <text x="598" y="145" fill="#00f5ff" font-size="24" font-weight="800">{peak_week_val} <tspan font-size="12" fill="#9fb0d6">commits</tspan></text>

    <rect x="768" y="88" width="170" height="76" rx="12" fill="#0d1630" stroke="#a879ff" stroke-opacity="0.3"/>
    <text x="786" y="113" fill="#8596bd" font-size="10.5">LONGEST STREAK</text>
    <text x="786" y="145" fill="#c8a8ff" font-size="24" font-weight="800">{longest_streak} <tspan font-size="12" fill="#9fb0d6">days</tspan></text>

    <rect x="956" y="88" width="178" height="76" rx="12" fill="#0d1630" stroke="#ff4fd8" stroke-opacity="0.3"/>
    <text x="974" y="113" fill="#8596bd" font-size="10.5">ACTIVE BUILD DAYS</text>
    <text x="974" y="145" fill="#ff7ae2" font-size="24" font-weight="800">{active_days} <tspan font-size="12" fill="#9fb0d6">/ 365d</tspan></text>
  </g>

  <text x="580" y="187" fill="#8596bd" font-size="10.5" font-family="monospace" letter-spacing="1">DOMINANT REPOSITORY LANGUAGES</text>
{chr(10).join(lang_rects)}
{chr(10).join(lang_labels)}

  <!-- BOTTOM CARD: 52-WEEK CONTRIBUTION WAVE -->
  <rect x="36" y="278" width="1128" height="238" rx="18" fill="url(#cardBg)" stroke="#7c5cff" stroke-opacity="0.35"/>
  <text x="64" y="314" fill="#effcff" font-size="15" font-family="Arial, Helvetica, sans-serif" font-weight="800" letter-spacing="2.4">03 // 52-WEEK CONTRIBUTION ACTIVITY WAVE</text>
  <text x="1134" y="314" text-anchor="end" fill="#8f9bb8" font-size="11" font-family="monospace">PEAK WEEK: {peak_week_val} CONTRIBUTIONS • TOTAL: {total_contrib:,}</text>

  <!-- Horizontal Guide Lines -->
  <g stroke="#7c72ff" stroke-opacity="0.14" stroke-dasharray="4 4" font-family="monospace" font-size="10" fill="#68789e">
    <line x1="76" y1="345" x2="1136" y2="345"/>
    <text x="66" y="349" text-anchor="end" stroke="none">{max_week}</text>
    <line x1="76" y1="415" x2="1136" y2="415"/>
    <text x="66" y="419" text-anchor="end" stroke="none">{max_week // 2}</text>
    <line x1="76" y1="485" x2="1136" y2="485"/>
    <text x="66" y="489" text-anchor="end" stroke="none">0</text>
  </g>

  <path d="{area_path}" fill="url(#waveArea)"/>
  <path d="{line_path}" fill="none" stroke="url(#waveLine)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
{chr(10).join(dots)}
</svg>
"""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg)


def main() -> int:
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    user_data = fetch_github_data(USERNAME)
    generate_3d_contrib_svg(
        user_data,
        os.path.join(repo_root, "profile-3d-contrib", "profile-night-rainbow.svg"),
    )
    generate_telemetry_dashboard_svg(
        user_data,
        os.path.join(repo_root, "assets", "developer-telemetry.svg"),
    )
    print("Generated profile-3d-contrib/profile-night-rainbow.svg and assets/developer-telemetry.svg successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
