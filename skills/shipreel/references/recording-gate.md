# Recording gate: "a file was written" is not "the footage shows the thing"

Read this before the first `record-*` command of a project, and again when a recording looks wrong. Most bad batches fail here, not in the edit.

## The seven rules

1. **Success signals lie.** Exit code 0, `ok: true`, a valid 1080x1920 mp4 and an audio track prove only that ffmpeg ran. The only proof is a contact sheet you looked at. `record-*` also prints `warn: STILL n%` when the footage froze: that is a failure, not a note. A capture fps warn, or `!!CHOPPY` in `rec list`, is a failure too (the web capture fell back to a live screencast).
2. **Software does not play itself.** An app or game waits in its first state (title screen, menu, tutorial, paused scene) until something presses a key or clicks. A recording with no `--steps` / `--autoplay` is a screensaver. Every recording needs a driver that (a) clears whatever blocks the first state, then (b) performs the feature being filmed. A driverless recording is only fine for a page that animates by itself, and the note should say so.
3. **Look before you script.** Never write steps for a screen you haven't seen. Do a 3 s probe recording (`--dur 3`, no steps), run `sheet --n 3`, and write down what is on screen and what is in the way (rule 4). Then write the steps.
4. **Clear the blockers first.** A headless browser is a brand-new user every time and a Godot run starts from the first scene, so first-run UI always appears. Put the dismissal at the start of the steps, before the feature. Blockers to look for:
   - tutorial / onboarding / "this is you" cards (Skip, Next, Got it)
   - title screen or "press start / any key"
   - cookie, consent, age gate, language picker, update or install prompts
   - login, paywall, permission dialogs
   - loading spinners and splash screens (use `waitFor`, not a guessed `wait`)
   - paused state, or a game that waits for the first input
5. **Docs and flags are claims, not facts.** "`/?solo=pro` jumps straight into a bot match", "run `main.tscn` to see the demo", "the dev server is on :3000": check each on screen. A README describes the project when everything works; it says nothing about what a fresh headless run shows.
6. **Frame for the output, not the source.** The final video is portrait (TikTok/Shorts) and full-bleed: the footage fills the frame, no blurred strips. Games and desktop apps record landscape, so decide framing twice and confirm it on a sheet of the *final* video:
   - at record time: `--portrait` for mobile-ish web UIs. For Godot, `record-godot --resolution WxH` builds a throwaway mirror project (folder junctions plus a patched `project.godot`; the real project is never written and a scratch copy of the player's saves is used), because Movie Maker takes its size from the project's viewport settings and ignores the flag otherwise. `--out-size 1080x1920` downscales afterwards, and a phone game's logical size is 1280 wide, so portrait is `--resolution 1280x2276 --out-size 1080x1920`. It only helps if the game's UI adapts to the shape: a HUD that sizes itself from the window can misplace when the OS window is clamped to your screen height, so open the sheet and fall back to landscape if the HUD is wrong. A closer in-game camera mode (chase, side, first-person) also helps
   - look for footage that already exists in the repo (`launch/`, `docs/`, store videos, device screen recordings): a 2408x1080 phone recording crops to 9:16 at 1:1 pixels, sharper than a 720p capture. Skip stretches that show private screens (wallets, logins)
   - at render time: `cover` with `focus: [x, y]` on the subject, or a `track` that glides across the frame following the action and swings to the HUD when a caption names it; `zoomin:1.4@x,y` pushes in. `crop:x,y,w,h` picks an exact region. Use `blurpad` only for UI screens where the whole width matters, never as the default for gameplay
   - the subject should be at least about a quarter of the frame height. A 20 px figure in a wide field reads as nothing
7. **Write only what you have seen, and show what you say.** Captions come from sheets and `marks`, never from the README's feature list. If the caption names a boss, a swipe, a score, enemies or a health bar, a frame of that thing must be on screen while the caption plays. If it's in the recording but off to the side or tiny, **move the camera to it**: a different `focus` per clip, a `track` glide, a `zoomin` on the HUD (`effects-cookbook.md`, "Getting the thing into view"). If it isn't in the recording at all, re-record it into view (autoplay `call`/`set`, open the panel, a closer camera mode) or change the caption. Read x,y positions off `clip.py sheet <rec> --grid`.

## After every recording (editor, mandatory)

```
C sheet temp/<p>/rec/<id>.mp4 --n 6      # then actually open the jpg
```

Answer these in writing, in the `notes` field of the result and in your return line:

- `saw:` one sentence on what the frames show (e.g. "player runs left, kills 3 enemies, hp bar drops at 6 s"). If you cannot write this, you did not look.
- **Changes?** Do frames 1 to 6 differ in a way a viewer would notice? Same frame six times = frozen.
- **Blocker visible?** Modal, menu, spinner, consent banner, login, loading bar in any frame = fix the steps.
- **Right thing, big enough?** The feature the id promises is in frame and not tiny or cropped away.
- `warn`: any `STILL n%` from the command, or `!!STILL` in `rec list`.

Any "no" → fix the steps/autoplay/camera and re-record. Max 2 retries, then the failure protocol (skip / fake it / ask). Never pass a recording on with "probably fine".

## Symptoms, causes, fixes

| what the sheet shows | usual cause | fix |
|---|---|---|
| same menu or start button for the whole clip | no click on Start / Play | add `{"click": "text=START"}` (web) or `{"action": "ui_accept"}` / `click` event (Godot) as the first step |
| a dimmed tutorial / consent card the whole clip | first-run overlay never dismissed | first step clicks Skip / Accept; or open the URL param/storage flag that skips it, but only after checking it works |
| character standing still, nothing happens | no autoplay events, or wrong action names | read `[input]` in `project.godot`, drive `move_*` / fire / ability actions with `hold` |
| blank page, spinner, or half-rendered UI | recorded before load | `waitFor` a selector that only exists when ready, then `wait` a beat |
| right scene, wrong content (empty list, no data) | needs data / login / seed | failure protocol: mock via URL params or `eval`, never fake a feature that doesn't exist |
| portrait video shows empty ground, the action is off to the side | landscape source + `cover` at centre | `cover` with `focus` / `track` on the subject, or record portrait (`--resolution`), or use a device recording from the repo |
| subject tiny in the frame | wide camera, full-screen field | camera mode, zoom, `crop:` or `zoomin@x,y` |
| caption says X, footage shows something else | caption written from the README | re-time the clip, re-record, or rewrite the caption to what is shown |
| probe lists `static_spans` > 3 s | frozen recording or a held title card | cut the span out, or re-record with motion |
| motion looks slow or stuttery | web capture fell back to a live screencast (`mode` screencast, or an fps warn) | re-record; virtual mode is the default. If it keeps failing, the page is too heavy or has a video element |

## Why this file exists

A real failed run: three projects recorded with no `--steps` / `--autoplay`. One clip was a stick figure standing in a field (top-down landscape cropped to the dead centre of a portrait frame), one was a "START" button for 12 s, one was a tutorial card over a paused table. All three exited 0, passed `check`, and the captions described a boss fight, a job interview and a goal in two seconds that appeared nowhere on screen. No frame was ever looked at. The seven rules are the general lessons; the table is the specific cases.
