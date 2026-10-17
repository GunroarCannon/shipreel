# Plan JSON

One file = one batch (≤5 videos). `{"project": "...", "pass": 1, "videos": [ ... ]}`. A single video object at the top level works too. Copy from `templates/plan.example.json`. Times are seconds; positions are fractions of the frame (0 to 1, from the top-left).

## Video

| key | type | notes |
|---|---|---|
| `id` | str | unique within the project: `t01`, `y01` (pass 2: `p2t01`) |
| `format` | `tiktok` \| `youtube` \| `short` \| `square` | tiktok/short 1080×1920, youtube 1920×1080 |
| `title` | str | human title, it becomes the file name. See copy-rules |
| `tags` | [str] | 3 to 5 niche hashtags without `#`. Also go in the file name |
| `series` | {name, part} | optional → `name-part-N_title_#tags` |
| `style` | caption preset | `pop` (default, TikTok Classic look) `label` (white box) `punch` `hormozi` `clean` `meme` `comic` `dev` `marker` `bold` `cinema` `cartoon`. Rotate them |
| `hook_type` | str | for the ledger: `contrarian`, `before-after`, `number`, `question`, `pov`, `fail`, `flex`, `tutorial`, `clickbait`... |
| `header` | str or {text, t, until} | persistent white-box text at the top (TikTok's "persistent caption") |
| `clips` | [clip] | in order. Total length = the sum |
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

## Clip

```json
{"src": "rec:combat-boss", "in": 3.2, "out": 8.0, "fit": "cover", "focus": [0.5, 0.4], "speed": 1.0,
 "fx": ["zoomin:1.25@0.6,0.4", "freeze:0.8", "bw"], "audio": "keep", "caption": "the boss has 3 phases"}
```

- `src`: `rec:<id>` (this project), `rec:<project>/<id>` (another project), `meme:<name>`, `gif:<name>`, a path, or an image.
- `in`/`out`: trim of the source. Images and `still` use `dur`.
- `still: true`: freeze the frame at `in` for `dur`.
- `card: "text"` + `dur` + `bg`: a full-screen text card on a color. Use sparingly (≤1 per TikTok).
- `fit`: `cover` (crop to fill, default for video), `contain` (letterbox), `blurpad` (blurred fill behind, default for images), `crop:x,y,w,h` (choose a region, then cover).
- `focus`: [x, y] for `cover` and zooms: where the crop window sits. Different clips of the same recording can use different `focus` values (a cut to the enemies, a cut to the health bar).
- `track`: a **moving camera** over the source frame: `[{"t":0,"x":0.2,"y":0.6}, {"t":3,"x":0.8,"y":0.3,"move":0.8}, {"t":6,"x":0.9,"y":0.1}]`. The first key is where the camera starts; each later key says "at `t` seconds (as the clip plays) glide to this point over `move` seconds (default 0.6), then hold". x,y = the point to centre on, as fractions of the **source** frame (get them from `clip.py sheet <rec> --grid`). Needs a source bigger than the window (a landscape recording in a portrait video); it replaces `fit`. `zoom` (≥1, default 1) tightens the window for the whole clip.
- `speed`: 0.25 to 4 (audio pitch kept).
- `audio`: `keep` | `mute` | a number (gain).
- `fx`: see effects-cookbook. Syntax `name[:arg][@x,y]`.
- `caption`: str or {text, t, d, style...}, with times relative to this clip. Good for "this clip says this".

## Caption

```json
{"t": 0, "d": 2.2, "text": "it took 3 rewrites", "style": "hook", "words": true, "per": 2}
```

- `style`: `box` (black text on a white box, readable on anything), `plate` (white text on a dark plate), `hook` (big, top third), `cap` (default, lower-middle above the UI), `mid` (center), `callout` (yellow, center or `x,y`), `card`, `code` (mono box), `lower` (lower third, YouTube), `title` (big center), `meme-top`, `meme-bottom` (classic impact).
- Animation: default `pop` for hook/cap/mid/callout, `fade` for others; `"anim": "none"`.
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
| `arrow`, `arrow-curved` | x, y (where the tip points), angle (deg, 0 = pointing right, 90 = down), color red/yellow/white/green, w, anim bob | |
| `ring` / `scribble` | x, y, r (radius as a fraction of width), color | circle a thing |
| `underline` | x, y, w, color | |
| `x` / `check` | x, y, w | wrong / right |
| `box` | x, y, w, h, color, thick | outline rect (top-left based) |
| `censor` | x, y, w, h | blur a region (secrets, emails) |
| `spotlight` | x, y, r | dims everything but a circle |
| `fx` | fx: bw/dim/sat/invert/blur | effect on a time range across clips |
| `flash` | color, d | quick full-frame flash |
| `progress` | color, h, pos top/bottom | progress bar for the whole video |
| `sticker` | asset (meme/gif/png/mp4), x, y (center), w, angle, anim pop/slide/shake/bob/none, key (chroma: green/black/...) | memes, reaction gifs |

## Audio

- `sfx`: `{"asset": "sfx:vine-boom", "t": 4.4, "vol": 0.7}`, plus `start`/`dur` to trim. Start an SFX 0.05 to 0.1 s **before** the visual beat.
- `music`: `{"asset": "music:sneaky-snitch", "vol": 0.14, "duck": true}` (find tracks with `assets.py find --type music`). Product audio drives ducking. The final mix is loudnormed to -14 LUFS. It loops and fades by itself.
- `product_music`: `"mute"` (default) or `"keep"`. With `music` set, `rec:` clips whose audio looks like music are muted automatically (`product_music_muted` in the render result) so two musics never play. `"keep"` leaves them alone.
