"""Meme sounds from myinstants.com -> downloaded into assets/sfx and indexed (so renders can use them offline).

  python sfx.py search "vine boom" [--limit 8]          # list candidates (title | slug-url)
  python sfx.py get "vine boom" --name vine-boom --moods shocked --themes reveal [--pick 0]
  python sfx.py get --url https://www.myinstants.com/media/sounds/x.mp3 --name x --moods ...

The myinstants MCP (npx myinstants-mcp) is for *previewing* sounds through speakers; this script is for
*using* them in edits. Check assets first: python assets.py find --type sfx --mood shocked
"""
import argparse, html, os, re, sys, urllib.parse
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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("search"); s.add_argument("q"); s.add_argument("--limit", type=int, default=8)
    g = sp.add_parser("get"); g.add_argument("q", nargs="?"); g.add_argument("--url"); g.add_argument("--pick", type=int, default=0)
    g.add_argument("--name"); g.add_argument("--moods", default=""); g.add_argument("--themes", default=""); g.add_argument("--rating", default="clean")
    a = ap.parse_args()
    try:
        if a.cmd == "search":
            for i, r in enumerate(search(a.q, a.limit)):
                print(f"{i} | {r['title']} | {r['url']}")
            return
        if a.url:
            url, title = a.url, os.path.basename(a.url)
        else:
            res = search(a.q, a.pick + 1)
            if len(res) <= a.pick:
                die("no results", q=a.q)
            url, title = res[a.pick]["url"], res[a.pick]["title"]
        name = slug(a.name or title)
        rel = f"sfx/{name}.mp3"
        dst = os.path.join(ASSETS, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        data = http_get(url)
        if len(data) < 1000:
            die("download too small", url=url)
        with open(dst, "wb") as f:
            f.write(data)
        dur = round(ffprobe(dst)["dur"], 2)
        idx = load_index()
        aid = f"sfx:{name}"
        idx["assets"] = [x for x in idx["assets"] if x["id"] != aid]
        idx["assets"].append({"id": aid, "type": "sfx", "path": rel, "moods": [m for m in a.moods.split(",") if m],
                              "themes": [t for t in a.themes.split(",") if t], "text": title, "rating": a.rating, "dur": dur, "source": url})
        save_index(idx)
        out({"ok": True, "id": aid, "dur": dur, "kb": len(data) // 1024})
    except Exception as e:
        die(str(e)[:300])


if __name__ == "__main__":
    main()
