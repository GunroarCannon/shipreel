# shipreel

**Turn your side projects into a faceless dev channel.** An agent skill for Claude Code (and other skill-compatible agents) that records select parts of your software and game projects, then edits them into captioned TikToks/Shorts and YouTube devlogs. It adds memes, SFX, arrows, freeze frames, trending caption fonts and human-sounding titles, descriptions and hashtags.

- **Records without touching your project**: web apps through headless Chrome (scripted clicks, typing, scrolling, a visible cursor), Godot games through Movie Maker with scripted input, anything else via screen capture, and old versions through temporary git worktrees.
- **Three modes**: **creator** for a dev channel (memes, meme SFX, chunky game captions, jokes), **pro** for product demos, launches and client work (clean Inter/Manrope/serif type, soft original sounds, sentence case, no memes), and **slide** for viral photo slideshows & swipe carousels (target callout hooks on slide 1, consistent feed theme/character, value slides, app CTA on the final slide, trending audio, and dual video + native PNG exports; `references/slide-mode.md`).
- **Frames by aspect ratio**: `fit: auto` fills the frame for each source shape (phone → TikTok fills it, a landscape game in a portrait video is cropped *onto the action* by motion-based auto focus, `track: "auto"` follows it like a camera operator, a phone recording in a YouTube video floats as a rounded card over a blur). Plus `stack` (whole shot + close-up) and `float` layouts.
- **Paces by length**: short videos cut fast, long ones breathe. Shot lengths, caption reading time, transition length and "something new every N seconds" come from the video's length, and `check` flags anything off-pace.
- **Edits with ffmpeg**: 25 caption presets on 25 fonts (TikTok Sans, Inter, Fredoka, Lilita One, Press Start 2P, Instrument Serif, Bricolage Grotesque…), word-pop, karaoke and typewriter captions, whip pans with motion blur, zoom, flash, iris, dip and push transitions, colour grades, zooms, freeze frames, b&w, shake, glitch and VHS, arrows, rings, scribbles, spotlights, censor blur, meme stickers, a progress bar, SFX, ducked music and loudness at -14 LUFS.
- **Small-model friendly**: `clip.py moments` finds the best moving spans of a recording, `clip.py scaffold` turns them into a timed plan (clips, transitions, caption slots, sounds) so a cheap model only writes the words, and `references/simple-rules.md` turns every judgment call into a number or an if-then rule.
- **Writes copy that doesn't sound like AI**: hook archetypes, a title/description/hashtag lint (AI tells, engagement bait, filler tags), and a set clickbait share that never lies.
- **Saves tokens**: a director/scout/writer/editor/reviewer split routes grunt work to Haiku and copy to Sonnet/Opus. Scripts print one-line JSON, and contact sheets replace frame-by-frame viewing.
- **Runs unattended**: one questionnaire up front, resumable state, cached recordings and segments. When it needs you, `buzzer.exe` flashes a red border around your screen with a sound, and you pick skip / fix / fake it / paste an env var.

Default run: **10 TikToks per project**, project after project. Then each later pass makes **2 YouTube videos (1 to 5 min) + 2 TikToks** per project.

## Install

### As a Claude Code plugin (recommended: includes the myinstants MCP)
```
/plugin marketplace add GunroarCannon/shipreel
/plugin install shipreel@shipreel
```

### As a plain skill
```
git clone https://github.com/GunroarCannon/shipreel
# then copy or link skills/shipreel into ~/.claude/skills/ (or your project's .claude/skills/)
```
or `npx skills add GunroarCannon/shipreel`.

### Requirements
- **ffmpeg** with libass + libx264 (`winget install Gyan.FFmpeg` / `brew install ffmpeg` / `apt install ffmpeg`)
- **Python 3.9+** (stdlib only; Pillow is used when present for rounded caption boxes, `float` cards and font checks; numpy only to regenerate the bundled original sounds)
- **Node 22+** + Chrome/Edge/Brave, for web recording (no npm install; it uses CDP over Node's built-in WebSocket)
- **Godot 4.x**, for Godot projects (set `GODOT_BIN` or let it search)
- Windows: the buzzer builds itself with the C# compiler that ships with Windows. macOS/Linux use notifications + a sound.

Check with `python skills/shipreel/scripts/clip.py doctor`.

### Bundled companions
The writer uses these for extra depth, and they ship in `skills/`, so one install gets everything:
- **viral-hooks, viral-captions-and-ctas, viral-tiktok-content, viral-youtube-shorts, viral-short-form-ideas**: from [vyralcontent/content-skills](https://github.com/vyralcontent/content-skills) (MIT, Copyright (c) 2026 Vyral). See `skills/viral-*/LICENSE`.
- **humanizer**: a merge of two AI-writing editors, the Wikipedia "Signs of AI writing" humanizer (v2.1.1) and The Humanizer by Crazy Marketer (v2.4), with the second one's self-editing step removed. Both were supplied by the repo owner; check their upstream licences before redistributing. shipreel's writer and reviewer run it on every caption, title and description.
- **tiktok-marketing**: from [sergebulaev/tiktok-skills](https://github.com/sergebulaev/tiktok-skills) (MIT, Copyright (c) 2026 Sergey Bulaev). See `skills/tiktok-marketing/LICENSE`.

## Use
In Claude Code, from the folder where you want `output/` and `temp/` (or set `SHIPREEL_HOME`):
```
make tiktoks of my projects in D:/dev/voidrunner and D:/dev/snaplist
```
It asks its questions once (model plan, projects, accounts, links, permissions), then works through the queue. Say "continue shipreel" in a new session and it resumes from `output/_state.json`.

## Output
```
output/<project>/
  the_bug_was_a_feature_the_whole_time_#gamedev_#godot_#indiedev.mp4   captioned
  the_bug_was_a_feature_the_whole_time_#gamedev_#godot_#indiedev.txt   description: links, mentions, tags
  textless/the_bug_was_a_feature_the_whole_time_#gamedev_#godot_#indiedev.mp4
  videos.csv                                                            ledger
```
Name = title + hashtags, underscores between words, dashes only for markers like `devlog-part-2_...`. No description → an empty file with the same name and no extension.

## Per-project shorthand
Each project gets a `.project-shorthand.txt` (features and how to reach them, development eras, true story angles, toggles, what never to show). The cheap scout model writes it once, and every later run reads it instead of the repo. Edit it to steer the videos. See `skills/shipreel/templates/project-shorthand.txt`.

## Assets
- `assets/memes/`: 199 reaction, rage-comic and wojak images, renamed by content and indexed by mood, theme and text (`scripts/assets.py find --mood smug`). Third-party meme images, used as short reaction inserts; their copyright stays with the original owners. Remove anything you're not comfortable publishing.
- `assets/sfx/`: 38 meme sounds from myinstants.com (`scripts/sfx.py get "<name>"` adds more) and 8 soft original sounds for pro mode, generated by `scripts/synth_sfx.py` (MIT).
- `assets/music/`: 19 meme-music loops (TikTok only) and 2 original beds (`ambient-pad`, `soft-pulse`) that are safe everywhere.
- `assets/fonts/`: OFL/Apache fonts, see `assets/fonts/LICENSES.md`.
- `assets/overlays/`: arrows, rings, scribbles, X and check marks (original, MIT).
- Add your own: drop files in `assets/inbox/` → `assets.py scan` → `assets.py add`.

## Name ideas
`shipreel` (working name) · `devreel` · `clipsmith` · `commit-to-clip` · `faceless-devlog` · `buildreel` · `repo2reel`

## License
Code: MIT. Bundled third-party assets keep their own licenses (see above).
