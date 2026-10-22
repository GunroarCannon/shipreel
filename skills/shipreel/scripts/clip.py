"""shipreel engine. Every command prints terse JSON/lines so agents spend few tokens reading output.

  clip.py doctor                                   tools, disk, RAM, fonts, chrome, godot
  clip.py init <project> --path <repo> [--shorthand-in-repo]
  clip.py probe <file>                             duration/size/audio (+ music-likely heuristic, scene cuts)
  clip.py sheet <file> [--n 6] [--width 900]       one contact-sheet jpg (cheap visual check)
  clip.py rec add|list|find <project> ...          recordings cache (temp/<project>/data.json)
  clip.py record-screen <project> --id X --dur 20 [--window "Title" | --region x,y,w,h]
  clip.py record-web <project> --id X --url URL [--steps s.json] [--portrait] [--dur 20]
  clip.py record-godot <project> --id X [--scene res://a.tscn] [--dur 15] [--autoplay t.json] [--godot path]
  clip.py worktree <project> add <commit>|--before DATE | remove <commit>    old versions without touching the repo (Godot: imports it)
  clip.py history <project> [--n 15]                            commits that changed the look: pick eras
  clip.py moments <rec-id|file> --project P [--format tiktok] [--pace fast] [--n 6]   best moving spans + where to frame them
  clip.py scaffold <project> --rec a,b --out plan.json [--recipe showcase|before-after|tour] [--mode pro] [--len 15]
  clip.py fonts                                    caption font families and what each is for
  clip.py check <plan.json>                        validate plan + copy lint (AI-tells, lengths, emoji) + pace/mode/framing rules
  clip.py render <plan.json> [--only ID] [--force] [--no-captioned]
  clip.py thumb <video|image> --t 3 --text "IT WORKS??" [--sticker meme:x] --out file.jpg
  clip.py name "title" --tags a,b [--series s --part 1]
  clip.py ledger <project> [--titles]              what already exists (avoid repeats)
  clip.py state next|show|note "..."               pass/queue progress (resume after context reset)
  clip.py clean <project> [--segments] [--worktrees]
"""
import argparse, csv, json, math, os, platform, re, shutil, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (SKILL_DIR, ASSETS, FONTS, out, die, slug, safe_title, video_name, sha, run, ffprobe, resolve_asset,
                    disk_free_gb, workspace, wpath, now, load_index, loudness_of, gain_to)

FORMATS = {"tiktok": (1080, 1920), "short": (1080, 1920), "reel": (1080, 1920), "portrait": (1080, 1920),
           "youtube": (1920, 1080), "landscape": (1920, 1080), "x": (1920, 1080), "twitter": (1920, 1080), "square": (1080, 1080)}
LIMITS = {"tiktok": (10, 30), "short": (10, 60), "reel": (10, 90), "portrait": (5, 180),
          "youtube": (60, 300), "landscape": (5, 600), "x": (5, 140), "twitter": (5, 140), "square": (5, 120)}
ENC_FINAL = ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-profile:v", "high", "-pix_fmt", "yuv420p",
             "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv", "-movflags", "+faststart"]
ENC_SEG = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p"]
AUD = ["-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]
SEG_VERSION = 5  # bump when segment rendering changes, so cached segments rebuild

# Pacing (references/pacing.md). shot = (min, average, max) seconds per clip; gap = longest stretch with nothing new;
# wps = caption reading speed (words per second); trans = default transition length; per = word-pop group size.
PACES = {
    "fast":   {"shot": (0.6, 1.8, 3.2), "gap": 2.5, "wps": 3.6, "cap_min": 0.9, "trans": 0.22, "per": 2, "first_cut": 3.0, "words": 6},
    "medium": {"shot": (1.0, 3.0, 5.5), "gap": 4.0, "wps": 3.0, "cap_min": 1.2, "trans": 0.4, "per": 3, "first_cut": 4.5, "words": 8},
    "slow":   {"shot": (1.5, 5.0, 10.0), "gap": 8.0, "wps": 2.5, "cap_min": 1.8, "trans": 0.7, "per": 4, "first_cut": 8.0, "words": 12},
}
MODES = ("creator", "pro")


def pace_for(length):
    """The natural pace for a video of this length: short = fast, long = slow."""
    return "fast" if length <= 22 else "medium" if length <= 60 else "slow"


def resolve_pace(v, length, cfg=None):
    p = str(v.get("pace") or (cfg or {}).get("pace") or "auto").lower()
    return pace_for(length) if p == "auto" else p


def resolve_mode(v, plan=None, cfg=None):
    return str(v.get("mode") or (plan or {}).get("mode") or (cfg or {}).get("mode") or "creator").lower()


def read_time(text, pace):
    """Seconds a caption must stay up to be read at this pace."""
    P = PACES.get(pace, PACES["medium"])
    n = len(str(text).replace("*", "").split())
    return round(max(P["cap_min"], 0.4 + n / P["wps"]), 2)


# Pro mode (references/pro-mode.md): what stays out of a professional video
PRO_STYLES = {"pro", "minimal", "editorial", "tech", "clean", "label", "cinema", "headline", "condensed"}
CREATOR_ONLY_FX = {"glitch", "vhs", "shake", "pixelate", "mirror", "reverse"}
SLANG = ["lol", "lmao", "bruh", "bro", "homie", "ngl", "fr fr", "no cap", "goated", "deadass", "wtf", "omg", "rizz", "sus", "yeet", "lowkey", "highkey"]
GRADES = {
    "none": None,
    "clean": "eq=contrast=1.05:saturation=1.08",
    "punchy": "eq=contrast=1.12:saturation=1.28,unsharp=5:5:0.35",
    "vivid": "eq=contrast=1.06:saturation=1.4",
    "warm": "colorbalance=rs=0.05:gs=0.01:bs=-0.05:rm=0.04:bm=-0.03,eq=saturation=1.06",
    "cool": "colorbalance=rs=-0.04:bs=0.05:rm=-0.02:bm=0.04,eq=saturation=1.02",
    "cinematic": "colorbalance=rs=-0.05:bs=0.06:rh=0.06:gh=0.02:bh=-0.05,eq=contrast=1.07:saturation=1.05",
    "film": "curves=preset=medium_contrast,eq=saturation=0.88,noise=alls=5:allf=t",
    "mono": "hue=s=0,eq=contrast=1.1",
}


def enc_final(cfg):
    """x264 preset: SHIPREEL_PRESET env > config render.preset > medium. faster/veryfast = quicker renders, bigger files."""
    p = os.environ.get("SHIPREEL_PRESET") or cfg.get("render", {}).get("preset") or "medium"
    return [p if x == "medium" else x for x in ENC_FINAL]


# ----------------------------------------------------------------------------- config / paths
def load_config():
    cfg = json.load(open(os.path.join(SKILL_DIR, "config", "defaults.json"), encoding="utf-8"))
    p = wpath("shipreel.config.json")
    if os.path.exists(p):
        user = json.load(open(p, encoding="utf-8"))
        for k, v in user.items():
            if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                cfg[k].update(v)
            else:
                cfg[k] = v
    return cfg


def pdir(kind, project, *parts):
    d = wpath(kind, slug(project), *parts)
    os.makedirs(d if not os.path.splitext(d)[1] else os.path.dirname(d), exist_ok=True)
    return d


def data_path(project):
    return os.path.join(pdir("temp", project), "data.json")


def load_data(project):
    p = data_path(project)
    if os.path.exists(p):
        return json.load(open(p, encoding="utf-8"))
    return {"project": project, "path": None, "recordings": [], "notes": {}}


def save_data(project, d):
    p = data_path(project)
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
    os.replace(p + ".tmp", p)


def still_spans(file, dur, min_s=2.0):
    """Frozen stretches [[start, end], ...] in seconds. A recording nobody drove (title card, tutorial modal) is one long span."""
    p = run(["ffmpeg", "-hide_banner", "-nostats", "-i", file, "-an", "-vf", f"scale=320:-2,freezedetect=n=0.003:d={min_s}", "-f", "null", "-"], check=False)
    starts = [float(x) for x in re.findall(r"freeze_start: ([\d.]+)", p.stderr)]
    ends = [float(x) for x in re.findall(r"freeze_end: ([\d.]+)", p.stderr)]
    return [[round(s, 1), round(ends[i] if i < len(ends) else dur, 1)] for i, s in enumerate(starts)][:20]


def register_rec(project, rid, file, **meta):
    d = load_data(project)
    info = ffprobe(file)
    rel = os.path.relpath(file, pdir("temp", project)).replace("\\", "/")
    entry = {"id": rid, "file": rel, "dur": info["dur"], "w": (info["video"] or {}).get("w"), "h": (info["video"] or {}).get("h"),
             "has_audio": bool(info["audio"]), "created": now(), **{k: v for k, v in meta.items() if v not in (None, "")}}
    if meta.get("how") != "file" and info["video"] and info["dur"]:
        # exit code 0 and "ok" only mean ffmpeg wrote a file. Frozen footage is the most common silent failure, so measure it here.
        spans = still_spans(file, info["dur"])
        still = round(sum(e - s for s, e in spans), 1)
        entry["still"] = spans
        entry["still_pct"] = round(100 * still / info["dur"])
        if entry["still_pct"] >= 30 or any(e - s >= 3 for s, e in spans):
            entry["warn"] = (f"STILL {entry['still_pct']}% ({still}s frozen: {spans[:4]}). Nothing moved. Run clip.py sheet on this file and look. "
                             "Likely a title screen, tutorial/consent modal or no input: fix the steps/autoplay and re-record; do not use it as is.")
    d["recordings"] = [r for r in d["recordings"] if r["id"] != rid] + [entry]
    save_data(project, d)
    return entry


def resolve_src(src, project):
    if src.startswith("rec:"):
        ref = src[4:]
        proj = project
        if "/" in ref:
            proj, ref = ref.split("/", 1)
        for r in load_data(proj)["recordings"]:
            if r["id"] == ref:
                return os.path.join(pdir("temp", proj), r["file"])
        raise FileNotFoundError(f"recording not found: {src} (clip.py rec list {proj})")
    if os.path.exists(src):
        return os.path.abspath(src)
    if os.path.exists(wpath(src)):
        return wpath(src)
    return resolve_asset(src)


def rec_meta(src, project):
    """The recordings-cache entry behind a rec: source (how it was recorded, orientation, still spans), or {}."""
    if not str(src).startswith("rec:"):
        return {}
    ref, proj = src[4:], project
    if "/" in ref:
        proj, ref = ref.split("/", 1)
    return next((r for r in load_data(proj)["recordings"] if r["id"] == ref), {})


IMG_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


# ----------------------------------------------------------------------------- framing: aspect-aware fit + auto focus
def auto_fit(clip, is_img, sw, sh, W, H, mode, rec):
    """What `fit: auto` (the default) becomes for this source shape in this frame (references/framing.md).
    Same shape (phone recording -> TikTok, landscape -> YouTube): cover, it fills the frame. Wide into tall: games and
    footage fill the frame (cover + auto focus), a landscape web UI floats over a blur. Tall into wide: float/blurpad."""
    fit = clip.get("fit") or "auto"
    if fit != "auto":
        return fit
    if clip.get("track"):
        return "cover"
    r = (sw / sh) / (W / H)
    if 0.8 <= r <= 1.25:
        return "cover"
    soft = "float" if mode == "pro" else "blurpad"
    if is_img or r < 0.8:
        return soft
    if rec.get("how") == "web":
        return soft  # a wide web UI: the whole width matters, so keep all of it
    return "cover"


def window_frac(sw, sh, W, H, zoom=1.0):
    """Fraction of the source width and height a `cover` crop into W x H keeps."""
    f = max(W / sw, H / sh) * max(1.0, float(zoom or 1))
    return min(1.0, W / (sw * f)), min(1.0, H / (sh * f))


def motion_frames(src, s_in, dur, sw, sh, cols=48, fps=6):
    """Tiny grey frame differences (cols wide) over a span: where things move."""
    rows = max(4, int(round(cols * sh / sw)))
    p = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0, s_in):.3f}", "-t", f"{max(0.3, dur):.3f}", "-i", src, "-an",
                        "-vf", f"fps={fps},scale={cols}:{rows}:flags=area,format=gray,tblend=all_mode=difference",
                        "-f", "rawvideo", "-pix_fmt", "gray", "pipe:1"], capture_output=True)
    n = cols * rows
    d = p.stdout
    return [d[i:i + n] for i in range(0, len(d) - n + 1, n)], cols, rows


def detail_grid(src, t, sw, sh, cols=48):
    """Edge density of one frame (cols wide): where the detail is, for footage that barely moves."""
    rows = max(4, int(round(cols * sh / sw)))
    p = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0, t):.3f}", "-i", src, "-frames:v", "1",
                        "-vf", f"scale={cols * 4}:{rows * 4},format=gray,edgedetect=low=0.08:high=0.25,scale={cols}:{rows}:flags=area",
                        "-f", "rawvideo", "-pix_fmt", "gray", "pipe:1"], capture_output=True)
    d = p.stdout
    return [float(x) for x in d[:cols * rows]] if len(d) >= cols * rows else None


def sum_frames(frames, n):
    acc = [0.0] * n
    for fr in frames:
        for i, b in enumerate(fr):
            acc[i] += b
    return acc


def best_window(grid, cols, rows, fw, fh, bias=0.15):
    """Slide a window of fw x fh (fractions) over an energy grid; returns (focus_x, focus_y, centre_x, centre_y, share).
    focus = where the crop sits in the slack (the `focus` field), centre = the point it centres on (a `track` key)."""
    wc, wr = max(1, min(cols, int(round(fw * cols)))), max(1, min(rows, int(round(fh * rows))))
    I = [[0.0] * (cols + 1) for _ in range(rows + 1)]
    for y in range(rows):
        acc = 0.0
        for x in range(cols):
            acc += grid[y * cols + x]
            I[y + 1][x + 1] = I[y][x + 1] + acc
    total = I[rows][cols] or 1.0
    best, bx, by = -1.0, (cols - wc) // 2, (rows - wr) // 2
    for y0 in range(rows - wr + 1):
        for x0 in range(cols - wc + 1):
            s = I[y0 + wr][x0 + wc] - I[y0][x0 + wc] - I[y0 + wr][x0] + I[y0][x0]
            cx, cy = (x0 + wc / 2) / cols, (y0 + wr / 2) / rows
            s *= 1 - bias * ((cx - 0.5) ** 2 + (cy - 0.5) ** 2) * 2  # a tie goes to the centre
            if s > best:
                best, bx, by = s, x0, y0
    fx = bx / (cols - wc) if cols > wc else 0.5
    fy = by / (rows - wr) if rows > wr else 0.5
    return round(fx, 3), round(fy, 3), round((bx + wc / 2) / cols, 3), round((by + wr / 2) / rows, 3), max(0.0, best) / total


def auto_focus(src, s_in, dur, sw, sh, fw, fh):
    """Where to put a crop window of fw x fh: on the motion, else on the detail, else the centre.
    Returns (focus [x, y], centre [x, y], how)."""
    frames, cols, rows = motion_frames(src, s_in, dur, sw, sh)
    g = sum_frames(frames, cols * rows) if frames else None
    how = "motion"
    if not g or sum(g) / (len(frames) * cols * rows) < 0.6:  # barely anything moves: use where the detail is
        g, how = detail_grid(src, s_in + dur / 2, sw, sh), "detail"
    if not g or not sum(g):
        return [0.5, 0.5], [0.5, 0.5], "centre"
    fx, fy, cx, cy, share = best_window(g, cols, rows, fw, fh)
    if share < min(1.0, fw * fh * 1.12):  # spread evenly: nothing to aim at, stay centred
        return [0.5, 0.5], [0.5, 0.5], "centre"
    return [fx, fy], [cx, cy], how


