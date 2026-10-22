# Effects cookbook

Effects exist to **point the eye** and **mark a beat**. One effect per beat; let calm footage breathe in between. How often depends on the pace (`pacing.md`): fast = something new every 2.5 s, medium every 4 s, slow every 8 s. A TikTok usually wants 3 to 6 "moments" (a zoom, an arrow, an SFX, a freeze) in 10 to 30 s, and a YouTube video about one per 5 to 10 s. Pro mode keeps the same rhythm with a smaller toolbox (`pro-mode.md`); `simple-rules.md` has the per-mode budget table.

## Clip `fx` (in `clips[].fx`)

| fx | arg | use for |
|---|---|---|
| `zoom:1.3@x,y` | factor, focus | static punch-in on a detail (UI text, a small sprite) |
| `zoomin:1.25@x,y` / `zoomout` | end factor | slow push toward the important thing; zoomout = reveal |
| `freeze:0.8` | seconds | freeze the last frame. "wait for it", the moment before a fail, a meme pause |
| `bw` | | flashback, "before", "the old version", dramatic freeze |
| `sepia` | | "years ago" eras |
| `slowmo:0.5` / `speed:2` | rate | slow = satisfying moment; fast = boring stretch (build, loading, grinding) |
| `shake:0.6` | strength | impact, explosion, crash, bug (creator only) |
| `flash` | dur | hard cut onto a reveal |
| `glitch` | | bug, error, "something broke" (creator only) |
| `vhs` | | retro/old version, nostalgia (creator only) |
| `pixelate:24` | block | censor, or "low-res prototype" joke |
| `blur:12` | sigma | background behind a card or meme |
| `dim:0.3` | | darken behind text |
| `vignette` | | focus, cinematic |
| `contrast:1.25`, `sat:1.4`, `bright:0.08` | | make dull UI pop (light touch) |
| `mirror`, `reverse` | | rewind gags ("let me explain"), loop endings |
| `fadein:0.4` / `fadeout:0.5` | | YouTube openers and endings only; never fade a TikTok in |

## Getting the thing into view (camera work)

Real TikToks don't talk about the enemies while the camera sits on the player: they move to the enemies, or zoom the health bar, while it's mentioned. A caption that names something the frame doesn't show is a bug (`recording-gate.md`). Fix it, cheapest first:

0. **Let auto aim first.** With no `fit`/`focus`, render points the crop at the motion (`framing` in the result says where), and `track: "auto"` follows it around (`framing.md`). That covers "show the action". The steps below are for showing a *specific* thing a caption names.
1. **Different `focus` per clip.** Cut the same recording into two or three clips and give each its own `focus` (`[0.2,0.5]` on the player, `[0.85,0.3]` on the enemies, `[0.1,0.08]` on the HUD). A cut is the most common look.
2. **`track`: a glide.** `"track":[{"t":0,"x":0.3,"y":0.6},{"t":2.5,"x":0.85,"y":0.3,"move":0.8}]` starts on the player and drifts to the enemies as the caption lands, then holds. Time it so the camera arrives about 0.3 s before the word appears. Hold at least 1 s on each stop.
3. **`zoomin:1.6@x,y` / `zoom:1.5@x,y`** pushes in on a HUD element or a small sprite; combine with a `focus`, `box` or `arrow` anchored to the same spot (a static `zoom` holds still, so highlights work on it; a `zoomin` never does, so the render drops highlights on it).
4. **Change the recording.** If it's never on screen, the footage is wrong: use an autoplay `call`/`set` to spawn the enemies, open the panel, take damage so the health bar moves, or pick a different camera mode, then re-record.
5. **Change the caption** to what is shown. Never leave the mismatch.

Find x,y with `clip.py sheet <rec.mp4> --grid`: it draws a 10% grid labelled 1 to 9 (yellow = x along the bottom, cyan = y down the right). Read the thing's position as tenths, e.g. enemies at x 8, y 3 → `[0.8, 0.3]`. After rendering, open the final's sheet and check the subject is actually in frame.

## Overlays (in `overlays[]`)

