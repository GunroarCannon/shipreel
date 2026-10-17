"""Meme sounds from myinstants.com -> downloaded into assets/sfx and indexed (so renders can use them offline).

  python sfx.py search "vine boom" [--limit 8]          # list candidates (title | slug-url)
  python sfx.py get "vine boom" --name vine-boom --moods shocked --themes reveal [--pick 0]
  python sfx.py get --url https://www.myinstants.com/media/sounds/x.mp3 --name x --moods ...
  python sfx.py get "sneaky snitch" --kind music --name sneaky-snitch --moods sus --themes bug   # meme *music* -> assets/music (background bed)
  python sfx.py seed-music [--only name1,name2]         # download the curated meme-music starter set (see SEED_MUSIC)

The myinstants MCP (npx myinstants-mcp) is for *previewing* sounds through speakers; this script is for
*using* them in edits. Check assets first: python assets.py find --type sfx --mood shocked
"""
import argparse, html, json, os, re, sys, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ASSETS, http_get, out, die, slug, load_index, save_index, ffprobe

BASE = "https://www.myinstants.com"


def search(q, limit=8):
    page = http_get(f"{BASE}/en/search/?name={urllib.parse.quote_plus(q)}").decode("utf-8", "replace")
    mp3s = re.findall(r"play\('([^']+\.mp3)'", page)
    titles = [html.unescape(t).strip() for t in re.findall(r'class="instant-link[^"]*"[^>]*>([^<]+)<', page)]
    res = []
    for i, m in enumerate(mp3s):
        res.append({"title": titles[i] if i < len(titles) else os.path.basename(m), "url": BASE + m})
    return res[:limit]


# name | myinstants query | pick | moods | themes. Background beds for TikToks; all are copyrighted songs/themes (see references/music-audio.md).
SEED_MUSIC = [
    ("sneaky-snitch", "sneaky snitch", 0, "sus,nervous", "bug,weird-behavior,plot-twist"),
    ("crab-rave", "crab rave", 0, "hype,chaos", "success,flex,showcase"),
    ("careless-whisper", "careless whisper", 0, "smug,sad", "fail,ending,cope"),
    ("megalovania", "megalovania", 0, "hype,determined", "escalation,boss,showcase"),
    ("wii-shop-channel", "wii shop channel", 0, "chill,nostalgic", "coding,progress,devlog"),
    ("mii-channel", "mii channel", 0, "chill,nostalgic,wholesome", "solo-dev,showcase,calm"),
    ("rickroll", "never gonna give you up", 2, "troll,smug", "punchline,reveal"),
    ("running-in-the-90s", "running in the 90s", 0, "hype,determined", "deadline,grind,escalation"),
    ("gas-gas-gas", "gas gas gas", 0, "hype,chaos", "speed,escalation,showcase"),
    ("benny-hill", "benny hill", 3, "chaos,laughing", "bug,funny,chase"),
    ("elevator-music", "elevator music", 0, "chill,tired,awkward", "waiting,loading,docs"),
    ("mission-impossible", "mission impossible theme", 2, "determined,nervous", "heist,big-brain,showcase"),
    ("pink-panther", "pink panther", 0, "sus,smug", "weird-behavior,sneaky"),
    ("phonk-yara", "phonk", 1, "hype,angry", "rage,flex,showcase"),
    ("cool-chill-lofi", "lofi", 2, "chill,tired", "late-night,coding,burnout"),
    ("minecraft-theme", "minecraft theme", 0, "nostalgic,wholesome", "nostalgia,old-version,sandbox"),
    ("curb-your-enthusiasm", "curb your enthusiasm", 0, "awkward,cringe", "fail,mistake,punchline"),
    ("hampster-dance", "hampster dance", 0, "happy,laughing,chaos", "funny,celebration"),
    ("nyan-cat", "nyan cat", 0, "happy,chaos", "funny,retro"),
]


def fetch(url, name, kind, title, moods, themes, rating="clean"):
    rel = f"{'music' if kind == 'music' else 'sfx'}/{name}.mp3"
    dst = os.path.join(ASSETS, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    data = http_get(url)
    if len(data) < 1000:
        die("download too small", url=url)
    with open(dst, "wb") as f:
        f.write(data)
    dur = round(ffprobe(dst)["dur"], 2)
    idx = load_index()
    aid = f"{kind}:{name}"
    idx["assets"] = [x for x in idx["assets"] if x["id"] != aid]
    entry = {"id": aid, "type": kind, "path": rel, "moods": [m for m in moods.split(",") if m],
             "themes": [t for t in themes.split(",") if t], "text": title, "rating": rating, "dur": dur, "source": url}
    if kind == "music":
        entry["license"] = "meme/copyrighted (myinstants): fine as a quiet TikTok bed, Content-ID risk on YouTube"
    idx["assets"].append(entry)
    save_index(idx)
    return {"ok": True, "id": aid, "dur": dur, "kb": len(data) // 1024}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("search"); s.add_argument("q"); s.add_argument("--limit", type=int, default=8)
    g = sp.add_parser("get"); g.add_argument("q", nargs="?"); g.add_argument("--url"); g.add_argument("--pick", type=int, default=0)
    g.add_argument("--name"); g.add_argument("--moods", default=""); g.add_argument("--themes", default=""); g.add_argument("--rating", default="clean")
    g.add_argument("--kind", choices=["sfx", "music"], default="sfx")
    m = sp.add_parser("seed-music"); m.add_argument("--only", default="")
    a = ap.parse_args()
    try:
        if a.cmd == "search":
            for i, r in enumerate(search(a.q, a.limit)):
                print(f"{i} | {r['title']} | {r['url']}")
            return
        if a.cmd == "seed-music":
            only = {x for x in a.only.split(",") if x}
            for name, q, pick, moods, themes in SEED_MUSIC:
                if only and name not in only:
                    continue
                try:
                    res = search(q, pick + 1)
                    if len(res) <= pick:
                        print(json.dumps({"ok": False, "id": f"music:{name}", "err": "no results"})); continue
                    print(json.dumps(fetch(res[pick]["url"], name, "music", res[pick]["title"], moods, themes)))
                except Exception as e:
                    print(json.dumps({"ok": False, "id": f"music:{name}", "err": str(e)[:120]}))
            return
        if a.url:
            url, title = a.url, os.path.basename(a.url)
        else:
            res = search(a.q, a.pick + 1)
            if len(res) <= a.pick:
                die("no results", q=a.q)
            url, title = res[a.pick]["url"], res[a.pick]["title"]
        out(fetch(url, slug(a.name or title), a.kind, title, a.moods, a.themes, a.rating))
    except Exception as e:
        die(str(e)[:300])


if __name__ == "__main__":
    main()
