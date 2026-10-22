# Effects cookbook

Effects exist to **point the eye** and **mark a beat**. One effect per beat; let calm footage breathe in between. A TikTok usually wants 3 to 6 "moments" (a zoom, an arrow, an SFX, a freeze) in 10 to 30 s, and a YouTube video about one per 5 to 10 s.

## Clip `fx` (in `clips[].fx`)

| fx | arg | use for |
|---|---|---|
| `zoom:1.3@x,y` | factor, focus | static punch-in on a detail (UI text, a small sprite) |
| `zoomin:1.25@x,y` / `zoomout` | end factor | slow push toward the important thing; zoomout = reveal |
| `freeze:0.8` | seconds | freeze the last frame. "wait for it", the moment before a fail, a meme pause |
| `bw` | | flashback, "before", "the old version", dramatic freeze |
| `sepia` | | "years ago" eras |
| `slowmo:0.5` / `speed:2` | rate | slow = satisfying moment; fast = boring stretch (build, loading, grinding) |
| `shake:0.6` | strength | impact, explosion, crash, bug |
| `flash` | dur | hard cut onto a reveal |
| `glitch` | | bug, error, "something broke" |
| `vhs` | | retro/old version, nostalgia |
| `pixelate:24` | block | censor, or "low-res prototype" joke |
| `blur:12` | sigma | background behind a card or meme |
| `dim:0.3` | | darken behind text |
| `vignette` | | focus, cinematic |
| `contrast:1.25`, `sat:1.4`, `bright:0.08` | | make dull UI pop (light touch) |
| `mirror`, `reverse` | | rewind gags ("let me explain"), loop endings |
| `fadein:0.4` / `fadeout:0.5` | | YouTube openers and endings only; never fade a TikTok in |

## Getting the thing into view (camera work)

Real TikToks don't talk about the enemies while the camera sits on the player: they move to the enemies, or zoom the health bar, while it's mentioned. A caption that names something the frame doesn't show is a bug (`recording-gate.md`). Fix it, cheapest first:

1. **Different `focus` per clip.** Cut the same recording into two or three clips and give each its own `focus` (`[0.2,0.5]` on the player, `[0.85,0.3]` on the enemies, `[0.1,0.08]` on the HUD). A cut is the most common look.
2. **`track`: a glide.** `"track":[{"t":0,"x":0.3,"y":0.6},{"t":2.5,"x":0.85,"y":0.3,"move":0.8}]` starts on the player and drifts to the enemies as the caption lands, then holds. Time it so the camera arrives about 0.3 s before the word appears. Hold at least 1 s on each stop.
3. **`zoomin:1.6@x,y` / `zoom:1.5@x,y`** pushes in on a HUD element or a small sprite; combine with a `ring` or `arrow` on the same spot.
4. **Change the recording.** If it's never on screen, the footage is wrong: use an autoplay `call`/`set` to spawn the enemies, open the panel, take damage so the health bar moves, or pick a different camera mode, then re-record.
5. **Change the caption** to what is shown. Never leave the mismatch.

Find x,y with `clip.py sheet <rec.mp4> --grid`: it draws a 10% grid labelled 1 to 9 (yellow = x along the bottom, cyan = y down the right). Read the thing's position as tenths, e.g. enemies at x 8, y 3 → `[0.8, 0.3]`. After rendering, open the final's sheet and check the subject is actually in frame.

## Overlays (in `overlays[]`)

- **Arrow at the thing**: `{"type":"arrow","t":4.5,"d":2,"x":0.62,"y":0.41,"angle":150,"color":"yellow"}`. x,y = what the tip touches; angle 0 = pointing right, 90 = down, 180 = left. Pair it with `ring` on the same spot and an SFX (`ding`, `pop`, `vine-boom`).
- **Circle it**: `ring` (clean) or `scribble` (hand-drawn, funnier).
- **Wrong vs right**: `x` on the old version, `check` on the new.
- **Spotlight** for "look here" in busy screens (YouTube especially).
- **Censor** any email, key, token, personal name or path on screen. Do it even if the shorthand doesn't list it.
- **Sticker memes**: `{"type":"sticker","asset":"meme:press-x-to-doubt","t":10.5,"d":1.4,"x":0.72,"y":0.62,"w":0.4,"anim":"slide"}`. Keep them inside the safe area, 1 to 2 s, with an SFX.
- **Progress bar** on longer TikToks (≥20 s) improves completion; skip it on short ones.
- **`fx` overlay** for a range across several clips (e.g. bw from 3 to 6 s).

## Patterns that work for dev content

- **Before/after**: era clip `bw` + `x` → whoosh + flash → current clip + `check` + `ding`.
- **Bug reveal**: normal play → `freeze:0.8` + `zoom:1.4@bug` + `ring` + `vine-boom` → caption "wait". Then the meme or the punchline.
- **Satisfying loop**: `slowmo:0.6` on the best moment; end on a frame that matches the first (loops count as rewatches).
- **Big number**: `card` "4,812 lines deleted" (1.2 s, `pop`) + `ding`. Use one at most.
- **Speedrun the boring part**: `speed:4` + `sfx:keyboard-typing` + caption "3 hours later".
- **Meme cut**: 1 to 1.5 s image clip (`fit: blurpad`, `zoomin:1.15`) with its SFX. Max 1 to 2 per TikTok; none in about half the videos (`config.mix.meme_share`).
- **"POV"**: header "POV: you finally fixed the physics" + a clean clip; no effects needed. Variety is good.

## Transitions (between clips)

A hard cut is the default. Use a transition on a version cut, a project switch, or a YouTube scene change. On TikTok pass `transition_dur` 0.25. Don't put one on every cut, and don't fade a TikTok in from black (`fadein` stays YouTube-only). The field names and the clock rule are in `plan-schema.md`.

## Fancy vs plain

`config.mix.fancy_per_batch` (default 2 of 10) = heavy-edit videos (many beats, memes, glitch). The rest are clean: one or two effects, good captions. A whole feed of maximal edits looks like a template farm.

## Caption presets ↔ vibe

`pop` (TikTok Classic: semibold white, thin black outline, yellow accent; the default), `label` (black text in a white box; best over busy footage), `punch` (the old extra-heavy look, for loud moments), `hormozi` (Montserrat Black caps + green highlight, punchy facts), `clean` (subtle, for pretty footage), `meme` (Anton, impact style), `comic` (Bangers, yellow, games), `cartoon` (Luckiest Guy, playful games), `dev` (JetBrains Mono, code-y), `marker` (Permanent Marker, hand-made feel), `bold` (Poppins + pink highlight), `cinema` (Bebas Neue, trailers, YouTube titles). Rotate. `clip.py check` warns when one preset covers more than 60% of a batch.
