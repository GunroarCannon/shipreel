"""Get the user's attention: flashing rounded screen border (Claude orange) + sound (Windows buzzer.exe), with fallbacks.

  python buzz.py "Need a GIPHY key (paste it in chat)" [-t 2] [--sound none|beep|path] [--color "#FFC107"]

Windows: tools/buzzer/buzzer.exe (auto-built with the built-in csc if missing).
macOS: notification + afplay.  Linux: notify-send + paplay/ffplay.  Anything else: terminal bell.
Non-blocking: returns immediately.
"""
import argparse, os, platform, shutil, subprocess, sys, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import SKILL_DIR, ASSETS

BUZZ_DIR = os.path.join(SKILL_DIR, "tools", "buzzer")


def ensure_exe():
    exe = os.path.join(BUZZ_DIR, "buzzer.exe")
    if not os.path.exists(exe):
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", os.path.join(BUZZ_DIR, "build.ps1")],
                       capture_output=True)
    return exe if os.path.exists(exe) else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("message", nargs="*")
    ap.add_argument("-t", "--time", type=float, default=float(os.environ.get("SHIPREEL_BUZZ_SECONDS", 2)))
    ap.add_argument("--sound"); ap.add_argument("--color", default=os.environ.get("SHIPREEL_BUZZ_COLOR", "#FFC107"))
    ap.add_argument("--force", action="store_true", help="buzz even if one just fired")
    a = ap.parse_args()
    msg = " ".join(a.message) or "shipreel needs you"
    sysname = platform.system()
    # one buzz per question: a global Claude Code hook and the shipreel skill may both ask for it within a moment
    stamp = os.path.join(tempfile.gettempdir(), "shipreel_buzz.stamp")
    try:
        if not a.force and time.time() - os.path.getmtime(stamp) < 6:
            print("buzz skipped (just buzzed)"); return
    except OSError:
        pass
    try:
        open(stamp, "w").close()
    except OSError:
        pass
    if os.environ.get("SHIPREEL_BUZZ", "1") == "0":
        print("\a" + msg); return
    if sysname == "Windows":
        exe = ensure_exe()
        if exe:
            args = [exe, "-t", str(a.time), "-m", msg, "-c", a.color] + (["-s", a.sound] if a.sound else [])
            subprocess.Popen(args, creationflags=0x00000008)  # DETACHED_PROCESS
            print(f"buzzed: {msg}"); return
    snd = a.sound or os.path.join(BUZZ_DIR, "buzzer.mp3")
    if sysname == "Darwin":
        subprocess.Popen(["osascript", "-e", f'display notification "{msg}" with title "shipreel" sound name "Funk"'])
        if os.path.exists(snd) and shutil.which("afplay"):
            subprocess.Popen(["afplay", snd])
    elif sysname == "Linux":
        if shutil.which("notify-send"):
            subprocess.Popen(["notify-send", "-u", "critical", "shipreel", msg])
        for player in (["paplay"], ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"]):
            if os.path.exists(snd) and shutil.which(player[0]):
                subprocess.Popen(player + [snd]); break
    print("\a" + f"buzzed: {msg}")


if __name__ == "__main__":
    main()
