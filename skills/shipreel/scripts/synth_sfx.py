"""Generate shipreel's original, licence-free "pro" sounds (soft whooshes, ticks, risers, impacts, two quiet music beds).

  python synth_sfx.py [--only whoosh-soft,riser] [--no-index]

Writes assets/sfx/<name>.mp3 and assets/music/<name>.mp3 and adds them to assets/index.json with "pro": true.
These are generated here from noise and sine waves, so they are MIT like the code and safe on YouTube, LinkedIn and
client work. Needs numpy (only for regenerating; the mp3s are committed) and ffmpeg.
"""
import argparse, os, subprocess, sys, tempfile, wave
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ASSETS, load_index, save_index, out

try:
    import numpy as np
except ImportError:  # the committed mp3s don't need this script at all
    np = None

SR = 44100
RNG = None


def t_axis(dur):
    return np.arange(int(dur * SR)) / SR


def noise(n, pink=True):
    w = RNG.standard_normal(n)
    if not pink:
        return w
    # Paul Kellet's economy pink filter
    b = np.zeros((3, n))
    out_ = np.empty(n)
    b0 = b1 = b2 = 0.0
    for i in range(n):
        x = w[i]
        b0 = 0.99765 * b0 + x * 0.0990460
        b1 = 0.96300 * b1 + x * 0.2965164
        b2 = 0.57000 * b2 + x * 1.0526913
        out_[i] = b0 + b1 + b2 + x * 0.1848
    return out_ / 4


def svf_bandpass(x, fc, q=1.2):
    """State-variable band-pass with a per-sample cutoff (Hz array): the sweep is what makes a whoosh."""
    y = np.empty_like(x)
    low = band = 0.0
    damp = 1.0 / q
    f = 2 * np.sin(np.pi * np.clip(fc, 20, SR / 6) / SR)
    for i in range(len(x)):
        high = x[i] - low - damp * band
        band += f[i] * high
        low += f[i] * band
        y[i] = band
    return y


def bell(n, peak=0.5, sharp=2.0):
    p = np.linspace(0, 1, n)
    up = np.clip(p / peak, 0, 1)
    down = np.clip((1 - p) / (1 - peak), 0, 1)
    return (np.sin(np.minimum(up, down) * np.pi / 2)) ** sharp


def stereo(mono, pan_from=0.0, pan_to=0.0):
    pan = np.linspace(pan_from, pan_to, len(mono))
    l = mono * np.cos((pan + 1) * np.pi / 4)
    r = mono * np.sin((pan + 1) * np.pi / 4)
    return np.stack([l, r], axis=1)


def sweep_sine(f0, f1, dur, curve="exp"):
    t = t_axis(dur)
    f = f0 * (f1 / f0) ** (t / dur) if curve == "exp" else np.linspace(f0, f1, len(t))
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def whoosh(dur, f_lo, f_hi, peak, pan=(-0.7, 0.7)):
    n = int(dur * SR)
    env = bell(n, peak, 1.6)
    p = np.linspace(0, 1, n)
    fc = f_lo + (f_hi - f_lo) * np.where(p < peak, (p / peak) ** 1.5, ((1 - p) / (1 - peak)) ** 0.8)
    x = svf_bandpass(noise(n), fc, 1.4)
    return stereo(x * env, *pan)


def reverb(x, secs=2.2, wet=0.28):
    """Convolution with a decaying-noise impulse: cheap, smooth room for the music beds."""
    n = int(secs * SR)
    ir = RNG.standard_normal((n, 2)) * np.exp(-np.linspace(0, 6, n))[:, None]
    ir[:int(0.012 * SR)] = 0
    L = len(x) + n
    size = 1 << (L - 1).bit_length()
    outs = []
    for c in range(2):
        X = np.fft.rfft(x[:, c], size)
        H = np.fft.rfft(ir[:, c], size)
        outs.append(np.fft.irfft(X * H, size)[:L])
    w = np.stack(outs, axis=1)
    w /= np.max(np.abs(w)) + 1e-9
    dry = np.pad(x, ((0, n), (0, 0)))
    return dry * (1 - wet) + w * wet * np.max(np.abs(x))


def wrap_loop(x, length):
    """Fold the tail past `length` back onto the start so the file loops without a seam."""
    y = x[:length].copy()
    tail = x[length:]
    k = min(len(tail), length)
    y[:k] += tail[:k]
    return y


def note(hz, dur, partials=10, detune=(-6, 0, 6), bright=1.6):
    t = t_axis(dur)
    s = np.zeros_like(t)
    for cents in detune:
        f = hz * 2 ** (cents / 1200)
        for k in range(1, partials + 1):
            if f * k > 9000:
                break
            s += np.sin(2 * np.pi * f * k * t + RNG.uniform(0, 6.28)) / k ** bright
    return s / len(detune)


