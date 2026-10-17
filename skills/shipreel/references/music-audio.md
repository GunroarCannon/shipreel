# Music and audio

## 0. Decide music for every video (don't skip this)

Every plan answers one question per video: **what is the music?** Write it in the plan (`music` set, or `"music": null` with a reason in the video's note). Leaving it blank by default is the failure this section exists to prevent.

- **TikTok**: use a meme-music bed on about `mix.music_share_short` (40%) of videos, more when the video is a joke, a fail, a reveal or a montage. See "Meme music bed" below.
- **YouTube**: product music or library tracks only (section 3).
- **Skip music** only when the product's own music is the point, a punchline needs silence, or `music.meme_bed` is `"off"`. Say which in the notes.

## 1. Know the product's own audio first

`clip.py probe <recording>` → `audio.music_likely`, `silent_pct`, `mean_db`. Combine that with the shorthand's `product_audio`, `music_where` and `music_ok_to_keep`.

| product audio | TikTok | YouTube |
|---|---|---|
| Original game music (made or licensed by the user) | keep it **or** mute it and put a meme bed under it, never both. Keep it when it's good and fits; mute it when it's a menu loop, quiet, or clashes with the joke | keep it; no added music |
| Game SFX only | keep SFX; add meme SFX on beats and a meme music bed | keep SFX; optional quiet library music, ducked |
| Silent (web apps, tools) | meme SFX + UI clicks + a meme music bed | library music, ducked, or a quiet `keyboard-typing` bed |
| Licensed or unknown third-party music in the product | mute it (`"audio": "mute"`) | mute it: Content ID risk |

**Mixing two musics is always wrong.** If a video has a `music` bed, the project's own music must go:
- **Automatic**: at render, any `rec:` clip whose audio looks like music (`probe` `music_likely`) is muted when the video has `music`. The render result lists `product_music_muted: ["clips[0]"]`, and `check` prints a `music:` note beforehand. Add `"product_music": "keep"` to the video to opt out (then drop `music`).
- **Per clip**: `"audio": "mute"` on a clip, or `"audio": 0.3` to lower it. `"product_volume": 0` mutes all product audio for the video (this also removes the game's SFX, so prefer per-clip muting if the game SFX is the fun part).
- **At record time** (if the project has a music toggle): use an env toggle, a settings-menu click in `--steps`, or an autoplay `set` that mutes the music bus (`AudioServer.set_bus_mute`). Never edit the project to do it (SKILL.md hard rules). If you can't turn it off, render-time muting is enough.
- If a project has music and the user hasn't said whether to keep it, that's an **ask** (`failure-protocol.md`).

## 2. TikTok: meme bed in the video, trending sound in-app

Two tools, use both:
1. **Burned-in meme bed** (`config.music.meme_bed`, default `"tiktok"`): a quiet looped track from the library under the video. It also survives into the textless re-cut.
2. **Trending sound in the app** (`config.music.tiktok = "in-app"`): trending sounds only count for reach when added through TikTok's sound picker, and burned-in commercial music can get muted. Put the advice in `sound_note`: "add a trending lo-fi or phonk sound at 10 to 15% volume; keep the original sound up". It goes into the `.txt`, clearly marked as not part of the caption.

If the plan's `music` is a meme track, also say so in `sound_note` ("burned-in: sneaky snitch; swap for a trending sound in-app if it gets muted") so the user knows what to expect.

### Meme music bed

Library: `python S/scripts/assets.py find --type music [--mood sus] [--theme bug]` (`assets.py vocab` lists moods and themes). The starter set is meme-music loops from myinstants: sneaky-snitch, crab-rave, careless-whisper, megalovania, wii-shop-channel, mii-channel, rickroll, running-in-the-90s, gas-gas-gas, benny-hill, elevator-music, mission-impossible, pink-panther, phonk-yara, cool-chill-lofi, minecraft-theme, curb-your-enthusiasm, hampster-dance, nyan-cat.

**Pick by the beat, not at random**:

| the video is... | try |
|---|---|
| a sneaky bug / weird behaviour | `sneaky-snitch`, `pink-panther`, `mission-impossible` |
| a fail / a crash / a facepalm | `careless-whisper`, `curb-your-enthusiasm`, `benny-hill` |
| a flex / a showcase / a speedrun | `crab-rave`, `gas-gas-gas`, `phonk-yara`, `running-in-the-90s`, `megalovania` |
| a calm devlog / building / late night | `wii-shop-channel`, `mii-channel`, `cool-chill-lofi`, `elevator-music` |
| nostalgia / old build / sandbox | `minecraft-theme`, `mii-channel` |
| a joke ending / troll | `rickroll`, `hampster-dance`, `nyan-cat` |

Use it:
- Plan: `"music": {"asset": "music:sneaky-snitch", "vol": 0.14, "duck": true}`. Keep it quiet (0.10 to 0.18): captions and SFX must still be the loudest things. `start` skips into the track. It loops and fades out on its own.
- Don't repeat the same track in more than 3 of 10 videos in a batch.
- One music per video. Meme SFX still go on beats on top (`vine-boom` over `sneaky-snitch` is the point).
- **Need a track that isn't in the library**: `python S/scripts/sfx.py search "<name>"`, then `python S/scripts/sfx.py get "<name>" --pick N --kind music --name <slug> --moods <m> --themes <t>`. Without `--kind music` it is filed as an SFX. The myinstants MCP (`.mcp.json`) can *preview* a sound through the speakers for the user, but it can't add files; use `sfx.py` for that. `sfx.py seed-music` re-downloads the starter set.
- **Copyright**: these are copyrighted songs and themes, not royalty-free. As a quiet bed on TikTok they are common, and the in-app picker is the safer route for reach. On YouTube they risk Content ID claims, which is why `meme_bed` defaults to `"tiktok"`. Don't use them on YouTube unless the user set `meme_bed` to `"all"`.

## 3. YouTube: no copyrighted music

Use product music, tracks the user puts in `assets/music/` (YouTube Audio Library, or their own music, with license notes in that README) or nothing. Never download popular songs for YouTube. Meme SFX clips from myinstants are short sound effects; keep each one under about 3 s and use them as effects, not as a soundtrack.

## 4. SFX

- Find: `assets.py find --type sfx --mood shocked` or `--theme fail` (`assets.py vocab --type sfx` lists moods: happy, shocked, panic, sad, hype, laughing, awkward...; themes: reveal, fail, success, bug, plot-twist, time-skip...). Missing → `sfx.py search "<name>"` → `sfx.py get`.
- Timing: start 0.05 to 0.1 s before the visual beat. Volume 0.5 to 0.8 (meme SFX are loud; vine-boom ≈ 0.6).
- Density: TikTok ≤ 1 SFX per 2.5 s, 2 to 5 per video; YouTube more spread out. Not every cut needs a sound. Silence before a punchline is a sound too.
- Pairing: arrow/ring → `ding`/`pop`; reveal → `vine-boom`/`dun-dun-dunnn`; fail → `sad-trombone`/`bruh`/`windows-xp-error`/`metal-pipe`; time skip → `2000-years-later`/`whoosh`; win → `tada`/`minecraft-level-up`/`hallelujah`; awkward → `crickets`; rewind → `record-scratch`.
- Don't use the same signature SFX in more than 3 of 10 videos in a batch.

## 5. Mix

The render does it: product audio × `product_volume` (+ per-clip `audio` gain) + SFX + music (ducked by product audio via sidechain) → loudnorm -14 LUFS, true peak -1.5 dB. That's the TikTok and YouTube target. Short clip edges get 30 to 40 ms fades, so cuts don't click.

The myinstants MCP (`.mcp.json`) can *play* a sound through the speakers. That's for the user ("preview vine boom"), not for renders. It costs nothing to skip.
