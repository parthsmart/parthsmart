#!/usr/bin/env python3
"""Self-contained profile renderer. See SETUP.md. Python 3.11+ and fonttools."""
import argparse
import base64
import calendar
import html
import hashlib
import json
import os
from pathlib import Path
import random
import re
import subprocess
import sys
import tempfile
import urllib.request
from datetime import date, datetime, timedelta, timezone
from xml.etree import ElementTree as ET

# EDIT THESE SETTINGS. Text is XML-escaped; links live outside the SVG images.
USERNAME = "parthsmart"
NAME = "Parth"
TAGLINE = "Student developer. Building useful apps and learning DSA."
MAIN, ACCENT, HIGHLIGHT = "#60A5FA", "#2DD4BF", "#FBBF24"
BG, INK, MUTED, LINE = "#161B22", "#F0F6FC", "#A7B4C4", "#30363D"
WEBSITE = ""  # Optional personal website, not a project URL.
PORTRAIT = ""  # Optional local .png or .jpg, embedded into the hero.
FEATURED = [
    ("Trendz-Tracker", "Trendz Tracker", "Building the next iteration of Trendz Tracker.", "JavaScript"),
    ("AINAVIGATOR", "AI Navigator", "From skill gaps to a personal learning roadmap.", "Career planning"),
    ("Mistake-Memo", "MistakeMemo", "Capture debugging lessons. Find the fix next time.", "Developer tools"),
]
TILES = [
    ("projects", "Projects", "Ideas into working apps", f"https://github.com/{USERNAME}?tab=repositories"),
    ("trendz", "Trendz Abacus", "Explore Trendz Tracker", f"https://github.com/{USERNAME}/Trendz-Tracker"),
    ("learning", "Learning", "C++ and DSA, day by day", f"https://github.com/{USERNAME}/CPP-Journey"),
]
ROOT = Path(__file__).resolve().parent
STATIC = os.environ.get("STATIC") == "1"
FONT_DIR = ROOT / "assets" / "fonts"
FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/lato/"
E = lambda value: html.escape(str(value), quote=True)


def download(url):
    req = urllib.request.Request(url, headers={"User-Agent": "profile-svg-cards"})
    with urllib.request.urlopen(req, timeout=45) as response:
        return response.read()


def prepare_fonts():
    """Download once. Commit these OFL-licensed files so CI needs no font network."""
    FONT_DIR.mkdir(parents=True, exist_ok=True)
    for filename in ("Lato-Regular.ttf", "Lato-Bold.ttf", "OFL.txt"):
        target = FONT_DIR / filename
        if not target.exists():
            target.write_bytes(download(FONT_URL + filename))


def font_css(text):
    from fontTools.ttLib import TTFont
    result = []
    for weight, style in ((400, "Regular"), (700, "Bold")):
        path = FONT_DIR / f"Lato-{style}.ttf"
        with TTFont(path) as font:
            names = {n.toUnicode() for n in font["name"].names if n.nameID in (1, 2, 4, 6, 16, 17)}
            subfamilies = {n.toUnicode().lower() for n in font["name"].names if n.nameID in (2, 17)}
            if (any("italic" in n.lower() or "oblique" in n.lower() for n in names)
                    or font["head"].macStyle & 2 or font["OS/2"].fsSelection & 1
                    or font["post"].italicAngle != 0):
                raise ValueError(f"Expected upright font, got {sorted(names)}")
            if style.lower() not in subfamilies or font["OS/2"].usWeightClass != weight:
                raise ValueError(f"Unexpected font style/weight: {sorted(names)}")
            missing = set(map(ord, text)) - set(font.getBestCmap()) - {10, 13}
            if missing:
                raise ValueError(f"Font lacks characters: {missing}")
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "subset.woff"
            chars = Path(folder) / "text.txt"
            chars.write_text(text, encoding="utf-8")
            # This is pyftsubset's module entry point; uses the current Python environment.
            subprocess.run([sys.executable, "-m", "fontTools.subset", str(path),
                            f"--text-file={chars}", "--flavor=woff", f"--output-file={output}",
                            "--no-recalc-timestamp"], check=True, capture_output=True)
            encoded = base64.b64encode(output.read_bytes()).decode("ascii")
        result.append(f"@font-face{{font-family:Card;src:url(data:font/woff;base64,{encoded}) format('woff');font-weight:{weight};font-style:normal}}")
    return "\n".join(result)


