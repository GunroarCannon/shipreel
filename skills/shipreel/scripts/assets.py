"""Asset index tool. Query memes/sfx/music/gifs/overlays/fonts by mood, theme, name — returns a short list.

  python assets.py find --type sfx --mood shocked --limit 5
  python assets.py find --q "this is fine"          # text search over id/text/themes
  python assets.py get meme:this-is-fine-dog         # -> absolute path
  python assets.py add C:/x/new.png --type image --name smug-cat --moods smug --themes success
  python assets.py scan                              # files in assets/ not yet indexed (+ assets/inbox/)
  python assets.py sheet --type image --mood smug    # contact sheet jpg for a quick visual pick
  python assets.py vocab                             # moods/themes in use with counts
"""
import argparse, os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ASSETS, load_index, save_index, out, die, slug, run, wpath, resolve_asset

TYPE_DIR = {"image": "memes/reaction", "sfx": "sfx", "music": "music", "gif": "gifs", "font": "fonts", "overlay": "overlays", "video": "gifs"}
PREFIX = {"image": "meme", "sfx": "sfx", "music": "music", "gif": "gif", "font": "font", "overlay": "overlay", "video": "gif"}
MEDIA_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".mp3", ".wav", ".ogg", ".m4a", ".mp4", ".webm", ".ttf", ".otf"}


def matches(a, args):
    if args.type and a["type"] != args.type:
        return False
    if not args.all_ratings and a.get("rating", "clean") == "nsfw":
        return False
    if args.clean and a.get("rating", "clean") != "clean":
        return False
    for m in args.mood or []:
        if m not in a.get("moods", []):
            return False
    for t in args.theme or []:
        if t not in a.get("themes", []):
            return False
    if args.q:
        hay = " ".join([a["id"], a.get("text", ""), " ".join(a.get("themes", [])), " ".join(a.get("moods", []))]).lower()
        if not all(w in hay for w in args.q.lower().split()):
            return False
    return True


def cmd_find(args):
    rows = [a for a in load_index()["assets"] if matches(a, args)]
    for a in rows[: args.limit]:
        extra = f" | {a['dur']}s" if a.get("dur") else ""
        txt = f" | \"{a['text']}\"" if a.get("text") else ""
        print(f"{a['id']} | {','.join(a.get('moods', []))} | {','.join(a.get('themes', []))}{extra}{txt}")
    if len(rows) > args.limit:
        print(f"... {len(rows) - args.limit} more (raise --limit or narrow)")
    if not rows:
        print("none")


def cmd_get(args):
    print(resolve_asset(args.id))


def cmd_add(args):
    if not os.path.exists(args.file):
        die("file not found")
    ext = os.path.splitext(args.file)[1].lower()
    name = slug(args.name or os.path.splitext(os.path.basename(args.file))[0])
    sub = args.dir or TYPE_DIR[args.type]
    rel = f"{sub}/{name}{ext}"
    dst = os.path.join(ASSETS, rel)
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    if os.path.abspath(args.file) != os.path.abspath(dst):
        (shutil.move if args.move else shutil.copy2)(args.file, dst)
    idx = load_index()
    aid = f"{PREFIX[args.type]}:{name}"
    idx["assets"] = [a for a in idx["assets"] if a["id"] != aid]
    entry = {"id": aid, "type": args.type, "path": rel, "moods": (args.moods or "").split(","), "themes": (args.themes or "").split(","),
             "text": args.text or "", "rating": args.rating}
    entry["moods"] = [m for m in entry["moods"] if m]; entry["themes"] = [t for t in entry["themes"] if t]
    if args.source:
        entry["source"] = args.source
    if args.type in ("sfx", "music", "gif", "video"):
        try:
            from common import ffprobe
            entry["dur"] = round(ffprobe(dst)["dur"], 2)
        except Exception:
            pass
    idx["assets"].append(entry)
    save_index(idx)
    out({"ok": True, "id": aid, "path": rel})


