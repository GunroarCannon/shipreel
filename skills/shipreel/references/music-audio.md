# Music and audio

## 00. Ask the user about music (once per batch)

Music is a taste and risk call, so the director **asks** before the writer starts, not the model alone. `config.music.ask`: `"each-batch"` (default: ask at the start of every project's batch), `"once"` (ask the first time, reuse the answer), `"never"` (use the defaults: bed on ~40%, YouTube-safe only). Skip the question when `music.meme_bed` is `"off"`. Buzz first, then one AskUserQuestion call with up to 3 questions. Fill the **recommendation and the reasons from this project**: the shorthand's `product_audio`, how many of the planned videos are jokes/fails/reveals, and whether the project has its own music. Don't ask the bare question without a recommendation.

**Q1: Music on the TikToks** (header "Music"). Option text must carry the tradeoff:

| option | what you get | tradeoff |
|---|---|---|
| `Meme bed on the ones it fits (Recommended)` | about 40% of the batch (jokes, fails, reveals, montages) get a quiet meme track picked per beat; the rest stay SFX + product sound | adds personality and holds muted viewers; burned-in copyrighted music can get muted by TikTok, and you can't swap it later without a re-render |
| `Meme bed on every TikTok` | consistent sound across the batch | repeats fast, more videos at risk of mute/claims, drowns the project's own audio (it's muted under the bed) |
| `No bed: SFX only, I'll add a trending sound in-app` | best chance at TikTok's trending-sound reach, no copyright risk | silent-ish if you forget to add one; the textless re-cut has no music either |
| `Keep the project's own music, no bed` (only if the project has music) | your own soundtrack, safe on every platform | menu loops and quiet tracks can be weak; no joke timing from music |

**Q2: Where the tracks come from** (ask only when Q1 is a bed). Say what's available and the catch:
- `Meme loops (myinstants: sneaky snitch, crab rave, careless whisper...)`: short, instantly recognisable; copyrighted, TikTok only.
- `Your meme-music folder (81 tracks: Nintendo/Wii, Kevin MacLeod, comedy, lofi)`: longer, more variety; mostly copyrighted game/media music, TikTok only. The ones marked `yt:credit` (Kevin MacLeod, Scott Buckley) are fine anywhere with a credit line.
- `YouTube-safe only (--yt-safe)`: cleared tracks, credit in the description; less meme-y.

**Q3: The project's own music** (ask only if the scout or `probe` found music and the user hasn't said): `mute it under the bed (Recommended)` / `keep it, add no bed` / `mute it, no bed`. Render mutes by default when a bed is set.

What works best (put this in the question or the recommendation): quiet (0.10 to 0.18) so captions and SFX stay loudest; match the track to the beat (sneaky for bugs, careless-whisper for fails, crab-rave for flexes, calm Wii/lofi for devlogs); one bed per video; start the track at its best bar with `start`; no more than 3 of 10 with the same track; stay off scenes where the product's own audio is the point.

After the answer: `clip.py state note "music: <choice>, source <x>, project music <mute|keep>"` and pass `music_policy: {share, source, project_music}` in the writer's slate. Don't re-ask for the same batch.

## 0. Decide music for every video (don't skip this)