def auto_track(src, s_in, dur, sw, sh, fw, fh, speed=1.0, max_keys=8):
    """A camera that follows the action: best window per second, smoothed, a glide only when it moved enough."""
    fps = 6
    frames, cols, rows = motion_frames(src, s_in, dur, sw, sh, fps=fps)
    if len(frames) < fps:
        _f, c, _h = auto_focus(src, s_in, dur, sw, sh, fw, fh)
        return [{"t": 0, "x": c[0], "y": c[1]}]
    pts = []
    for i in range(0, len(frames), fps):
        g = sum_frames(frames[i:i + fps], cols * rows)
        if sum(g) < 0.6 * cols * rows * len(frames[i:i + fps]):
            pts.append(None); continue
        _fx, _fy, cx, cy, _s = best_window(g, cols, rows, fw, fh)
        pts.append((cx, cy))
    known = [p for p in pts if p]
    if not known:
        return [{"t": 0, "x": 0.5, "y": 0.5}]
    last = known[0]
    pts = [p or None for p in pts]
    filled = []
    for p in pts:
        last = p or last
        filled.append(last)
    def med3(vals):
        return sorted(vals)[len(vals) // 2]
    sm = []  # median of 3: a one-second blip doesn't move the camera, and it never drifts to a spot where nothing is
    for i in range(len(filled)):
        win = filled[max(0, i - 1):i + 2]
        sm.append((med3([p[0] for p in win]), med3([p[1] for p in win])))
    keys = [{"t": 0, "x": round(sm[0][0], 3), "y": round(sm[0][1], 3)}]
    lx, ly = sm[0]
    for i, (x, y) in enumerate(sm[1:], 1):
        if abs(x - lx) > 0.35 * fw or abs(y - ly) > 0.35 * fh:
            keys.append({"t": round(max(0.0, i - 0.15) / max(0.05, speed), 2), "x": round(x, 3), "y": round(y, 3), "move": 0.6})
            lx, ly = x, y
    return keys[:max_keys]


# ----------------------------------------------------------------------------- doctor / init / probe / sheet
def find_chrome():
    c = os.environ.get("CHROME_PATH")
    cands = [c] if c else []
    if platform.system() == "Windows":
        for base in (os.environ.get("PROGRAMFILES", ""), os.environ.get("PROGRAMFILES(X86)", ""), os.environ.get("LOCALAPPDATA", "")):
            cands += [os.path.join(base, "Google", "Chrome", "Application", "chrome.exe"), os.path.join(base, "Microsoft", "Edge", "Application", "msedge.exe"),
                      os.path.join(base, "BraveSoftware", "Brave-Browser", "Application", "brave.exe")]
    elif platform.system() == "Darwin":
        cands += ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"]
    cands += [shutil.which(n) for n in ("google-chrome", "chromium", "chromium-browser", "chrome", "msedge")]
    return next((x for x in cands if x and os.path.exists(x)), None)


def find_godot(cfg=None):
    g = os.environ.get("GODOT_BIN") or (cfg or {}).get("godot_bin")
    if g and os.path.exists(g):
        return g
    for n in ("godot", "godot4", "Godot"):
        if shutil.which(n):
            return shutil.which(n)
    home = os.path.expanduser("~")
    for d in (home, os.path.join(home, "Downloads"), os.path.join(home, "Desktop"), "C:/Program Files/Godot", "/Applications"):
        try:
            hits = sorted([f for f in os.listdir(d) if f.lower().startswith("godot") and (f.endswith("_console.exe") or f.endswith(".app") or f.endswith(".x86_64"))], reverse=True)
            if hits:
                p = os.path.join(d, hits[0])
                return os.path.join(p, "Contents", "MacOS", "Godot") if p.endswith(".app") else p
        except OSError:
            pass
    return None


def cmd_doctor(a):
    cfg = load_config()
    r = {"ffmpeg": bool(shutil.which("ffmpeg")), "ffprobe": bool(shutil.which("ffprobe"))}
    if r["ffmpeg"]:
        b = run(["ffmpeg", "-hide_banner", "-buildconf"], check=False).stdout
        r["libass"] = "enable-libass" in b
        r["x264"] = "enable-libx264" in b
    node = shutil.which("node")
    r["node"] = run([node, "-v"], check=False).stdout.strip() if node else None
    r["node_websocket"] = bool(r["node"]) and int(re.sub(r"\D", "", r["node"].split(".")[0]) or 0) >= 22
    r["chrome"] = find_chrome()
    r["godot"] = find_godot(cfg)
    r["git"] = bool(shutil.which("git"))
    r["disk_free_gb"] = disk_free_gb()
    try:
        if platform.system() == "Windows":
            o = run(["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory"], check=False).stdout
            r["ram_free_gb"] = round(int(o.strip()) / 1e6, 2)
        elif os.path.exists("/proc/meminfo"):
            m = open("/proc/meminfo").read(); r["ram_free_gb"] = round(int(re.search(r"MemAvailable:\s+(\d+)", m).group(1)) / 1e6, 2)
    except Exception:
        pass
    r["fonts"] = len([f for f in os.listdir(FONTS) if f.endswith((".ttf", ".otf"))])
    r["workspace"] = workspace()
    warn = []
    if not r["ffmpeg"]:
        warn.append("install ffmpeg (winget install Gyan.FFmpeg / brew install ffmpeg / apt install ffmpeg)")
    if r["disk_free_gb"] < cfg["limits"]["min_free_gb"]:
        warn.append(f"low disk: {r['disk_free_gb']}GB free (<{cfg['limits']['min_free_gb']}). Ask user to free space or set SHIPREEL_HOME to another drive")
    if r.get("ram_free_gb", 9) < 1.0:
        warn.append("low free RAM: renders run one at a time; close heavy apps for long YouTube renders")
    if not r["node_websocket"]:
        warn.append("web recording needs Node >= 22 (built-in WebSocket)")
    if not r["chrome"]:
        warn.append("no Chrome/Edge/Brave found for web recording (set CHROME_PATH)")
    r["warn"] = warn
    out(r)


SHORTHAND_TEMPLATE = os.path.join(SKILL_DIR, "templates", "project-shorthand.txt")


def cmd_init(a):
    cfg = load_config()
    for k in ("output", "temp"):
        pdir(k, a.project)
    os.makedirs(os.path.join(pdir("output", a.project), "textless"), exist_ok=True)
    d = load_data(a.project)
    if a.path:
        d["path"] = os.path.abspath(a.path)
    save_data(a.project, d)
    sh = None
    if d.get("path"):
        in_repo = os.path.join(d["path"], ".project-shorthand.txt")
        alt = os.path.join(pdir("temp", a.project), ".project-shorthand.txt")
        sh = in_repo if os.path.exists(in_repo) else alt
        if not os.path.exists(sh):
            sh = in_repo if a.shorthand_in_repo else alt
            shutil.copy(SHORTHAND_TEMPLATE, sh)
            new = True
        else:
            new = False
    out({"ok": True, "project": slug(a.project), "output": pdir("output", a.project), "temp": pdir("temp", a.project),
         "shorthand": sh, "shorthand_is_template": bool(sh) and new})


def audio_stats(path, dur):
    """silence %, mean dB and a crude 'music likely' flag (continuous non-silent audio)."""
    p = run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-vn", "-af", "silencedetect=n=-45dB:d=0.4,volumedetect", "-f", "null", "-"], check=False)
    err = p.stderr
    sil = sum(float(x) for x in re.findall(r"silence_duration: ([\d.]+)", err))
    mean = re.search(r"mean_volume: (-?[\d.]+) dB", err)
    gaps = len(re.findall(r"silence_start", err))
    sil_pct = round(100 * sil / dur, 1) if dur else 0
    return {"silent_pct": sil_pct, "mean_db": float(mean.group(1)) if mean else None, "gaps": gaps,
            "music_likely": bool(mean) and sil_pct < 8 and gaps <= max(1, int(dur / 20)) and float(mean.group(1)) > -35}


_MUSIC_CACHE = {}


def product_has_music(src):
    """True when a clip's own audio probably carries music (continuous, non-silent). Cached per file."""
    k = (src, os.path.getmtime(src))
    if k not in _MUSIC_CACHE:
        info = ffprobe(src)
        _MUSIC_CACHE[k] = bool(info["audio"]) and audio_stats(src, info["dur"])["music_likely"]
    return _MUSIC_CACHE[k]


def product_music_clips(v, project):
    """Indexes of clips whose own audio would fight a library music bed. Only matters when the video has `music`
    and the plan didn't opt out with product_music:"keep". A clip with audio:"mute" is already fine."""
    if not v.get("music") or v.get("product_music", "mute") == "keep" or float(v.get("product_volume", 1.0)) <= 0.05:
        return []
    hits = []
    for i, c in enumerate(v["clips"]):
        if "card" in c or c.get("still") or c.get("audio") == "mute" or not str(c.get("src", "")).startswith("rec:"):
            continue
        try:
            src = resolve_src(c["src"], project)
            if os.path.splitext(src)[1].lower() not in IMG_EXT and product_has_music(src):
                hits.append(i)
        except Exception:
            pass
    return hits


def cmd_probe(a):
    info = ffprobe(a.file)
    if info["audio"] and not a.fast:
        info["audio"].update(audio_stats(a.file, info["dur"]))
    if info["video"] and not a.fast and info["dur"] < 900:
        p = run(["ffmpeg", "-hide_banner", "-nostats", "-i", a.file, "-an", "-vf", "scale=320:-2,select='gt(scene,0.3)',showinfo", "-f", "null", "-"], check=False)
        cuts = [round(float(x), 2) for x in re.findall(r"pts_time:([\d.]+)", p.stderr)]
        info["scene_cuts"] = cuts[:40]
        # still sections: frozen video longer than 3s (low-effort signal)
        p = run(["ffmpeg", "-hide_banner", "-nostats", "-i", a.file, "-an", "-vf", "scale=320:-2,freezedetect=n=0.003:d=3", "-f", "null", "-"], check=False)
        info["static_spans"] = [round(float(x), 1) for x in re.findall(r"freeze_start: ([\d.]+)", p.stderr)][:20]
    out(info)


def make_sheet(a):
    info = ffprobe(a.file)
    n = max(2, min(16, a.n))
    cols = min(n, a.cols or (3 if (info["video"] or {}).get("h", 1) > (info["video"] or {}).get("w", 1) else 2) if n > 3 else n)
    rows = math.ceil(n / cols)
    dur = info["dur"] or 1
    times = [round(dur * (i + 0.5) / n, 2) for i in range(n)] if not a.times else [float(t) for t in a.times.split(",")]
    cw = a.width // cols
    dst = a.out or wpath("temp", "_sheets", slug(os.path.basename(a.file)) + ".jpg")
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    inputs, parts = [], []
    for i, t in enumerate(times):
        inputs += ["-ss", str(t), "-i", a.file]
        grid = ""
        if a.grid:  # tenths grid with labels: read an x,y (0 to 1) straight off the sheet for focus / track / overlays
            fs = max(10, cw // 28)
            fnt = ffesc(os.path.join(FONTS, 'Montserrat-Bold.ttf'))
            grid = ",drawgrid=w=iw/10:h=ih/10:t=1:c=white@0.45," + ",".join(
                [f"drawtext=fontfile='{fnt}':text='{j}':x=w*{j}/10+2:y=h-{fs + 4}:fontsize={fs}:fontcolor=yellow:borderw=2:bordercolor=black" for j in range(1, 10)] +
                [f"drawtext=fontfile='{fnt}':text='{j}':x=w-{fs + 4}:y=h*{j}/10+2:fontsize={fs}:fontcolor=cyan:borderw=2:bordercolor=black" for j in range(1, 10)])
        parts.append(f"[{i}:v]scale={cw}:-2{grid},drawtext=fontfile='{ffesc(os.path.join(FONTS, 'Montserrat-Bold.ttf'))}':text='{t}s':x=6:y=6:fontsize=22:fontcolor=white:box=1:boxcolor=black@0.6,setsar=1[f{i}]")
    if len(times) > 1:
        layout = "|".join(f"{'+'.join(['w0'] * (i % cols)) or 0}_{'+'.join(['h0'] * (i // cols)) or 0}" for i in range(len(times)))
        fc = ";".join(parts) + ";" + "".join(f"[f{i}]" for i in range(len(times))) + f"xstack=inputs={len(times)}:layout={layout}:fill=black[o]"
    else:
        fc = parts[0].replace("[f0]", "[o]")
    run(["ffmpeg", "-y", "-v", "error", *sum([["-frames:v", "1"] for _ in []], []), *inputs, "-filter_complex", fc, "-map", "[o]", "-frames:v", "1", "-q:v", "5", dst])
    return dst, times


def cmd_sheet(a):
    dst, times = make_sheet(a)
    out({"sheet": dst, "times": times})


def ffesc(p):
    """Escape a path for use inside an ffmpeg filtergraph option value."""
    return p.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


# ----------------------------------------------------------------------------- recordings
def cmd_rec(a):
    if a.action == "list":
        for r in load_data(a.project)["recordings"]:
            extras = " ".join(f"{k}={r[k]}" for k in ("feature", "era", "commit", "orient", "music") if r.get(k))
            flag = ""
            warn = str(r.get("warn") or "")
            if (r.get("still_pct") or 0) >= 30 or warn.startswith("STILL"):
                flag += f" !!STILL {r.get('still_pct', 0)}%"
            try:
                cap_fps = float(r.get("fps"))
            except (TypeError, ValueError):
                cap_fps = None
            if r.get("capture") == "screencast" and cap_fps is not None and cap_fps < 20:
                flag += f" !!CHOPPY {r.get('fps')}fps"
            print(f"{r['id']} | {r['dur']}s {r.get('w')}x{r.get('h')} audio={int(r.get('has_audio', 0))}{flag} | {extras} | {r.get('notes', '')[:80]}")
        return
    if a.action == "find":
        q = (a.query or "").lower().split()
        hits = [r for r in load_data(a.project)["recordings"] if all(w in json.dumps(r).lower() for w in q)]
        for r in hits:
            print(f"{r['id']} | {r['dur']}s | {r.get('feature', '')} | {r.get('era', '')} | {r.get('notes', '')[:60]}")
        print(f"{len(hits)} hit(s)")
        return
    if a.action == "add":
        if not a.file or not a.id:
            die("rec add needs --file and --id")
        src = os.path.abspath(a.file)
        dst = src
        if a.copy:
            dst = os.path.join(pdir("temp", a.project, "rec"), slug(a.id) + os.path.splitext(src)[1])
            shutil.copy2(src, dst)
        out({"ok": True, **register_rec(a.project, a.id, dst, feature=a.feature, era=a.era, commit=a.commit, notes=a.notes, how="file")})


def rec_out(project, rid):
    return os.path.join(pdir("temp", project, "rec"), slug(rid, 90) + ".mp4")


def cmd_record_screen(a):
    dst = rec_out(a.project, a.id)
    sysname = platform.system()
    if sysname == "Windows":
        src = ["-f", "gdigrab", "-framerate", str(a.fps), "-draw_mouse", "1"]
        if a.region:
            x, y, w, h = [int(v) for v in a.region.split(",")]
            src += ["-offset_x", str(x), "-offset_y", str(y), "-video_size", f"{w}x{h}", "-i", "desktop"]
        else:
            src += ["-i", f"title={a.window}" if a.window else "desktop"]
        aud = ["-f", "dshow", "-i", f"audio={a.audio_device}"] if a.audio_device else []
    elif sysname == "Darwin":
        src = ["-f", "avfoundation", "-framerate", str(a.fps), "-capture_cursor", "1", "-i", f"{a.display or 1}:{a.audio_device or 'none'}"]
        aud = []
    else:
        disp = os.environ.get("DISPLAY", ":0")
        if a.region:
            x, y, w, h = [int(v) for v in a.region.split(",")]
            src = ["-f", "x11grab", "-framerate", str(a.fps), "-video_size", f"{w}x{h}", "-i", f"{disp}+{x},{y}"]
        else:
            src = ["-f", "x11grab", "-framerate", str(a.fps), "-i", disp]
        aud = ["-f", "pulse", "-i", a.audio_device] if a.audio_device else []
    cmd = ["ffmpeg", "-y", "-v", "error", *src, *aud, "-t", str(a.dur), "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
           "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18", "-pix_fmt", "yuv420p", *(AUD if aud else []), dst]
    if a.delay:
        time.sleep(a.delay)
    try:
        run(cmd, timeout=a.dur + 60)
    except Exception as e:
        die(str(e)[-400:])
    out({"ok": True, **register_rec(a.project, a.id, dst, feature=a.feature, era=a.era, commit=a.commit, notes=a.notes, how="screen")})


def cmd_record_web(a):
    dst = rec_out(a.project, a.id)
    chrome = find_chrome()
    if not chrome:
        die("no chrome/edge found; set CHROME_PATH", code=3)
    w, h = (a.size.split("x") if a.size else (("405", "720") if a.portrait else ("1280", "720")))
    scale = a.scale or (1080 / int(w) if a.portrait else 1.5)
    cmd = ["node", os.path.join(SKILL_DIR, "scripts", "record_web.mjs"), "--url", a.url, "--out", dst, "--w", str(w), "--h", str(h),
           "--scale", f"{scale:.4f}", "--dur", str(a.dur), "--chrome", chrome, "--fps", str(a.fps)]
    if a.steps:
        cmd += ["--steps", a.steps]
    if a.portrait or a.mobile:
        cmd += ["--mobile"]
    if a.no_cursor:
        cmd += ["--no-cursor"]
    if a.dark:
        cmd += ["--dark"]
    if a.headed:
        cmd += ["--headed"]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        die("record-web failed", tail=(p.stderr or p.stdout)[-600:])
    meta = {}
    try:
        meta = json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        pass
    e = register_rec(a.project, a.id, dst, feature=a.feature, era=a.era, commit=a.commit, notes=a.notes, how="web",
                     url=a.url, marks=meta.get("marks"), targets=meta.get("targets"), orient="portrait" if a.portrait else "landscape",
                     capture=meta.get("mode"), fps=meta.get("fps"))
    cap_warn = meta.get("warn")
    if cap_warn:
        d = load_data(a.project)
        for r in d["recordings"]:
            if r["id"] == a.id:
                prev = r.get("warn")
                r["warn"] = f"{prev} | {cap_warn}" if prev else cap_warn
                e = r
                break
        save_data(a.project, d)
    out({"ok": True, **e})


def shadow_project(proj, res, dest, scale=None):
    """A throwaway mirror of a Godot project whose viewport is res (WxH). Movie Maker takes its output size from the project's
    viewport settings and ignores --resolution, so a portrait capture of a landscape game needs patched settings. Folders are
    junctions/symlinks, so nothing is copied and the real project is never written to. scale = UI scale (1.5 for 1080 wide
    when the UI was drawn for 720)."""
    w, h = (int(x) for x in res.lower().split("x"))
    if os.path.isdir(dest):
        shutil.rmtree(dest, ignore_errors=True)
    os.makedirs(dest)
    for name in os.listdir(proj):
        if name in (".git", "project.godot"):
            continue
        src, dst = os.path.join(proj, name), os.path.join(dest, name)
        if os.path.isdir(src):
            if platform.system() == "Windows":
                subprocess.run(["cmd", "/c", "mklink", "/J", dst, src], capture_output=True)
            else:
                os.symlink(src, dst)
        elif name != "project.godot":
            try:
                os.link(src, dst)
            except OSError:
                shutil.copy2(src, dst)
    cfg = open(os.path.join(proj, "project.godot"), encoding="utf-8").read()
    nl = chr(10)
    drop = re.compile(r"window/size/(viewport_|window_)(width|height)(_override)?\s*=|window/stretch/scale\s*=")
    cfg = nl.join(ln for ln in cfg.split(nl) if not drop.match(ln.strip()))
    add = f"window/size/viewport_width={w}{nl}window/size/viewport_height={h}{nl}" + (f"window/stretch/scale={scale}{nl}" if scale else "")
    if re.search(r"^\[display\]\s*$", cfg, re.M):
        cfg = re.sub(r"^\[display\]\s*$", lambda m: "[display]" + nl + nl + add.rstrip(nl), cfg, count=1, flags=re.M)
    else:
        cfg += nl + "[display]" + nl + nl + add
    # saves and prefs the game writes during a capture go to a scratch user dir, not the player's real one
    cfg = re.sub(r"^config/(use_custom_user_dir|custom_user_dir_name)\s*=.*$", "", cfg, flags=re.M)
    cfg = re.sub(r"^\[application\]\s*$", lambda m: "[application]" + nl + nl + "config/use_custom_user_dir=true" + nl + "config/custom_user_dir_name=\"shipreel-capture\"", cfg, count=1, flags=re.M)
    open(os.path.join(dest, "project.godot"), "w", encoding="utf-8").write(cfg)
    # start from a copy of the player's own saves/prefs (tutorials already done, settings as they play), written to the scratch dir
    nm = re.search(r'^config/name="([^"]*)"', cfg, re.M)
    appdata = os.environ.get("APPDATA") or os.path.expanduser("~/.local/share")
    real = os.path.join(appdata, "Godot", "app_userdata", nm.group(1)) if nm else ""
    scratch = os.path.join(appdata, "shipreel-capture")
    shutil.rmtree(scratch, ignore_errors=True)
    if real and os.path.isdir(real):
        shutil.copytree(real, scratch, ignore=shutil.ignore_patterns("logs", "shader_cache", "vulkan"), dirs_exist_ok=True)
    return dest


def cmd_record_godot(a):
    cfg = load_config()
    godot = a.godot or find_godot(cfg)
    if not godot:
        die("godot binary not found: pass --godot or set GODOT_BIN", code=3)
    proj = a.path or load_data(a.project).get("path")
    if not proj or not os.path.exists(os.path.join(proj, "project.godot")):
        die("no project.godot at project path (use --path, or a worktree path)")
    tmp_avi = os.path.join(pdir("temp", a.project, "rec"), slug(a.id, 90) + ".avi")
    frames = int(a.dur * a.fps)
    if a.resolution:
        w_, h_ = (int(x) for x in a.resolution.lower().split("x"))
        proj = shadow_project(proj, a.resolution, os.path.join(pdir("temp", a.project, "shadow"), a.resolution), a.ui_scale)
    cmd = [godot, "--path", proj, "--write-movie", tmp_avi, "--fixed-fps", str(a.fps), "--quit-after", str(frames)]
    if a.resolution:
        cmd += ["--resolution", a.resolution]
    env = dict(os.environ)
    if a.autoplay:
        env["SHIPREEL_AUTOPLAY"] = os.path.abspath(a.autoplay)
        env["SHIPREEL_SCENE"] = a.scene or ""
        env["SHIPREEL_RES"] = a.resolution or ""
        cmd += ["--script", os.path.join(SKILL_DIR, "templates", "godot_autoplay.gd")]
    elif a.scene:
        cmd += [a.scene]
    for kv in a.env or []:
        k, v = kv.split("=", 1); env[k] = v
    p = subprocess.run(cmd, capture_output=True, text=True, env=env, encoding="utf-8", errors="replace", timeout=a.dur * 20 + 120)
    if not os.path.exists(tmp_avi):
        die("godot did not write a movie", tail=(p.stderr or p.stdout)[-600:])
    dst = rec_out(a.project, a.id)
    vf = ["-vf", f"scale={a.out_size.replace('x', ':')}:flags=lanczos"] if a.out_size else []
    run(["ffmpeg", "-y", "-v", "error", "-i", tmp_avi, *vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", *AUD, dst])
    os.remove(tmp_avi)  # MJPEG avi is huge; keep only the mp4
    out({"ok": True, **register_rec(a.project, a.id, dst, feature=a.feature, era=a.era, commit=a.commit, notes=a.notes, how="godot", scene=a.scene)})


def cmd_worktree(a):
    repo = load_data(a.project).get("path")
    if not repo:
        die("project path unknown: clip.py init <project> --path <repo>")
    commit = a.commit
    if a.before:  # "the game as it looked on 2026-09-20": last commit on or before that date
        commit = subprocess.run(
            ["git", "-C", repo, "rev-list", "-1", f"--before={a.before} 23:59", "HEAD"], capture_output=True, text=True).stdout.strip()
        if not commit:
            die(f"no commit on or before {a.before}")
    if not commit:
        die("give a commit/tag or --before YYYY-MM-DD")
    wt = os.path.join(pdir("temp", a.project, "wt"), commit[:10])
    if a.action == "add":
        if not os.path.exists(wt):
            run(["git", "-C", repo, "worktree", "add", "--detach", wt, commit])
        info = {"ok": True, "path": wt, "commit": commit[:10],
                "date": subprocess.run(["git", "-C", repo, "log", "-1", "--format=%ad|%s", "--date=short", commit], capture_output=True, text=True).stdout.strip(),
                "note": "read-only use; remove when done: clip.py worktree <p> remove <commit>"}
        if os.path.exists(os.path.join(wt, "project.godot")):
            # a fresh checkout has no .godot import cache, so Godot would open it with every asset missing: import once
            godot = find_godot(load_config())
            if godot and not os.path.isdir(os.path.join(wt, ".godot", "imported")):
                p = subprocess.run([godot, "--headless", "--path", wt, "--import"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
                info["imported"] = os.path.isdir(os.path.join(wt, ".godot", "imported"))
                if not info["imported"]:
                    info["import_tail"] = (p.stderr or p.stdout)[-300:]
            info["next"] = f"clip.py record-godot {a.project} --path {wt} --id <feature>-<era> --era <e1> --commit {commit[:10]} ... (old input actions: read {wt}/project.godot [input])"
        elif os.path.exists(os.path.join(wt, "package.json")):
            info["next"] = f"cd {wt} && npm ci (or the project's install) in the background, start its dev server on a free port, then record-web; kill both after"
        out(info)
    else:
        run(["git", "-C", repo, "worktree", "remove", "--force", wt], check=False)
        run(["git", "-C", repo, "worktree", "prune"], check=False)
        out({"ok": True, "removed": wt})


def cmd_history(a):
    """Commits with dates and what kind of change they were, to pick eras where the project LOOKED different."""
    repo = load_data(a.project).get("path")
    if not repo:
        die("project path unknown: clip.py init <project> --path <repo>")
    log = subprocess.run(["git", "-C", repo, "log", "--reverse", "--format=@@%h|%ad|%s", "--date=short", "--numstat"], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
    rows, cur = [], None
    vis = re.compile(r"\.(tscn|scn|png|jpe?g|webp|svg|css|scss|html|shader|gdshader|tres|vue|jsx|tsx|ttf|otf)$", re.I)
    for ln in log.splitlines():
        if ln.startswith("@@"):
            h, d, subj = ln[2:].split("|", 2)
            cur = {"sha": h, "date": d, "subject": subj[:70], "files": 0, "visual": 0}
            rows.append(cur)
        elif ln.strip() and cur:
            parts = ln.split("	")
            if len(parts) == 3:
                cur["files"] += 1
                cur["visual"] += 1 if vis.search(parts[2]) else 0
    big = sorted(rows, key=lambda r: -r["visual"])[:a.n]
    out({"ok": True, "commits": len(rows), "first": rows[0] if rows else None, "last": rows[-1] if rows else None,
         "most_visual_changes": sorted(big, key=lambda r: r["date"]),
         "next": "pick 2 to 4 eras that look clearly different, then clip.py worktree <p> add <sha> and record each"})


# ----------------------------------------------------------------------------- captions (ASS)
STYLE_FIELDS = "Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding"


def ass_color(c, alpha=0):
    """'#RRGGBB' or name -> &HAABBGGRR"""
    names = {"white": "#FFFFFF", "black": "#000000", "yellow": "#FFE600", "red": "#FF2D2D", "green": "#2BE36B", "blue": "#2D8CFF",
             "pink": "#FF3EA5", "orange": "#FF8A00", "cyan": "#00E5FF", "tiktok": "#FE2C55", "purple": "#9B5CFF"}
    c = names.get(c, c).lstrip("#")
    r, g, b = c[0:2], c[2:4], c[4:6]
    return f"&H{alpha:02X}{b}{g}{r}".upper()


# Caption presets. Sizes are for the short side = 1080; scaled for other sizes.
PRESETS = {
    #           font,                      size, fill,     outline, ol,  shadow, upper, highlight
    # pop = TikTok's own "Classic" caption look: semibold white, thin crisp black outline, no glow, one yellow accent word/line
    "pop":     {"font": "TikTok Sans SemiBold", "size": 82, "fill": "white", "outline": "black", "ol": 5, "sh": 0, "upper": False, "hi": "yellow"},
    # label = TikTok's "background" look: black text on a white box (stays readable on any footage)
    "label":   {"font": "TikTok Sans SemiBold", "size": 70, "fill": "black", "outline": "white", "ol": 12, "sh": 0, "upper": False, "hi": "red", "box": True},
    "punch":   {"font": "TikTok Sans ExtraBold", "size": 96, "fill": "white", "outline": "black", "ol": 6, "sh": 2, "upper": False, "hi": "yellow"},
    "hormozi": {"font": "Montserrat Black", "size": 100, "fill": "white", "outline": "black", "ol": 7, "sh": 0, "upper": True, "hi": "green"},
    "clean":   {"font": "TikTok Sans SemiBold", "size": 80, "fill": "white", "outline": "black", "ol": 3, "sh": 3, "upper": False, "hi": "cyan"},
    "meme":    {"font": "Anton", "size": 112, "fill": "white", "outline": "black", "ol": 6, "sh": 0, "upper": True, "hi": "yellow"},
    "comic":   {"font": "Bangers", "size": 118, "fill": "yellow", "outline": "black", "ol": 7, "sh": 3, "upper": True, "hi": "white"},
    "dev":     {"font": "JetBrains Mono ExtraBold", "size": 72, "fill": "white", "outline": "black", "ol": 5, "sh": 0, "upper": False, "hi": "green"},
    "marker":  {"font": "Permanent Marker", "size": 98, "fill": "white", "outline": "black", "ol": 5, "sh": 2, "upper": False, "hi": "yellow"},
    "bold":    {"font": "Poppins ExtraBold", "size": 96, "fill": "white", "outline": "black", "ol": 6, "sh": 1, "upper": False, "hi": "pink"},
    "cinema":  {"font": "Bebas Neue", "size": 124, "fill": "white", "outline": "black", "ol": 3, "sh": 4, "upper": True, "hi": "yellow"},
    # bubble = the rounded, chunky game-dev-TikTok look: bold rounded face, thick dark outline, soft drop shadow, mid-frame
    "bubble":  {"font": "Fredoka Bold", "size": 108, "fill": "white", "outline": "#1B1B1F", "ol": 11, "sh": 6, "upper": False, "hi": "#3DA5FF", "cap_mv": 0.40, "no_plate": True},
    # chip = a small translucent rounded grey box with dark bold lowercase text, low in the frame (the "cool sticks." look)
    "chip":    {"font": "Nunito ExtraBold", "size": 58, "fill": "#1B1B1F", "outline": "#1B1B1F", "ol": 0, "sh": 0, "upper": False, "hi": "#D62D2D", "box": True,
                "boxcolor": "#E9E9EC", "boxalpha": 0x2E, "cap_mv": 0.22},
    "cartoon": {"font": "Luckiest Guy", "size": 106, "fill": "white", "outline": "black", "ol": 7, "sh": 3, "upper": True, "hi": "orange"},
    # --- pro presets (references/pro-mode.md): clean sans/serif, thin soft halo instead of a cartoon outline, fade in
    "pro":       {"font": "Inter SemiBold", "size": 76, "fill": "white", "outline": "#0B0B0F", "ol": 3, "sh": 0, "blur": 4, "upper": False,
                  "hi": "#5AA9FF", "cap_mv": 0.24, "anim": "fade"},
    "minimal":   {"font": "Manrope ExtraBold", "size": 72, "fill": "white", "outline": "#0B0B0F", "ol": 3, "sh": 0, "blur": 4, "upper": False,
                  "hi": "#B8F35A", "cap_mv": 0.24, "anim": "fade"},
    "editorial": {"font": "Instrument Serif", "size": 112, "fill": "white", "outline": "#0B0B0F", "ol": 3, "sh": 0, "blur": 5, "upper": False,
                  "hi": "#F2C14E", "cap_mv": 0.26, "anim": "fade"},
    "tech":      {"font": "Space Grotesk Bold", "size": 78, "fill": "white", "outline": "#05070A", "ol": 4, "sh": 0, "blur": 2, "upper": False,
                  "hi": "#7CFFB2", "anim": "fade"},
    "headline":  {"font": "Archivo Black", "size": 86, "fill": "white", "outline": "black", "ol": 5, "sh": 0, "upper": False, "hi": "#FFE600"},
    "condensed": {"font": "Oswald SemiBold", "size": 104, "fill": "white", "outline": "black", "ol": 4, "sh": 2, "upper": True, "hi": "#FFE600"},
    # --- more creator looks
    "game":      {"font": "Lilita One", "size": 110, "fill": "white", "outline": "#1B1B1F", "ol": 10, "sh": 6, "upper": False, "hi": "#FFD400",
                  "cap_mv": 0.40, "no_plate": True},
    "candy":     {"font": "Titan One", "size": 96, "fill": "white", "outline": "#2A1240", "ol": 9, "sh": 5, "upper": False, "hi": "#FF5DA2",
                  "cap_mv": 0.40, "no_plate": True},
    "pixel":     {"font": "Press Start 2P", "size": 52, "fill": "white", "outline": "black", "ol": 7, "sh": 4, "upper": True, "hi": "#FFE600",
                  "no_plate": True},
    "note":      {"font": "Caveat Bold", "size": 118, "fill": "white", "outline": "#1B1B1F", "ol": 4, "sh": 3, "upper": False, "hi": "#FFE27A"},
    "trendy":    {"font": "Bricolage Grotesque ExtraBold", "size": 92, "fill": "white", "outline": "black", "ol": 6, "sh": 0, "upper": False,
                  "hi": "#C6FF3D"},
}
# Which preset fits which footage, for `clip.py fonts` and references/caption-look.md
PRESET_USE = {
    "pop": "TikTok Classic look, any dev clip (creator default for non-games)", "bubble": "game-dev TikTok look, rounded and chunky",
    "chip": "small grey tag: dates, labels, deadpan asides", "label": "black on white box: busy footage", "punch": "loud single beats",
    "hormozi": "punchy facts, caps + green", "clean": "pretty footage, subtle", "meme": "impact-style memes", "comic": "comic/action games",
    "cartoon": "playful games", "dev": "code, terminals", "marker": "hand-made feel", "bold": "lifestyle-ish, pink accent",
    "cinema": "trailers, big titles", "pro": "PRO default: product demos, SaaS, client work", "minimal": "PRO: startup/product, very clean",
    "editorial": "PRO: story, documentary, case study (serif)", "tech": "PRO: dev tools, APIs, infra", "headline": "PRO/creator: news-style claims",
    "condensed": "PRO/creator: sports-style stats and countdowns", "game": "game TikToks (Lilita One), bold and friendly",
    "candy": "cozy/cute games", "pixel": "retro and pixel-art games", "note": "handwritten asides and annotations", "trendy": "modern creator look, lime accent",
}
EMOJI_RE = re.compile("[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0000FE0F\U0000200D]+")


def ass_text(s, upper=False):
    s = EMOJI_RE.sub("", s).strip()  # libass cannot draw colour emoji: keep them for descriptions only
    s = s.upper() if upper else s
    return s.replace("\\", "\\\\").replace("{", "(").replace("}", ")").replace("\n", "\\N")


def ts(t):
    t = max(0, t)
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


_FONT_FILES = {}
_PIL_FONTS = {}


def pil_font(name, px):
    """PIL font for an ASS font family name (to measure text for rounded caption boxes). None if it can't be found."""
    key = (name, px)
    if key in _PIL_FONTS:
        return _PIL_FONTS[key]
    f = None
    try:
        from PIL import ImageFont
        if not _FONT_FILES:
            for fn in os.listdir(FONTS):
                if fn.lower().endswith((".ttf", ".otf")):
                    try:
                        nm = " ".join(x for x in ImageFont.truetype(os.path.join(FONTS, fn), 20).getname() if x != "Regular")
                        _FONT_FILES[nm.lower()] = os.path.join(FONTS, fn)
                        _FONT_FILES.setdefault(os.path.splitext(fn)[0].replace("-", " ").lower(), os.path.join(FONTS, fn))
                    except Exception:
                        pass
        fp = _FONT_FILES.get(name.lower())
        f = ImageFont.truetype(fp, px) if fp else None
    except Exception:
        f = None
    _PIL_FONTS[key] = f
    return f


def text_metrics(name, px, txt):
    """(width, line height) in px. Falls back to an estimate when the font can't be loaded."""
    f = pil_font(name, px)
    if not f:
        return len(txt) * px * 0.55, px * 1.25
    asc, desc = f.getmetrics()
    return f.getlength(txt), asc + desc


def round_rect(w, h, r):
    """ASS drawing path of a rounded rectangle w x h with corner radius r (top-left at 0,0)."""
    w, h = int(round(w)), int(round(h))
    r = int(max(1, min(r, h // 2, w // 2)))
    c = int(round(r * 0.4477))  # r * (1 - 0.5523): bezier control offset for a quarter circle
    return (f"m {r} 0 l {w - r} 0 b {w - c} 0 {w} {c} {w} {r} l {w} {h - r} b {w} {h - c} {w - c} {h} {w - r} {h} "
            f"l {r} {h} b {c} {h} 0 {h - c} 0 {h - r} l 0 {r} b 0 {c} {c} 0 {r} 0")


def default_style(mode):
    return "pro" if mode == "pro" else "pop"


def video_preset(v, mode):
    """The caption preset for a video, with the video's `font` override (any bundled family, see `clip.py fonts`)."""
    P = dict(PRESETS.get(v.get("style") or default_style(mode), PRESETS["pop"]))
    if v.get("font"):
        P["font"] = v["font"]
    accent = v.get("accent") or (v.get("_brand_accent") if mode == "pro" else None)
    if accent:
        P["hi"] = accent  # the brand colour for *accent* words
    return P


def build_ass(v, W, H, total, path):
    k = min(W, H) / 1080
    portrait = H > W
    mode = v.get("_mode", "creator")
    pace = v.get("_pace", "medium")
    preset = video_preset(v, mode)
    pro = mode == "pro"
    ui_font, ui_heavy = ("Inter SemiBold", "Inter ExtraBold") if pro else ("TikTok Sans SemiBold", "Montserrat Black")
    styles, events = [], []

    boxmeta = {}

    def style(name, font, size, fill, outline, ol, sh, align, ml, mr, mv, box=False, back="black", back_alpha=0):
        # Box styles are drawn as rounded rectangles under the text (libass BorderStyle 3 can only make square boxes)
        if box:
            boxmeta[name] = {"font": font, "px": int(size * k), "al": align, "ml": ml, "mr": mr, "mv": mv, "back": back, "ba": back_alpha}
            ol, sh = 0, 0
        oc = ass_color(outline)
        styles.append(f"Style: {name},{font},{int(size * k)},{ass_color(fill)},{ass_color(fill)},{oc},{ass_color(back, 0x60)},0,0,0,0,100,100,0,0,1,{0 if box else max(1, int(ol * k))},{int(sh * k)},{align},{int(ml)},{int(mr)},{int(mv)},1")

    P = preset
    side = 0.08 * W
    right = (0.15 if portrait else 0.08) * W  # TikTok right rail
    bx = bool(P.get("box"))
    hook_mv = ((0.23 if v.get("header") else 0.15) if portrait else 0.08) * H  # sit under a persistent header, never on it
    cap_mv = (P.get("cap_mv", 0.30) if portrait else 0.10) * H
    for nm, sz, al, mv in (("hook", P["size"] * 1.18, 8, hook_mv), ("cap", P["size"], 2, cap_mv), ("mid", P["size"], 5, 0)):
        style(nm, P["font"], sz, P["fill"], P["outline"], P["ol"] + (1 if nm == "hook" and not bx else 0), P["sh"], al, side, right, mv, box=bx,
              back=P.get("boxcolor", P["outline"] if bx else "black"), back_alpha=P.get("boxalpha", 0))
        # auto-contrast fallback (see auto_contrast): same geometry on a dark plate, for busy or colour-clashing footage
        style(nm + "_plate", P["font"], sz, "white", "black", 12, 0, al, side, right, mv, box=True, back="#141418" if pro else "black",
              back_alpha=0x30 if pro else 0x58)
    style("box", ui_font, 70, "black", "white", 12, 0, 2, side, right, (0.30 if portrait else 0.10) * H, box=True, back="white")
    style("plate", ui_font, 70, "white", "black", 12, 0, 2, side, right, (0.30 if portrait else 0.10) * H, box=True, back="black", back_alpha=0x58)
    style("chip", "Inter SemiBold" if pro else "Nunito ExtraBold", 54 if pro else 56, "#1B1B1F", "#1B1B1F", 0, 0, 2, side, right,
          (0.22 if portrait else 0.08) * H, box=True, back="#E9E9EC", back_alpha=0x2E)
    style("callout", ui_heavy, 80, P["hi"] if pro else "yellow", "black", 3 if pro else 6, 0, 5, 0, 0, 0)
    style("header", "Inter ExtraBold" if pro else "TikTok Sans ExtraBold", 66, "black", "white", 14, 0, 8, side, right, (0.115 if portrait else 0.05) * H, box=True, back="white")
    style("card", P["font"], P["size"] * 1.35, "white", "black", 3 if pro else 6, 0, 5, side, side, 0)
    style("code", "JetBrains Mono ExtraBold", 60, "#7CFFB2", "black", 12, 0, 2, side, right, (0.30 if portrait else 0.12) * H, box=True, back="#0B0F14", back_alpha=0x20)
    style("lower", ui_font if pro else "Montserrat Bold", 56, "white", "black", 16, 0, 1, 0.06 * W, 0, (0.24 if portrait else 0.09) * H,
          box=True, back="#0B0B0F" if pro else "black", back_alpha=0x40 if pro else 0x50)
    style("title", ui_heavy, 104, "white", "black", 4 if pro else 8, 0 if pro else 4, 5, side, side, 0)
    style("meme-top", "Anton", 96, "white", "black", 6, 0, 8, side, side, 0.13 * H if portrait else 0.04 * H)
    style("meme-bottom", "Anton", 96, "white", "black", 6, 0, 2, side, side, 0.28 * H if portrait else 0.05 * H)

    hi = ass_color(P["hi"])
    fill_c = ass_color(P["fill"])
    upper_default = P["upper"]

    def mark(txt, hic, back):
        """*word* -> accent colour, then back to the style colour (a reset would also cancel the pop animation)."""
        return re.sub(r"\*([^*]+)\*", lambda m: "{\\1c" + hic + "}" + m.group(1) + "{\\1c" + back + "}", txt)

    def add_box(t0, t1, st, text, tags):
        """Rounded caption box: one rounded rectangle per text line (layer 0) under the text (layer 1), like TikTok's background look."""
        m = boxmeta[st]
        font, px, al = m["font"], m["px"], m["al"]
        fn = re.search(r"\\fn([^\\}]+)", tags)
        if fn:
            font = fn.group(1)  # a caption-level font override: measure with it so the box fits
        pm = re.search(r"\\pos\((-?\d+),(-?\d+)\)", tags)
        inner = "".join(re.findall(r"\{([^}]*)\}", re.sub(r"\{\\an5\\pos\([^)]*\)\}", "", tags)))
        box_inner = re.sub(r"\\c&H[0-9A-Fa-f]+&", "", inner)
        pad_x = 0.34 * px
        maxw = W - m["ml"] - m["mr"] - 2 * pad_x if not pm else W * 0.84 - 2 * pad_x
        # wrap on the visible text, keep override tags (accent colours) attached to their words
        lines = []
        for hard in text.split("\\N"):
            toks = re.split(r"(\{[^}]*\})", hard)
            plain = "".join(t for t in toks if not t.startswith("{")).replace("\\\\", "\\")
            words, cur, brk = plain.split(" "), "", set()
            pos_i = 0
            for wi, w in enumerate(words):
                trial = (cur + " " + w) if cur else w
                if cur and text_metrics(font, px, trial)[0] > maxw:
                    brk.add(pos_i - 1)  # index of the space before this word
                    cur = w
                else:
                    cur = trial
                pos_i += len(w) + 1
            out_l, line, idx, carry = [], "", 0, ""
            for t in toks:
                if t.startswith("{"):
                    line += t
                    if re.search(r"\\1?c&H", t) or "\\alpha" in t:
                        carry = t
                    continue
                for ch in t:
                    if idx in brk and ch == " ":
                        out_l.append(line); line = carry
                    else:
                        line += ch
                    idx += 1
            out_l.append(line)
            lines += out_l
        plains = [re.sub(r"\{[^}]*\}", "", ln).replace("\\\\", "\\") for ln in lines]
        n = len(lines)
        widths = [text_metrics(font, px, pl)[0] for pl in plains]
        ph = text_metrics(font, px, "Hg")[1]
        rad = 0.30 * ph
        if pm:
            cx, y0, h_al = int(pm.group(1)), int(pm.group(2)) - n * ph / 2, 2
        else:
            h_al = {1: 1, 2: 2, 0: 3}[al % 3]  # 1 left, 2 centre, 3 right
            cx = (m["ml"] + W - m["mr"]) / 2 if h_al == 2 else (m["ml"] if h_al == 1 else W - m["mr"])
            if al in (7, 8, 9):
                y0 = m["mv"]
            elif al in (4, 5, 6):
                y0 = (H - n * ph) / 2 + m["mv"]
            else:
                y0 = H - m["mv"] - n * ph
        an_t = {1: 4, 2: 5, 3: 6}[h_al]
        back_rgb = ass_color(m["back"])[4:]
        for i, (ln, pl, lw) in enumerate(zip(lines, plains, widths)):
            if not pl.strip():
                continue
            cy = int(y0 + (i + 0.5) * ph)
            rw = lw + 2 * pad_x
            rx = cx - (pad_x if h_al == 1 else -pad_x if h_al == 3 else 0)
            rect = (f"{{\\an{an_t}\\pos({int(rx)},{cy})\\bord0\\shad0\\1c&H{back_rgb}&\\1a&H{m['ba']:02X}&{box_inner}\\p1}}"
                    f"{round_rect(rw, ph, rad)}{{\\p0}}")
            events.append(f"Dialogue: 0,{ts(t0)},{ts(t1)},{st},,0,0,0,,{rect}")
            events.append(f"Dialogue: 1,{ts(t0)},{ts(t1)},{st},,0,0,0,,{{\\an{an_t}\\pos({int(cx)},{cy}){inner}}}{ln}")

    def add(t0, t1, st, text, tags=""):
        if st in boxmeta:
            return add_box(t0, t1, st, text, tags)
        events.append(f"Dialogue: 0,{ts(t0)},{ts(t1)},{st},,0,0,0,,{tags}{text}")

    POP = "{\\fscx72\\fscy72\\t(0,90,\\fscx106\\fscy106)\\t(90,150,\\fscx100\\fscy100)}"
    FADE = "{\\fad(120,100)}" if pace != "slow" else "{\\fad(220,160)}"
    RISE = "{\\fad(160,100)\\frx40\\t(0,220,\\frx0)}"  # a short tilt-up: the clean "pro" entrance
    halo = f"{{\\blur{P['blur']}}}" if P.get("blur") and not bx else ""

    if v.get("header"):
        hd = v["header"] if isinstance(v["header"], dict) else {"text": v["header"]}
        add(hd.get("t", 0), hd.get("until") or total, "header", ass_text(hd["text"]), "{\\fad(150,0)}")

    for c in v.get("captions", []):
        st = c.get("style", "cap")
        t0 = float(c.get("t", 0))
        d = float(c["d"]) if c.get("d") not in (None, "") else read_time(c.get("text", ""), pace)
        t1 = min(total, t0 + d)
        up = c.get("upper", upper_default if st in ("hook", "cap", "mid", "card") else False)
        pos = ""
        if "x" in c and "y" in c:
            pos = f"{{\\an5\\pos({int(c['x'] * W)},{int(c['y'] * H)})}}"
        if c.get("font"):
            pos += f"{{\\fn{c['font']}}}"
        main = st in ("hook", "cap", "mid", "callout") or st.endswith("_plate")
        anim = c.get("anim") or (P.get("anim") if main else None) or ("fade" if pace == "slow" or not main else "pop")
        a_tag = (POP if anim == "pop" else FADE if anim == "fade" else RISE if anim == "rise" else "") + (halo if st in ("hook", "cap", "mid") else "")
        if c.get("color"):
            pos += f"{{\\c{ass_color(c['color'])}}}"
        hic = ass_color(c["hi"]) if c.get("hi") else hi
        if c.get("color"):
            back_c = ass_color(c["color"])
        elif st in ("box", "chip"):
            back_c = ass_color("black")
        elif bx and st in ("hook", "cap", "mid"):
            back_c = fill_c
        elif st in ("plate",) or st.endswith("_plate"):
            back_c = ass_color("white")
        else:
            back_c = fill_c
        words = c["text"].replace("*", "").split()
        if c.get("words") and len(words) > 1:  # word-by-word groups, each popping in
            n = int(c.get("per") or (PACES.get(pace, PACES["medium"])["per"] if len(words) <= 8 else 3))
            groups = [" ".join(words[i:i + n]) for i in range(0, len(words), n)]
            weights = [max(3, len(g)) for g in groups]
            tt = t0
            for g, wgt in zip(groups, weights):
                gd = (t1 - t0) * wgt / sum(weights)
                add(tt, tt + gd, st, ass_text(g, up), pos + a_tag)
                tt += gd
        elif c.get("karaoke") and len(words) > 1:  # whole line, active word highlighted
            weights = [max(2, len(w)) for w in words]
            tt = t0
            for i, wgt in enumerate(weights):
                wd = (t1 - t0) * wgt / sum(weights)
                line = " ".join((f"{{\\c{hi}\\fscx108\\fscy108}}{ass_text(w, up)}{{\\r}}" if j == i else ass_text(w, up)) for j, w in enumerate(words))
                add(tt, tt + wd, st, line, pos)
                tt += wd
        elif c.get("type"):  # typewriter
            txt = ass_text(c["text"], up)
            steps = min(len(txt), 40)
            for i in range(1, steps + 1):
                cut = round(len(txt) * i / steps)
                tt = t0 + (t1 - t0) * 0.6 * (i - 1) / steps
                te = t0 + (t1 - t0) * 0.6 * i / steps if i < steps else t1
                add(tt, te, st, txt[:cut] + ("{\\alpha&HFF&}" + txt[cut:] if cut < len(txt) else ""), pos)
        else:
            add(t0, t1, st, mark(ass_text(c["text"], up), hic, back_c), pos + a_tag)

    head = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "WrapStyle: 0", "ScaledBorderAndShadow: yes", "",
            "[V4+ Styles]", f"Format: {STYLE_FIELDS}", *styles, "", "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text", *events]
    with open(path, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(head) + "\n")
    return len(events)


# ----------------------------------------------------------------------------- render: segments
def parse_fx(fx):
    name, _, arg = fx.partition(":")
    focus = None
    if "@" in arg:
        arg, f = arg.split("@", 1)
        focus = [float(x) for x in f.split(",")]
    return name, arg, focus


def even(x):
    return max(2, int(round(x / 2)) * 2)


def float_box(sw, sh, W, H, scale):
    """Size and position of the floating card for fit float[:scale]."""
    s = min(W * scale / sw, H * scale / sh)
    fw, fh = even(sw * s), even(sh * s)
    return fw, fh, (W - fw) // 2, (H - fh) // 2


def float_assets(fw, fh, W, H, seg_dir):
    """Rounded-corner mask + soft drop shadow pngs for a floating card (PIL). None when PIL is missing."""
    try:
        from PIL import Image, ImageDraw, ImageFilter
    except ImportError:
        return None
    r = max(10, int(min(fw, fh) * 0.045))
    mask = os.path.join(seg_dir, f"_mask_{fw}x{fh}_{r}.png")
    pad = max(12, int(min(W, H) * 0.04))
    shadow = os.path.join(seg_dir, f"_shadow_{fw}x{fh}_{r}_{pad}.png")
    if not os.path.exists(mask):
        m = Image.new("L", (fw, fh), 0)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, fw - 1, fh - 1], r, fill=255)
        m.save(mask)
    if not os.path.exists(shadow):
        a = Image.new("L", (fw + 2 * pad, fh + 2 * pad), 0)
        ImageDraw.Draw(a).rounded_rectangle([pad, pad, pad + fw - 1, pad + fh - 1], r, fill=150)
        a = a.filter(ImageFilter.GaussianBlur(pad / 2.4))
        img = Image.new("RGBA", a.size, (0, 0, 0, 0))
        img.putalpha(a)
        img.save(shadow)
    return mask, shadow, pad


def fit_chain(fit, W, H, focus, src_wh=None, aux=None):
    """Filter chain that frames one source into W x H. aux = input indexes of the float mask/shadow pngs."""
    fx_, fy_ = focus or (0.5, 0.5)
    name, _, arg = fit.partition(":")
    if name == "crop":
        x, y, w, h = [float(v) for v in arg.split(",")]
        return f"crop=iw*{w}:ih*{h}:iw*{x}:ih*{y}," + fit_chain("cover", W, H, focus)
    if name == "contain":
        return f"scale={W}:{H}:force_original_aspect_ratio=decrease:force_divisible_by=2,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black"
    bg = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},gblur=sigma=30,eq=brightness=-0.14:saturation=1.15"
    if name == "blurpad":  # blurpad:1.3 = the sharp copy 30% bigger (crops its sides) so less blur shows
        z = max(1.0, float(arg or 1))
        return (f"split=2[bga][fga];[bga]{bg}[bgb];"
                f"[fga]scale={int(W * z)}:{int(H * z)}:force_original_aspect_ratio=decrease:force_divisible_by=2,"
                f"crop=w='min(iw,{W})':h='min(ih,{H})':x='(iw-ow)*{fx_}':y='(ih-oh)*{fy_}'[fgb];[bgb][fgb]overlay=(W-w)/2:(H-h)/2")
    if name == "float" and src_wh and aux:  # a rounded card with a soft shadow floating over a blur of itself
        fw, fh, x0, y0 = float_box(*src_wh, W, H, float(arg or 0.86))
        mi, si, pad = aux
        return (f"split=2[bga][fga];[bga]{bg},eq=brightness=-0.06[bgb];[fga]scale={fw}:{fh},format=rgba[fgc];"
                f"[{mi}:v]format=gray[fgm];[fgc][fgm]alphamerge[fgd];[{si}:v]format=rgba[shd];"
                f"[bgb][shd]overlay={x0 - pad}:{y0 - pad + int(H * 0.008)}[bgs];[bgs][fgd]overlay={x0}:{y0},format=yuv420p")
    if name == "float":  # no PIL: a plain floating card
        return fit_chain(f"blurpad:{min(1.0, float(arg or 0.86))}", W, H, focus)
    if name == "stack" and src_wh and H > W:  # wide source in a tall frame: the whole shot on top, a close-up of the action below
        sw, sh = src_wh
        top = even(H * 0.10)  # under TikTok's top tabs: a blurred strip
        fh = min(even(W * sh / sw), even(H * 0.42))
        dh = H - top - fh
        return (f"split=3[sta][stb][stc];[sta]scale={W}:{top}:force_original_aspect_ratio=increase,crop={W}:{top},gblur=sigma=20,eq=brightness=-0.2[st1];"
                f"[stb]scale={W}:{fh}:force_original_aspect_ratio=increase,crop={W}:{fh},drawbox=x=0:y=ih-{even(H * 0.004)}:w=iw:h={even(H * 0.004)}:color=black@0.9:t=fill[st2];"
                f"[stc]scale={W}:{dh}:force_original_aspect_ratio=increase,crop={W}:{dh}:(iw-{W})*{fx_}:(ih-{dh})*{fy_}[st3];"
                f"[st1][st2][st3]vstack=inputs=3")
    if name == "stack":
        return fit_chain("blurpad", W, H, focus)
    # cover (default)
    return f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}:(iw-{W})*{fx_}:(ih-{H})*{fy_}"


def stack_window(sw, sh, W, H):
    """Crop fractions of the close-up part of fit stack."""
    top = even(H * 0.10)
    fh = min(even(W * sh / sw), even(H * 0.42))
    return window_frac(sw, sh, W, H - top - fh)


def track_chain(track, zoom, sw, sh, W, H):
    """Moving camera over a source frame: hold on a point, glide to the next. Keys {t, x, y, move}; x,y = the point to
    centre on, as fractions of the SOURCE frame; t = seconds into the clip as it plays; move = glide seconds (default 0.6).
    The first key is the starting position. Scaled to cover first, so the pan moves in whole output pixels (smooth)."""
    ks = sorted(track, key=lambda k: float(k.get("t", 0)))
    f = max(W / sw, H / sh) * max(1.0, float(zoom or 1))
    SW, SH = max(W, math.ceil(sw * f)), max(H, math.ceil(sh * f))

    def comp(key):
        e = f"{float(ks[0][key]):.4f}"
        for prev, k in zip(ks, ks[1:]):
            st = f"min(1,max(0,(t-{float(k.get('t', 0)):.3f})/{max(0.05, float(k.get('move', 0.6))):.3f}))"
            e += f"+({float(k[key]) - float(prev[key]):.4f})*({st}*{st}*(3-2*{st}))"
        return e
    return (f"scale={SW}:{SH}:flags=bicubic,crop={W}:{H}:x='max(0,min({SW - W},({comp('x')})*{SW}-{W / 2:g}))':"
            f"y='max(0,min({SH - H},({comp('y')})*{SH}-{H / 2:g}))'")


def build_segment(clip, W, H, fps, project, seg_dir, cfg, mode="creator"):
    """One clip -> normalized mp4 (W x H, fps, stereo 48k). Cached by content hash.
    Returns (path, seconds, framing note) where the note says what fit/focus/track `auto` chose."""
    if "card" in clip:
        src = None
    else:
        src = resolve_src(clip["src"], project)
    key_src = {"mt": os.path.getmtime(src), "sz": os.path.getsize(src)} if src else None
    key = sha({"c": {k: v for k, v in clip.items() if k not in ("caption", "chapter", "note", "transition_sfx")}, "W": W, "H": H, "fps": fps,
               "s": key_src, "m": mode, "v": SEG_VERSION}, 14)
    dst = os.path.join(seg_dir, f"{key}.mp4")
    note_path = dst[:-4] + ".json"
    is_img = bool(src) and os.path.splitext(src)[1].lower() in IMG_EXT
    speed = float(clip.get("speed", 1))
    fxs = list(clip.get("fx", []))
    freeze = 0.0
    for f in fxs:
        n, arg, _ = parse_fx(f)
        if n in ("speed", "slowmo"):
            speed = float(arg or 0.5)
        if n == "freeze":
            freeze += float(arg or 1)
    if src and not is_img and not clip.get("still"):
        info = ffprobe(src)
        s_in = float(clip.get("in", 0))
        s_out = float(clip.get("out", info["dur"]))
        s_out = min(s_out, info["dur"])
        base_dur = max(0.1, (s_out - s_in) / speed)
        has_audio = bool(info["audio"])
    else:
        info, s_in, has_audio = None, float(clip.get("in", 0)), False
        base_dur = float(clip.get("dur", 2.0))
    dur = round(base_dur + freeze, 3)
    if os.path.exists(dst) and os.path.getsize(dst) > 1000:
        try:
            note = json.load(open(note_path, encoding="utf-8"))
        except Exception:
            note = {}
        return dst, dur, note

    # framing: what fit / focus / track resolve to for this source shape in this frame (references/framing.md)
    note = {}
    sw = sh = None
    if src is not None:
        vinfo = (info or {}).get("video") if info else None
        if not vinfo:
            try:
                vinfo = ffprobe(src)["video"]
            except Exception:
                vinfo = None
        if vinfo and vinfo.get("w") and vinfo.get("h"):
            sw, sh = vinfo["w"], vinfo["h"]
    fit = clip.get("fit") or "auto"
    focus = clip.get("focus")
    track = clip.get("track")
    if sw:
        rec = rec_meta(clip.get("src", ""), project)
        fit = auto_fit(clip, is_img, sw, sh, W, H, mode, rec)
        if fit != (clip.get("fit") or "auto") and fit != "cover":
            note["fit"] = fit  # auto picked a layout (float, blurpad); a plain cover is the unremarkable case
        moving = not is_img and not clip.get("still")
        span = (s_in, max(0.3, (s_out - s_in))) if info else (s_in, 1.5)  # a still aims at what moves around its frame
        if track == "auto" and moving:
            fw, fh = window_frac(sw, sh, W, H, clip.get("zoom"))
            track = auto_track(src, span[0], span[1], sw, sh, fw, fh, speed)
            note.update({"fit": fit, "track": track})
        elif track == "auto":
            track = None
        r = (sw / sh) / (W / H)
        needs_aim = fit.split(":")[0] in ("cover", "stack", "blurpad") and not track and (focus in (None, "auto")) and not (0.9 <= r <= 1.1)
        if needs_aim and not is_img and fit.split(":")[0] != "blurpad":
            fw, fh = stack_window(sw, sh, W, H) if fit == "stack" else window_frac(sw, sh, W, H)
            focus, centre, how = auto_focus(src, span[0], span[1], sw, sh, fw, fh)
            note.update({"fit": fit, "focus": focus, "aim": how})
        elif focus == "auto":
            focus = None
    elif focus == "auto":
        focus = None
    if track == "auto":
        track = None

    inputs = []
    if src is None:
        inputs = ["-f", "lavfi", "-t", str(dur), "-i", f"color=c={clip.get('bg', 'black')}:s={W}x{H}:r={fps}"]
    elif is_img:
        inputs = ["-loop", "1", "-framerate", str(fps), "-t", str(dur), "-i", src]
    elif clip.get("still"):
        inputs = ["-ss", str(s_in), "-i", src]
    else:
        inputs = ["-ss", str(s_in), "-t", str(round(s_out - s_in, 3)), "-i", src]

    chain = []
    if clip.get("still"):
        chain.append(f"trim=end_frame=1,loop=loop=-1:size=1,fps={fps},trim=duration={dur},setpts=PTS-STARTPTS")
    if speed != 1 and not clip.get("still") and not is_img:
        chain.append(f"setpts=PTS/{speed}")
    v = [",".join(chain)] if chain else []
    aux_in, aux_idx = [], None
    if src is not None and sw and fit.split(":")[0] == "float":
        _a, _sep, farg = fit.partition(":")
        fw_, fh_, _x0, _y0 = float_box(sw, sh, W, H, float(farg or 0.86))
        made = float_assets(fw_, fh_, W, H, seg_dir)
        if made:
            mask, shadow, pad = made
            aux_in = ["-loop", "1", "-framerate", str(fps), "-t", str(dur), "-i", mask, "-loop", "1", "-framerate", str(fps), "-t", str(dur), "-i", shadow]
            aux_idx = (1, 2, pad)
    if src is not None and sw:  # what the crop ended up as, so overlays can be anchored to the source (anchor_overlays)
        eff = fit if not (fit.split(":")[0] == "float" and not aux_idx) else f"blurpad:{min(1.0, float(fit.partition(':')[2] or 0.86))}"
        note["geo"] = {"sw": sw, "sh": sh, "fit": "track" if track else eff, "focus": focus, "track": track or None, "zoom": clip.get("zoom"),
                       "fx": [[n_, arg_, ff_] for n_, arg_, ff_ in (parse_fx(f) for f in fxs) if n_ in ("zoom", "zoomin", "zoomout", "shake", "mirror")]}
    if src is not None and track and sw:
        v.append(track_chain(track, clip.get("zoom"), sw, sh, W, H))
    elif src is not None:
        v.append(fit_chain(fit, W, H, focus, (sw, sh) if sw else None, aux_idx))
    post = []
    for f in fxs:
        n, arg, ffocus = parse_fx(f)
        fx_, fy_ = ffocus or focus or (0.5, 0.5)
        if n == "bw":
            post.append("hue=s=0")
        elif n == "sepia":
            post.append("colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131")
        elif n == "contrast":
            post.append(f"eq=contrast={arg or 1.25}")
        elif n == "sat":
            post.append(f"eq=saturation={arg or 1.4}")
        elif n == "bright":
            post.append(f"eq=brightness={arg or 0.08}")
        elif n == "dim":
            post.append(f"eq=brightness=-{arg or 0.25}")
        elif n == "blur":
            post.append(f"gblur=sigma={arg or 12}")
        elif n == "vignette":
            post.append("vignette=PI/4")
        elif n == "zoom":
            z = float(arg or 1.3)
            post.append(f"crop={W}/{z}:{H}/{z}:({W}-{W}/{z})*{fx_}:({H}-{H}/{z})*{fy_},scale={W}:{H}")
        elif n in ("zoomin", "zoomout"):
            z = float(arg or 1.25)
            frames = max(1, int(dur * fps))
            zexpr = f"1+{z - 1}*min(1,on/{frames})" if n == "zoomin" else f"{z}-{z - 1}*min(1,on/{frames})"
            post.append(f"scale={int(W * 1.5)}:{int(H * 1.5)},zoompan=z='{zexpr}':x='(iw-iw/zoom)*{fx_}':y='(ih-ih/zoom)*{fy_}':d=1:s={W}x{H}:fps={fps}")
        elif n == "shake":
            amp = int(float(arg or 1) * W * 0.012) + 2
            post.append(f"crop={W - 2 * amp}:{H - 2 * amp}:x='{amp}+{amp}*sin(n*1.9)*cos(n*0.7)':y='{amp}+{amp}*cos(n*1.3)',scale={W}:{H}")
        elif n == "glitch":
            post.append("rgbashift=rh=-10:bh=10:gv=4,noise=alls=22:allf=t")
        elif n == "vhs":
            post.append("rgbashift=rh=4:bh=-4,noise=alls=16:allf=t,eq=saturation=1.3:contrast=1.08,gblur=sigma=0.7")
        elif n == "pixelate":
            px = int(arg or 24)
            post.append(f"scale=iw/{px}:ih/{px},scale={W}:{H}:flags=neighbor")
        elif n == "mirror":
            post.append("hflip")
        elif n == "flash":
            post.append(f"fade=in:st=0:d={arg or 0.25}:color=white")
        elif n == "fadein":
            post.append(f"fade=in:st=0:d={arg or 0.4}")
        elif n == "fadeout":
            post.append(f"fade=out:st={max(0, dur - float(arg or 0.5))}:d={arg or 0.5}")
        elif n == "reverse":
            post.append("reverse")
        elif n == "freeze":
            post.append(f"tpad=stop_mode=clone:stop_duration={arg or 1}")
        elif n in ("speed", "slowmo"):
            pass
        else:
            raise ValueError(
                f"unknown fx '{n}' (allowed: bw, sepia, contrast, sat, bright, dim, blur, vignette, "
                "zoom, zoomin, zoomout, shake, glitch, vhs, pixelate, mirror, flash, fadein, fadeout, "
                "reverse, freeze, speed, slowmo; see references/effects-cookbook.md)")
    if post:
        v.append(",".join(post))
    v.append(f"fps={fps},format=yuv420p,setsar=1,trim=duration={dur},setpts=PTS-STARTPTS")
    vgraph = "[0:v]" + ",".join(x for x in v if x) + "[vo]"
    # fit_chain may contain labelled sub-graphs (blurpad) -> join with ',' works because labels are inline

    audio_mode = clip.get("audio", "keep")
    if has_audio and audio_mode != "mute":
        vol = 1.0 if audio_mode == "keep" else float(audio_mode)
        a = []
        sp = speed
        while sp > 2.0:
            a.append("atempo=2.0"); sp /= 2.0
        while sp < 0.5:
            a.append("atempo=0.5"); sp /= 0.5
        if sp != 1:
            a.append(f"atempo={sp:.4f}")
        if "reverse" in [parse_fx(f)[0] for f in fxs]:
            a.append("areverse")
        a += [f"volume={vol}", "aresample=48000", "aformat=channel_layouts=stereo", "afade=t=in:d=0.03",
              f"afade=t=out:st={max(0, base_dur - 0.04):.3f}:d=0.04", f"apad,atrim=duration={dur}"]
        agraph = "[0:a]" + ",".join(a) + "[ao]"
        amap = ["-map", "[ao]"]
        extra_in = []
    else:
        agraph = None
        extra_in = ["-f", "lavfi", "-t", str(dur), "-i", "anullsrc=r=48000:cl=stereo"]
        amap = ["-map", f"{1 + (2 if aux_in else 0)}:a"]  # float's mask + shadow pngs sit at inputs 1 and 2
    fc = vgraph + (";" + agraph if agraph else "")
    cmd = ["ffmpeg", "-y", "-v", "error", *inputs, *aux_in, *extra_in, "-filter_complex", fc, "-map", "[vo]", *amap,
           "-t", str(dur), *ENC_SEG, *AUD, "-r", str(fps), dst]
    run(cmd)
    with open(note_path, "w", encoding="utf-8") as f:
        json.dump(note, f)
    return dst, dur, note


# ----------------------------------------------------------------------------- render: overlays + audio mix
# ----------------------------------------------------------------------------- highlights anchored to the source (references/highlighting.md)
POINTERS = ("arrow", "arrow-curved", "ring", "circle", "scribble", "underline", "bar", "box", "marker", "focus", "spotlight", "x", "check")
RECTS = ("box", "marker", "focus")
HL_COLORS = {"yellow": (255, 214, 10), "red": (255, 59, 48), "green": (52, 199, 89), "white": (255, 255, 255), "blue": (10, 132, 255),
             "orange": (255, 149, 0), "pink": (255, 45, 140), "black": (0, 0, 0)}


def _smooth(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def _track_at(keys, t):
    ks = sorted(keys, key=lambda k: float(k.get("t", 0)))
    out_ = []
    for comp in ("x", "y"):
        val = float(ks[0][comp])
        for prev, k in zip(ks, ks[1:]):
            val += (float(k[comp]) - float(prev[comp])) * _smooth((t - float(k.get("t", 0))) / max(0.05, float(k.get("move", 0.6))))
        out_.append(val)
    return out_


def src_to_out(geo, sx, sy, t, W, H):
    """Where a point of the SOURCE frame (fractions) lands in the W x H output at clip time t, as fractions of the output.
    Mirrors fit_chain / track_chain / the geometric fx. None when the layout can't be mapped (stack, crop), "moving" for
    fx that never hold still (zoomin, zoomout, shake)."""
    sw, sh = geo["sw"], geo["sh"]
    name, _, arg = str(geo["fit"]).partition(":")
    fx_, fy_ = geo.get("focus") or (0.5, 0.5)
    if name == "track":
        f = max(W / sw, H / sh) * max(1.0, float(geo.get("zoom") or 1))
        SW, SH = max(W, math.ceil(sw * f)), max(H, math.ceil(sh * f))
        cx, cy = _track_at(geo["track"], t)
        x0, y0 = max(0, min(SW - W, cx * SW - W / 2)), max(0, min(SH - H, cy * SH - H / 2))
        x, y = (sx * SW - x0) / W, (sy * SH - y0) / H
    elif name == "cover":
        f = max(W / sw, H / sh)
        SW, SH = sw * f, sh * f
        x, y = (sx * SW - (SW - W) * fx_) / W, (sy * SH - (SH - H) * fy_) / H
    elif name == "contain":
        s_ = min(W / sw, H / sh)
        x, y = ((W - sw * s_) / 2 + sx * sw * s_) / W, ((H - sh * s_) / 2 + sy * sh * s_) / H
    elif name == "blurpad":
        z = max(1.0, float(arg or 1))
        s_ = min(W * z / sw, H * z / sh)
        iw, ih = sw * s_, sh * s_
        cw, ch = min(iw, W), min(ih, H)
        x, y = ((W - cw) / 2 + sx * iw - (iw - cw) * fx_) / W, ((H - ch) / 2 + sy * ih - (ih - ch) * fy_) / H
    elif name == "float":
        fw, fh, x0, y0 = float_box(sw, sh, W, H, float(arg or 0.86))
        x, y = (x0 + sx * fw) / W, (y0 + sy * fh) / H
    else:
        return None
    for n_, arg_, ff_ in geo.get("fx", []):
        zx, zy = ff_ or geo.get("focus") or (0.5, 0.5)
        if n_ == "zoom":
            z = float(arg_ or 1.3)
            x, y = (x - (1 - 1 / z) * zx) * z, (y - (1 - 1 / z) * zy) * z
        elif n_ == "mirror":
            x = 1 - x
        elif n_ in ("zoomin", "zoomout", "shake"):
            return "moving"
    return x, y


def static_span(geo, ct0, ct1, pts, W, H, step=0.05):
    """The longest stretch of [ct0, ct1] (clip time) in which every source point in `pts` stays put in the output, i.e. the
    camera is holding. Returns (t_start, t_end) or None when the layout can't be mapped or never holds."""
    best, run0, ref, last = None, None, None, None
    t = ct0
    while t <= ct1 + 1e-6:
        ps = [src_to_out(geo, px, py, t, W, H) for px, py in pts]
        if any(p_ is None or p_ == "moving" for p_ in ps):
            return None
        if ref is None or any(abs(p_[0] - r_[0]) > 0.004 or abs(p_[1] - r_[1]) > 0.004 for p_, r_ in zip(ps, ref)):
            if run0 is not None and (best is None or last - run0 > best[1] - best[0]):
                best = (run0, last)
            run0, ref = t, ps
        last = t
        t += step
    if run0 is not None and (best is None or last - run0 > best[1] - best[0]):
        best = (run0, last)
    return best


def anchor_overlays(v, built, starts, durs, geos, project, W, H):
    """Overlays that carry `at` [sx, sy] / `box` [sx, sy, w, h] / `target` (a name record-web saved) are given in the SOURCE
    frame of the clip they sit on; this maps them through that clip's crop / track / zoom so they land on the thing.
    A highlight that can't be placed exactly (off-frame, the camera still moving, a layout it can't follow) is DROPPED, not
    drawn: no highlight beats a wrong one. Returns (overlays for the renderer, notes on what was dropped or moved, proof rows)."""
    outl, notes, proof = [], [], []
    for i, o in enumerate(v.get("overlays", [])):
        if not any(k in o for k in ("at", "box", "target")):
            outl.append(o)
            continue
        typ = o.get("type", "ring")
        t0 = float(o.get("t", 0)); d = float(o.get("d", 2.0)); t1 = t0 + d
        ci = o.get("clip")
        if ci is None:
            ci = max((k for k in range(len(starts)) if starts[k] <= t0 + 1e-6), default=0)
        what = o.get("what") or o.get("target") or f"overlays[{i}]"
        tag = f"overlays[{i}] {typ} '{what}'"
        if ci >= len(built) or not geos[ci]:
            notes.append(f"{tag} dropped: clips[{ci}] has no mappable source (a card, or not a recording)")
            continue
        geo = geos[ci]
        box = o.get("box")
        if o.get("target"):
            tg = (rec_meta(built[ci].get("src", ""), project).get("targets") or {}).get(o["target"])
            if not tg:
                notes.append(f"{tag} dropped: the recording behind clips[{ci}] has no target '{o['target']}' (add a record-web step {{\"target\":\"{o['target']}\",\"sel\":\"...\"}} and re-record)")
                continue
            box = tg["box"]
            lo_, hi_ = float(built[ci].get("in", 0)), float(built[ci].get("out", 1e9))
            if not lo_ - 0.05 <= float(tg.get("t", lo_)) <= hi_ + 0.05 and not o.get("any_time"):
                notes.append(f"{tag} dropped: target '{o['target']}' was measured at {tg.get('t')}s, outside clips[{ci}] ({lo_}-{hi_}s), where the page may look different")
                continue
        pts = [(box[0], box[1]), (box[0] + box[2], box[1] + box[3])] if box else [tuple(o["at"])]
        cstart = starts[ci]
        ct0, ct1 = max(0.0, t0 - cstart), max(0.0, min(durs[ci], t1 - cstart))
        span = static_span(geo, ct0, ct1, pts, W, H)
        if span is None:
            notes.append(f"{tag} dropped: clips[{ci}] uses a layout or move a highlight can't follow (stack/crop, zoomin/zoomout, shake)")
            continue
        a0, a1 = span
        if a1 - a0 < min(0.8, d) - 1e-6:
            notes.append(f"{tag} dropped: the camera moves for most of {t0:.1f}-{t1:.1f}s (track glide / zoom). Hold the shot there, or put the highlight on a steady stretch")
            continue
        P = [src_to_out(geo, px, py, a0, W, H) for px, py in pts]
        xs, ys = [p_[0] for p_ in P], [p_[1] for p_ in P]
        x_min, x_max, y_min, y_max = min(xs), max(xs), min(ys), max(ys)
        tol = 0.012
        if x_min < -tol or y_min < -tol or x_max > 1 + tol or y_max > 1 + tol:
            notes.append(f"{tag} dropped: the target is outside the frame at {cstart + a0:.1f}s (x {x_min:.2f}-{x_max:.2f}, y {y_min:.2f}-{y_max:.2f}); aim the camera at it (focus / track) or pick another shot")
            continue
        r = {k: val for k, val in o.items() if k not in ("at", "box", "target", "clip")}
        r["t"], r["d"] = round(cstart + a0, 3), round(min(d, a1 - a0), 3)
        bw, bh = x_max - x_min, y_max - y_min
        cx, cy = (x_min + x_max) / 2, (y_min + y_max) / 2
        pad = float(o.get("pad", 0.012))
        if typ in RECTS:
            if not box:
                notes.append(f"{tag} dropped: a {typ} needs `box` or `target`, not a single point")
                continue
            px_, py_ = pad, pad * W / H
            r.update(x=max(0.0, x_min - px_), y=max(0.0, y_min - py_), w=min(1.0, bw + 2 * px_), h=min(1.0, bh + 2 * py_))
        elif typ == "spotlight":
            r.update(x=cx, y=cy, r=float(o.get("r", max(0.1, 0.5 * math.hypot(bw * W, bh * H) / W * 1.15))))
        elif typ in ("ring", "circle", "scribble"):
            r.update(x=cx, y=cy, r=float(o["r"]) if o.get("r") else (max(0.05, 0.5 * max(bw, bh * H / W) * 1.3 + 0.01) if box else 0.09))
        elif typ == "bar":  # a clean straight underline, as wide as the target
            if not box:
                notes.append(f"{tag} dropped: a bar needs `box` or `target`")
                continue
            r.update(x=x_min, y=min(0.99, y_max + 0.004), w=bw, h=max(0.004, 0.0065 * W / H))
        elif typ == "underline":  # the hand-drawn png
            r.update(x=cx, y=(y_max if box else cy) + 0.006, w=float(o.get("w", max(0.18, bw if box else 0.3))))
        elif typ in ("arrow", "arrow-curved"):
            wlen = float(o.get("w", 0.28))
            chosen = None
            for a_ in ([o["angle"]] if o.get("angle") is not None else [90, 0, 180, 270]):  # 90 = pointing down (arrow sits above), 0 = pointing right
                ar = math.radians(float(a_))
                tx, ty = cx - math.cos(ar) * (bw / 2 if box else 0.0), cy - math.sin(ar) * (bh / 2 if box else 0.0)  # tip on the edge facing the arrow
                bx, by = tx - math.cos(ar) * wlen, ty - math.sin(ar) * wlen * W / H
                if 0.03 <= bx <= 0.97 and 0.03 <= by <= 0.97:
                    chosen = (a_, tx, ty)
                    break
            if chosen is None:
                if o.get("angle") is None:
                    notes.append(f"{tag} dropped: no direction leaves the arrow's body inside the frame; use a box or marker instead")
                    continue
                chosen = (o["angle"], cx, cy)
            r.update(angle=chosen[0], x=chosen[1], y=chosen[2])
        else:  # x / check
            r.update(x=cx, y=cy)
        outl.append(r)
        proof.append({"i": i, "type": typ, "what": what, "t": r["t"], "d": r["d"], "xy": [round(cx, 3), round(cy, 3)]})
        if abs(r["t"] - t0) > 0.15:
            notes.append(f"{tag} moved from {t0:.1f}s to {r['t']:.1f}s to wait for the camera to settle")
    return outl, notes, proof


def hl_rgb(color):
    c = str(color or "yellow")
    if c.startswith("#") and len(c) == 7:
        return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))
    return HL_COLORS.get(c, HL_COLORS["yellow"])


def hl_png(kind, W, H, o, dst_dir):
    """A rounded highlight as a transparent png (PIL): `box` (outline + faint tint), `marker` (a highlighter swipe),
    `focus` (the whole frame dimmed except a rounded window). Returns (path, x_px, y_px) or None without PIL."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return None
    x, y, w, h = int(o["x"] * W), int(o["y"] * H), max(4, int(o["w"] * W)), max(4, int(o["h"] * H))
    rgb = hl_rgb(o.get("color", "red" if kind == "box" else "yellow"))
    thick = max(3, int(o.get("thick", max(4, W * 0.0055))))
    rad = int(o.get("radius", min(26, max(6, min(w, h) * 0.2))))
    key = sha({"k": kind, "w": w, "h": h, "c": rgb, "t": thick, "r": rad, "W": W, "H": H}, 10)
    path = os.path.join(dst_dir, f"hl_{kind}_{key}.png")
    if os.path.exists(path):
        return path, x, y
    S = 3  # supersample, then shrink: smooth corners
    if kind == "focus":
        im = Image.new("RGBA", (W * S, H * S), (0, 0, 0, int(255 * float(o.get("dim", 0.6)))))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([x * S, y * S, (x + w) * S, (y + h) * S], rad * S, fill=(0, 0, 0, 0))
        d.rounded_rectangle([x * S, y * S, (x + w) * S, (y + h) * S], rad * S, outline=rgb + (235,), width=max(2, thick // 2) * S)
        im.resize((W, H), Image.LANCZOS).save(path)
        return path, 0, 0
    im = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if kind == "bar":
        d.rounded_rectangle([0, 0, w * S - 1, h * S - 1], h * S // 2, fill=rgb + (245,))
    elif kind == "marker":
        d.rounded_rectangle([0, 0, w * S - 1, h * S - 1], max(4, rad // 2) * S, fill=rgb + (int(255 * float(o.get("alpha", 0.36))),))
    else:
        d.rounded_rectangle([0, 0, w * S - 1, h * S - 1], rad * S, fill=rgb + (22,), outline=rgb + (245,), width=thick * S)
    im.resize((w, h), Image.LANCZOS).save(path)
    return path, x, y


OV_TIP = {"arrow": (0.95, 0.5), "arrow-curved": (0.84, 0.76)}  # where the tip sits inside the png (normalized)


def overlay_graph(v, W, H, fps, total, inputs_start, ov_dir=None):
    """Returns (extra_inputs, filter_lines, out_label). Base video is [vbase]."""
    ins, lines = [], []
    cur = "vbase"
    n_in = inputs_start
    for i, o in enumerate(v.get("overlays", [])):
        typ = o.get("type", "sticker")
        t0 = float(o.get("t", 0)); d = float(o.get("d", total - t0)); t1 = min(total, t0 + d)
        en = f"enable='between(t,{t0:.3f},{t1:.3f})'"
        nxt = f"v{i}"
        if typ in RECTS or typ == "bar":
            made = hl_png(typ, W, H, o, ov_dir) if ov_dir else None
            if made:
                path, px_, py_ = made
                ins += ["-loop", "1", "-framerate", str(fps), "-t", str(total), "-i", path]
                lines.append(f"[{n_in}:v]format=rgba,fade=in:st={t0:.3f}:d=0.14:alpha=1,fade=out:st={max(t0, t1 - 0.14):.3f}:d=0.14:alpha=1[r{i}];"
                             f"[{cur}][r{i}]overlay={px_}:{py_}:eof_action=pass:{en}[{nxt}]")
                n_in += 1
            else:  # no PIL: plain rectangles
                x, y, w, h = o["x"], o["y"], o["w"], o["h"]
                bx, by, bw_, bh_ = int(x * W), int(y * H), int(w * W), int(h * H)
                if typ == "focus":
                    lines.append(f"[{cur}]drawbox=x=0:y=0:w=iw:h={by}:color=black@0.6:t=fill:{en},drawbox=x=0:y={by + bh_}:w=iw:h=ih-{by + bh_}:color=black@0.6:t=fill:{en},"
                                 f"drawbox=x=0:y={by}:w={bx}:h={bh_}:color=black@0.6:t=fill:{en},drawbox=x={bx + bw_}:y={by}:w=iw-{bx + bw_}:h={bh_}:color=black@0.6:t=fill:{en}[{nxt}]")
                elif typ in ("marker", "bar"):
                    lines.append(f"[{cur}]drawbox=x={bx}:y={by}:w={bw_}:h={bh_}:color={o.get('color', 'yellow')}@{0.36 if typ == 'marker' else 0.95}:t=fill:{en}[{nxt}]")
                else:
                    lines.append(f"[{cur}]drawbox=x={bx}:y={by}:w={bw_}:h={bh_}:color={o.get('color', 'red')}@0.95:t={int(o.get('thick', 8))}:{en}[{nxt}]")
        elif typ == "censor":
            x, y, w, h = o["x"], o["y"], o["w"], o["h"]
            cw, ch = max(2, int(w * W)) // 2 * 2, max(2, int(h * H)) // 2 * 2
            lines.append(f"[{cur}]split=2[c{i}a][c{i}b];[c{i}b]crop={cw}:{ch}:{int(x * W)}:{int(y * H)},boxblur=24:3[c{i}c];[c{i}a][c{i}c]overlay={int(x * W)}:{int(y * H)}:{en}[{nxt}]")
        elif typ == "fx":
            f = o.get("fx", "bw")
            flt = {"bw": "hue=s=0", "dim": "eq=brightness=-0.25", "sat": "eq=saturation=1.5", "invert": "negate", "blur": "gblur=sigma=14"}.get(f, "hue=s=0")
            lines.append(f"[{cur}]{flt}:{en}[{nxt}]")
        elif typ == "flash":
            ins += ["-f", "lavfi", "-t", str(total), "-i", f"color=c={o.get('color', 'white')}:s={W}x{H}:r={fps}"]
            fd = float(o.get("d", 0.3))
            lines.append(f"[{n_in}:v]format=rgba,fade=in:st={t0}:d={fd / 3:.3f}:alpha=1,fade=out:st={t0 + fd / 3:.3f}:d={fd * 2 / 3:.3f}:alpha=1[f{i}];[{cur}][f{i}]overlay=0:0:enable='between(t,{t0},{t0 + fd})'[{nxt}]")
            n_in += 1
        elif typ == "progress":
            ins += ["-f", "lavfi", "-t", str(total), "-i", f"color=c={o.get('color', 'white')}:s={W}x{int(o.get('h', 10))}:r={fps}"]
            yy = 0 if o.get("pos", "top") == "top" else H - int(o.get("h", 10))
            lines.append(f"[{cur}][{n_in}:v]overlay=x='-W+W*t/{total:.3f}':y={yy}[{nxt}]")
            n_in += 1
        elif typ == "spotlight":
            r = float(o.get("r", 0.18)) * W
            m = max(2, int(r * 8)) // 2 * 2  # hole radius = 1/8 of mask side
            big = max(W, H) * 2 + m
            ox, oy = int(o["x"] * W - big / 2), int(o["y"] * H - big / 2)
            ins += ["-loop", "1", "-framerate", str(fps), "-t", str(total), "-i", os.path.join(ASSETS, "overlays", "spotlight-mask.png")]
            pad = (big - m) // 2
            lines.append(f"[{n_in}:v]format=rgba,scale={m}:{m},pad={big}:{big}:{pad}:{pad}:color=black@0.72,fade=in:st={t0}:d=0.2:alpha=1[s{i}];"
                         f"[{cur}][s{i}]overlay={ox}:{oy}:{en}[{nxt}]")
            n_in += 1
        else:  # arrow / ring / sticker / meme / gif / video / image overlay
            asset = o.get("asset")
            color = o.get("color", "red")
            if typ in ("arrow", "arrow-curved"):
                asset = f"overlay:{typ}-{color}"
            elif typ in ("ring", "circle"):
                asset = f"overlay:ring-{color}"
            elif typ == "scribble":
                asset = f"overlay:scribble-circle-{color}"
            elif typ == "underline":
                asset = f"overlay:underline-{color}"
            elif typ in ("x", "check"):
                asset = "overlay:x-mark-red" if typ == "x" else "overlay:check-mark-green"
            path = resolve_asset(asset)
            ext = os.path.splitext(path)[1].lower()
            moving = ext in (".mp4", ".webm", ".gif", ".mov", ".mkv")
            if moving:
                ins += (["-stream_loop", "-1"] if o.get("loop", True) else []) + ["-i", path]
            else:
                ins += ["-loop", "1", "-framerate", str(fps), "-t", str(total), "-i", path]
            # size
            if typ in ("ring", "circle", "scribble"):
                wpx = int(2 * float(o.get("r", 0.12)) * W / (0.93 if typ != "scribble" else 0.86))
            else:
                wpx = int(float(o.get("w", 0.28 if typ.startswith("arrow") else 0.42)) * W)
            wpx = max(16, wpx // 2 * 2)
            from_png_h = None
            if not moving:
                try:
                    iw, ih = png_size(path)
                    from_png_h = ih / iw
                except Exception:
                    pass
            hpx = int(wpx * (from_png_h or 1))
            chain = [f"[{n_in}:v]"]
            f = []
            if moving:
                f.append(f"setpts=PTS-STARTPTS+{t0}/TB")
            f.append(f"format=rgba,scale={wpx}:-2")
            if o.get("key"):
                kc = {"green": "0x00FF00", "blue": "0x0000FF", "black": "0x000000", "white": "0xFFFFFF"}.get(o["key"], o["key"])
                f.append(f"colorkey={kc}:0.3:0.12")
            ang = float(o.get("angle", 0))
            rot_w, rot_h = wpx, hpx
            if ang:
                a = math.radians(ang)
                rot_w = int(abs(wpx * math.cos(a)) + abs(hpx * math.sin(a))) // 2 * 2 + 2
                rot_h = int(abs(wpx * math.sin(a)) + abs(hpx * math.cos(a))) // 2 * 2 + 2
                f.append(f"rotate={a:.5f}:c=none:ow={rot_w}:oh={rot_h}")
            if o.get("fade", True):
                f.append(f"fade=in:st={t0}:d=0.12:alpha=1")
                if not moving:
                    f.append(f"fade=out:st={max(t0, t1 - 0.15):.3f}:d=0.15:alpha=1")
            lines.append(chain[0] + ",".join(f) + f"[o{i}]")
            # position: x,y = centre; for arrows x,y = the point the tip touches
            cx, cy = float(o.get("x", 0.5)) * W, float(o.get("y", 0.5)) * H
            if typ in OV_TIP:
                tx, ty = OV_TIP[typ]
                dx, dy = (tx - 0.5) * wpx, (ty - 0.5) * hpx
                a = math.radians(ang)
                rx, ry = dx * math.cos(a) - dy * math.sin(a), dx * math.sin(a) + dy * math.cos(a)
                cx, cy = cx - rx, cy - ry
            x0, y0 = cx - rot_w / 2, cy - rot_h / 2
            anim = o.get("anim", "bob" if typ.startswith("arrow") else "pop")
            if anim == "bob":
                a = math.radians(ang)
                amp = 0.018 * W
                xe = f"{x0:.1f}-{amp * math.cos(a):.1f}*abs(sin(2*PI*1.6*t))"
                ye = f"{y0:.1f}-{amp * math.sin(a):.1f}*abs(sin(2*PI*1.6*t))"
            elif anim == "slide":
                xe = f"{x0:.1f}"
                ye = f"{y0:.1f}+max(0,1-(t-{t0})/0.18)*{H * 0.35:.0f}"
            elif anim == "shake":
                xe = f"{x0:.1f}+6*sin(t*53)"
                ye = f"{y0:.1f}+6*cos(t*47)"
            else:
                xe, ye = f"{x0:.1f}", f"{y0:.1f}"
            lines.append(f"[{cur}][o{i}]overlay=x='{xe}':y='{ye}':eof_action=pass:{en}[{nxt}]")
            n_in += 1
        cur = nxt
    return ins, lines, cur, n_in


def png_size(path):
    with open(path, "rb") as f:
        head = f.read(32)
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        import struct
        return struct.unpack(">II", head[16:24])
    info = ffprobe(path)["video"]
    return info["w"], info["h"]


SFX_LUFS, MUSIC_LUFS, SFX_MAX_S = -18.0, -16.0, 4.0  # every sound is levelled to these first; `vol` is then relative to them
FINAL_LUFS, FINAL_TP = -14.0, -2.0  # -2 dB true peak: leaves room for the AAC encode


def audio_graph(v, total, base_in, n_in, has_product_music):
    """Sound design in one graph. Library sounds differ by 25+ dB in loudness, so each SFX and the music bed is levelled to a
    reference first and `vol` then means the same thing for every sound. SFX get short fades and a length cap, and they
    duck the music together with the product audio (a gentle compressor, not a pump). Ends on a limiter; the overall level
    is set afterwards from the measured mix (finish_audio), never by boosting a quiet mix into its peaks."""
    ins, lines = [], []
    prod_vol = float(v.get("product_volume", 1.0))
    lines.append(f"[{base_in}]volume={prod_vol}[pa0]")
    music = v.get("music")
    sfx = v.get("sfx", [])
    keys = ["[pa1]"]
    lines.append("[pa0]asplit=2[pa][pa1]" if music else "[pa0]anull[pa]")
    sfx_labels = []
    for j, s in enumerate(sfx):
        path = resolve_asset(s["asset"])
        ins += ["-i", path]
        t = float(s.get("t", 0)); ms = int(max(0.0, t) * 1000)
        m = loudness_of(path)
        gain = 10 ** (gain_to(path, SFX_LUFS) / 20) * float(s.get("vol", 0.7))
        st = float(s.get("start", 0))
        length = float(s["dur"]) if s.get("dur") else min(SFX_MAX_S, max(0.05, m["dur"] - st))
        fo = min(0.25, max(0.02, length * 0.25))
        lines.append(f"[{n_in}:a]atrim=start={st}:duration={length:.3f},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,"
                     f"volume={gain:.4f},afade=t=in:d=0.004,afade=t=out:st={max(0.0, length - fo):.3f}:d={fo:.3f},adelay={ms}|{ms}[s{j}]")
        sfx_labels.append(f"[s{j}]")
        n_in += 1
    if sfx_labels and music:  # the SFX bus also feeds the ducking key
        lines.append("".join(sfx_labels) + f"amix=inputs={len(sfx_labels)}:normalize=0:duration=longest,asplit=2[sfxbus][sfxkey]")
        keys.append("[sfxkey]")
        mix = ["[pa]", "[sfxbus]"]
    else:
        mix = ["[pa]"] + sfx_labels
    if music:
        mm = music if isinstance(music, dict) else {"asset": music}
        path = resolve_asset(mm["asset"])
        ins += ["-stream_loop", "-1", "-i", path]
        st = float(mm.get("start", 0)); vol = float(mm.get("vol", 0.16))
        gain = 10 ** (gain_to(path, MUSIC_LUFS) / 20) * vol
        lines.append(f"[{n_in}:a]atrim=start={st},asetpts=PTS-STARTPTS,atrim=duration={total:.3f},aresample=48000,aformat=channel_layouts=stereo,"
                     f"highpass=f=45,volume={gain:.4f},afade=t=in:d=0.8,afade=t=out:st={max(0, total - 1.8):.3f}:d=1.8[mus0]")
        if mm.get("duck", True):
            lines.append(("".join(keys) + "amix=inputs=2:normalize=0[key];" if len(keys) == 2 else f"{keys[0]}anull[key];") +
                         "[mus0][key]sidechaincompress=threshold=0.05:ratio=3:attack=20:release=500:makeup=1[mus]")
        else:
            lines.append("".join(keys) + "anullsink;[mus0]anull[mus]")
        mix.append("[mus]")
        n_in += 1
    lines.append("".join(mix) + f"amix=inputs={len(mix)}:normalize=0:duration=first,alimiter=limit=0.89:attack=4:release=80:level=disabled,aresample=48000[aout]")
    return ins, lines, n_in


def finish_audio(video_only, mix_wav, dst, cfg):
    """Set the overall level from the measured mix: towards -14 LUFS, but never past -1.5 dB true peak (a mix of a quiet bed
    and a few SFX stays natural instead of being cranked into a limiter). Muxes the textless master."""
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", mix_wav, "-af", f"loudnorm=I={FINAL_LUFS}:TP={FINAL_TP}:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", p.stderr or "", re.S)
    gain, info = 0.0, {}
    if m:
        try:
            j = json.loads(m.group(0))
            i_, tp = float(j["input_i"]), float(j["input_tp"])
            if i_ > -60:
                gain = max(-24.0, min(FINAL_LUFS - i_, FINAL_TP - tp, 12.0))
                info = {"mix_lufs": round(i_, 1), "gain_db": round(gain, 1), "peak_db": round(tp + gain, 1)}
        except (ValueError, KeyError):
            pass
    run(["ffmpeg", "-y", "-v", "error", "-i", video_only, "-i", mix_wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
         "-af", f"volume={gain:.2f}dB,alimiter=limit=0.84:attack=3:release=60:level=disabled", *AUD, "-movflags", "+faststart", dst])
    return info


def write_description(v, cfg, base_path, total):
    desc = v.get("description")
    links = v.get("links") or []
    if not desc:
        open(base_path, "w").close()  # extensionless empty file = "no description" marker
        return base_path
    tags = " ".join("#" + t.lstrip("#") for t in v.get("tags", []))
    parts = [desc.strip()]
    if v.get("chapters"):
        parts.append("\n".join(f"{int(c['t'] // 60)}:{int(c['t'] % 60):02d} {c['title']}" for c in v["chapters"]))
    if links:
        parts.append("\n".join(links))
    if v.get("mentions"):
        parts.append(" ".join(v["mentions"]))
    if tags and tags not in desc:
        parts.append(tags)
    if v.get("sound_note"):
        parts.append(f"[posting note — not part of caption] sound: {v['sound_note']}")
    p = base_path + ".txt"
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n\n".join(parts) + "\n")
    return p


LEDGER_COLS = ["id", "date", "pass", "format", "dur", "title", "tags", "series", "file", "sources", "hook", "style", "plan_hash"]


def ledger_path(project):
    return os.path.join(pdir("output", project), "videos.csv")


def read_ledger(project):
    p = ledger_path(project)
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_ledger_row(project, row):
    rows = [r for r in read_ledger(project) if r["id"] != row["id"]] + [row]
    with open(ledger_path(project), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LEDGER_COLS, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)


# ----------------------------------------------------------------------------- caption contrast (auto)
def _lin(c):
    c /= 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def _rel_lum(rgb):
    return 0.2126 * _lin(rgb[0]) + 0.7152 * _lin(rgb[1]) + 0.0722 * _lin(rgb[2])


def _ratio(a, b):
    la, lb = _rel_lum(a), _rel_lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def _hex(c):
    names = {"white": "FFFFFF", "black": "000000", "yellow": "FFE600", "red": "FF2D2D", "green": "2BE36B", "blue": "2D8CFF",
             "pink": "FF3EA5", "orange": "FF8A00", "cyan": "00E5FF", "tiktok": "FE2C55", "purple": "9B5CFF"}
    c = names.get(c, c).lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def cap_region(c, preset, W, H, portrait, has_header):
    """Rough pixel box (x, y, w, h) a caption will cover, from its style geometry."""
    k = min(W, H) / 1080
    st = c.get("style", "cap")
    size = preset["size"] * k * (1.18 if st == "hook" else 1)
    text = c.get("text", "").replace("*", "")
    side, right = 0.08 * W, (0.15 if portrait else 0.08) * W
    avail = W - side - right
    tw = min(avail, len(text) * size * 0.52)
    lines = max(1, math.ceil(len(text) * size * 0.52 / avail))
    th = lines * size * 1.3
    if "x" in c and "y" in c:
        cx, cy = c["x"] * W, c["y"] * H
        x0, y0 = cx - tw / 2, cy - th / 2
    else:
        cx = side + avail / 2
        x0 = cx - tw / 2
        if st == "hook":
            y0 = ((0.23 if has_header else 0.15) if portrait else 0.08) * H
        elif st == "mid":
            y0 = H / 2 - th / 2
        else:
            y0 = H - ((preset.get("cap_mv", 0.30) if portrait else 0.10) * H) - th
    x0, y0 = max(0, min(W - 8, x0)), max(0, min(H - 8, y0))
    return int(x0), int(y0), int(max(8, min(tw, W - x0))), int(max(8, min(th, H - y0)))


def sample_region(video, t, region, W, H):
    """(mean_rgb, luma_std 0-1) of a region of the frame at time t."""
    x, y, w, h = region
    p = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", video, "-frames:v", "1", "-vf", f"crop={w}:{h}:{x}:{y},scale=24:24:flags=area",
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"], capture_output=True)
    d = p.stdout
    if len(d) < 24 * 24 * 3:
        return None
    px = [(d[i], d[i + 1], d[i + 2]) for i in range(0, 24 * 24 * 3, 3)]
    mean = tuple(sum(q[j] for q in px) / len(px) for j in range(3))
    ys = [(0.299 * q[0] + 0.587 * q[1] + 0.114 * q[2]) / 255 for q in px]
    ym = sum(ys) / len(ys)
    return mean, (sum((v - ym) ** 2 for v in ys) / len(ys)) ** 0.5


def auto_contrast(caps, textless, preset, W, H, total, has_header):
    """Look at the real footage under each caption and fix what would clash: busy background -> dark plate, tinted text that
    matches the background -> white, accent word that matches -> a colour that doesn't. Returns (captions, notes)."""
    portrait = H > W
    out_caps, notes = [], []
    for c in caps:
        st = c.get("style", "cap")
        if st not in ("hook", "cap", "mid") or c.get("contrast") is False or preset.get("box"):
            out_caps.append(c); continue
        t0, d = float(c.get("t", 0)), float(c.get("d", 2))
        region = cap_region(c, preset, W, H, portrait, has_header)
        samples = [sample_region(textless, min(max(0, total - 0.1), t0 + f * d), region, W, H) for f in (0.15, 0.5, 0.85)]
        samples = [s_ for s_ in samples if s_]
        if not samples:
            out_caps.append(c); continue
        busy = max(s_[1] for s_ in samples)
        fill = c.get("color") or preset["fill"]
        c2, fix = dict(c), []
        plate = busy > 0.20 and not preset.get("no_plate")
        if plate:  # on a dark plate the text is judged against the plate, not the footage
            c2["style"] = st + "_plate"; fix.append(f"busy background (detail {busy:.2f}) -> dark plate")
            samples = [((20, 20, 24), 0.0)]
        if fill not in ("white", "black", "#FFFFFF", "#000000") and min(_ratio(_hex(fill), s_[0]) for s_ in samples) < 1.9:
            c2["color"] = "white"; fix.append(f"{fill} text clashed with the background -> white")
        if "*" in c.get("text", ""):
            hi = c.get("hi") or preset["hi"]
            if min(_ratio(_hex(hi), s_[0]) for s_ in samples) < 1.9:
                best = max(("yellow", "white", "cyan", "pink", "orange"), key=lambda n: min(_ratio(_hex(n), s_[0]) for s_ in samples))
                c2["hi"] = best; fix.append(f"accent {hi} clashed -> {best}")
        if fix:
            notes.append({"t": round(t0, 1), "text": c.get("text", "")[:24], "fix": "; ".join(fix)})
        out_caps.append(c2)
    return out_caps, notes


# Friendly transition names -> ffmpeg xfade names (references/effects-cookbook.md, "Transitions"). Any xfade name in XFADE works too.
TRANSITIONS = {
    "none": None, "cut": None,
    "fade": "fade", "crossfade": "fade", "dissolve": "dissolve", "dip": "fadeblack", "fadeblack": "fadeblack",
    "flash": "fadewhite", "fadewhite": "fadewhite", "fadegrays": "fadegrays",
    "whip": "slideleft", "whipleft": "slideleft", "whipright": "slideright", "whipup": "slideup", "whipdown": "slidedown",
    "push": "slideleft", "pushleft": "slideleft", "pushright": "slideright", "pushup": "slideup", "pushdown": "slidedown",
    "zoom": "zoomin", "iris": "circleopen", "irisclose": "circleclose", "blur": "hblur", "glitch": "pixelize",
    "squeeze": "squeezeh", "reveal": "revealleft", "cover": "coverleft", "smooth": "smoothleft", "radial": "radial",
}
XFADE = {"fade", "fadeblack", "fadewhite", "fadegrays", "dissolve", "wipeleft", "wiperight", "wipeup", "wipedown", "slideleft", "slideright",
         "slideup", "slidedown", "smoothleft", "smoothright", "smoothup", "smoothdown", "circleopen", "circleclose", "circlecrop", "rectcrop",
         "radial", "pixelize", "hblur", "zoomin", "squeezeh", "squeezev", "coverleft", "coverright", "coverup", "coverdown", "revealleft",
         "revealright", "revealup", "revealdown", "horzopen", "horzclose", "vertopen", "vertclose", "distance", "diagtl", "diagbr", "hlwind", "hrwind"}
WHIPS = {"whip": "h", "whipleft": "h", "whipright": "h", "whipup": "v", "whipdown": "v"}
TRANSITION_DEFAULT = 0.35
# what a transition sounds like when transition_sfx is true (whips default to it): creator, pro
TRANSITION_SFX = {"whip": ("sfx:whoosh", "sfx:swoosh-fast"), "push": ("sfx:whoosh", "sfx:whoosh-soft"), "zoom": ("sfx:whoosh", "sfx:whoosh-soft"),
                  "flash": ("sfx:camera-shutter", "sfx:impact-soft"), "glitch": ("sfx:error", "sfx:tick"), "dip": ("sfx:whoosh", "sfx:whoosh-soft")}


def transition_name(raw):
    """(friendly name, ffmpeg xfade name or None) for a clip's `transition` value; raises on unknown names."""
    name = str(raw or "none").strip().lower()
    if name in TRANSITIONS:
        return name, TRANSITIONS[name]
    if name in XFADE:
        return name, name
    raise ValueError(f"transition '{raw}' is not allowed. Use one of: {', '.join(k for k in TRANSITIONS if k not in ('cut',))} "
                     "(or an ffmpeg xfade name). Remove the field for a hard cut.")


def clip_transition(clip, index, prev_dur, this_dur, pace="medium"):
    """Transition INTO this clip. (ffmpeg name or None, seconds, friendly name). First clip ignores the field.
    Without transition_dur the length follows the pace: whips and flashes stay short."""
    raw = clip.get("transition")
    if index == 0 or raw in (None, "", "none", "cut"):
        return None, 0.0, None
    try:
        friendly, name = transition_name(raw)
    except ValueError as e:
        raise ValueError(f"clips[{index}] {e}")
    if name is None:
        return None, 0.0, None
    if "transition_dur" in clip and clip["transition_dur"] not in (None, ""):
        td = float(clip["transition_dur"])
    else:
        td = PACES.get(pace, PACES["medium"])["trans"]
        if friendly in WHIPS or friendly in ("flash", "glitch"):
            td = min(td, 0.22)
    limit = min(prev_dur, this_dur) - (1 / 30)
    if td <= 0:
        return None, 0.0, None
    if td > max(0.05, limit):
        if "transition_dur" not in clip:
            td = max(0.05, round(limit * 0.6, 3))  # a pace default that doesn't fit a short clip just shrinks
        else:
            cap = max(0.05, round(limit, 3))
            raise ValueError(
                f"clips[{index}] transition_dur {td:g}s is longer than the shorter clip "
                f"({min(prev_dur, this_dur):.2f}s). Use transition_dur <= {cap:.2f} or lengthen the clip.")
    return name, round(td, 3), friendly


def concat_graph(durs, trans):
    """Pairwise xfade or hard concat. trans[i] is (ffmpeg name or None, seconds, friendly name) INTO clip i.
    Ends on [vcat][acat]. Output duration is the sum of durs minus the overlaps. Whips get a motion blur on the overlap."""
    # one timebase for every segment: xfade refuses inputs whose timebases differ, and concat outputs a different one
    lines = [f"[{i}:v]settb=AVTB[vi{i}]" for i in range(len(durs))]
    vprev, aprev = "vi0", "0:a"
    acc = durs[0]
    last = len(durs) - 1
    for i in range(1, len(durs)):
        name, td, friendly = trans[i]
        vout = "vcat" if i == last else f"vx{i}"
        aout = "acat" if i == last else f"ax{i}"
        if name and td > 0:
            offset = max(0.0, round(acc - td, 3))
            if friendly in WHIPS:
                axis = "sizeX=64:sizeY=1" if WHIPS[friendly] == "h" else "sizeX=1:sizeY=64"
                lines.append(f"[{vprev}][vi{i}]xfade=transition={name}:duration={td:.3f}:offset={offset:.3f},"
                             f"avgblur={axis}:enable='between(t,{max(0, offset - 0.04):.3f},{offset + td + 0.04:.3f})'[{vout}]")
            else:
                lines.append(f"[{vprev}][vi{i}]xfade=transition={name}:duration={td:.3f}:offset={offset:.3f}[{vout}]")
            lines.append(f"[{aprev}][{i}:a]acrossfade=d={td:.3f}:c1=tri:c2=tri[{aout}]")
            acc = acc + durs[i] - td
        else:
            lines.append(f"[{vprev}][{aprev}][vi{i}][{i}:a]concat=n=2:v=1:a=1[{vout}][{aout}]")  # concat wants v,a per segment
            acc += durs[i]
        vprev, aprev = vout, aout
    return ";".join(lines)


def render_video(v, plan, cfg, a):
    project = v.get("project") or plan.get("project")
    fmt = v.get("format", "tiktok")
    W, H = FORMATS[fmt]
    fps = int(v.get("fps", cfg["render"]["fps"]))
    tdir = pdir("temp", project)
    seg_dir = os.path.join(tdir, "seg"); os.makedirs(seg_dir, exist_ok=True)
    vdir = os.path.join(tdir, "build", v["id"]); os.makedirs(vdir, exist_ok=True)
    series = v.get("series") or {}
    name = video_name(v["title"], v.get("tags", []), series.get("name"), series.get("part"))
    odir = pdir("output", project)
    final = os.path.join(odir, name + ".mp4")
    textless = os.path.join(odir, "textless", name + ".mp4")
    phash = sha(v, 12)
    led = {r["id"]: r for r in read_ledger(project)}
    if not a.force and v["id"] in led and led[v["id"]].get("plan_hash") == phash and os.path.exists(final):
        return {"id": v["id"], "ok": True, "skipped": "unchanged", "file": os.path.relpath(final, workspace())}
    if disk_free_gb() < cfg["limits"]["min_free_gb"] / 2:
        raise RuntimeError(f"NEED_DISK only {disk_free_gb()}GB free")

    mode = resolve_mode(v, plan, cfg)
    if mode not in MODES:
        raise ValueError(f"mode '{mode}' is not one of {', '.join(MODES)}")
    # A) segments, then the post-overlap timeline (a transition overlaps the previous clip)
    segs, durs, built, framing, geos = [], [], [], [], []
    card_caps = []
    muted_music = product_music_clips(v, project)
    for ci, c in enumerate(v["clips"]):
        if ci in muted_music:
            c = {**c, "audio": "mute"}  # the project's own music would fight the library bed: two musics is always wrong
        p, d, note = build_segment(c, W, H, fps, project, seg_dir, cfg, mode)
        segs.append(p); durs.append(d); built.append(c)
        geos.append(note.get("geo"))
        if {k: x_ for k, x_ in note.items() if k != "geo"}:
            framing.append({"clip": ci, **{k: x_ for k, x_ in note.items() if k != "geo"}})
    pace = resolve_pace(v, sum(durs), cfg)
    if pace not in PACES:
        raise ValueError(f"pace '{pace}' is not one of auto, {', '.join(PACES)}")
    trans = []
    for ci, c in enumerate(built):
        prev = durs[ci - 1] if ci else 0.0
        trans.append(clip_transition(c, ci, prev, durs[ci], pace))
    cursor = 0.0
    trans_sfx, starts = [], []
    for ci, c in enumerate(built):
        _name, td, friendly = trans[ci]
        start = cursor - td
        starts.append(max(0.0, start))
        d = durs[ci]
        ts_ = c.get("transition_sfx", friendly in WHIPS)
        if friendly and ts_:
            base = next((k for k in TRANSITION_SFX if friendly.startswith(k)), None)
            asset = ts_ if isinstance(ts_, str) else (TRANSITION_SFX[base][mode == "pro"] if base else ("sfx:whoosh-soft" if mode == "pro" else "sfx:whoosh"))
            trans_sfx.append({"asset": asset, "t": round(max(0.0, start - 0.06), 3), "vol": 0.55 if mode == "pro" else 0.7})
        if "card" in c:
            card_caps.append({"t": round(start, 3), "d": d, "text": c["card"], "style": "card", "anim": "fade" if mode == "pro" else "pop"})
        if c.get("caption"):  # shorthand: caption tied to a clip, relative to when this clip starts to appear
            cc = c["caption"] if isinstance(c["caption"], dict) else {"text": c["caption"]}
            card_caps.append({**cc, "t": round(start + float(cc.get("t", 0)), 3), "d": float(cc.get("d", d - float(cc.get("t", 0))))})
        cursor = start + d
    total = round(cursor, 3)
    grade = v.get("grade") or "none"
    if grade not in GRADES:
        raise ValueError(f"grade '{grade}' is not one of {', '.join(GRADES)}")
    # B+C) concat filter (not the concat demuxer: its stream-copied timestamps make overlays drop/dup frames)
    #      + overlays + audio mix -> textless master, one encode
    #      all-hard-cut plans keep the single concat so the filter matches the old render
    seg_in = sum((["-i", sp_] for sp_ in segs), [])
    n = len(segs)
    if n == 1 or all(t_[0] is None for t_ in trans):
        cat = "".join(f"[{i}:v][{i}:a]" for i in range(n)) + f"concat=n={n}:v=1:a=1[vcat][acat]"
    else:
        cat = concat_graph(durs, trans)
    ov_dir = os.path.join(vdir, "ov"); os.makedirs(ov_dir, exist_ok=True)
    ovs, ov_notes, proof_rows = anchor_overlays(v, built, starts, durs, geos, project, W, H)
    ov_in, ov_lines, vlabel, n_in = overlay_graph({**v, "overlays": ovs}, W, H, fps, total, n, ov_dir)
    va = {**v, "sfx": list(v.get("sfx", [])) + trans_sfx} if trans_sfx else v
    au_in, au_lines, n_in = audio_graph(va, total, "acat", n_in, False)
    # the colour look goes under the overlays, so arrows and stickers keep their colours
    base = f"[vcat]{GRADES[grade]}[vbase]" if GRADES[grade] else "[vcat]null[vbase]"
    # pin fps: with extra overlay inputs ffmpeg otherwise guesses 25fps and drops frames (captions drift)
    fc = ";".join([cat, base] + ov_lines + [f"[{vlabel}]fps={fps},format=yuv420p[vout]"] + au_lines)
    os.makedirs(os.path.dirname(textless), exist_ok=True)
    vonly, mixwav = os.path.join(vdir, "video_only.mp4"), os.path.join(vdir, "mix.wav")
    run(["ffmpeg", "-y", "-v", "error", *seg_in, *ov_in, *au_in, "-filter_complex", fc,
         "-map", "[vout]", "-an", "-t", str(total), "-r", str(fps), *enc_final(cfg), vonly,
         "-map", "[aout]", "-t", str(total), "-c:a", "pcm_s16le", "-ar", "48000", mixwav])
    audio_info = finish_audio(vonly, mixwav, textless, cfg)
    # D) captions -> final
    v2 = dict(v); v2["captions"] = [dict(c) for c in card_caps + list(v.get("captions", []))]
    v2["_mode"], v2["_pace"] = mode, pace
    v2["_brand_accent"] = (cfg.get("brand") or {}).get("accent")
    for c in v2["captions"]:
        if c.get("d") in (None, ""):
            c["d"] = read_time(c.get("text", ""), pace)  # long enough to read at this pace
    contrast_notes = []
    if v.get("auto_contrast", cfg["render"].get("auto_contrast", True)):
        v2["captions"], contrast_notes = auto_contrast(v2["captions"], textless, video_preset(v2, mode), W, H, total, bool(v.get("header")))
    ass = os.path.join(vdir, "captions.ass")
    n_ev = build_ass(v2, W, H, total, ass)
    if n_ev and not a.no_captioned:
        vf = f"subtitles=filename='{ffesc(ass)}':fontsdir='{ffesc(FONTS)}'"
        run(["ffmpeg", "-y", "-v", "error", "-i", textless, "-vf", vf, "-c:a", "copy", "-r", str(fps), *enc_final(cfg), final])
    else:
        shutil.copy2(textless, final)
    proof = None
    legacy = [o for o in ovs if o.get("type") in POINTERS and any(o is x for x in v.get("overlays", []))]  # placed by hand in output coordinates
    shown = [(r_["t"], r_) for r_ in proof_rows] + [(float(o.get("t", 0)), {"d": float(o.get("d", 2))}) for o in legacy]
    if shown:  # one frame per highlight, from the finished video: the reviewer checks each lands on its target (references/highlighting.md)
        try:
            times = [round(min(total - 0.05, t_ + min(0.6, r_["d"] / 2)), 2) for t_, r_ in sorted(shown, key=lambda x: x[0])][:12]
            proof, _t = make_sheet(argparse.Namespace(file=final, n=len(times), cols=min(4, len(times)) if W > H else min(3, len(times)), grid=False, width=1200 if W > H else 1000,
                                                      times=",".join(map(str, times)), out=os.path.join(pdir("temp", project, "proof"), v["id"] + ".jpg")))
        except Exception:
            proof = None
    desc = write_description(v, cfg, os.path.join(odir, name), total)
    thumb = None
    if v.get("thumb"):
        th = v["thumb"]
        thumb = os.path.join(odir, name + ".jpg")
        make_thumb(textless if th.get("from", "textless") == "textless" else final, float(th.get("t", total * 0.3)), th.get("text", ""),
                   th.get("sticker"), thumb, (1280, 720) if W > H else (1080, 1920), th.get("color", "yellow"))
    write_ledger_row(project, {"id": v["id"], "date": now(), "pass": plan.get("pass", v.get("pass", "")), "format": fmt, "dur": total,
                               "title": v["title"], "tags": " ".join(v.get("tags", [])), "series": f"{series.get('name', '')}#{series.get('part', '')}" if series else "",
                               "file": name + ".mp4", "sources": " ".join(sorted({c.get("src", "card") for c in v["clips"]})),
                               "hook": v.get("hook_type", ""), "style": v.get("style") or default_style(mode), "plan_hash": phash})
    if not a.keep_build:
        shutil.rmtree(vdir, ignore_errors=True)
    lo, hi = LIMITS.get(fmt, (1, 9999))
    warn = [] if lo <= total <= hi else [f"duration {total}s outside {lo}-{hi}s for {fmt}"]
    return {"id": v["id"], "ok": True, "dur": total, "pace": pace, "mode": mode, "file": os.path.relpath(final, workspace()), "desc": os.path.basename(desc),
            **({"framing": framing} if framing else {}),
            **({"thumb": os.path.basename(thumb)} if thumb else {}), **({"warn": warn} if warn else {}),
            **({"contrast_fixed": contrast_notes} if contrast_notes else {}),
            **({"audio": audio_info} if audio_info else {}),
            **({"highlights": proof_rows} if proof_rows else {}), **({"overlay_notes": ov_notes} if ov_notes else {}),
            **({"proof": os.path.relpath(proof, workspace())} if proof else {}),
            **({"product_music_muted": [f"clips[{i}]" for i in muted_music]} if muted_music else {})}


def load_plan(path):
    plan = json.load(open(path, encoding="utf-8"))
    vids = plan.get("videos") or [plan]
    for i, v in enumerate(vids):
        v.setdefault("id", f"v{i + 1:03d}")
    return plan, vids


def cmd_render(a):
    cfg = load_config()
    plan, vids = load_plan(a.plan)
    if a.only:
        keep = set(a.only.split(","))
        vids = [v for v in vids if v["id"] in keep]
    fails = 0
    for v in vids:
        try:
            out(render_video(v, plan, cfg, a))
        except Exception as e:
            fails += 1
            out({"id": v.get("id"), "ok": False, "error": str(e)[-700:]})
    sys.exit(1 if fails else 0)


# ----------------------------------------------------------------------------- check / lint
AI_TELLS = ["delve", "leverage", "utilize", "seamless", "robust", "game-changer", "game changer", "unlock", "elevate", "embark", "tapestry",
            "realm", "in today's", "it's not just", "let's dive", "dive in", "buckle up", "ever wondered", "look no further", "revolutioniz",
            "cutting-edge", "harness", "testament", "navigate the", "landscape", "crucial", "furthermore", "moreover", "journey", "unleash",
            "supercharge", "next level", "next-level", "seamlessly", "effortlessly", "empower", "streamline", "comprehensive", "transformative",
            "here's the thing", "the best part?", "spoiler alert", "let that sink in", "you won't believe", "follow for more", "like and subscribe",
            "smash that", "comment below", "tag a friend", "stay tuned"]


# Housekeeping that only the developer cares about: a stranger scrolling past has no reason to read it (copy-rules.md, "Would a stranger care?")
INSIDER = ["licence", "license", "cc0", "font swap", "swapped for", "refactor", "dependenc", "linter", "typo", "changelog", "ci pipeline", "boilerplate",
           "config file", "renamed the", "bumped", "migrat", "tech debt", "unit test"]


def lint_text(s):
    s_l = s.lower()
    hits = [w for w in AI_TELLS if w in s_l]
    issues = [f"ai-tell:'{h}'" for h in hits]
    issues += [f"insider:'{w}' (would a stranger care?)" for w in INSIDER if w in s_l]
    if s.count("—") > 1:
        issues.append("em-dashes>1")
    if EMOJI_RE.search(s):
        issues.append("emoji-in-burned-text(stripped)")
    return issues


def still_in_clip(c, proj, d):
    """Hard issue when a clip's span lands on frozen footage recorded in the rec cache (see register_rec)."""
    src = c.get("src", "")
    if not src.startswith("rec:") or c.get("still") or any(str(f).startswith("freeze") for f in c.get("fx", [])):
        return []
    ref, p2 = src[4:], proj
    if "/" in ref:
        p2, ref = ref.split("/", 1)
    rec = next((r for r in load_data(p2)["recordings"] if r["id"] == ref), None)
    if not rec:
        return []
    a0, b0 = float(c.get("in", 0)), min(float(c.get("out", d)), d)
    hit = sum(max(0.0, min(b0, e) - max(a0, s)) for s, e in rec.get("still", []))
    if hit >= 2.5 or (b0 - a0 > 0 and hit / (b0 - a0) > 0.6):
        return [f"frozen footage: {src} {a0:g}-{b0:g}s is {hit:.1f}s still (rec still spans {rec.get('still')}). Pick a moving span or re-record"]
    return []


def asset_entry(ref):
    """The index row behind an asset ref (exact id, then a loose name match like resolve_asset), or None for plain paths."""
    if not ref or ":" not in str(ref) or re.match(r"^[A-Za-z]:[\\/]", str(ref)):
        return None
    rows = load_index()["assets"]
    kind, name = str(ref).split(":", 1)
    return next((a for a in rows if a["id"] == ref), None) or next((a for a in rows if a["id"].split(":", 1)[0] == kind and name in a["id"]), None)


def pro_ok_sound(ref, kind):
    """Pro mode keeps meme sounds out: an asset passes when its index row says pro, or it's the user's own file."""
    e = asset_entry(ref)
    if e is None:
        return True
    if e.get("pro"):
        return True
    return kind == "music" and e.get("yt") in ("ok", "credit")


def has_todo(s):
    return bool(re.search(r"\bTODO\b", str(s or "")))


def src_size(path):
    try:
        if os.path.splitext(path)[1].lower() == ".png":
            return png_size(path)
        vi = ffprobe(path)["video"]
        return (vi["w"], vi["h"]) if vi else None
    except Exception:
        return None


SOFT = ("cap ai-tell", "desc ai-tell", "title ai-tell", "cap insider", "title insider", "desc insider", "cap emoji", "long caption", "tags=",
        "music:", "bare:", "pace:", "framing:", "pro note:", "todo list:", "overlay note:", "sfx note:", "sound:")


def cmd_check(a):
    cfg = load_config()
    plan, vids = load_plan(a.plan)
    titles_seen = {r["title"].lower(): r["id"] for p in [plan.get("project")] if p for r in read_ledger(p)}
    families = font_families()
    report, bad = [], 0
    styles_used = {}
    for v in vids:
        iss = []
        proj = v.get("project") or plan.get("project")
        if not proj:
            iss.append("no project")
        fmt = v.get("format", "tiktok")
        if fmt not in FORMATS:
            iss.append(f"bad format {fmt}")
        W, H = FORMATS.get(fmt, (1080, 1920))
        mode = resolve_mode(v, plan, cfg)
        if mode not in MODES:
            iss.append(f"mode '{mode}' must be creator or pro")
        style = v.get("style") or default_style(mode)
        if style not in PRESETS:
            iss.append(f"style '{style}' is not a preset ({', '.join(PRESETS)})")
        for k in ("title", "clips"):
            if not v.get(k):
                iss.append(f"missing {k}")
        tags = v.get("tags", [])
        if not (2 <= len(tags) <= 6):
            iss.append(f"tags={len(tags)} (want 3-5)")
        if any(t.lower().lstrip("#") in ("fyp", "foryou", "foryoupage", "viral", "trending") for t in tags):
            iss.append("filler hashtag (#fyp/#viral) - use niche tags")
        if titles_seen.get(v.get("title", "").lower(), v["id"]) != v["id"]:
            iss.append("title already used")
        is_wide = fmt in ("youtube", "landscape", "x", "twitter")
        if len(v.get("title", "")) > (100 if is_wide else 90):
            iss.append("title too long")
        iss += [f"title {x}" for x in lint_text(v.get("title", ""))]
        todo = [k for k in ("title", "description") if has_todo(v.get(k))] + (["tags"] if any(has_todo(t) for t in tags) else [])
        todo += [f"captions[{i}]" for i, c in enumerate(v.get("captions", [])) if has_todo(c.get("text"))]
        todo += [f"chapters[{i}]" for i, c in enumerate(v.get("chapters") or []) if has_todo(c.get("title"))]
        todo += ["hook_type"] if has_todo(v.get("hook_type")) else []
        for i, c in enumerate(v.get("clips", [])):
            cc = c.get("caption")
            if has_todo(cc.get("text") if isinstance(cc, dict) else cc) or has_todo(c.get("card")):
                todo.append(f"clips[{i}]")
        if todo:
            iss.append(f"TODO text left in {', '.join(todo)}: write the real words (copy-rules.md)")
        if v.get("todo"):
            iss.append(f"todo list: {len(v['todo'])} reminder(s) in the plan's `todo`; do them, then delete the field")
        if v.get("description"):
            if fmt in ("x", "twitter"):
                plain_desc = re.sub(r'https?://\S+', 'x' * 23, v["description"])
                if len(plain_desc) > 280:
                    iss.append(f"desc {len(plain_desc)} chars (>280 limit for standard X/Twitter post)")
            iss += [f"desc {x}" for x in lint_text(v["description"])]
        for f_ in [v.get("font")] + [c.get("font") for c in v.get("captions", [])]:
            if f_ and families and f_.lower() not in families:
                iss.append(f"font '{f_}' is not bundled (clip.py fonts lists the families)")
        if (v.get("grade") or "none") not in GRADES:
            iss.append(f"grade '{v.get('grade')}' is not one of {', '.join(GRADES)}")

        # clip lengths (and what each source looks like, for the framing rules)
        piece_durs, kinds = [], []
        for i, c in enumerate(v.get("clips", [])):
            piece = 0.0
            kind = "card" if "card" in c else "img"
            try:
                if "card" not in c:
                    p = resolve_src(c["src"], proj)
                    size = src_size(p)
                    if os.path.splitext(p)[1].lower() in IMG_EXT or c.get("still"):
                        piece = float(c.get("dur", 2))
                    else:
                        kind = "video"
                        d = ffprobe(p)["dur"]
                        piece = (min(float(c.get("out", d)), d) - float(c.get("in", 0))) / float(c.get("speed", 1))
                        iss += still_in_clip(c, proj, d)
                        tr = c.get("track")
                        if isinstance(tr, list):
                            for k in tr:
                                if not (0 <= float(k.get("x", -1)) <= 1 and 0 <= float(k.get("y", -1)) <= 1):
                                    iss.append(f"track key {k} needs x,y between 0 and 1 (fractions of the source frame; read them off clip.py sheet --grid)")
                            if len(tr) < 2:
                                iss.append("track needs 2+ keys (start point + where to glide); for one fixed spot use focus, or track:\"auto\"")
                        elif tr not in (None, "auto"):
                            iss.append(f"clips[{i}].track must be a list of keys or \"auto\"")
                    if size:
                        iss += framing_issues(c, i, kind, size, W, H, mode, rec_meta(c.get("src", ""), proj))
                else:
                    piece = float(c.get("dur", 1.5))
                for f in c.get("fx", []):
                    n, arg, _ = parse_fx(f)
                    if n == "freeze":
                        piece += float(arg or 1)
                    if mode == "pro" and n in CREATOR_ONLY_FX:
                        iss.append(f"pro: clips[{i}] fx '{n}' reads as a meme edit; pro uses zoom/zoomin, freeze, slowmo, speed, contrast, sat, dim, vignette")
                if mode == "pro" and str(c.get("src", "")).startswith(("meme:", "gif:")):
                    iss.append(f"pro: clips[{i}] is a meme ({c['src']}); pro videos show the product, not memes")
            except Exception as e:
                iss.append(f"clip src: {str(e)[:90]}")
            piece_durs.append(piece)
            kinds.append(kind)
        pace = resolve_pace(v, sum(piece_durs), cfg)
        if pace not in PACES:
            iss.append(f"pace '{pace}' must be auto, fast, medium or slow")
            pace = "medium"
        overlap, starts, cursor = 0.0, [], 0.0
        for i, c in enumerate(v.get("clips", [])):
            prev = piece_durs[i - 1] if i else 0.0
            this = piece_durs[i]
            td = 0.0
            if not (i > 0 and (prev <= 0 or this <= 0)):
                try:
                    _name, td, _f = clip_transition(c, i, prev, this, pace)
                except ValueError as e:
                    iss.append(str(e))
            overlap += td
            starts.append(cursor - td)
            cursor = cursor - td + this
        est = sum(piece_durs) - overlap
        lo, hi = LIMITS.get(fmt, (1, 9999))
        if not (lo <= est <= hi):
            iss.append(f"est duration {est:.1f}s outside {lo}-{hi}")
        caps_all = list(v.get("captions", []))
        for i, c in enumerate(v.get("clips", [])):
            if c.get("caption"):
                cc = c["caption"] if isinstance(c["caption"], dict) else {"text": c["caption"]}
                caps_all.append({**cc, "t": starts[i] + float(cc.get("t", 0))})
        for c in v.get("captions", []):
            if float(c.get("t", 0)) >= est:
                iss.append(f"caption after end: '{c['text'][:20]}'")
            if len(c.get("text", "").split()) > (12 if is_wide else 9):
                iss.append(f"long caption ({len(c['text'].split())}w): '{c['text'][:24]}...'")
            iss += [f"cap {x}" for x in lint_text(c.get("text", ""))]
        iss += pace_issues(v, pace, piece_durs, kinds, starts, caps_all, est)
        if mode == "pro":
            iss += pro_issues(v, style)
        plain = [c for c in v.get("captions", []) if "x" not in c and c.get("style", "cap") in ("hook", "cap", "mid")]
        for i, c1 in enumerate(plain):
            for c2 in plain[i + 1:]:
                d1 = float(c1.get("d") or read_time(c1.get("text", ""), pace))
                d2 = float(c2.get("d") or read_time(c2.get("text", ""), pace))
                if c1.get("style", "cap") == c2.get("style", "cap") and float(c1.get("t", 0)) < float(c2.get("t", 0)) + d2 and float(c2.get("t", 0)) < float(c1.get("t", 0)) + d1:
                    iss.append(f"captions overlap in time at the same spot: '{c1['text'][:18]}' / '{c2['text'][:18]}' (stack them in one caption with a line break, or shorten d)")
        caps = [c for c in caps_all if float(c.get("t", 0)) < 1.0]
        if not is_wide and not caps and not v.get("header"):
            iss.append("no on-screen hook in first second")
        for o in v.get("overlays", []):
            if o.get("asset"):
                try:
                    resolve_asset(o["asset"])
                except Exception as e:
                    iss.append(str(e)[:80])
        iss += highlight_issues(v, mode) + sound_issues(v, mode)
        trans_sound_keywords = ("whoosh", "swoosh", "whip", "swipe")
        for s in v.get("sfx", []):
            try:
                resolve_asset(s["asset"])
            except Exception as e:
                iss.append(str(e)[:80])
            if mode == "pro" and not pro_ok_sound(s.get("asset"), "sfx"):
                iss.append(f"pro: {s.get('asset')} is a meme sound; pro sounds: assets.py find --type sfx --pro")
            asset_name = str(s.get("asset", "")).lower()
            st = float(s.get("t", 0))
            if any(k in asset_name for k in trans_sound_keywords):
                near_trans = any(abs(st - st_i) <= 0.4 for st_i in starts[1:])
                near_camera_move = False
                for ci, c in enumerate(v.get("clips", [])):
                    c_start = starts[ci]
                    c_end = c_start + piece_durs[ci]
                    if c_start - 0.2 <= st <= c_end + 0.2:
                        if c.get("track") or any(parse_fx(f)[0] in ("zoomin", "zoomout") for f in c.get("fx", [])):
                            near_camera_move = True
                            break
                if not near_trans and not near_camera_move:
                    iss.append(f"sfx: '{s.get('asset')}' at {st:.2f}s is a transition sound but no cut, transition, or camera move occurs near this time (avoid transition sounds when no transition happens)")
                for ci, c in enumerate(v.get("clips", [])):
                    if ci > 0 and abs(st - starts[ci]) <= 0.35:
                        tr_name = str(c.get("transition", "")).lower()
                        if tr_name in ("dissolve", "fade", "none", "cut", ""):
                            iss.append(f"sfx note: transition sound '{s.get('asset')}' at {st:.2f}s on a gentle '{tr_name or 'cut'}' transition; whooshes belong on whips, pushes, or camera moves")
                        if c.get("transition_sfx") or tr_name in WHIPS:
                            iss.append(f"sfx: duplicate transition sound near {starts[ci]:.2f}s (both clip transition_sfx and manual plan sfx)")
        if mode == "pro" and len(v.get("sfx", [])) > 6:
            iss.append(f"pro note: video has {len(v.get('sfx', []))} SFX; pro mode recommends 2-4 subtle SFX (title, 1-2 key reveals, outro). Avoid sound clutter.")
        for c in v.get("captions", []):
            if is_wide and c.get("style") in ("title", "mid") and "x" not in c and "y" not in c:
                iss.append(f"caption '{c.get('text', '')[:20]}': unplated '{c.get('style')}' style on wide/UI footage risks text collision with underlying page text; use 'plate', 'box', or 'lower' with clean margin")
        if v.get("music"):
            mref = v["music"]["asset"] if isinstance(v["music"], dict) else v["music"]
            try:
                resolve_asset(mref)
            except Exception as e:
                iss.append(str(e)[:80])
            if mode == "pro" and not pro_ok_sound(mref, "music"):
                iss.append(f"pro: {mref} is meme music; pro beds: assets.py find --type music --pro (or the user's own licensed tracks)")
            pm = product_music_clips(v, proj) if proj else []
            if pm:
                iss.append(f"music: clips{pm} have their own music; render will mute them under the library track (add \"product_music\":\"keep\" to keep it and drop `music`)")
        elif fmt == "tiktok" and not v.get("sfx") and not v.get("overlays") and not any("fx" in c or "sticker" in c for c in v["clips"]):
            iss.append("bare: no music, SFX, overlay or fx - raw recording with captions. Add at least one SFX and one pointing overlay or fx (references/effects-cookbook.md)")
        if fmt == "youtube" and v.get("chapters"):
            ch = v["chapters"]
            if ch[0]["t"] != 0 or len(ch) < 3:
                iss.append("chapters: first must be 0:00 and >=3 chapters")
        styles_used[style] = styles_used.get(style, 0) + 1
        hard = [x for x in iss if not x.startswith(SOFT)]
        bad += bool(hard)
        report.append({"id": v["id"], "est": round(est, 1), "pace": pace, "mode": mode, "issues": iss})
    for r in report:
        print(f"{r['id']} ~{r['est']}s {r['pace']}/{r['mode']} " + ("OK" if not r["issues"] else "| " + "; ".join(r["issues"])))
    if len(vids) >= 6 and max(styles_used.values()) > len(vids) * 0.6:
        print(f"variety: style '{max(styles_used, key=styles_used.get)}' used {max(styles_used.values())}/{len(vids)} - rotate presets")
    tt = [v for v in vids if v.get("format", "tiktok") == "tiktok" and resolve_mode(v, plan, cfg) == "creator"]
    bed = (cfg.get("music") or {}).get("meme_bed", "tiktok")
    if len(tt) >= 5 and bed != "off":
        want = float(cfg.get("mix", {}).get("music_share_short", 0.4))
        have = sum(1 for v in tt if v.get("music"))
        if have < max(1, int(len(tt) * want * 0.5)):
            print(f"music: {have}/{len(tt)} TikToks have a music bed (target about {int(want * 100)}%). "
                  "Pick tracks with `assets.py find --type music --mood <m>` (references/music-audio.md, section 'Meme music bed').")
    sys.exit(1 if bad else 0)


def framing_issues(c, i, kind, size, W, H, mode, rec):
    """Framing rules by aspect ratio (references/framing.md): fill the frame, never centre-crop the action away."""
    sw, sh = size
    if not sw or not sh:
        return []
    r = (sw / sh) / (W / H)
    fit = (c.get("fit") or "auto").split(":")[0]
    aimed = c.get("focus") not in (None, "auto") or c.get("track")
    out_ = []
    if kind == "video" and fit == "cover" and not aimed:
        if r > 1.6:
            out_.append(f"framing: clips[{i}] centre-crops a {sw}x{sh} source to {100 / r:.0f}% of its width; drop `fit` (auto aims at the action), "
                        "or set focus [x,y] / track \"auto\"")
        elif r < 0.62:
            out_.append(f"framing: clips[{i}] crops a tall {sw}x{sh} source to {100 * r:.0f}% of its height in a wide frame; use fit auto, float or blurpad")
    if kind == "video" and fit in ("contain", "blurpad") and r > 1.25 and H > W and rec.get("how") != "web":
        out_.append(f"framing: clips[{i}] puts wide footage in a strip with bars; gameplay should fill a portrait frame (drop `fit` for auto, or fit stack)")
    if 0.8 <= r <= 1.25 and fit in ("blurpad", "contain", "float"):
        out_.append(f"framing: clips[{i}] source is already the frame's shape ({sw}x{sh}); `cover` (or no `fit`) fills it edge to edge")
    return out_


def pace_issues(v, pace, piece_durs, kinds, starts, caps, est):
    """Pacing rules (references/pacing.md): shot length, reading time, dead air, an early first cut."""
    P = PACES[pace]
    lo, _avg, mx = P["shot"]
    out_ = []
    vids_ = [(i, d) for i, (d, k) in enumerate(zip(piece_durs, kinds)) if k == "video" and d > 0]
    for i, d in vids_:
        c = v["clips"][i]
        moving = bool(c.get("track")) or any(parse_fx(f)[0] in ("zoomin", "zoomout") for f in c.get("fx", []))
        limit = mx * (1.5 if moving else 1)  # a moving camera keeps a long shot alive
        if d > 2 * limit:
            out_.append(f"pace!: clips[{i}] runs {d:.1f}s; {pace} pace shots stay under {limit:.1f}s. Split it into 2-3 clips with different focus, "
                        "trim it, or speed:2 the boring part")
        elif d > limit:
            out_.append(f"pace: clips[{i}] runs {d:.1f}s (> {limit:.1f}s for {pace}); split it, add track/zoomin, or trim")
        elif d < lo and 0 < i < len(piece_durs) - 1:
            out_.append(f"pace: clips[{i}] is {d:.1f}s, a flicker at {pace} pace (min {lo}s)")
    c0 = v["clips"][0] if v.get("clips") else {}
    first_moves = bool(c0.get("track")) or any(parse_fx(f)[0] in ("zoomin", "zoomout") for f in c0.get("fx", []))
    if vids_ and len(piece_durs) > 1 and piece_durs[0] > P["first_cut"] and not first_moves:
        out_.append(f"pace: first cut at {piece_durs[0]:.1f}s; {pace} videos cut or move the camera by {P['first_cut']}s")
    for c in caps:
        txt = c.get("text", "")
        n = len(txt.replace("*", "").split())
        if not n or c.get("style") in ("chip", "header"):
            continue
        need = read_time(txt, pace)
        d = float(c["d"]) if c.get("d") not in (None, "") else need
        if d < 0.6 * need:
            out_.append(f"pace!: caption '{txt[:22]}' is up {d:.1f}s but {n} words need {need:.1f}s to read; cut words or raise d")
        elif d < need * 0.9:
            out_.append(f"pace: caption '{txt[:22]}' {d:.1f}s is short for {n} words (needs ~{need:.1f}s)")
        if n > P["words"]:
            out_.append(f"pace: caption '{txt[:22]}' has {n} words; {pace} pace wants <= {P['words']}")
    events = [0.0, est] + list(starts)
    events += [float(c.get("t", 0)) for c in caps]
    events += [float(o.get("t", 0)) for o in v.get("overlays", []) if o.get("type") not in ("progress", "ring", "circle")]
    for i, c in enumerate(v.get("clips", [])):
        if isinstance(c.get("track"), list):
            events += [starts[i] + float(k.get("t", 0)) for k in c["track"][1:]]
        elif c.get("track") == "auto":
            events += [starts[i] + j * 1.5 for j in range(int(piece_durs[i] / 1.5) + 1)]
        if any(parse_fx(f)[0] in ("zoomin", "zoomout") for f in c.get("fx", [])):
            events += [starts[i] + piece_durs[i] / 2]
    events = sorted(e for e in events if 0 <= e <= est)
    gaps = [(b - a, a, b) for a, b in zip(events, events[1:])]
    if gaps:
        g, a0, b0 = max(gaps)
        if g > P["gap"] * 1.15:
            out_.append(f"pace: nothing new from {a0:.1f}s to {b0:.1f}s ({g:.1f}s; {pace} pace wants something every {P['gap']}s): "
                        "add a cut, caption, zoom, sfx or overlay")
    return out_


def sound_issues(v, mode):
    """Sound design (references/music-audio.md, section 5): sounds are levelled at render, so what is left to catch is clutter."""
    out_ = []
    sfx = sorted(((float(x.get("t", 0)), x) for x in v.get("sfx", [])), key=lambda a: a[0])
    for (t1, a), (t2, b) in zip(sfx, sfx[1:]):
        if t2 - t1 < 0.3 and a.get("asset") != b.get("asset"):
            out_.append(f"sound: '{a.get('asset')}' at {t1:.2f}s and '{b.get('asset')}' at {t2:.2f}s pile up within {t2 - t1:.2f}s; keep one sound per beat")
    for _t, x in sfx:
        try:
            dur = loudness_of(resolve_asset(x["asset"]))["dur"]
        except Exception:
            continue
        if dur > SFX_MAX_S and not x.get("dur"):
            out_.append(f"sound: {x['asset']} is {dur:.1f}s long; the render cuts SFX at {SFX_MAX_S:g}s with a short fade. Set `dur` to choose where it ends (a sound that rings through the next beat sounds like a mistake)")
        if float(x.get("vol", 0.7)) > 0.9:
            out_.append(f"sound: {x['asset']} vol {x.get('vol')} is above 0.9; sounds are levelled first, 0.4 to 0.8 is the working range")
    m = v.get("music")
    if m and isinstance(m, dict) and float(m.get("vol", 0.16)) > 0.3:
        out_.append(f"sound: music vol {m.get('vol')} is loud for a bed (it is levelled first; 0.10 to 0.18 keeps captions and SFX on top)")
    if mode == "pro":
        for _t, x in sfx:
            if float(x.get("vol", 0.7)) > 0.7:
                out_.append(f"sfx note: pro SFX sit at 0.4 to 0.6; {x.get('asset')} is {x.get('vol')}")
    return out_


def highlight_issues(v, mode):
    """Highlights (references/highlighting.md): a pointer placed by guess is worse than none, so a hand-placed one must be marked
    verified; anchored ones (at / box / target) are mapped and checked by the renderer."""
    out_ = []
    ovs = v.get("overlays", [])
    ptr = [(i, o) for i, o in enumerate(ovs) if o.get("type") in POINTERS and o.get("type") not in ("x", "check")]
    for i, o in ptr:
        typ = o.get("type")
        anchored = any(k in o for k in ("at", "box", "target"))
        if anchored:
            if not o.get("what") and not o.get("target"):
                out_.append(f"overlay: overlays[{i}] {typ} needs `what` (the thing it points at, e.g. \"Export button\"): the reviewer checks the proof frame against it")
            if typ in RECTS + ("bar", "spotlight") and "box" not in o and "target" not in o and typ != "spotlight":
                out_.append(f"overlay: overlays[{i}] {typ} needs `box` [x, y, w, h] or `target`")
        elif not o.get("verified"):
            out_.append(f"overlay: overlays[{i}] {typ} is placed by hand in output coordinates. Anchor it to the source instead (`target` from record-web, or `box`/`at` read off `clip.py sheet <rec> --grid`; the render maps it through the crop and drops it if it can't land), "
                        "or add \"verified\": true once the proof sheet shows it exactly on target. A wrong highlight is worse than none")
    kinds = [o.get("type") for _i, o in ptr]
    if len(kinds) >= 3 and len(set(kinds)) == 1:
        out_.append(f"overlay note: all {len(kinds)} highlights are '{kinds[0]}'; vary them to what each target is (references/highlighting.md, section 'Pick the highlight')")
    if mode == "pro":
        for i, o in ptr:
            if o.get("type") in ("scribble", "arrow-curved"):
                out_.append(f"pro note: overlays[{i}] {o.get('type')} looks hand-drawn; box, bar, marker, focus or a straight arrow read cleaner")
    return out_


def pro_issues(v, style):
    """Pro mode (references/pro-mode.md): no meme looks, no slang, sentence case."""
    out_ = []
    if style not in PRO_STYLES:
        out_.append(f"pro: style '{style}' is a creator look; pro presets: {', '.join(sorted(PRO_STYLES))}")
    for i, o in enumerate(v.get("overlays", [])):
        typ = o.get("type", "sticker")
        if typ == "sticker" and str(o.get("asset", "")).startswith(("meme:", "gif:")):
            out_.append(f"pro: overlays[{i}] is a meme sticker; pro videos keep memes out")
        if typ in ("ring", "circle"):
            out_.append(f"pro note: overlays[{i}] '{typ}' is a creator look; a pro video points with box, bar, marker or focus")
    if v.get("hook_type") == "clickbait":
        out_.append("pro note: clickbait hook in a pro video; lead with the outcome instead")
    texts = [("title", v.get("title", ""))] + [(f"captions[{i}]", c.get("text", "")) for i, c in enumerate(v.get("captions", []))]
    for where, t in texts:
        low = f" {t.lower()} "
        hit = [w for w in SLANG if re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", low)]
        if hit:
            out_.append(f"pro note: {where} uses slang ({', '.join(hit)})")
        shout = [w for w in re.findall(r"[A-Za-z]{3,}", t) if w.isupper() and w not in ("API", "CLI", "SDK", "GPU", "CPU", "FPS", "SQL", "CSS")]
        if len(shout) > 1:
            out_.append(f"pro note: {where} shouts in caps ({' '.join(shout[:3])})")
    title = v.get("title", "").strip()
    if title and title[0].isalpha() and title[0].islower():
        out_.append("pro note: title in sentence case (\"Faster exports in 3 clicks\")")
    if EMOJI_RE.search(v.get("description", "") or ""):
        out_.append("pro note: emoji in a pro description; keep it plain")
    return out_


# ----------------------------------------------------------------------------- thumbnail / name / ledger / state / clean
def make_thumb(src, t, text, sticker, dst, size, color="yellow"):
    W, H = size
    font = ffesc(os.path.join(FONTS, "Montserrat-Black.ttf"))
    is_img = os.path.splitext(src)[1].lower() in IMG_EXT
    ins = ["-i", src] if is_img else ["-ss", str(t), "-i", src]
    lines = [f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},eq=contrast=1.12:saturation=1.25[b]"]
    cur = "b"
    if sticker:
        ins += ["-i", resolve_asset(sticker)]
        lines.append(f"[1:v]scale=-2:{int(H * 0.62)}[st];[{cur}][st]overlay=W-w-{int(W * 0.03)}:H-h[b2]")
        cur = "b2"
    if text:
        txt = EMOJI_RE.sub("", text).upper().replace("'", "\u2019").replace(":", "\\:")
        fs = int(H * (0.16 if W > H else 0.075))
        lines.append(f"[{cur}]drawtext=fontfile='{font}':text='{txt}':fontsize={fs}:fontcolor={color}:borderw={max(4, fs // 12)}:bordercolor=black:"
                     f"x={int(W * 0.05)}:y=h-th-{int(H * (0.08 if W > H else 0.3))}[o]")
        cur = "o"
    run(["ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", ";".join(lines), "-map", f"[{cur}]", "-frames:v", "1", "-q:v", "3", dst])


def cmd_thumb(a):
    make_thumb(a.src, a.t, a.text, a.sticker, a.out, tuple(int(x) for x in a.size.split("x")), a.color)
    out({"ok": True, "thumb": a.out})


def cmd_name(a):
    print(video_name(a.title, [t for t in (a.tags or "").split(",") if t], a.series, a.part))


def cmd_ledger(a):
    rows = read_ledger(a.project)
    if a.titles:
        for r in rows:
            print(f"{r['id']} [{r['format']} p{r['pass']}] {r['title']} ({r['hook']}/{r['style']})")
    else:
        from collections import Counter
        out({"videos": len(rows), "by_format": Counter(r["format"] for r in rows), "by_pass": Counter(r["pass"] for r in rows),
             "styles": Counter(r["style"] for r in rows), "last": rows[-1]["id"] if rows else None})


def state_path():
    os.makedirs(wpath("output"), exist_ok=True)
    return wpath("output", "_state.json")


def cmd_state(a):
    cfg = load_config()
    sp = state_path()
    st = json.load(open(sp, encoding="utf-8")) if os.path.exists(sp) else {"pass": 1, "notes": []}
    projects = [p["name"] if isinstance(p, dict) else p for p in cfg.get("projects", [])]
    if a.action == "note":
        st.setdefault("notes", []).append(f"{now()} {a.text}")
        st["notes"] = st["notes"][-15:]
    elif a.action == "next":
        if not projects:
            die("no projects in shipreel.config.json (run the questionnaire)")
        q = cfg["quota"]
        while True:
            p_no = st["pass"]
            quota = q["first_pass"] if p_no == 1 else q["later_passes"]
            for proj in projects:
                rows = [r for r in read_ledger(proj) if str(r["pass"]) == str(p_no)]
                have = {}
                for r in rows:
                    have[r["format"]] = have.get(r["format"], 0) + 1
                need = {f: n - have.get(f, 0) for f, n in quota.items() if n - have.get(f, 0) > 0}
                if need:
                    st["current"] = {"project": proj, "pass": p_no, "need": need}
                    json.dump(st, open(sp, "w", encoding="utf-8"), indent=1)
                    out({"next": st["current"], "free_gb": disk_free_gb()})
                    return
            if cfg["quota"].get("max_passes") and p_no >= cfg["quota"]["max_passes"]:
                out({"done": True, "pass": p_no, "msg": "all passes complete"})
                return
            st["pass"] = p_no + 1
    json.dump(st, open(sp, "w", encoding="utf-8"), indent=1)
    out(st)


def cmd_clean(a):
    t = pdir("temp", a.project)
    freed = 0
    def rm(p):
        nonlocal freed
        for root, _, fs in os.walk(p):
            for f in fs:
                try:
                    freed += os.path.getsize(os.path.join(root, f))
                except OSError:
                    pass
        shutil.rmtree(p, ignore_errors=True)
    if a.segments:
        rm(os.path.join(t, "seg")); rm(os.path.join(t, "build"))
    if a.worktrees:
        repo = load_data(a.project).get("path")
        for c in os.listdir(os.path.join(t, "wt")) if os.path.exists(os.path.join(t, "wt")) else []:
            run(["git", "-C", repo, "worktree", "remove", "--force", os.path.join(t, "wt", c)], check=False)
        run(["git", "-C", repo, "worktree", "prune"], check=False)
    out({"ok": True, "freed_mb": round(freed / 1e6, 1), "free_gb": disk_free_gb()})


# ----------------------------------------------------------------------------- fonts / moments / scaffold
def font_families():
    """{family name in lower case: file} for the bundled fonts; empty when PIL isn't installed (then nothing is validated)."""
    pil_font("TikTok Sans SemiBold", 10)  # fills _FONT_FILES
    return dict(_FONT_FILES)


def cmd_fonts(a):
    fam = {}
    try:
        from PIL import ImageFont
        for fn in sorted(os.listdir(FONTS)):
            if fn.lower().endswith((".ttf", ".otf")):
                nm = " ".join(x for x in ImageFont.truetype(os.path.join(FONTS, fn), 20).getname() if x != "Regular")
                fam[nm] = fn
    except ImportError:
        fam = {os.path.splitext(fn)[0]: fn for fn in sorted(os.listdir(FONTS)) if fn.lower().endswith((".ttf", ".otf"))}
    for nm, fn in fam.items():
        presets = [k for k, p in PRESETS.items() if p["font"] == nm]
        use = "; ".join(PRESET_USE.get(k, "") for k in presets) or "caption-level `font` override, styles box/plate/lower"
        print(f"{nm} | {fn} | presets: {','.join(presets) or '-'} | {use}")
    print("use: \"style\": <preset> on a video, \"font\": \"<family>\" on a video or a caption (references/caption-look.md)")


def find_rec_file(ref, project):
    """A rec id, rec:<id>, or a file path -> (path, src string for plans, recordings-cache entry)."""
    if project and not os.path.exists(ref):
        r = ref if ref.startswith("rec:") else "rec:" + ref
        try:
            return resolve_src(r, project), r, rec_meta(r, project)
        except FileNotFoundError:
            pass
    if os.path.exists(ref):
        return os.path.abspath(ref), os.path.abspath(ref).replace("\\", "/"), {}
    raise FileNotFoundError(f"no recording or file '{ref}' (clip.py rec list <project>)")


def find_moments(src, rec, W, H, pace, n=6, length=None, mode="creator"):
    """The n best non-overlapping moving spans of a recording, each with the framing `fit: auto` would use."""
    info = ffprobe(src)
    vi = info["video"]
    if not vi:
        raise ValueError("no video stream")
    dur, sw, sh = info["dur"], vi["w"], vi["h"]
    fps = 4 if dur <= 180 else 2
    frames, cols, rows = motion_frames(src, 0, min(dur, 600), sw, sh, cols=32, fps=fps)
    if not frames:
        raise ValueError("could not read frames")
    energy = [sum(fr) / len(fr) for fr in frames]
    L = float(length or PACES[pace]["shot"][1])
    win = max(1, int(round(L * fps)))
    still = rec.get("still") or []
    cand = []
    for i in range(0, max(1, len(energy) - win + 1)):
        t0 = (i + 1) / fps  # frame i of the difference stream sits between source frames i and i+1
        t1 = min(dur, t0 + L)
        if t1 - t0 < L * 0.6:
            continue
        frozen = sum(max(0.0, min(t1, e) - max(t0, s)) for s, e in still)
        if frozen > 0.3 * (t1 - t0):
            continue
        seg = energy[i:i + win]
        cand.append((sum(seg) / len(seg), round(t0, 2), round(t1, 2), i))
    cand.sort(reverse=True)
    picks = []
    for sc, t0, t1, i in cand:
        if all(t1 <= p[1] - 0.25 or t0 >= p[2] + 0.25 for p in picks):
            picks.append((sc, t0, t1, i))
        if len(picks) >= n:
            break
    top = picks[0][0] if picks else 1.0
    clip = {"src": "x"}
    fit = auto_fit(clip, False, sw, sh, W, H, mode, rec)
    r = (sw / sh) / (W / H)
    res = []
    for rank, (sc, t0, t1, i) in enumerate(picks):
        seg = energy[i:i + win]
        m = {"rank": rank + 1, "in": t0, "out": t1, "score": round(sc / (top or 1), 2), "peak": round(t0 + seg.index(max(seg)) / fps, 2), "fit": fit}
        if fit in ("cover", "stack") and not (0.9 <= r <= 1.1):
            fw, fh = stack_window(sw, sh, W, H) if fit == "stack" else window_frac(sw, sh, W, H)
            g = sum_frames(frames[i:i + win], cols * rows)
            if sum(g) / (len(g) * len(frames[i:i + win])) >= 0.6:
                fx, fy, cx, cy, share = best_window(g, cols, rows, fw, fh)
                if share >= min(1.0, fw * fh * 1.12):
                    m.update({"focus": [fx, fy], "centre": [cx, cy]})
        res.append(m)
    return {"dur": dur, "size": f"{sw}x{sh}", "fit": fit, "len": L, "moments": res, "still": still}


def cmd_moments(a):
    W, H = FORMATS[a.format]
    path, srcref, rec = find_rec_file(a.ref, a.project)
    pace = a.pace or ("fast" if a.format in ("tiktok", "short", "reel", "portrait", "square") else "medium")
    r = find_moments(path, rec, W, H, pace, a.n, a.len, a.mode or load_config().get("mode", "creator"))
    out({"ok": True, "src": srcref, "pace": pace, **r,
         "tip": "moments[0] is the strongest: open the video on it. Use in/out as a clip; leave fit/focus out (auto) unless the sheet shows a miss"})


DEFAULT_LEN = {"tiktok": 15, "short": 20, "reel": 20, "portrait": 20, "square": 15, "x": 25, "twitter": 25, "youtube": 75, "landscape": 60}


def era_label(rec, project):
    """'sep 5' style date for an era recording (from its commit), else a TODO."""
    repo = load_data(project).get("path") if project else None
    if rec.get("commit") and repo:
        d = subprocess.run(["git", "-C", repo, "log", "-1", "--format=%ad", "--date=format:%b %d", rec["commit"]],
                           capture_output=True, text=True).stdout.strip()
        if d:
            return d.lower().replace(" 0", " ")
    return rec.get("era") or "TODO date"


def cmd_scaffold(a):
    """A timed plan skeleton from the best moments of recordings: clips, transitions, caption slots and sounds placed
    for the pace and mode. A writer only fills in the TODO words (and `todo`), then runs check."""
    cfg = load_config()
    mode = a.mode or cfg.get("mode") or "creator"
    fmt = a.format
    W, H = FORMATS[fmt]
    wide = W > H
    recs = [r.strip() for r in a.rec.split(",") if r.strip()]
    recipe = a.recipe
    if recipe == "before-after" and len(recs) != 2:
        die("before-after needs --rec <old>,<new>")
    L = float(a.len or (90 if recipe == "tour" and wide else 45 if recipe == "tour" else DEFAULT_LEN.get(fmt, 20) + (5 if mode == "pro" and not wide else 0)))
    pace = a.pace or pace_for(L)
    P = PACES[pace]
    shot = P["shot"][1]
    pro = mode == "pro"
    sources = []
    for r in recs:
        path, srcref, meta = find_rec_file(r, a.project)
        want = max(3, int(L / shot / max(1, len(recs))) + 3)
        m = find_moments(path, meta, W, H, pace, want, shot * (1.4 if recipe == "tour" else 1.0), mode)
        sources.append({"src": srcref, "meta": meta, "m": m["moments"], "wide_src": float(m["size"].split("x")[0]) / float(m["size"].split("x")[1]) / (W / H) > 1.6})
    if not any(s["m"] for s in sources):
        die("no moving moments found in those recordings (are they frozen? rec list shows !!STILL)")

    def clip_of(s, mo, extra=None):
        c = {"src": s["src"], "in": mo["in"], "out": mo["out"]}
        if s["wide_src"] and mo["out"] - mo["in"] >= 2.5 and not wide:
            c["track"] = "auto"
        if extra:
            c.update(extra)
        return c

    clips, sections = [], []
    if recipe == "before-after":
        old, new = sources
        old_m, new_m = old["m"][:max(1, int(L * 0.4 / shot))], new["m"][:max(2, int(L * 0.6 / shot))]
        look = {"fx": ["sat:0.35", "vignette"]} if pro else {"fx": ["bw"]}
        clips = [clip_of(old, mo, look) for mo in sorted(old_m, key=lambda x: x["in"])]
        switch = len(clips)
        news = [clip_of(new, mo) for mo in sorted(new_m[1:], key=lambda x: x["in"])] + [clip_of(new, new_m[0])]  # best new shot last: the payoff
        news[0]["transition"] = "smooth" if pro else "flash"
        clips += news
        sections = [0, switch]
    elif recipe == "tour":
        for si, s in enumerate(sources):
            sec = [clip_of(s, mo) for mo in sorted(s["m"][:max(2, int(L / len(sources) / (shot * 1.4)))], key=lambda x: x["in"])]
            if si and sec:
                sec[0]["transition"] = "dip" if pro else "whip"
            sections.append(len(clips))
            clips += sec
    else:  # showcase: best moment first (the hook), second best last (the payoff), the rest in story order
        pool = []
        for k in range(max(len(s["m"]) for s in sources)):
            for s in sources:
                if k < len(s["m"]):
                    pool.append((s, s["m"][k]))
        pool.sort(key=lambda p: -p[1]["score"])
        hook, rest = pool[0], pool[1:]
        payoff = rest[0] if rest else None
        mid, total = [], (hook[1]["out"] - hook[1]["in"]) + ((payoff[1]["out"] - payoff[1]["in"]) if payoff else 0)
        for s, mo in rest[1:]:
            if total >= L:
                break
            mid.append((s, mo))
            total += mo["out"] - mo["in"]
        mid.sort(key=lambda p: (sources.index(p[0]), p[1]["in"]))
        clips = [clip_of(*hook)] + [clip_of(*p) for p in mid] + ([clip_of(*payoff)] if payoff else [])
        sections = [0]
        n = len(clips)
        if n >= 4:
            j = n // 2
            if pro:
                clips[j]["transition"] = "push" if pace != "slow" else "dissolve"
            elif pace != "slow":
                clips[j]["transition"] = "whip"
        if pace == "slow":
            for j in range(2, n, 2):
                clips[j].setdefault("transition", "dissolve")
    if wide and fmt in ("youtube", "landscape"):
        clips[0].setdefault("fx", []).append("fadein:0.4")
        clips[-1].setdefault("fx", []).append("fadeout:0.6")

    # timeline (same rules as render), then caption slots and sounds on it
    durs = [c["out"] - c["in"] for c in clips]
    starts, cur = [], 0.0
    for i, c in enumerate(clips):
        _nm, td, _f = clip_transition(c, i, durs[i - 1] if i else 0, durs[i], pace)
        starts.append(round(cur - td, 2))
        cur = cur - td + durs[i]
    est = round(cur, 1)
    beat_d = read_time("a b c d e", pace)
    caps = [{"t": 0, "d": read_time("a b c d e", pace), "text": "TODO hook", "style": "hook" if not pro else "mid"}]
    sfx, overlays = [], []
    last_end = caps[0]["d"]
    for i in range(1, len(clips)):
        t = starts[i] + 0.1
        if i == len(clips) - 1:
            caps.append({"t": round(t, 2), "d": round(max(min(beat_d + 0.6, est - t), 0.5), 2), "text": "TODO payoff", "style": "cap"})
            break
        if t >= last_end + (0.6 if pace == "fast" else 1.0) and t + beat_d < est - 1.0:
            caps.append({"t": round(t, 2), "d": beat_d, "text": f"TODO clips[{i}] beat", "style": "cap"})
            last_end = t + beat_d
    if recipe == "before-after":
        for si, idx in enumerate(sections):
            caps.append({"t": round(starts[idx] + 0.2, 2), "d": round(min(2.4, durs[idx] + (durs[idx + 1] if idx + 1 < len(durs) and idx + 1 not in sections else 0)), 2),
                         "text": era_label(sources[si]["meta"], a.project), "style": "chip"})
        sw_t = starts[sections[1]]
        sfx += [{"asset": "sfx:whoosh-soft" if pro else "sfx:whoosh", "t": round(max(0, sw_t - 0.12), 2), "vol": 0.6},
                {"asset": "sfx:shimmer" if pro else "sfx:ding", "t": round(sw_t + 0.25, 2), "vol": 0.55 if pro else 0.7}]
        if not pro:
            overlays += [{"type": "x", "t": 0.6, "d": round(max(1.0, sw_t - 0.8), 2), "x": 0.5, "y": 0.36, "w": 0.26},
                         {"type": "check", "t": round(sw_t + 0.4, 2), "d": 2.0, "x": 0.5, "y": 0.36, "w": 0.26}]
    if recipe == "tour":
        for si, idx in enumerate(sections):
            caps.append({"t": round(starts[idx] + 0.3, 2), "d": 2.6, "text": f"TODO section {si + 1}", "style": "lower" if wide else "chip"})
    sfx.insert(0, {"asset": "sfx:impact-soft" if pro else "sfx:pop", "t": 0.0, "vol": 0.5 if pro else 0.6})
    for c in caps[1:3]:
        if c["style"] == "cap" and all(abs(x["t"] - c["t"]) > 0.6 for x in sfx):  # one sound per beat, never a pile-up
            sfx.append({"asset": "sfx:pop-soft" if pro else "sfx:pop", "t": round(max(0, c["t"] - 0.05), 2), "vol": 0.45 if pro else 0.55})
    if not pro and est >= 20 and not wide:
        overlays.append({"type": "progress", "color": "white"})
    v = {"id": a.id, "format": fmt, "mode": mode, "pace": pace, "recipe": recipe,
         "style": ("pro" if pro else ("clean" if wide else "bubble")), "hook_type": "TODO",
         "title": "TODO title", "tags": ["TODO"], "description": "TODO description (or delete the field for none)",
         "clips": clips, "captions": caps, "sfx": sfx, "overlays": overlays}
    if pro:
        v["grade"] = "clean"
        v["music"] = {"asset": "music:ambient-pad" if pace == "slow" else "music:soft-pulse", "vol": 0.12, "duck": True}
    if wide and fmt == "youtube" and est >= 60 and len(sections) >= 3:
        v["chapters"] = [{"t": 0 if k == 0 else round(starts[idx], 1), "title": f"TODO chapter {k + 1}"} for k, idx in enumerate(sections)]
    v["todo"] = ["Write every TODO text. Hook (captions[0]) = the promise in 3-6 words. Each `TODO clips[i] beat` = 2-6 words naming what clips[i] "
                 "shows (open clip.py sheet <rec>). Payoff = the result, the number or the joke. Keep the word count the pace allows (pacing.md)",
                 "Pointers: anchor them to the source (`target` from record-web, or `box` read off `clip.py sheet <rec> --grid`) with a `what`, pick the type for the target, and open the `proof` sheet after rendering (references/highlighting.md). No exact target = no highlight."]
    if not pro:
        v["todo"].append("Music decision (music-audio.md section 0): a bed from assets.py find --type music, or \"music\": null with a reason")
    v["todo"].append("After render: read `framing`, `overlay_notes` and `audio` in the result; open clip.py sheet on the final and the `proof` sheet: the subject must be in frame and every highlight on its target")
    plan = {"project": a.project, "pass": a.pass_no, "videos": []}
    if os.path.exists(a.out):
        try:
            plan = json.load(open(a.out, encoding="utf-8"))
            plan.setdefault("videos", [])
        except Exception:
            die(f"{a.out} exists and isn't a plan JSON")
    plan["videos"] = [x for x in plan["videos"] if x.get("id") != a.id] + [v]
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=1, ensure_ascii=False)
    lo, _hi = LIMITS.get(fmt, (1, 9999))
    short = est < min(L * 0.8, lo) or est < lo
    out({"ok": True, "plan": a.out, "id": a.id, "recipe": recipe, "mode": mode, "pace": pace, "est": est, "clips": len(clips), "captions": len(caps),
         **({"warn": f"only {est}s of moving footage for a {L:g}s target ({fmt} needs >= {lo}s): record more, add --rec ids, or pick a shorter format"} if short else {}),
         "next": "replace every TODO (title, tags, description, captions, hook_type), do the `todo` list, delete it, then clip.py check"})


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("doctor").set_defaults(f=cmd_doctor)
    p = sp.add_parser("init"); p.add_argument("project"); p.add_argument("--path"); p.add_argument("--shorthand-in-repo", action="store_true"); p.set_defaults(f=cmd_init)
    p = sp.add_parser("probe"); p.add_argument("file"); p.add_argument("--fast", action="store_true"); p.set_defaults(f=cmd_probe)
    p = sp.add_parser("sheet"); p.add_argument("file"); p.add_argument("--n", type=int, default=6); p.add_argument("--cols", type=int); p.add_argument("--grid", action="store_true")
    p.add_argument("--width", type=int, default=900); p.add_argument("--times"); p.add_argument("--out"); p.set_defaults(f=cmd_sheet)
    p = sp.add_parser("rec"); p.add_argument("action", choices=["add", "list", "find"]); p.add_argument("project"); p.add_argument("query", nargs="?")
    for k in ("--file", "--id", "--feature", "--era", "--commit", "--notes"):
        p.add_argument(k)
    p.add_argument("--copy", action="store_true"); p.set_defaults(f=cmd_rec)

    def recargs(p):
        p.add_argument("project"); p.add_argument("--id", required=True); p.add_argument("--dur", type=float, default=20); p.add_argument("--fps", type=int, default=30)
        for k in ("--feature", "--era", "--commit", "--notes"):
            p.add_argument(k)
    p = sp.add_parser("record-screen"); recargs(p); p.add_argument("--window"); p.add_argument("--region"); p.add_argument("--display")
    p.add_argument("--audio-device"); p.add_argument("--delay", type=float, default=0); p.set_defaults(f=cmd_record_screen)
    p = sp.add_parser("record-web"); recargs(p); p.add_argument("--url", required=True); p.add_argument("--steps"); p.add_argument("--portrait", action="store_true")
    p.add_argument("--mobile", action="store_true"); p.add_argument("--size"); p.add_argument("--scale", type=float); p.add_argument("--no-cursor", action="store_true")
    p.add_argument("--dark", action="store_true"); p.add_argument("--headed", action="store_true"); p.set_defaults(f=cmd_record_web)
    p = sp.add_parser("record-godot"); recargs(p); p.add_argument("--scene"); p.add_argument("--path"); p.add_argument("--godot"); p.add_argument("--resolution"); p.add_argument("--ui-scale", type=float, default=None); p.add_argument("--out-size", help="downscale the capture to WxH, e.g. 1080x1920 after rendering the phone's logical 1280x2276")
    p.add_argument("--autoplay"); p.add_argument("--env", action="append", help="KEY=VALUE toggles passed to the game"); p.set_defaults(f=cmd_record_godot)
    p = sp.add_parser("worktree"); p.add_argument("project"); p.add_argument("action", choices=["add", "remove"]); p.add_argument("commit", nargs="?", default=""); p.add_argument("--before", help="YYYY-MM-DD: the last commit on or before this date"); p.set_defaults(f=cmd_worktree)
    p = sp.add_parser("history"); p.add_argument("project"); p.add_argument("--n", type=int, default=15); p.set_defaults(f=cmd_history)
    p = sp.add_parser("check"); p.add_argument("plan"); p.set_defaults(f=cmd_check)
    p = sp.add_parser("fonts"); p.set_defaults(f=cmd_fonts)
    p = sp.add_parser("moments"); p.add_argument("ref", help="rec id (with --project), rec:<id> or a video file"); p.add_argument("--project")
    p.add_argument("--format", default="tiktok", choices=sorted(FORMATS)); p.add_argument("--pace", choices=sorted(PACES)); p.add_argument("--n", type=int, default=6)
    p.add_argument("--len", type=float, help="seconds per moment (default: the pace's average shot)"); p.add_argument("--mode", choices=MODES); p.set_defaults(f=cmd_moments)
    p = sp.add_parser("scaffold"); p.add_argument("project"); p.add_argument("--rec", required=True, help="rec ids, comma separated (before-after: old,new)")
    p.add_argument("--out", required=True); p.add_argument("--id", default="t01"); p.add_argument("--format", default="tiktok", choices=sorted(FORMATS))
    p.add_argument("--mode", choices=MODES); p.add_argument("--pace", choices=sorted(PACES)); p.add_argument("--len", type=float)
    p.add_argument("--recipe", default="showcase", choices=["showcase", "before-after", "tour"]); p.add_argument("--pass", dest="pass_no", type=int, default=1)
    p.set_defaults(f=cmd_scaffold)
    p = sp.add_parser("render"); p.add_argument("plan"); p.add_argument("--only"); p.add_argument("--force", action="store_true")
    p.add_argument("--no-captioned", action="store_true"); p.add_argument("--keep-build", action="store_true"); p.set_defaults(f=cmd_render)
    p = sp.add_parser("thumb"); p.add_argument("src"); p.add_argument("--t", type=float, default=1.0); p.add_argument("--text", default="")
    p.add_argument("--sticker"); p.add_argument("--out", required=True); p.add_argument("--size", default="1280x720"); p.add_argument("--color", default="yellow"); p.set_defaults(f=cmd_thumb)
    p = sp.add_parser("name"); p.add_argument("title"); p.add_argument("--tags"); p.add_argument("--series"); p.add_argument("--part"); p.set_defaults(f=cmd_name)
    p = sp.add_parser("ledger"); p.add_argument("project"); p.add_argument("--titles", action="store_true"); p.set_defaults(f=cmd_ledger)
    p = sp.add_parser("state"); p.add_argument("action", choices=["next", "show", "note"]); p.add_argument("text", nargs="?"); p.set_defaults(f=cmd_state)
    p = sp.add_parser("clean"); p.add_argument("project"); p.add_argument("--segments", action="store_true"); p.add_argument("--worktrees", action="store_true"); p.set_defaults(f=cmd_clean)
    a = ap.parse_args()
    try:
        a.f(a)
    except SystemExit:
        raise
    except Exception as e:
        die(str(e)[-700:])


if __name__ == "__main__":
    main()