def midi(m):
    return 440 * 2 ** ((m - 69) / 12)


CHORDS = [[48, 52, 55, 59], [45, 48, 52, 55], [41, 45, 48, 52], [43, 47, 50, 52]]  # Cmaj7 Am7 Fmaj7 G6


# ----------------------------------------------------------------------------- the sounds
def s_whoosh_soft():
    return whoosh(0.75, 250, 2600, 0.55)


def s_swoosh_fast():
    return whoosh(0.32, 500, 4200, 0.42, (-0.9, 0.9))


def s_riser():
    dur = 1.6
    n = int(dur * SR)
    p = np.linspace(0, 1, n)
    fc = 200 * (6000 / 200) ** p
    x = svf_bandpass(noise(n), fc, 2.0) * p ** 2.2
    tone = sweep_sine(180, 900, dur) * 0.25 * p ** 2.5
    y = x + tone
    y[-int(0.02 * SR):] *= np.linspace(1, 0, int(0.02 * SR))
    return stereo(y)


def s_impact_soft():
    dur = 1.1
    t = t_axis(dur)
    f = 38 + (85 - 38) * np.exp(-t * 7)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 3.6)
    n = int(0.03 * SR)
    hit = np.zeros_like(t)
    hit[:n] = svf_bandpass(noise(n, False), np.full(n, 900.0), 0.8) * np.linspace(1, 0, n) * 0.6
    return stereo(np.tanh((body + hit) * 1.4))


def s_tick():
    t = t_axis(0.08)
    y = (np.sin(2 * np.pi * 2800 * t) + 0.5 * np.sin(2 * np.pi * 4200 * t)) * np.exp(-t * 90)
    return stereo(y * 0.8)


def s_ui_click():
    t = t_axis(0.12)
    n = int(0.006 * SR)
    burst = np.zeros_like(t)
    burst[:n] = svf_bandpass(noise(n, False), np.full(n, 2200.0), 1.0) * np.linspace(1, 0, n)
    thump = np.sin(2 * np.pi * 180 * t) * np.exp(-t * 42) * 0.5
    return stereo(burst * 1.6 + thump)


def s_pop_soft():
    dur = 0.14
    t = t_axis(dur)
    f = 520 + 480 * np.clip(t / 0.04, 0, 1)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 34)
    y[:int(0.002 * SR)] *= np.linspace(0, 1, int(0.002 * SR))
    return stereo(y)


def s_shimmer():
    dur = 1.4
    t = t_axis(dur)
    y = np.zeros_like(t)
    for i, hz in enumerate((2093, 2637, 3136, 4186, 3520)):
        st = i * 0.07
        tt = np.clip(t - st, 0, None)
        y += np.where(t >= st, np.sin(2 * np.pi * hz * tt) * np.exp(-tt * 3.2), 0) / (1 + i * 0.15)
    return reverb(stereo(y * 0.35, -0.4, 0.4), 1.2, 0.35)[:len(t)]


def m_ambient_pad():
    seg, total = 8.0, 32.0
    n_total = int(total * SR)
    x = np.zeros(int((total + seg + 4) * SR))
    for i, ch in enumerate(CHORDS):
        n = int((seg + 2.0) * SR)
        env = bell(n, 0.35, 1.0)
        s = sum(note(midi(m), seg + 2.0, 8, (-7, 0, 7), 1.8) for m in ch) / len(ch)
        s += 0.35 * np.sin(2 * np.pi * midi(ch[0] - 12) * t_axis(seg + 2.0))
        start = int((i * seg - 1.0) * SR) % n_total
        seg_y = s * env
        idx = (np.arange(n) + start)
        x[idx] += seg_y
    x = wrap_loop(x, n_total)
    trem = 1 + 0.08 * np.sin(2 * np.pi * 0.125 * t_axis(total))  # 4 cycles per loop: seamless
    y = stereo(x * trem)
    y[:, 1] = np.roll(y[:, 1], int(0.011 * SR))
    return wrap_loop(reverb(y, 3.0, 0.35), n_total)


