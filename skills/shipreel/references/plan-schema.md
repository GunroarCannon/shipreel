# Plan JSON

One file = one batch (≤5 videos). `{"project": "...", "pass": 1, "mode": "creator", "videos": [ ... ]}`. A single video object at the top level works too. The fastest correct start is `clip.py scaffold` (it writes a timed skeleton with `TODO` text); otherwise copy from `templates/plan.example.json` (creator) or `templates/plan.pro.example.json` (pro). Times are seconds; positions are fractions of the frame (0 to 1, from the top-left).

## Video

| key | type | notes |
|---|---|---|
| `id` | str | unique within the project: `t01`, `y01` (pass 2: `p2t01`) |
| `format` | `tiktok` \| `youtube` \| `short` \| `square` \| `x` \| `twitter` \| `landscape` | tiktok/short 1080×1920, youtube/x/twitter/landscape 1920×1080, square 1080×1080 |
| `title` | str | human title, it becomes the file name. See copy-rules |
| `tags` | [str] | 3 to 5 niche hashtags without `#`. Also go in the file name |
| `series` | {name, part} | optional → `name-part-N_title_#tags` |
| `mode` | `creator` \| `pro` | default `config.mode` (creator). Pro = no memes, clean type, soft sounds: `pro-mode.md` |
| `pace` | `auto` \| `fast` \| `medium` \| `slow` | default auto: ≤22 s fast, ≤60 s medium, longer slow. Sets shot lengths, reading time, transition length: `pacing.md` |
| `style` | caption preset | creator: `pop` (default) `bubble` `game` `candy` `pixel` `trendy` `note` `chip` `label` `punch` `hormozi` `clean` `meme` `comic` `dev` `marker` `bold` `cinema` `cartoon`. Pro: `pro` (default) `minimal` `editorial` `tech` `headline` `condensed` (+ `clean` `label` `cinema`). Rotate them; `clip.py fonts` lists which font each uses |
| `font` | family name | override the preset's font for the whole video (any family from `clip.py fonts`) |
| `accent` | colour | override the accent colour for `*starred*` words (pro also reads `config.brand.accent`) |
| `grade` | `none` `clean` `punchy` `vivid` `warm` `cool` `cinematic` `film` `mono` | one colour look over the whole video, under the overlays |
| `hook_type` | str | for the ledger: `contrarian`, `before-after`, `number`, `question`, `pov`, `fail`, `flex`, `tutorial`, `clickbait`... |
| `header` | str or {text, t, until} | persistent white-box text at the top (TikTok's "persistent caption"). Off by default: a project name boxed on every frame reads as a template |
| `clips` | [clip] | in order. Total length = the sum of clip lengths minus transition overlaps |
| `captions` | [caption] | burned in (not in the textless file) |
| `overlays` | [overlay] | in the textless file too |
| `sfx` | [{asset, t, vol=0.8, start, dur}] | |
| `music` | asset or {asset, vol=0.16, start, duck=true} | meme/library bed, ducked under product audio. The project's own music in `rec:` clips is auto-muted (`product_music:"keep"` opts out) |
| `product_volume` | float | global product-audio gain (1.0) |
| `description` | str | caption or description body. Omit → empty extensionless marker file |
| `links` | [str] | lines appended to the description |
| `mentions` | [str] | `@handle`s appended |
| `chapters` | [{t, title}] | YouTube. First must be t=0, ≥3 entries, each ≥10 s apart |
| `thumb` | {t, text, sticker, color, from} | thumbnail jpg (1280×720 or 1080×1920) |
| `sound_note` | str | posting note for in-app sound, written to the .txt and marked as not caption |
| `fps` | int | default from config (30) |
| `recipe`, `todo` | written by `scaffold` | `todo` = reminders; `check` warns until you delete it. Any `TODO` text fails `check` |

## Clip

```json
{"src": "rec:combat-boss", "in": 3.2, "out": 8.0, "fit": "cover", "focus": [0.5, 0.4], "speed": 1.0,
 "fx": ["zoomin:1.25@0.6,0.4", "freeze:0.8", "bw"], "audio": "keep", "caption": "the boss has 3 phases"}
```

- `src`: `rec:<id>` (this project), `rec:<project>/<id>` (another project), `meme:<name>`, `gif:<name>`, a path, or an image.
- `in`/`out`: trim of the source. Images and `still` use `dur`.
- `still: true`: freeze the frame at `in` for `dur`.
- `card: "text"` + `dur` + `bg`: a full-screen text card on a color. Use sparingly (≤1 per TikTok).
- `fit`: leave it out (= `auto`: picks by source shape and aims at the action, `framing.md`). Or `cover` (crop to fill), `stack` (portrait: whole shot on top + close-up below), `float[:0.86]` (rounded card with a shadow over a blur), `blurpad[:1.3]` (whole source over its blur; the number enlarges it), `contain` (bars), `crop:x,y,w,h` (choose a region, then cover).
- `focus`: [x, y] for `cover`, `stack` and zooms: where the crop window sits (0 = left/top, 1 = right/bottom). Leave it out (or `"auto"`) and render aims at the motion; the result's `framing` says where. Different clips of the same recording can use different `focus` values (a cut to the enemies, a cut to the health bar).
- `track: "auto"`: a follow-cam that glides to where the action moves (needs a source wider or taller than the frame).
- `track`: a **moving camera** over the source frame: `[{"t":0,"x":0.2,"y":0.6}, {"t":3,"x":0.8,"y":0.3,"move":0.8}, {"t":6,"x":0.9,"y":0.1}]`. The first key is where the camera starts; each later key says "at `t` seconds (as the clip plays) glide to this point over `move` seconds (default 0.6), then hold". x,y = the point to centre on, as fractions of the **source** frame (get them from `clip.py sheet <rec> --grid`). Needs a source bigger than the window (a landscape recording in a portrait video); it replaces `fit`. `zoom` (≥1, default 1) tightens the window for the whole clip.
- `speed`: 0.25 to 4 (audio pitch kept).
- `audio`: `keep` | `mute` | a number (gain).
- `fx`: see effects-cookbook. Syntax `name[:arg][@x,y]`.
- `caption`: str or {text, t, d, style...}. `t` is relative to when this clip starts to appear (the start of the transition into it). Good for "this clip says this".
- `transition`: optional, on clips after the first. Omitted, `none` or `cut` is a hard cut. Names: `fade` `dissolve` `dip` (through black) `flash` (through white) `whip` `whipright` `whipup` `whipdown` (fast slide with motion blur and a whoosh) `push` `pushright` `pushup` `pushdown` `zoom` `iris` `irisclose` `blur` `glitch` `squeeze` `reveal` `cover` `smooth` `radial`, or any ffmpeg xfade name (`wipeleft`, `slideup`, `circleopen`...). The first clip ignores this field. When to use which: `effects-cookbook.md`.
- `transition_dur`: seconds. Omitted = the pace's length (fast 0.22, medium 0.4, slow 0.7; whips, flashes and glitches ≤ 0.22). `0` is a hard cut. It has to be shorter than both clips it joins.
- `transition_sfx`: `true` (a matching sound: whoosh for whip/push/zoom, shutter or impact for flash), `false`, or an asset (`"sfx:riser"`). Whips default to `true`; the others to `false`.
- Video-level captions, sfx, overlays and chapters sit on the finished timeline. Each transition shortens the video by its overlap. A caption near a join can sit on the blend. When to use a transition: `effects-cookbook.md`.

## Caption

```json
{"t": 0, "d": 2.2, "text": "it took 3 rewrites", "style": "hook", "words": true, "per": 2}
```

- `d`: seconds on screen. Leave it out and render uses the reading time for the pace (`pacing.md`).
- `font`: a family from `clip.py fonts` for this caption only.
- `style`: `chip` (small translucent rounded box, dark lowercase text, low in the frame: date tags and deadpan asides, works inside any preset), `box` (black text on a white box, readable on anything), `plate` (white text on a dark plate), `hook` (big, top third), `cap` (default, lower-middle above the UI), `mid` (center), `callout` (yellow, center or `x,y`), `card`, `code` (mono box), `lower` (lower third, YouTube), `title` (big center), `meme-top`, `meme-bottom` (classic impact).
- Animation: default `pop` for hook/cap/mid/callout (`fade` for pro presets and slow pace), `fade` for others; `"anim": "rise"` (a short tilt-up), `"anim": "none"`.
- Modes: `words: true` (2 to 3 word groups popping, `per`), `karaoke: true` (line stays, active word highlighted), `type: true` (typewriter).
- `x`, `y` (position the center), `color`, `upper` (override the preset's uppercase), `hi` (accent colour for `*starred*` words), `contrast: false` (opt out of the auto-fix below).
- **Accent words and lines**: wrap them in asterisks, `"it took *3 rewrites*"`, or put a second line in the accent colour with `
`: `"Top 10 most viewed videos
*#10: 4.2 million views*"`. One accent per caption.
- **Auto-contrast**: at render, shipreel looks at the footage under each `hook`/`cap`/`mid` caption. Busy background → a dark plate behind the text; tinted text or accent that matches the background → white or a colour that doesn't. The render result lists what it changed in `contrast_fixed`. Turn it off per video with `auto_contrast: false`.
- Emoji are stripped from burned text. Keep emoji for descriptions.
- TikTok safe zone: the styles already keep clear of the top 13%, the bottom 25 to 30% and the right 15%. Custom `x,y`: keep y in 0.12 to 0.70 and x ≤ 0.80.

## Overlay

All have `t`, `d`.

| type | keys | |
|---|---|---|
| pointers | `target` (a name from record-web) or `box` [x,y,w,h] / `at` [x,y] in the **source** frame, plus `what` | **the way to point at something** (`highlighting.md`): the render maps it through the crop/track/zoom and drops it if it can't land exactly |
| `box` `marker` `bar` `focus` | box/target; color, thick | rounded outline / highlighter / clean underline / dim-everything-else window |
| `arrow`, `arrow-curved` | box/target/at, or x, y (where the tip points), angle (deg, 0 = pointing right, 90 = down), color red/yellow/white/green, w, anim bob | |
| `ring` / `scribble` | box/target/at, or x, y, r (radius as a fraction of width), color | circle a thing |
| `underline` | box/target/at, or x, y, w, color | hand-drawn |
| `x` / `check` | x, y, w | wrong / right |
| a pointer with only `x,y(,w,h)` | | output-frame coordinates; `check` fails it unless `"verified": true` |
| `censor` | x, y, w, h | blur a region (secrets, emails) |
| `spotlight` | box/target/at, or x, y, r | dims everything but a circle |
| `fx` | fx: bw/dim/sat/invert/blur | effect on a time range across clips |
| `flash` | color, d | quick full-frame flash |
| `progress` | color, h, pos top/bottom | progress bar for the whole video |
| `sticker` | asset (meme/gif/png/mp4), x, y (center), w, angle, anim pop/slide/shake/bob/none, key (chroma: green/black/...) | memes, reaction gifs |

## Audio

- `sfx`: `{"asset": "sfx:vine-boom", "t": 4.4, "vol": 0.7}`, plus `start`/`dur` to trim. Start an SFX 0.05 to 0.1 s **before** the visual beat.
- `music`: `{"asset": "music:sneaky-snitch", "vol": 0.14, "duck": true}` (find tracks with `assets.py find --type music`; pro: `--pro`). Product audio and SFX drive the ducking. It loops and fades by itself.
- Levels: every sound is levelled to a reference before `vol` applies (so `vol` means the same for every sound), SFX are cut at 4 s unless `dur` is set, and the overall level is set from the measured mix. Details: `music-audio.md` section 5.
- `product_music`: `"mute"` (default) or `"keep"`. With `music` set, `rec:` clips whose audio looks like music are muted automatically (`product_music_muted` in the render result) so two musics never play. `"keep"` leaves them alone.
