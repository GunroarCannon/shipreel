"""shipreel engine. Every command prints terse JSON/lines so agents spend few tokens reading output.

  clip.py doctor                                   tools, disk, RAM, fonts, chrome, godot
  clip.py init <project> --path <repo> [--shorthand-in-repo]
  clip.py probe <file>                             duration/size/audio (+ music-likely heuristic, scene cuts)
  clip.py sheet <file> [--n 6] [--width 900]       one contact-sheet jpg (cheap visual check)
  clip.py rec add|list|find <project> ...          recordings cache (temp/<project>/data.json)
  clip.py record-screen <project> --id X --dur 20 [--window "Title" | --region x,y,w,h]
  clip.py record-web <project> --id X --url URL [--steps s.json] [--portrait] [--dur 20]
  clip.py record-godot <project> --id X [--scene res://a.tscn] [--dur 15] [--autoplay t.json] [--godot path]
  clip.py worktree <project> add <commit> | remove <commit>    old versions without touching the repo
  clip.py check <plan.json>                        validate plan + copy lint (AI-tells, lengths, emoji)
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
                    disk_free_gb, workspace, wpath, now)

FORMATS = {"tiktok": (1080, 1920), "short": (1080, 1920), "reel": (1080, 1920), "portrait": (1080, 1920),
           "youtube": (1920, 1080), "landscape": (1920, 1080), "square": (1080, 1080)}
LIMITS = {"tiktok": (10, 30), "short": (10, 60), "reel": (10, 90), "portrait": (5, 180), "youtube": (60, 300), "landscape": (5, 600), "square": (5, 120)}
ENC_FINAL = ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-profile:v", "high", "-pix_fmt", "yuv420p",
             "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv", "-movflags", "+faststart"]
ENC_SEG = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p"]
AUD = ["-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]


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


IMG_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


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


def cmd_sheet(a):
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
    out({"sheet": dst, "times": times})


def ffesc(p):
    """Escape a path for use inside an ffmpeg filtergraph option value."""
    return p.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


# ----------------------------------------------------------------------------- recordings
def cmd_rec(a):
    if a.action == "list":
        for r in load_data(a.project)["recordings"]:
            extras = " ".join(f"{k}={r[k]}" for k in ("feature", "era", "commit", "orient", "music") if r.get(k))
            flag = f" !!STILL {r['still_pct']}%" if r.get("warn") else ""
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
                     url=a.url, marks=meta.get("marks"), orient="portrait" if a.portrait else "landscape")
    out({"ok": True, **e})


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
    cmd = [godot, "--path", proj, "--write-movie", tmp_avi, "--fixed-fps", str(a.fps), "--quit-after", str(frames)]
    if a.resolution:
        cmd += ["--resolution", a.resolution]
    env = dict(os.environ)
    if a.autoplay:
        env["SHIPREEL_AUTOPLAY"] = os.path.abspath(a.autoplay)
        env["SHIPREEL_SCENE"] = a.scene or ""
        cmd += ["--script", os.path.join(SKILL_DIR, "templates", "godot_autoplay.gd")]
    elif a.scene:
        cmd += [a.scene]
    for kv in a.env or []:
        k, v = kv.split("=", 1); env[k] = v
    p = subprocess.run(cmd, capture_output=True, text=True, env=env, encoding="utf-8", errors="replace", timeout=a.dur * 20 + 120)
    if not os.path.exists(tmp_avi):
        die("godot did not write a movie", tail=(p.stderr or p.stdout)[-600:])
    dst = rec_out(a.project, a.id)
    run(["ffmpeg", "-y", "-v", "error", "-i", tmp_avi, "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", *AUD, dst])
    os.remove(tmp_avi)  # MJPEG avi is huge; keep only the mp4
    out({"ok": True, **register_rec(a.project, a.id, dst, feature=a.feature, era=a.era, commit=a.commit, notes=a.notes, how="godot", scene=a.scene)})


def cmd_worktree(a):
    repo = load_data(a.project).get("path")
    if not repo:
        die("project path unknown: clip.py init <project> --path <repo>")
    wt = os.path.join(pdir("temp", a.project, "wt"), a.commit[:10])
    if a.action == "add":
        if not os.path.exists(wt):
            run(["git", "-C", repo, "worktree", "add", "--detach", wt, a.commit])
        out({"ok": True, "path": wt, "note": "read-only use; remove when done: clip.py worktree <p> remove <commit>"})
    else:
        run(["git", "-C", repo, "worktree", "remove", "--force", wt], check=False)
        run(["git", "-C", repo, "worktree", "prune"], check=False)
        out({"ok": True, "removed": wt})


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
    "cartoon": {"font": "Luckiest Guy", "size": 106, "fill": "white", "outline": "black", "ol": 7, "sh": 3, "upper": True, "hi": "orange"},
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


def build_ass(v, W, H, total, path):
    k = min(W, H) / 1080
    portrait = H > W
    preset = PRESETS.get(v.get("style", "pop"), PRESETS["pop"])
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
    for nm, sz, al, mv in (("hook", P["size"] * 1.18, 8, hook_mv), ("cap", P["size"], 2, (0.30 if portrait else 0.10) * H), ("mid", P["size"], 5, 0)):
        style(nm, P["font"], sz, P["fill"], P["outline"], P["ol"] + (1 if nm == "hook" and not bx else 0), P["sh"], al, side, right, mv, box=bx, back=P["outline"] if bx else "black")
        # auto-contrast fallback (see auto_contrast): same geometry on a dark plate, for busy or colour-clashing footage
        style(nm + "_plate", P["font"], sz, "white", "black", 12, 0, al, side, right, mv, box=True, back="black", back_alpha=0x58)
    style("box", "TikTok Sans SemiBold", 70, "black", "white", 12, 0, 2, side, right, (0.30 if portrait else 0.10) * H, box=True, back="white")
    style("plate", "TikTok Sans SemiBold", 70, "white", "black", 12, 0, 2, side, right, (0.30 if portrait else 0.10) * H, box=True, back="black", back_alpha=0x58)
    style("callout", "Montserrat Black", 80, "yellow", "black", 6, 0, 5, 0, 0, 0)
    style("header", "TikTok Sans ExtraBold", 66, "black", "white", 14, 0, 8, side, right, (0.115 if portrait else 0.05) * H, box=True, back="white")
    style("card", P["font"], P["size"] * 1.35, "white", "black", 6, 0, 5, side, side, 0)
    style("code", "JetBrains Mono ExtraBold", 60, "#7CFFB2", "black", 12, 0, 2, side, right, (0.30 if portrait else 0.12) * H, box=True, back="#0B0F14", back_alpha=0x20)
    style("lower", "Montserrat Bold", 56, "white", "black", 16, 0, 1, 0.06 * W, 0, 0.09 * H, box=True, back="black", back_alpha=0x50)
    style("title", "Montserrat Black", 104, "white", "black", 8, 4, 5, side, side, 0)
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
    FADE = "{\\fad(120,100)}"

    if v.get("header"):
        hd = v["header"] if isinstance(v["header"], dict) else {"text": v["header"]}
        add(hd.get("t", 0), hd.get("until") or total, "header", ass_text(hd["text"]), "{\\fad(150,0)}")

    for c in v.get("captions", []):
        st = c.get("style", "cap")
        t0, d = float(c.get("t", 0)), float(c.get("d", 2))
        t1 = min(total, t0 + d)
        up = c.get("upper", upper_default if st in ("hook", "cap", "mid", "card") else False)
        pos = ""
        if "x" in c and "y" in c:
            pos = f"{{\\an5\\pos({int(c['x'] * W)},{int(c['y'] * H)})}}"
        anim = c.get("anim", "pop" if st in ("hook", "cap", "mid", "callout") else "fade")
        a_tag = POP if anim == "pop" else FADE if anim == "fade" else ""
        if c.get("color"):
            pos += f"{{\\c{ass_color(c['color'])}}}"
        hic = ass_color(c["hi"]) if c.get("hi") else hi
        if c.get("color"):
            back_c = ass_color(c["color"])
        elif st in ("box",) or (bx and st in ("hook", "cap", "mid")):
            back_c = ass_color("black")
        elif st in ("plate",) or st.endswith("_plate"):
            back_c = ass_color("white")
        else:
            back_c = fill_c
        words = c["text"].replace("*", "").split()
        if c.get("words") and len(words) > 1:  # word-by-word groups, each popping in
            n = int(c.get("per", 2 if len(words) <= 8 else 3))
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


def fit_chain(fit, W, H, focus):
    fx_, fy_ = focus or (0.5, 0.5)
    if fit.startswith("crop:"):
        x, y, w, h = [float(v) for v in fit[5:].split(",")]
        return f"crop=iw*{w}:ih*{h}:iw*{x}:ih*{y}," + fit_chain("cover", W, H, focus)
    if fit == "contain":
        return f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black"
    if fit == "blurpad":
        return (f"split=2[bga][fga];[bga]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},gblur=sigma=28,eq=brightness=-0.12:saturation=1.2[bgb];"
                f"[fga]scale={W}:{H}:force_original_aspect_ratio=decrease[fgb];[bgb][fgb]overlay=(W-w)/2:(H-h)/2")
    # cover (default)
    return f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}:(iw-{W})*{fx_}:(ih-{H})*{fy_}"


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


def build_segment(clip, W, H, fps, project, seg_dir, cfg):
    """One clip -> normalized mp4 (W x H, fps, stereo 48k). Cached by content hash."""
    if "card" in clip:
        src = None
    else:
        src = resolve_src(clip["src"], project)
    key_src = {"mt": os.path.getmtime(src), "sz": os.path.getsize(src)} if src else None
    key = sha({"c": {k: v for k, v in clip.items() if k not in ("caption", "chapter", "note")}, "W": W, "H": H, "fps": fps, "s": key_src}, 14)
    dst = os.path.join(seg_dir, f"{key}.mp4")
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
        return dst, dur

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
    # focus for fit = first zoom focus if any
    fit_focus = clip.get("focus")
    v = [",".join(chain)] if chain else []
    fit = clip.get("fit", "blurpad" if is_img else "cover")
    if src is not None and clip.get("track") and info and info["video"]:
        v.append(track_chain(clip["track"], clip.get("zoom"), info["video"]["w"], info["video"]["h"], W, H))
    elif src is not None:
        v.append(fit_chain(fit, W, H, fit_focus))
    post = []
    for f in fxs:
        n, arg, focus = parse_fx(f)
        fx_, fy_ = focus or clip.get("focus") or (0.5, 0.5)
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
            raise ValueError(f"unknown fx '{n}' (see references/effects-cookbook.md)")
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
        amap = ["-map", "1:a"]
    fc = vgraph + (";" + agraph if agraph else "")
    cmd = ["ffmpeg", "-y", "-v", "error", *inputs, *extra_in, "-filter_complex", fc, "-map", "[vo]", *amap,
           "-t", str(dur), *ENC_SEG, *AUD, "-r", str(fps), dst]
    run(cmd)
    return dst, dur


# ----------------------------------------------------------------------------- render: overlays + audio mix
OV_TIP = {"arrow": (0.95, 0.5), "arrow-curved": (0.84, 0.76)}  # where the tip sits inside the png (normalized)


def overlay_graph(v, W, H, fps, total, inputs_start):
    """Returns (extra_inputs, filter_lines, out_label). Base video is [vbase]."""
    ins, lines = [], []
    cur = "vbase"
    n_in = inputs_start
    for i, o in enumerate(v.get("overlays", [])):
        typ = o.get("type", "sticker")
        t0 = float(o.get("t", 0)); d = float(o.get("d", total - t0)); t1 = min(total, t0 + d)
        en = f"enable='between(t,{t0:.3f},{t1:.3f})'"
        nxt = f"v{i}"
        if typ == "box":
            x, y, w, h = o["x"], o["y"], o["w"], o["h"]
            lines.append(f"[{cur}]drawbox=x={int(x * W)}:y={int(y * H)}:w={int(w * W)}:h={int(h * H)}:color={o.get('color', 'red')}@0.95:t={int(o.get('thick', 8))}:{en}[{nxt}]")
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


def audio_graph(v, total, base_in, n_in, has_product_music):
    ins, lines = [], []
    mix = ["[pa]"]
    prod_vol = float(v.get("product_volume", 1.0))
    lines.append(f"[{base_in}]volume={prod_vol}[pa0]")
    music = v.get("music")
    if music:
        lines.append("[pa0]asplit=2[pa][key]")
    else:
        lines.append("[pa0]anull[pa]")
    for j, s in enumerate(v.get("sfx", [])):
        path = resolve_asset(s["asset"])
        ins += ["-i", path]
        t = float(s.get("t", 0)); ms = int(t * 1000)
        trim = f"atrim=start={s.get('start', 0)}" + (f":duration={s['dur']}" if s.get("dur") else "") + ",asetpts=PTS-STARTPTS,"
        lines.append(f"[{n_in}:a]{trim}aresample=48000,aformat=channel_layouts=stereo,volume={s.get('vol', 0.8)},adelay={ms}|{ms}[s{j}]")
        mix.append(f"[s{j}]")
        n_in += 1
    if music:
        mm = music if isinstance(music, dict) else {"asset": music}
        path = resolve_asset(mm["asset"])
        ins += ["-stream_loop", "-1", "-i", path]
        st = float(mm.get("start", 0)); vol = float(mm.get("vol", 0.16))
        lines.append(f"[{n_in}:a]atrim=start={st},asetpts=PTS-STARTPTS,atrim=duration={total:.3f},aresample=48000,aformat=channel_layouts=stereo,"
                     f"volume={vol},afade=t=in:d=0.6,afade=t=out:st={max(0, total - 1.5):.3f}:d=1.5[mus0]")
        if mm.get("duck", True):
            lines.append("[mus0][key]sidechaincompress=threshold=0.04:ratio=8:attack=15:release=350[mus]")
        else:
            lines.append("[key]anullsink;[mus0]anull[mus]")
        mix.append("[mus]")
        n_in += 1
    lines.append("".join(mix) + f"amix=inputs={len(mix)}:normalize=0:duration=first,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[aout]")
    return ins, lines, n_in


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
            y0 = H - ((0.30 if portrait else 0.10) * H) - th
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
        if fill not in ("white", "black", "#FFFFFF", "#000000") and min(_ratio(_hex(fill), s_[0]) for s_ in samples) < 1.9:
            c2["color"] = "white"; fix.append(f"{fill} text clashed with the background -> white")
        if "*" in c.get("text", ""):
            hi = c.get("hi") or preset["hi"]
            if min(_ratio(_hex(hi), s_[0]) for s_ in samples) < 1.9:
                best = max(("yellow", "white", "cyan", "pink", "orange"), key=lambda n: min(_ratio(_hex(n), s_[0]) for s_ in samples))
                c2["hi"] = best; fix.append(f"accent {hi} clashed -> {best}")
        if busy > 0.20:
            c2["style"] = st + "_plate"; fix.append(f"busy background (detail {busy:.2f}) -> dark plate")
        if fix:
            notes.append({"t": round(t0, 1), "text": c.get("text", "")[:24], "fix": "; ".join(fix)})
        out_caps.append(c2)
    return out_caps, notes


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

    # A) segments
    segs, total = [], 0.0
    card_caps = []
    muted_music = product_music_clips(v, project)
    for ci, c in enumerate(v["clips"]):
        if ci in muted_music:
            c = {**c, "audio": "mute"}  # the project's own music would fight the library bed: two musics is always wrong
        p, d = build_segment(c, W, H, fps, project, seg_dir, cfg)
        if "card" in c:
            card_caps.append({"t": total, "d": d, "text": c["card"], "style": "card", "anim": "pop"})
        if c.get("caption"):  # shorthand: caption tied to a clip, relative times
            cc = c["caption"] if isinstance(c["caption"], dict) else {"text": c["caption"]}
            card_caps.append({**cc, "t": total + float(cc.get("t", 0)), "d": float(cc.get("d", d - float(cc.get("t", 0))))})
        segs.append(p); total += d
    total = round(total, 3)
    # B+C) concat filter (not the concat demuxer: its stream-copied timestamps make overlays drop/dup frames)
    #      + overlays + audio mix -> textless master, one encode
    seg_in = sum((["-i", sp_] for sp_ in segs), [])
    n = len(segs)
    cat = "".join(f"[{i}:v][{i}:a]" for i in range(n)) + f"concat=n={n}:v=1:a=1[vcat][acat]"
    ov_in, ov_lines, vlabel, n_in = overlay_graph(v, W, H, fps, total, n)
    au_in, au_lines, n_in = audio_graph(v, total, "acat", n_in, False)
    # pin fps: with extra overlay inputs ffmpeg otherwise guesses 25fps and drops frames (captions drift)
    fc = ";".join([cat, "[vcat]null[vbase]"] + ov_lines + [f"[{vlabel}]fps={fps},format=yuv420p[vout]"] + au_lines)
    os.makedirs(os.path.dirname(textless), exist_ok=True)
    run(["ffmpeg", "-y", "-v", "error", *seg_in, *ov_in, *au_in, "-filter_complex", fc, "-map", "[vout]", "-map", "[aout]",
         "-t", str(total), "-r", str(fps), *enc_final(cfg), *AUD, textless])
    # D) captions -> final
    v2 = dict(v); v2["captions"] = card_caps + list(v.get("captions", []))
    contrast_notes = []
    if v.get("auto_contrast", cfg["render"].get("auto_contrast", True)):
        v2["captions"], contrast_notes = auto_contrast(v2["captions"], textless, PRESETS.get(v.get("style", "pop"), PRESETS["pop"]), W, H, total, bool(v.get("header")))
    ass = os.path.join(vdir, "captions.ass")
    n_ev = build_ass(v2, W, H, total, ass)
    if n_ev and not a.no_captioned:
        vf = f"subtitles=filename='{ffesc(ass)}':fontsdir='{ffesc(FONTS)}'"
        run(["ffmpeg", "-y", "-v", "error", "-i", textless, "-vf", vf, "-c:a", "copy", "-r", str(fps), *enc_final(cfg), final])
    else:
        shutil.copy2(textless, final)
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
                               "hook": v.get("hook_type", ""), "style": v.get("style", "pop"), "plan_hash": phash})
    if not a.keep_build:
        shutil.rmtree(vdir, ignore_errors=True)
    lo, hi = LIMITS.get(fmt, (1, 9999))
    warn = [] if lo <= total <= hi else [f"duration {total}s outside {lo}-{hi}s for {fmt}"]
    return {"id": v["id"], "ok": True, "dur": total, "file": os.path.relpath(final, workspace()), "desc": os.path.basename(desc),
            **({"thumb": os.path.basename(thumb)} if thumb else {}), **({"warn": warn} if warn else {}),
            **({"contrast_fixed": contrast_notes} if contrast_notes else {}),
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


def lint_text(s):
    s_l = s.lower()
    hits = [w for w in AI_TELLS if w in s_l]
    issues = [f"ai-tell:'{h}'" for h in hits]
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


def cmd_check(a):
    cfg = load_config()
    plan, vids = load_plan(a.plan)
    titles_seen = {r["title"].lower(): r["id"] for p in [plan.get("project")] if p for r in read_ledger(p)}
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
        if len(v.get("title", "")) > (100 if fmt == "youtube" else 90):
            iss.append("title too long")
        iss += [f"title {x}" for x in lint_text(v.get("title", ""))]
        if v.get("description"):
            iss += [f"desc {x}" for x in lint_text(v["description"])]
        est = 0.0
        for c in v.get("clips", []):
            try:
                if "card" not in c:
                    p = resolve_src(c["src"], proj)
                    if os.path.splitext(p)[1].lower() in IMG_EXT or c.get("still"):
                        est += float(c.get("dur", 2))
                    else:
                        d = ffprobe(p)["dur"]
                        est += (min(float(c.get("out", d)), d) - float(c.get("in", 0))) / float(c.get("speed", 1))
                        iss += still_in_clip(c, proj, d)
                        for k in c.get("track", []):
                            if not (0 <= float(k.get("x", -1)) <= 1 and 0 <= float(k.get("y", -1)) <= 1):
                                iss.append(f"track key {k} needs x,y between 0 and 1 (fractions of the source frame; read them off clip.py sheet --grid)")
                        if c.get("track") and len(c["track"]) < 2:
                            iss.append("track needs 2+ keys (start point + where to glide); for one fixed spot use focus")
                else:
                    est += float(c.get("dur", 1.5))
                for f in c.get("fx", []):
                    n, arg, _ = parse_fx(f)
                    if n == "freeze":
                        est += float(arg or 1)
            except Exception as e:
                iss.append(f"clip src: {str(e)[:90]}")
        lo, hi = LIMITS.get(fmt, (1, 9999))
        if not (lo <= est <= hi):
            iss.append(f"est duration {est:.1f}s outside {lo}-{hi}")
        for c in v.get("captions", []):
            if float(c.get("t", 0)) >= est:
                iss.append(f"caption after end: '{c['text'][:20]}'")
            if len(c.get("text", "").split()) > (12 if fmt == "youtube" else 9):
                iss.append(f"long caption ({len(c['text'].split())}w): '{c['text'][:24]}...'")
            iss += [f"cap {x}" for x in lint_text(c.get("text", ""))]
        plain = [c for c in v.get("captions", []) if "x" not in c and c.get("style", "cap") in ("hook", "cap", "mid")]
        for i, c1 in enumerate(plain):
            for c2 in plain[i + 1:]:
                if c1.get("style", "cap") == c2.get("style", "cap") and float(c1.get("t", 0)) < float(c2.get("t", 0)) + float(c2.get("d", 2)) and float(c2.get("t", 0)) < float(c1.get("t", 0)) + float(c1.get("d", 2)):
                    iss.append(f"captions overlap in time at the same spot: '{c1['text'][:18]}' / '{c2['text'][:18]}' (stack them in one caption with a line break, or shorten d)")
        caps = [c for c in v.get("captions", []) if float(c.get("t", 0)) < 1.0]
        if fmt != "youtube" and not caps and not v.get("header"):
            iss.append("no on-screen hook in first second")
        for o in v.get("overlays", []):
            if o.get("asset"):
                try:
                    resolve_asset(o["asset"])
                except Exception as e:
                    iss.append(str(e)[:80])
        for s in v.get("sfx", []):
            try:
                resolve_asset(s["asset"])
            except Exception as e:
                iss.append(str(e)[:80])
        if v.get("music"):
            try:
                resolve_asset(v["music"]["asset"] if isinstance(v["music"], dict) else v["music"])
            except Exception as e:
                iss.append(str(e)[:80])
            pm = product_music_clips(v, proj) if proj else []
            if pm:
                iss.append(f"music: clips{pm} have their own music; render will mute them under the library track (add \"product_music\":\"keep\" to keep it and drop `music`)")
        elif fmt == "tiktok" and not v.get("sfx") and not v.get("overlays") and not any("fx" in c or "sticker" in c for c in v["clips"]):
            iss.append("bare: no music, SFX, overlay or fx - raw recording with captions. Add at least a meme SFX and one pointing overlay or fx (references/effects-cookbook.md)")
        if fmt == "youtube" and v.get("chapters"):
            ch = v["chapters"]
            if ch[0]["t"] != 0 or len(ch) < 3:
                iss.append("chapters: first must be 0:00 and >=3 chapters")
        styles_used[v.get("style", "pop")] = styles_used.get(v.get("style", "pop"), 0) + 1
        hard = [x for x in iss if not x.startswith(("cap ai-tell", "desc ai-tell", "title ai-tell", "cap emoji", "long caption", "tags=", "music:", "bare:"))]
        bad += bool(hard)
        report.append({"id": v["id"], "est": round(est, 1), "issues": iss})
    for r in report:
        print(f"{r['id']} ~{r['est']}s " + ("OK" if not r["issues"] else "| " + "; ".join(r["issues"])))
    if len(vids) >= 6 and max(styles_used.values()) > len(vids) * 0.6:
        print(f"variety: style '{max(styles_used, key=styles_used.get)}' used {max(styles_used.values())}/{len(vids)} - rotate presets")
    tt = [v for v in vids if v.get("format", "tiktok") == "tiktok"]
    mode = (cfg.get("music") or {}).get("meme_bed", "tiktok")
    if len(tt) >= 5 and mode != "off":
        want = float(cfg.get("mix", {}).get("music_share_short", 0.4))
        have = sum(1 for v in tt if v.get("music"))
        if have < max(1, int(len(tt) * want * 0.5)):
            print(f"music: {have}/{len(tt)} TikToks have a music bed (target about {int(want * 100)}%). "
                  "Pick tracks with `assets.py find --type music --mood <m>` (references/music-audio.md, section 'Meme music bed').")
    sys.exit(1 if bad else 0)


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
    p = sp.add_parser("record-godot"); recargs(p); p.add_argument("--scene"); p.add_argument("--path"); p.add_argument("--godot"); p.add_argument("--resolution")
    p.add_argument("--autoplay"); p.add_argument("--env", action="append", help="KEY=VALUE toggles passed to the game"); p.set_defaults(f=cmd_record_godot)
    p = sp.add_parser("worktree"); p.add_argument("project"); p.add_argument("action", choices=["add", "remove"]); p.add_argument("commit"); p.set_defaults(f=cmd_worktree)
    p = sp.add_parser("check"); p.add_argument("plan"); p.set_defaults(f=cmd_check)
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