def m_soft_pulse():
    bpm, bars_per_chord = 96, 2
    beat = 60 / bpm
    seg = 4 * beat * bars_per_chord
    total = seg * len(CHORDS)
    n_total = int(total * SR)
    x = np.zeros(n_total + int(2 * SR))
    pattern = [0, 2, 1, 3, 2, 1, 3, 2]  # chord tones on eighth notes
    for i, ch in enumerate(CHORDS):
        for e in range(int(seg / (beat / 2))):
            m = ch[pattern[e % 8]] + 12
            t0 = int((i * seg + e * beat / 2) * SR)
            nd = 0.5
            tt = t_axis(nd)
            pl = (np.sin(2 * np.pi * midi(m) * tt) + 0.3 * np.sin(4 * np.pi * midi(m) * tt)) * np.exp(-tt * 9) * (0.9 if e % 2 == 0 else 0.6)
            x[t0:t0 + len(pl)] += pl * 0.5
        bass = note(midi(ch[0] - 12), seg, 4, (0,), 2.4) * bell(int(seg * SR), 0.1, 0.6) * 0.5
        s0 = int(i * seg * SR)
        x[s0:s0 + len(bass)] += bass
    x = wrap_loop(x, n_total)
    y = stereo(x)
    y[:, 0] = np.roll(y[:, 0], int(0.009 * SR))
    return wrap_loop(reverb(y, 2.4, 0.3), n_total)


SOUNDS = {
    # name: (fn, type, moods, themes, text)
    "whoosh-soft": (s_whoosh_soft, "sfx", ["calm", "neutral"], ["transition", "time-skip", "reveal"], "soft whoosh (pro)"),
    "swoosh-fast": (s_swoosh_fast, "sfx", ["hype", "neutral"], ["transition", "whip"], "fast swoosh for whip pans (pro)"),
    "riser": (s_riser, "sfx", ["tension", "hype"], ["reveal", "build-up", "before-drop"], "noise + tone riser, 1.6 s (pro)"),
    "impact-soft": (s_impact_soft, "sfx", ["serious", "hype"], ["reveal", "title", "drop"], "soft sub impact (pro)"),
    "tick": (s_tick, "sfx", ["neutral", "calm"], ["ui", "caption", "count"], "tiny tick for text and counters (pro)"),
    "ui-click": (s_ui_click, "sfx", ["neutral"], ["ui", "click"], "clean UI click (pro)"),
    "pop-soft": (s_pop_soft, "sfx", ["happy", "neutral"], ["ui", "caption", "pointer"], "soft pop for arrows and labels (pro)"),
    "shimmer": (s_shimmer, "sfx", ["happy", "calm"], ["reveal", "success", "polish"], "bright shimmer for reveals (pro)"),
    "ambient-pad": (m_ambient_pad, "music", ["calm", "neutral", "serious"], ["devlog", "product", "tutorial", "pro"], "Ambient pad, 32 s loop (original)"),
    "soft-pulse": (m_soft_pulse, "music", ["calm", "focused", "happy"], ["product", "tech", "tutorial", "pro"], "Soft pluck pulse, 96 bpm loop (original)"),
}


def write_mp3(y, dst, loudness):
    y = y / (np.max(np.abs(y)) + 1e-9) * 0.89
    pcm = (np.clip(y, -1, 1) * 32767).astype("<i2")
    fd, tmp = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    with wave.open(tmp, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
    af = f"loudnorm=I={loudness}:TP=-1.5:LRA=11" if loudness else "anull"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", tmp, "-af", af, "-ar", "44100", "-c:a", "libmp3lame", "-b:a", "192k", dst], check=True)
    os.remove(tmp)
    return round(len(y) / SR, 2)


def main():
    global RNG
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only")
    ap.add_argument("--no-index", action="store_true")
    a = ap.parse_args()
    if np is None:
        sys.exit("synth_sfx.py needs numpy (pip install numpy). The bundled mp3s work without it.")
    RNG = np.random.default_rng(7)
    names = a.only.split(",") if a.only else list(SOUNDS)
    idx = load_index()
    done = []
    for nm in names:
        fn, typ, moods, themes, text = SOUNDS[nm]
        folder = "sfx" if typ == "sfx" else "music"
        rel = f"{folder}/{nm}.mp3"
        dur = write_mp3(fn(), os.path.join(ASSETS, rel), -18 if typ == "music" else None)
        entry = {"id": f"{typ}:{nm}", "type": typ, "path": rel, "moods": moods, "themes": themes, "text": text, "rating": "clean",
                 "dur": dur, "source": "scripts/synth_sfx.py (generated)", "license": "original, MIT (generated by scripts/synth_sfx.py)",
                 "yt": "ok", "pro": True}
        idx["assets"] = [x for x in idx["assets"] if x["id"] != entry["id"]] + [entry]
        done.append(f"{entry['id']} {dur}s")
    if not a.no_index:
        save_index(idx)
    out({"ok": True, "made": done})


if __name__ == "__main__":
    main()