def window(end):
    month = end.year * 12 + end.month - 1 - 11
    return date(month // 12, month % 12 + 1, 1)


def validate(data):
    if data.get("username") != USERNAME:
        raise ValueError("JSON username does not match USERNAME")
    start, end = date.fromisoformat(data["start"]), date.fromisoformat(data["end"])
    if start != window(end):
        raise ValueError("Expected current calendar month plus previous 11 months")
    rows = data["days"]
    expected = [str(start + timedelta(days=i)) for i in range((end-start).days+1)]
    if [r["date"] for r in rows] != expected:
        raise ValueError("Contribution dates must be sorted, complete and unique")
    if any(type(r["count"]) is not int or r["count"] < 0 for r in rows):
        raise ValueError("Contribution counts must be nonnegative integers")
    return data


def refresh(path):
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise ValueError("Set GH_TOKEN, or run the supplied GitHub Action")
    now = datetime.now(timezone.utc)
    end, start = now.date(), window(now.date())
    query = """query($login:String!,$from:DateTime!,$to:DateTime!){
      user(login:$login){contributionsCollection(from:$from,to:$to){
        contributionCalendar{weeks{contributionDays{date contributionCount}}}
      }}}
    """
    payload = {"query": query, "variables": {"login": USERNAME,
        "from": str(start)+"T00:00:00Z", "to": now.isoformat()}}
    req = urllib.request.Request("https://api.github.com/graphql",
        data=json.dumps(payload).encode(), headers={"Authorization": f"Bearer {token}",
        "Content-Type": "application/json", "User-Agent": "profile-svg-cards"})
    with urllib.request.urlopen(req, timeout=45) as response:
        body = json.load(response)
    if body.get("errors") or not body.get("data", {}).get("user"):
        raise ValueError("GitHub returned an error or unknown user; old JSON is unchanged")
    weeks = body["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    rows = sorted(({"date": d["date"], "count": d["contributionCount"]}
        for w in weeks for d in w["contributionDays"] if str(start) <= d["date"] <= str(end)),
        key=lambda d: d["date"])
    data = validate({"username": USERNAME, "start": str(start), "end": str(end),
                     "demo": False, "days": rows})
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2)+"\n", encoding="utf-8")
    temporary.replace(path)  # Never replace good data with a partial/error response.


def demo_data():
    end = date(2026, 11, 19)
    start, rng = window(end), random.Random(24)
    rows = []
    for i in range((end-start).days+1):
        day = start + timedelta(days=i)
        count = rng.choice([0, 0, 0, 1, 2, 3, 5, 8, 13]) if day.month >= 6 else 0
        rows.append({"date": str(day), "count": count})
    return {"username": USERNAME, "start": str(start), "end": str(end), "demo": True, "days": rows}


def stats(data):
    rows = data["days"]
    counts = [r["count"] for r in rows]
    # Today may still be in progress. A zero today does not break yesterday's streak.
    index = len(counts)-1 if counts[-1] else len(counts)-2
    streak = 0
    while index >= 0 and counts[index] > 0:
        streak += 1
        index -= 1
    busiest = max(rows, key=lambda d: d["count"])  # Earliest date wins ties.
    return sum(counts), sum(c > 0 for c in counts), streak, busiest


def text(x, y, value, size=18, weight=400, fill=INK, extra=""):
    return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" {extra}>{E(value)}</text>'


def rect(x, y, w, h, fill, radius=0, extra=""):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" {extra}/>'


def write_card(out, name, width, height, body, delay, title):
    # Only CSS animations: unlike SMIL, CSS can be fully disabled by a media query.
    motion = "" if STATIC else f"""
      @keyframes enter{{from{{opacity:0;transform:translateY(7px)}}to{{opacity:1;transform:translateY(0)}}}}
      @keyframes rise{{from{{transform:scaleY(0)}}to{{transform:scaleY(1)}}}}
      @media (prefers-reduced-motion:no-preference){{
        .content{{animation:enter .55s ease-out {delay}s backwards}}
        .bar{{transform-box:fill-box;transform-origin:center bottom;
          animation:rise .65s ease-out calc({delay}s + var(--i,0) * .035s) backwards}}
      }}
      @media (prefers-reduced-motion:reduce){{*{{animation:none!important;transition:none!important}}}}
    """
    visible_text = "".join(ET.fromstring(f"<g>{body}</g>").itertext())
    css = font_css(visible_text + title)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title">