Every plan answers one question per video: **what is the music?** Write it in the plan (`music` set, or `"music": null` with a reason in the video's note). Leaving it blank by default is the failure this section exists to prevent.

- **TikTok**: follow the user's answer to the music question above (`music_policy`). With no answer, a meme-music bed on about `mix.music_share_short` (40%) of videos, more for jokes, fails, reveals and montages. See "Meme music bed" below.
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

Library: `python S/scripts/assets.py find --type music [--mood sus] [--theme bug] [--yt-safe] [--q myinstants|meme-music]` (`assets.py vocab --type music` lists moods and themes; each row shows `yt:ok|credit|risky`). Two sources: the myinstants loops below, and the user's `assets/music/meme-music/` folder (81 longer tracks, indexed in the local-only `assets/index.local.json`; add more folders with `assets.py index-dir <folder> --local`). Tracks marked `yt:credit` need a credit line in the description (see their `license`). The starter set is meme-music loops from myinstants: sneaky-snitch, crab-rave, careless-whisper, megalovania, wii-shop-channel, mii-channel, rickroll, running-in-the-90s, gas-gas-gas, benny-hill, elevator-music, mission-impossible, pink-panther, phonk-yara, cool-chill-lofi, minecraft-theme, curb-your-enthusiasm, hampster-dance, nyan-cat.

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

## 2b. Pro mode: original and cleared sounds only

Pro videos (`pro-mode.md`) skip the meme toolbox. SFX: `assets.py find --type sfx --pro` (soft whooshes, ticks, a riser, a soft impact, UI clicks, a shimmer: generated originals from `scripts/synth_sfx.py`, plus the clean library sounds). Beds: `assets.py find --type music --pro`: `ambient-pad` and `soft-pulse` (originals, safe everywhere), library tracks marked `yt:ok`/`yt:credit`, or the brand's own track. `check` fails meme sounds and meme music in pro videos. Still ask the music question, with pro options: `calm original bed (Recommended)` / `your own licensed track (path)` / `no bed, SFX only`.

## 3. YouTube: no copyrighted music

Use product music, tracks the user puts in `assets/music/` (YouTube Audio Library, or their own music, with license notes in that README) or nothing. Never download popular songs for YouTube. Meme SFX clips from myinstants are short sound effects; keep each one under about 3 s and use them as effects, not as a soundtrack.

## 4. SFX

- Find: `assets.py find --type sfx --mood shocked` or `--theme fail` (`assets.py vocab --type sfx` lists moods: happy, shocked, panic, sad, hype, laughing, awkward...; themes: reveal, fail, success, bug, plot-twist, time-skip...). Missing → `sfx.py search "<name>"` → `sfx.py get`.
- Timing: start 0.05 to 0.1 s before the visual beat. Silence before a punchline or outcome is a sound too.
- **Levels**: the render levels every sound first (the library ranges from -27 to +1 LUFS, so raw files can't be mixed by ear), then applies `vol`. So `vol` means the same for every sound: **0.5 to 0.8 creator, 0.35 to 0.6 pro**. Don't compensate for a quiet-sounding file by raising `vol`; pick a different sound.
- **Length**: a sound is cut at 4 s with a short fade. Set `dur` to end it where you want (`tada` is 19 s, `oh-no-no-no` 11 s: use `"dur": 1.5`). A sound that rings into the next beat reads as a mistake.
- Density: TikTok ≤ 1 SFX per 2.5 s, 2 to 5 per video; YouTube more spread out. Pro: 2 to 4 per video. Not every cut needs a sound.
- **No phantom transition sounds**: never play `whoosh`, `swoosh`, `whip`, or `swipe` unless an actual transition or fast camera move happens at that exact timestamp. Whooshes over static clips or gentle dissolves sound broken.
- Pairing: highlight appears → `ding`/`pop` (pro: `ui-click`/`pop-soft`); reveal → `vine-boom`/`dun-dun-dunnn` (pro: `impact-soft`); fail → `sad-trombone`/`bruh`/`windows-xp-error`/`metal-pipe`; time skip → `2000-years-later`/`whoosh`; win → `tada`/`minecraft-level-up`/`hallelujah` (pro: `shimmer`); awkward → `crickets`; rewind → `record-scratch`.
- Don't use the same signature SFX in more than 3 of 10 videos in a batch.

## 4b. Sound design: give every sound a job

A good mix has few sounds, each with a reason a viewer could name. Plan them like captions: list the beats, then decide which beats get a sound.

| role | when | creator | pro |
|---|---|---|---|
| **Open** | the first frame / hook lands | `pop`, `vine-boom` | `impact-soft` (once, under the title) |
| **Point** | a highlight appears | `ding`, `pop` | `ui-click`, `pop-soft` |
| **Turn** | a transition or camera move (and only then) | `whoosh`, `swoosh-fast`, `camera-shutter` | `whoosh-soft`, `swoosh-fast` on a push or zoom |
| **Result** | the thing worked / failed | `tada`, `ding`, `sad-trombone` | `shimmer` |
| **Typing/UI** | the screen shows typing or a click | `keyboard-typing` (quiet; `dur` = the typing), `mouse-click` | `ui-click`, `tick` |
| **Bed** | the whole video | meme track, or the project's own music | `ambient-pad` or `soft-pulse`, or none |

Rules that keep it clean:
1. **One layer at a time.** A sound at a beat means no other sound within 0.3 s (`check` flags pile-ups). A bed plus a few SFX is the whole mix.
2. **The bed is a bed.** `vol` 0.10 to 0.18, `duck: true` (the default). It dips under SFX and product audio, then returns. No bed where the product's own audio is the point, or where a punchline needs silence.
3. **A pro video is mostly quiet.** No bed beats a loud one; if there is one, a viewer should only notice it when it stops.
4. **Silence is a tool.** Leave a 0.3 s gap before the payoff.
5. **Never fix a sound by adding another.** If a beat feels flat, change the sound or the timing, not the count.
6. **Don't sound-track what isn't happening.** No `whoosh` on a static clip, no `ding` with nothing on screen, no keyboard sound over a clip with no typing.

## 5. Mix

What the render does (you don't set any of this):

1. **Levels every library sound** to a reference (SFX -18 LUFS, music -16 LUFS, peaks capped at -3 dBFS), then applies your `vol`. Raw file loudness no longer matters.
2. **Shapes each SFX**: 4 ms fade-in, a fade-out, cut at 4 s unless `dur` says otherwise.
3. **Ducks the music** from the product audio and the SFX together with a gentle compressor (3:1, slow release), so the bed breathes instead of pumping.
4. **Limits the sum**, then sets the overall level from the measured mix: towards -14 LUFS, but never past -2 dB true peak. A quiet bed with a few SFX stays quiet and natural instead of being cranked into distortion. The result reports it as `audio: {mix_lufs, gain_db, peak_db}`.
5. Clip edges get 30 to 40 ms fades, so cuts don't click.

If `audio.gain_db` is above about 10, the mix is very quiet (no product audio, a low bed, few sounds): fine for pro, but check the bed is audible. If a sound is too quiet or loud **relative to the others**, change its `vol` by 0.1 to 0.2 at a time.

The myinstants MCP (`.mcp.json`) can *play* a sound through the speakers for the user ("preview vine boom"). It's not used in renders.