- **Pointing at a thing: `references/highlighting.md`.** Anchor it to the source (`target` from `record-web`, or `box`/`at` read off `sheet --grid`) with a `what`, pick the type for the target (`box`/`focus` for UI, `marker`/`bar` for text, `arrow` for small things, `ring` only for round game objects), and open the `proof` sheet after rendering. The render drops a highlight it can't place exactly; no highlight beats a wrong one.
- **Arrow**: `{"type":"arrow","t":4.5,"d":2,"box":[0.58,0.4,0.14,0.08],"what":"boss health bar","color":"yellow"}`; the tip touches the nearest edge of the box. Pair it with a sound (`ding`, `pop`; pro `ui-click`).
- **Circle it (`ring` / `scribble`)**: round game objects only, creator mode. Pro and UI: `box`, `focus`, `marker`, `bar`.
- **Wrong vs right**: `x` on the old version, `check` on the new.
- **`focus`** (dims everything but a rounded window) for "look here" on busy screens, YouTube especially; `spotlight` is the round version.
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

A hard cut is the default and stays the most common join. A transition marks a **turn**: a version change, a project switch, a new section, a reveal. One or two per TikTok, one per section change on YouTube. Never on every cut, and never fade a TikTok in from black (`fadein` stays YouTube-only). Leave `transition_dur` out: the pace sets it (fast 0.22 s, medium 0.4 s, slow 0.7 s; whips and flashes stay ≤ 0.22 s).

| transition | looks like | use for | mode |
|---|---|---|---|
| `whip` (`whipright`, `whipup`, `whipdown`) | fast slide with horizontal motion blur + a whoosh (automatic) | energy, "meanwhile", jump to the next feature | creator; pro once |
| `flash` | through white | a reveal, "now", the after side of before/after | creator; pro for one reveal |
| `zoom` | push into the old shot as the new one appears | "let's look closer", into a detail | both |
| `glitch` | pixel break-up | a bug, a crash, "something broke" | creator |
| `iris` / `irisclose` | circle opens / closes | cartoon intros and outros, a "the end" | creator |
| `dissolve` / `fade` | soft blend | time passing, calm devlogs, story pieces | both; pro and slow |
| `dip` | through black | new section, chapter change, "later" | both; pro and slow |
| `push` (`pushright`, `pushup`) | the new shot pushes the old one out | next feature, next step in a tour | both; pro |
| `smooth` | soft-edged wipe | before → after in pro | pro |
| `blur`, `squeeze`, `reveal`, `cover`, `radial` | ffmpeg xfade looks | variety, sparingly | both |

Sound: `"transition_sfx": true` adds a matching sound (whoosh for whip/push/zoom/dip, shutter or impact for flash, an error for glitch; soft versions in pro), or name one (`"sfx:riser"`). Whips get theirs automatically. The sound starts 0.06 s before the join.

## Colour grade (`grade` on the video)

One look over the whole video, applied under the overlays (arrows and stickers keep their colours). `clean` for UI and product footage, `punchy`/`vivid` for dull game captures, `cinematic` (teal shadows, warm highlights) for trailers and story pieces, `warm`/`cool` to match a brand or a mood, `film` for nostalgia (adds grain: not on small UI text), `mono` for a whole black-and-white piece. For one era of a comparison use the clip `fx` (`bw`, `sepia`, `sat:0.35`) instead.

## Fancy vs plain

`config.mix.fancy_per_batch` (default 2 of 10) = heavy-edit videos (many beats, memes, glitch). The rest are clean: one or two effects, good captions. A whole feed of maximal edits looks like a template farm.

## Caption presets ↔ vibe

Creator: `pop` (TikTok Classic: semibold white, thin black outline, yellow accent; the default), `bubble` (Fredoka, rounded and chunky: the game-dev look), `game` (Lilita One, bold friendly game captions), `candy` (Titan One, cozy and cute games), `pixel` (Press Start 2P, retro and pixel-art games), `trendy` (Bricolage Grotesque + lime accent, modern creator look), `note` (Caveat, handwritten asides), `label` (black text in a white box; best over busy footage), `punch` (the old extra-heavy look, for loud moments), `hormozi` (Montserrat Black caps + green highlight, punchy facts), `clean` (subtle, for pretty footage), `meme` (Anton, impact style), `comic` (Bangers, yellow, games), `cartoon` (Luckiest Guy, playful games), `dev` (JetBrains Mono, code-y), `marker` (Permanent Marker, hand-made feel), `bold` (Poppins + pink highlight), `cinema` (Bebas Neue, trailers, YouTube titles).

Pro: `pro` (Inter), `minimal` (Manrope), `editorial` (Instrument Serif), `tech` (Space Grotesk), `headline` (Archivo Black), `condensed` (Oswald caps). Match the font to the footage: pixel art with `pixel`, a cozy farming game with `candy`, a dev tool with `tech` or `dev`. Rotate between videos, never inside one. `clip.py fonts` lists every family; `clip.py check` warns when one preset covers more than 60% of a batch.
