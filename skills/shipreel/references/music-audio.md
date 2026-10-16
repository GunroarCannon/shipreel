# Music and audio

## 1. Know the product's own audio first

`clip.py probe <recording>` → `audio.music_likely`, `silent_pct`, `mean_db`. Combine that with the shorthand's `product_audio`, `music_where` and `music_ok_to_keep`.

| product audio | TikTok | YouTube |
|---|---|---|
| Original game music (made or licensed by the user) | keep it; it's the best soundtrack and it's yours | keep it; no added music |
| Game SFX only | keep SFX; add meme SFX on beats; music via `sound_note` | keep SFX; optional quiet library music, ducked |
| Silent (web apps, tools) | meme SFX + UI clicks (`mouse-click`, `pop`); music via `sound_note` | library music, ducked, or a quiet `keyboard-typing` bed |
| Licensed or unknown third-party music in the product | mute it (`"audio": "mute"`) or ask | mute it: Content ID risk |

Mixing two musics is always wrong. If the product has music in that clip, don't add a track (`music` stays null) and don't put a music `sound_note`.

## 2. TikTok: sounds are added in-app

`config.music.tiktok = "in-app"` (default). Trending sounds only count for reach when added through TikTok's sound picker, and burned-in commercial music gets muted. So:
- Render with product audio + SFX only.
- Put the advice in `sound_note`: "add a trending lo-fi or phonk sound at 10 to 15% volume; keep the original sound up". It goes into the `.txt`, clearly marked as not part of the caption.
- The textless version has the same audio, so the user can re-cut it in CapCut and the like.

## 3. YouTube: no copyrighted music

Use product music, tracks the user puts in `assets/music/` (YouTube Audio Library, or their own music, with license notes in that README) or nothing. Never download popular songs. Meme SFX clips from myinstants are short sound effects; keep each one under about 3 s and use them as effects, not as a soundtrack.

## 4. SFX

- Find: `assets.py find --type sfx --mood shocked` or `--theme fail` (`assets.py vocab --type sfx` lists moods: happy, shocked, panic, sad, hype, laughing, awkward...; themes: reveal, fail, success, bug, plot-twist, time-skip...). Missing → `sfx.py search "<name>"` → `sfx.py get`.
- Timing: start 0.05 to 0.1 s before the visual beat. Volume 0.5 to 0.8 (meme SFX are loud; vine-boom ≈ 0.6).
- Density: TikTok ≤ 1 SFX per 2.5 s, 2 to 5 per video; YouTube more spread out. Not every cut needs a sound. Silence before a punchline is a sound too.
- Pairing: arrow/ring → `ding`/`pop`; reveal → `vine-boom`/`dun-dun-dunnn`; fail → `sad-trombone`/`bruh`/`windows-xp-error`/`metal-pipe`; time skip → `2000-years-later`/`whoosh`; win → `tada`/`minecraft-level-up`/`hallelujah`; awkward → `crickets`; rewind → `record-scratch`.
- Don't use the same signature SFX in more than 3 of 10 videos in a batch.

## 5. Mix

The render does it: product audio × `product_volume` (+ per-clip `audio` gain) + SFX + music (ducked by product audio via sidechain) → loudnorm -14 LUFS, true peak -1.5 dB. That's the TikTok and YouTube target. Short clip edges get 30 to 40 ms fades, so cuts don't click.

The myinstants MCP (`.mcp.json`) can *play* a sound through the speakers. That's for the user ("preview vine boom"), not for renders. It costs nothing to skip.
