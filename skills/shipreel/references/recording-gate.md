# Recording gate: "a file was written" is not "the footage shows the thing"

Read this before the first `record-*` command of a project, and again when a recording looks wrong. Most bad batches fail here, not in the edit.

## The seven rules

1. **Success signals lie.** Exit code 0, `ok: true`, a valid 1080x1920 mp4 and an audio track prove only that ffmpeg ran. The only proof is a contact sheet you looked at. `record-*` also prints `warn: STILL n%` when the footage froze: that is a failure, not a note.
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
6. **Frame for the output, not the source.** The final video is portrait (TikTok/Shorts) but games and desktop apps record landscape. The default `cover` fit keeps only the centre ~35% of a 16:9 frame, which is often empty ground. Decide framing twice, and confirm it on a sheet of the *final* video:
   - at record time: `--portrait` for mobile-ish web UIs; for Godot try `--resolution 1080x1920` (it only helps if the project's stretch/camera adapts, so check the sheet); use an in-game camera mode (chase, side, first-person) that keeps the subject large; zoom the page/UI to the part that matters
   - at render time: `fit: "blurpad"` keeps the whole landscape frame in the middle of a portrait video with a blurred fill, which is the safe default for gameplay. Use `cover` only when the action sits near the centre, and then set `focus: [x, y]` on the subject. `crop:x,y,w,h` picks an exact region; `zoomin:1.4@x,y` pushes in on a HUD element or character
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
| portrait video shows empty ground, the action is off to the side | landscape source + `cover` at centre | `fit: "blurpad"`, or `cover` with `focus` on the subject, or record portrait |
| subject tiny in the frame | wide camera, full-screen field | camera mode, zoom, `crop:` or `zoomin@x,y` |
| caption says X, footage shows something else | caption written from the README | re-time the clip, re-record, or rewrite the caption to what is shown |
| probe lists `static_spans` > 3 s | frozen recording or a held title card | cut the span out, or re-record with motion |

## Why this file exists

A real failed run: three projects recorded with no `--steps` / `--autoplay`. One clip was a stick figure standing in a field (top-down landscape cropped to the dead centre of a portrait frame), one was a "START" button for 12 s, one was a tutorial card over a paused table. All three exited 0, passed `check`, and the captions described a boss fight, a job interview and a goal in two seconds that appeared nowhere on screen. No frame was ever looked at. The seven rules are the general lessons; the table is the specific cases.
