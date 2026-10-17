"""Shared helpers for shipreel scripts. Stdlib only (plus ffmpeg/ffprobe on PATH)."""
import hashlib, json, os, re, shutil, subprocess, sys, time

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(SKILL_DIR, "assets")
INDEX = os.path.join(ASSETS, "index.json")
FONTS = os.path.join(ASSETS, "fonts")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"}

# Make Windows consoles accept unicode output (titles with emoji etc.)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def workspace():
    """Where output/ and temp/ live. SHIPREEL_HOME env > config > cwd."""
    return os.path.abspath(os.environ.get("SHIPREEL_HOME") or os.getcwd())


def wpath(*parts):
    return os.path.join(workspace(), *parts)


def out(obj):
    """Terse single-line JSON to stdout (cheap for the agent to read)."""
    print(json.dumps(obj, ensure_ascii=False, separators=(",", ":")))


def die(msg, code=1, **extra):
    out(dict(ok=False, error=msg, **extra))
    sys.exit(code)


def need_env(name, why):
    """Exit code 3 = the agent must ask the user for an env value (see references/failure-protocol.md)."""
    v = os.environ.get(name)
    if not v:
        die(f"NEED_ENV {name}", code=3, why=why)
    return v


def slug(s, maxlen=60):
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.lower()).strip("-")
    return s[:maxlen].strip("-") or "x"


def safe_title(s):
    """Video filename part: keep words, swap spaces for underscores, drop chars illegal on Windows/macOS."""
    s = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "", s)
    s = re.sub(r"\s+", "_", s.strip())
    return s.strip("._")


def video_name(title, tags=(), series=None, part=None, maxlen=150):
    """<title>_#tag1_#tag2  or  <series>-part-<n>_<title>_#tags  (underscores; dashes only for special markers)."""
    base = safe_title(title)
    if series:
        base = f"{safe_title(series)}-part-{part}_{base}"
    tagstr = "".join(f"_#{re.sub(r'[^A-Za-z0-9_]', '', t.lstrip('#'))}" for t in tags if t)
    name = base[: max(20, maxlen - len(tagstr))] + tagstr
    return name


def sha(obj, n=10):
    return hashlib.sha1(json.dumps(obj, sort_keys=True).encode()).hexdigest()[:n]


def run(cmd, check=True, quiet=True, timeout=None):
    """Run a command; on failure return the last stderr lines only (token-cheap)."""
    if os.environ.get("SHIPREEL_DEBUG"):
        print("[cmd] " + subprocess.list2cmdline([str(c) for c in cmd]), file=sys.stderr)
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    if check and p.returncode != 0:
        tail = "\n".join((p.stderr or p.stdout or "").strip().splitlines()[-12:])
        raise RuntimeError(f"cmd failed ({p.returncode}): {' '.join(map(str, cmd[:6]))}...\n{tail}")
    return p


def ffprobe(path):
    p = run(["ffprobe", "-v", "error", "-show_entries",
             "format=duration:stream=index,codec_type,width,height,r_frame_rate,sample_rate,channels",
             "-of", "json", path])
    j = json.loads(p.stdout)
    info = {"dur": round(float(j.get("format", {}).get("duration", 0) or 0), 3), "video": None, "audio": None}
    for s in j.get("streams", []):
        if s.get("codec_type") == "video" and not info["video"]:
            num, den = (s.get("r_frame_rate") or "0/1").split("/")
            info["video"] = {"w": s.get("width"), "h": s.get("height"), "fps": round(float(num) / float(den or 1), 2) if float(den or 1) else 0}
        if s.get("codec_type") == "audio" and not info["audio"]:
            info["audio"] = {"sr": int(s.get("sample_rate") or 0), "ch": s.get("channels")}
    return info


LOCAL_INDEX = os.path.join(ASSETS, "index.local.json")  # gitignored: assets that live only on this machine (e.g. a music folder the user added)


def _read_index(path):
    if not os.path.exists(path):
        return {"version": 1, "assets": []}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_index():
    """Shared index + this machine's local index. Entries from the local file carry "local": true."""
    idx = _read_index(INDEX)
    have = {a["id"] for a in idx["assets"]}
    for a in _read_index(LOCAL_INDEX)["assets"]:
        if a["id"] not in have:
            idx["assets"].append({**a, "local": True})
    return idx


def save_index(idx):
    shared = sorted((a for a in idx["assets"] if not a.get("local")), key=lambda a: a["id"])
    local = sorted((a for a in idx["assets"] if a.get("local")), key=lambda a: a["id"])
    for path, rows in ((INDEX, shared), (LOCAL_INDEX, local)):
        if not rows and path == LOCAL_INDEX and not os.path.exists(path):
            continue
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({**{k: v for k, v in idx.items() if k != "assets"}, "assets": rows}, f, indent=1, ensure_ascii=False)
        os.replace(tmp, path)


def resolve_asset(ref):
    """'meme:this-is-fine-dog' / 'sfx:vine-boom' / 'overlay:arrow-red' / 'font:..' / plain path -> absolute path."""
    if not ref:
        return None
    if os.path.exists(ref):
        return os.path.abspath(ref)
    if ":" in ref and not re.match(r"^[A-Za-z]:[\\/]", ref):
        kind, name = ref.split(":", 1)
        if kind == "overlay":
            p = os.path.join(ASSETS, "overlays", name + ".png")
            if os.path.exists(p):
                return p
        for a in load_index()["assets"]:
            if a["id"] == ref:
                return os.path.join(ASSETS, a["path"])
        # loose match on name
        for a in load_index()["assets"]:
            if a["id"].split(":", 1)[0] == kind and name in a["id"]:
                return os.path.join(ASSETS, a["path"])
    raise FileNotFoundError(f"asset not found: {ref}")


def disk_free_gb(path=None):
    return round(shutil.disk_usage(path or workspace()).free / 1e9, 2)


def http_get(url, headers=None, timeout=30):
    import urllib.request
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def now():
    return time.strftime("%Y-%m-%d %H:%M")
