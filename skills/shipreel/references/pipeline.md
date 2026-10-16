# Pipeline: commands per step

`C` = `python S/scripts/clip.py`. Every command prints one JSON line (or short lines). Exit 0 = ok, 1 = failed, 3 = needs the user (failure protocol).

## 0. Setup (once per workspace)

```
C doctor                                  # ffmpeg+libass, node>=22, chrome, godot, disk, RAM
C init <project> --path <repo>            # creates output/<p>/, output/<p>/textless/, temp/<p>/; returns shorthand path
```

## 1. Brief: `.project-shorthand.txt`

`C init` returns `shorthand` and `shorthand_is_template`. Read it **first**, before opening anything in the repo.
- Template or missing → scout subagent (`roles/scout.md`) fills it.
- Exists → check `git -C <repo> log <scouted_sha>..HEAD --oneline | head -20`. Re-scout only if new work matters (new features, visual changes).

From it the director picks the **batch slate**: for N videos, N different (feature × angle × era) combos. Spread across features. Use eras for "then vs now" videos. Write the slate as a `state note` so a resumed session knows it.

## 2. Record (only what's missing)

```
C rec list <p>                            # what's cached: id | dur | WxH | feature/era | notes
C rec find <p> "inventory"
```

Recording ids: `<feature>-<what>[-<era>]`, e.g. `combat-boss-intro`, `editor-drag-drop-v1`. Record **raw and long enough** (10 to 40 s). Cut in the plan, not at record time, so one recording feeds several videos. Record portrait (`--portrait`) for mobile-ish web UIs and landscape for games and desktop apps; the render crops (`fit`).

### Web apps
```
C record-web <p> --id signup-flow --url http://localhost:3000 --steps temp/<p>/steps/signup.json --dur 20 [--portrait] [--dark]
```
Steps (wait/ms are milliseconds):
```json
[{"waitFor": "#app"}, {"wait": 600}, {"click": "text=Get started"}, {"type": "hello@demo.dev", "into": "input[type=email]"},
 {"press": "Enter"}, {"mark": "dashboard"}, {"scroll": 700, "ms": 1200}, {"hover": ".chart"}, {"wait": 1500}]
```
`mark` puts exact timestamps in the result (`marks`), so the writer can cut on `in: marks.dashboard - 0.3` without looking at frames. `--portrait` gives exactly 1080×1920; landscape is 1280×720 CSS at 1.5×. A fake cursor with click ripples is drawn (`--no-cursor` to hide it). Use the shorthand's `live_url` if the dev server is expensive to start. If you start a dev server, run it in the background and kill it after.

### Godot games
```
C record-godot <p> --id boss-fight --scene res://levels/boss.tscn --dur 15 --autoplay temp/<p>/steps/boss.json [--env DEBUG_OVERLAY=0] [--resolution 1920x1080]
```
Uses Movie Maker (`--write-movie`, fixed fps, so it's deterministic and frame-perfect even on a slow PC) and `templates/godot_autoplay.gd` via `--script`. Nothing in the project changes. Timeline:
```json
{"events": [{"t": 0.5, "action": "ui_accept"}, {"t": 1, "action": "move_right", "hold": 1.5}, {"t": 3, "key": "SPACE"},
            {"t": 4, "click": [640, 360]}, {"t": 5, "call": ["/root/Main", "spawn_boss"]}, {"t": 6, "set": ["/root/Main/Player", "speed", 900]}]}
```
Times start at the scene's first frame. Pick input actions from `project.godot` `[input]`. The game's own audio is recorded too.

### Anything else (desktop apps, CLIs, other engines)
```
C record-screen <p> --id cli-demo --dur 12 [--window "Window Title" | --region x,y,w,h] [--delay 1]
```
Start the app first (background). For CLIs, open a terminal with a big font and type with a script. Screen capture records whatever is on screen: confirm nothing private is visible (`never show` list), or record a `--window` only.

### Existing files (trailers, screenshots, gifs in the repo)
```
C rec add <p> --file <repo>/media/trailer.mp4 --id trailer --feature overview [--copy]
```

### Old versions ("then vs now", dev-stage videos)
```
C worktree <p> add <commit-or-tag>        # → temp/<p>/wt/<sha>; record from that path (record-godot --path / start its dev server)
C worktree <p> remove <commit-or-tag>
```
Tag those recordings with `--era e1 --commit <sha>`. Old commits often don't build. Give it one try with the documented run command; if it fails, use the failure protocol (fake it = screenshots from git history or old media in the repo).

## 3. Write the plan

Writer subagent → `temp/<p>/plans/p<pass>_<batch>.json` with ≤5 videos (`plan-schema.md`, `copy-rules.md`, `effects-cookbook.md`, `templates/plan.example.json`). Inputs: shorthand path, `rec list` output, `ledger --titles` output (avoid repeats), slate, pass number, `config.mix`.

## 4. Check
```
C check temp/<p>/plans/p1_a.json
```
Fix every hard issue (exit 1). Soft issues (ai-tell in captions, long caption, tag count) → fix unless deliberate.

## 5. Render
```
C render temp/<p>/plans/p1_a.json [--only t03,t04] [--force]
```
Per video: `output/<p>/<name>.mp4` (captioned), `output/<p>/textless/<name>.mp4`, `<name>.txt` description (or an empty extensionless `<name>` file when there's no description), `<name>.jpg` if `thumb`, and a row in `output/<p>/videos.csv`. Unchanged videos are skipped (plan hash), and normalized segments are cached in `temp/<p>/seg/` by content hash, so re-renders after a caption fix skip the segment step. On a low-end laptop a 15 s TikTok takes about 1 to 2 min and a 1-minute YouTube video about 3 to 4 min at the default x264 `medium`. `SHIPREEL_PRESET=veryfast` (or `render.preset` in config) makes them about 2.5× faster with roughly 30% bigger files. Use it for drafts and review rounds, and drop it for the final pass if disk allows.

## 6. Review
```
C sheet output/<p>/<name>.mp4 --n 6       # one jpg, 6 frames with timestamps
C probe output/<p>/<name>.mp4             # static_spans (>3s frozen = low-effort flag), loudness sanity
```
Reviewer subagent (`roles/reviewer.md`) gets the sheet paths + plan path, and returns fixes per id. Apply → `render --only`. Max 2 fix rounds per video; then ship it or drop it.

## 7. Wrap the project
```
C state note "<p> pass1 done: 10 tiktoks; best angles: x,y; unused recs: a,b"
C clean <p> --segments --worktrees        # frees temp; keeps recordings (rec/) for later passes
C state next
```

## Later passes

Pass 2+ = 2 YouTube (60 to 300 s) + 2 TikToks per project. YouTube videos are compilations or stories: a devlog ("I rebuilt X 3 times"), a feature tour, a then-vs-now, "making of" with eras. Reuse cached recordings and record new angles. YouTube gets chapters, a thumbnail, more overlays (lower thirds, code cards, spotlights) and the longer description. Don't upload TikTok cuts back-to-back inside a YouTube video: that's the reused-content flag.