<title id="title">{E(title)}</title>
<style>{css}\ntext{{font-family:Card,Arial,sans-serif}}{motion}</style>
{rect(.5,.5,width-1,height-1,BG,20,extra=f'stroke="{LINE}"')}
<g class="content">{body}</g></svg>'''
    ET.fromstring(svg)
    (out / f"{name}.svg").write_text(svg, encoding="utf-8")


def render(data, out):
    validate(data)
    out.mkdir(parents=True, exist_ok=True)
    total, active, streak, busy = stats(data)
    demo = "DEMO DATA / " if data.get("demo") else ""
    period = f'{data["start"]} to {data["end"]} (UTC)'
    card = lambda name,w,h,body,delay,title: write_card(out,name,w,h,body,delay,title)
    hero = text(36,43,"PARTH / BUILDER'S NOTEBOOK",12,700,MUTED)
    hero += text(34,119,f"Hi, I'm {NAME}.",58,700)
    hero += text(36,164,TAGLINE,19)
    hero += rect(36,197,34,4,MAIN,2)+rect(76,197,18,4,ACCENT,2)+rect(100,197,10,4,HIGHLIGHT,2)
    hero += text(126,204,f"@{USERNAME}   /   Build. Learn. Repeat.",14,400,MUTED)
    if PORTRAIT:
        p = ROOT / PORTRAIT
        mime = {".png":"image/png", ".jpg":"image/jpeg", ".jpeg":"image/jpeg"}[p.suffix.lower()]
        uri = base64.b64encode(p.read_bytes()).decode()
        hero += f'<image x="700" y="32" width="84" height="84" href="data:{mime};base64,{uri}" preserveAspectRatio="xMidYMid meet"/>'
    else:
        hero += rect(716,34,64,64,MAIN,16)+text(748,77,"P",34,700,BG,'text-anchor="middle"')
    card("hero",840,238,hero,0,f"{NAME}. {TAGLINE}")

    graph = text(32,39,"The daily practice",24,700)
    graph += text(808,38,f"{total:,} contributions",15,700,MAIN,'text-anchor="end"')
    graph += text(32,64,demo+period,12,400,MUTED)
    start = date.fromisoformat(data["start"])
    sunday = start - timedelta(days=(start.weekday()+1)%7)
    maxcount = max(d["count"] for d in data["days"]) or 1
    for d in data["days"]:
        day = date.fromisoformat(d["date"])
        column, row = divmod((day-sunday).days,7)
        if day.day == 1:
            graph += text(46+column*14,91,day.strftime("%b"),10,400,MUTED)
        opacity = .25 + .75*d["count"]/maxcount
        graph += rect(46+column*14,103+row*14,10,10,MAIN if d["count"] else LINE,2,
                      f'fill-opacity="{opacity if d["count"] else 1:.3f}"')
    for r,label in ((1,"M"),(3,"W"),(5,"F")):
        graph += text(26,111+r*14,label,9,400,MUTED)
    graph += text(32,224,"One square, one day. Every small step counts.",13,400,MUTED)
    graph += text(651,224,"Less",11,400,MUTED)
    for i in range(5):
        graph += rect(681+i*17,214,11,11,MAIN if i else LINE,2,f'fill-opacity="{i/4 if i else 1}"')
    graph += text(773,224,"More",11,400,MUTED)
    card("contributions",840,246,graph,.6,f"{demo}{total} contributions. {period}")

    months = {}
    for d in data["days"]:
        key = d["date"][:7]
        months[key] = months.get(key,0)+d["count"]
    peak = max(months.values()) or 1
    bars = text(32,41,"A little progress, every month",24,700)
    bars += text(32,66,demo+"12 calendar months / current month is partial",12,400,MUTED)
    for i,(month,count) in enumerate(months.items()):
        x,h = 48+i*63,round(count/peak*105,2)
        bars += rect(x,200-h,34,h,MAIN,4,f'class="bar" style="--i:{i}"')
        bars += text(x+17,190-h,count,11,700,MUTED,'text-anchor="middle"')
        bars += text(x+17,221,calendar.month_abbr[int(month[-2:])],12,400,MUTED,'text-anchor="middle"')
    bars += rect(32,242,776,1,LINE)
    busiest = f'{busy["date"]} / {busy["count"]}' if busy["count"] else "No activity yet"
    for x,value,label in ((32,f"{streak} days","CURRENT STREAK"),(265,str(active),"ACTIVE DAYS"),(498,busiest,"BUSIEST DAY / COUNT")):
        bars += text(x,277,value,23,700)+text(x,301,label,11,700,MUTED)
    bars += text(32,328,"Streak allows an unfinished today; all statistics use the displayed window.",11,400,MUTED)
    card("monthly",840,349,bars,1.2,f"{demo}Monthly contributions. {streak} day streak; {active} active days; busiest {busiest}.")
    for i,(slug,title,subtitle,url) in enumerate(TILES):
        b = text(24,34,f"0{i+1} / EXPLORE",11,700,MUTED)
        b += text(24,76,title,25,700)+text(24,104,subtitle,13,400,MUTED)
        b += rect(24,127,28,3,(MAIN,ACCENT,HIGHLIGHT)[i],1)
        b += text(245,132,"↗",22,400,MAIN,'text-anchor="end"')
        card("tile-"+slug,273,154,b,1.95+i*.12,title+": "+subtitle)
    for i,(repo,title,description,tag) in enumerate(FEATURED):
        b = text(32,34,f"0{i+1} / FEATURED PROJECT",11,700,MUTED)
        b += text(32,76,title,30,700)+text(32,109,description,18)
        b += text(32,145,tag+"   /   "+repo,13,400,MUTED)
        b += text(791,81,"↗",30,400,(MAIN,ACCENT,HIGHLIGHT)[i],'text-anchor="end"')
        card(f"repo-{i+1}",840,174,b,2.5+i*.35,title+". "+description)


def write_readme(out, demo=False):
    prefix = out.relative_to(ROOT).as_posix()
    def img(file,alt,width="100%"):
        version = hashlib.sha256((out / f"{file}.svg").read_bytes()).hexdigest()[:12]
        return f'<img src="{prefix}/{file}.svg?v={version}" width="{width}" alt="{E(alt)}">'
    rows = ["<!-- Generated by render_cards.py. Edit its configuration, then regenerate. -->"]
    if demo:
        rows += ["**Preview: contribution statistics below are demo data. Run the daily workflow for real data.**", ""]
    rows += [img("hero",f"{NAME} — {TAGLINE}"),"",img("contributions","Contribution calendar"),"",img("monthly","Monthly contributions and activity statistics"),"",'<p align="center">']
    for slug,title,subtitle,url in TILES:
        rows += [f'  <a href="{E(url)}">{img("tile-"+slug,title,"32.5%")}</a>']
    rows += ["</p>", ""]
    for i,(repo,title,description,tag) in enumerate(FEATURED):
        rows += [f'<a href="https://github.com/{USERNAME}/{E(repo)}">{img(f"repo-{i+1}",title+": "+description)}</a>',""]
    if WEBSITE:
        rows += [f"[Visit my website]({WEBSITE})", ""]
    if out == ROOT / "cards":
        (ROOT / "README.md").write_text("\n".join(rows)+"\n",encoding="utf-8")
    # Preview deliberately uses img tags, the same embedding context as GitHub.
    preview = '\n'.join(r for r in rows if r.startswith("<") or r.startswith("  <"))
    (out / "preview.html").write_text('<!doctype html><meta charset="utf-8"><title>Parth | Profile cards</title><style>body{max-width:840px;margin:32px auto;padding:0 16px;background:#0d1117;color:#f0f6fc}img{vertical-align:top;margin-bottom:12px}p{margin:0}</style>'+preview.replace(prefix+"/", ""),encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Fetch real data, save JSON, then exit")
    parser.add_argument("--demo", action="store_true", help="Explicitly generate labeled demo data")
    parser.add_argument("--data", type=Path, default=ROOT/"data"/"contributions.json")
    parser.add_argument("--out", type=Path, default=ROOT/"cards")
    args = parser.parse_args()
    if args.refresh:
        if args.demo:
            parser.error("--refresh and --demo cannot be combined")
        refresh(args.data)
        return
    prepare_fonts()
    data = demo_data() if args.demo else json.loads(args.data.read_text(encoding="utf-8"))
    out = args.out.resolve()
    out.relative_to(ROOT)  # Keep generated links and outputs within this package.
    render(data,out)
    write_readme(out,data.get("demo",False))
    print(f"Rendered 9 {'static' if STATIC else 'animated'} cards in {out}")


if __name__ == "__main__":
    main()