def cmd_scan(args):
    known = {a["path"].replace("\\", "/") for a in load_index()["assets"]}
    new = []
    for root, _, files in os.walk(ASSETS):
        for f in files:
            if os.path.splitext(f)[1].lower() not in MEDIA_EXT:
                continue
            rel = os.path.relpath(os.path.join(root, f), ASSETS).replace("\\", "/")
            if rel.startswith(("overlays/", "fonts/")) or rel in known:
                continue
            new.append(rel)
    for r in new:
        print(r)
    print(f"{len(new)} unindexed. Tag them: assets.py add <file> --type ... --move  (view many at once: assets.py sheet --dir inbox)")


def cmd_sheet(args):
    """Tile up to 20 images into one jpg so an agent can eyeball/tag them for ~1 image worth of tokens."""
    if args.dir:
        d = os.path.join(ASSETS, args.dir)
        files = [os.path.join(d, f) for f in sorted(os.listdir(d)) if os.path.splitext(f)[1].lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif"}]
        labels = [os.path.basename(f) for f in files]
    else:
        rows = [a for a in load_index()["assets"] if a["type"] == "image" and matches(a, args)]
        files = [os.path.join(ASSETS, a["path"]) for a in rows]
        labels = [a["id"] for a in rows]
    files, labels = files[args.offset: args.offset + 20], labels[args.offset: args.offset + 20]
    if not files:
        die("no images")
    cols, cell = 5, 240
    inputs, parts = [], []
    for i, f in enumerate(files):
        inputs += ["-i", f]
        parts.append(f"[{i}:v]scale={cell}:{cell}:force_original_aspect_ratio=decrease,pad={cell}:{cell}:(ow-iw)/2:(oh-ih)/2:color=gray,"
                     f"drawtext=text='{i + args.offset}':x=4:y=4:fontsize=26:fontcolor=white:box=1:boxcolor=red,format=rgb24[c{i}]")
    n = len(files)
    rows_n = (n + cols - 1) // cols
    layout = "|".join(f"{(i % cols) * cell}_{(i // cols) * cell}" for i in range(n))
    fc = ";".join(parts) + ";" + "".join(f"[c{i}]" for i in range(n)) + f"xstack=inputs={n}:layout={layout}:fill=gray[o]" if n > 1 else ";".join(parts).replace(f"[c0]", "[o]")
    dst = args.out or wpath("temp", "_sheets", f"assets_{args.offset}.jpg")
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", fc, "-map", "[o]", "-frames:v", "1", "-q:v", "4", dst])
    for i, l in enumerate(labels):
        print(f"{i + args.offset}: {l}")
    out({"sheet": dst, "rows": rows_n})


def cmd_vocab(args):
    from collections import Counter
    m, t = Counter(), Counter()
    for a in load_index()["assets"]:
        if args.type and a["type"] != args.type:
            continue
        m.update(a.get("moods", [])); t.update(a.get("themes", []))
    print("moods: " + " ".join(f"{k}:{v}" for k, v in m.most_common()))
    print("themes: " + " ".join(f"{k}:{v}" for k, v in t.most_common(60)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    def filt(p):
        p.add_argument("--type", choices=list(TYPE_DIR)); p.add_argument("--mood", action="append"); p.add_argument("--theme", action="append")
        p.add_argument("--q"); p.add_argument("--clean", action="store_true", help="only rating=clean")
        p.add_argument("--all-ratings", action="store_true", help="include nsfw-flagged"); p.add_argument("--limit", type=int, default=12)
    p = sp.add_parser("find"); filt(p); p.set_defaults(f=cmd_find)
    p = sp.add_parser("get"); p.add_argument("id"); p.set_defaults(f=cmd_get)
    p = sp.add_parser("add"); p.add_argument("file"); p.add_argument("--type", required=True, choices=list(TYPE_DIR))
    p.add_argument("--name"); p.add_argument("--moods"); p.add_argument("--themes"); p.add_argument("--text"); p.add_argument("--dir")
    p.add_argument("--rating", default="clean", choices=["clean", "mild", "nsfw"]); p.add_argument("--source"); p.add_argument("--move", action="store_true")
    p.set_defaults(f=cmd_add)
    p = sp.add_parser("scan"); p.set_defaults(f=cmd_scan)
    p = sp.add_parser("sheet"); filt(p); p.add_argument("--dir"); p.add_argument("--offset", type=int, default=0); p.add_argument("--out"); p.set_defaults(f=cmd_sheet)
    p = sp.add_parser("vocab"); p.add_argument("--type"); p.set_defaults(f=cmd_vocab)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
