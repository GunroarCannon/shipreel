"""Reaction GIFs (as MP4, for overlays) from GIPHY / KLIPY / Tenor -> assets/gifs + index.

  python gif.py search "surprised pikachu" [--provider giphy] [--limit 6]
  python gif.py get "surprised pikachu" --name surprised-pikachu --moods shocked [--pick 0] [--sticker]

Needs ONE key in env: GIPHY_API_KEY (developers.giphy.com, free) | KLIPY_API_KEY (klipy.com/developers, free)
| TENOR_API_KEY (Google Cloud). Missing key -> exit 3 "NEED_ENV ..." -> buzz the user and ask them to paste it.
Keys are read from env only and never written anywhere by this script.
--sticker asks GIPHY for transparent stickers (downloads .webp/.gif with alpha; overlay with type "sticker").
"""
import argparse, json, os, sys, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ASSETS, http_get, out, die, slug, load_index, save_index, ffprobe


def provider_key(pref):
    order = [pref] if pref else ["giphy", "klipy", "tenor"]
    for p in order:
        k = os.environ.get(f"{p.upper()}_API_KEY")
        if k:
            return p, k
    die("NEED_ENV GIPHY_API_KEY", code=3, why="GIF search needs a free API key (GIPHY, KLIPY or TENOR)")


def search(q, provider=None, limit=6, sticker=False):
    p, key = provider_key(provider)
    qq = urllib.parse.quote_plus(q)
    res = []
    if p == "giphy":
        kind = "stickers" if sticker else "gifs"
        j = json.loads(http_get(f"https://api.giphy.com/v1/{kind}/search?api_key={key}&q={qq}&limit={limit}&rating=pg-13"))
        for g in j.get("data", []):
            im = g["images"]["original"]
            url = (im.get("webp") if sticker else im.get("mp4")) or im.get("url")
            res.append({"title": g.get("title") or g.get("slug"), "url": url, "ext": ".webp" if sticker else ".mp4"})
    elif p == "klipy":
        j = json.loads(http_get(f"https://api.klipy.com/api/v1/{key}/{'stickers' if sticker else 'gifs'}/search?q={qq}&per_page={limit}"))
        for g in (j.get("data", {}) or {}).get("data", []):
            f = g.get("file", {}).get("hd") or g.get("file", {}).get("md") or {}
            m = f.get("mp4") or f.get("webp") or f.get("gif") or {}
            if m.get("url"):
                res.append({"title": g.get("title") or g.get("slug"), "url": m["url"], "ext": os.path.splitext(m["url"])[1] or ".mp4"})
    else:
        j = json.loads(http_get(f"https://tenor.googleapis.com/v2/search?key={key}&q={qq}&limit={limit}&media_filter=mp4,webp_transparent"))
        for g in j.get("results", []):
            mf = g.get("media_formats", {})
            m = (mf.get("webp_transparent") if sticker else mf.get("mp4")) or mf.get("mp4") or {}
            if m.get("url"):
                res.append({"title": g.get("content_description", ""), "url": m["url"], "ext": os.path.splitext(m["url"])[1] or ".mp4"})
    return res[:limit]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    for n in ("search", "get"):
        p = sp.add_parser(n); p.add_argument("q"); p.add_argument("--provider", choices=["giphy", "klipy", "tenor"])
        p.add_argument("--limit", type=int, default=6); p.add_argument("--sticker", action="store_true")
        if n == "get":
            p.add_argument("--pick", type=int, default=0); p.add_argument("--name"); p.add_argument("--moods", default=""); p.add_argument("--themes", default="")
    a = ap.parse_args()
    try:
        res = search(a.q, a.provider, max(a.limit, getattr(a, "pick", 0) + 1), a.sticker)
        if a.cmd == "search":
            for i, r in enumerate(res):
                print(f"{i} | {r['title'][:70]}")
            return
        if len(res) <= a.pick:
            die("no results", q=a.q)
        r = res[a.pick]
        name = slug(a.name or a.q)
        rel = f"gifs/{name}{r['ext'].split('?')[0]}"
        dst = os.path.join(ASSETS, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "wb") as f:
            f.write(http_get(r["url"]))
        idx = load_index(); aid = f"gif:{name}"
        idx["assets"] = [x for x in idx["assets"] if x["id"] != aid]
        e = {"id": aid, "type": "gif", "path": rel, "moods": [m for m in a.moods.split(",") if m], "themes": [t for t in a.themes.split(",") if t],
             "text": r["title"][:80], "rating": "clean", "sticker": a.sticker}
        try:
            e["dur"] = round(ffprobe(dst)["dur"], 2)
        except Exception:
            pass
        idx["assets"].append(e); save_index(idx)
        out({"ok": True, "id": aid, "path": rel})
    except SystemExit:
        raise
    except Exception as e:
        die(str(e)[:300])


if __name__ == "__main__":
    main()
