---
name: shipreel
description: "Turn the user's software and game projects into faceless, voiceless short-form and long-form videos: records select parts of each project (web apps through headless Chrome, Godot games through Movie Maker, anything through screen capture, old versions through git worktrees), then edits them with ffmpeg into captioned TikToks/Shorts (10-30s portrait), YouTube videos (1-5 min landscape) and X.com (Twitter) devlog clips. Creator mode (memes, meme SFX, chunky game captions) or pro mode (clean type, soft original sounds, no memes) for product demos and client work; aspect-aware auto framing that aims at the action, pacing that follows length, 25 caption fonts, whip/zoom/flash/dissolve transitions, colour grades and human-sounding titles, write-ups and hashtags. Use when the user wants devlog/showcase content, TikToks, YouTube or X.com videos of their projects, a content batch for a dev channel, or asks to continue a shipreel run."
license: MIT
---

# shipreel

You are the **director**. You plan, delegate cheap work to cheaper models, and check results. Scripts do the heavy lifting and print one-line JSON, so read outputs for status, but **pictures only count when you've looked at a sheet**: a JSON `ok` never means the video shows the right thing.

`S` = this skill's folder. Run scripts as `python S/scripts/clip.py ...`. Outputs land in the **workspace** (`$SHIPREEL_HOME`, else the cwd): `output/<project>/` and `temp/<project>/`.

## Start of every session

1. `clip.py doctor`. Any `warn` → fix or tell the user (low disk: suggest `SHIPREEL_HOME` on another drive).
2. No `shipreel.config.json` in the workspace → run the **questionnaire** (`references/questionnaire.md`). It picks the model plan, projects, handles, permissions and how often to be asked. Ask the setup up front, but that doesn't mean "never ask again": mid-run questions are expected (see "Ask, don't guess").
3. `clip.py state show`. If a run is in progress, resume from it; don't redo work the ledger already has.

## The loop

```
state next → {project, pass, need:{tiktok:10}}            # pass 1: 10 TikToks per project, then next project
  brief    → read .project-shorthand.txt (scout fills it if it's the template or stale)
  music    → ask the user the music question once per batch (references/music-audio.md, section 00), with a recommendation and tradeoffs
  record   → rec list; record only what's missing (editor): look at the first state, drive it, then SHEET it
  look     → clip.py sheet temp/<p>/rec/<id>.mp4; write "saw: ..." per recording. No saw line, no recording
  write    → moments + scaffold per video, then the writer fills the words: plan JSON for ≤5 videos (from the sheets, not the README)
  check    → clip.py check plan.json → fix until OK
  render   → clip.py render plan.json
  review   → clip.py sheet <video> per video → fix → render --only id (reviewer)
  note     → clip.py state note "<project>: t01-t10 done, angle notes..."
repeat until state next says done
```

Pass 1 = 10 TikToks per project. Later passes = 2 YouTube + 2 TikToks per project (`config.quota`). Each pass covers every project before the next pass starts.

Details for every step, with the exact commands: `references/pipeline.md`.

## Model routing (save tokens, keep quality)

Delegate with the Agent tool and set `model` from `config.models`. Give each subagent its role file plus the few paths it needs, never this whole conversation.

| role | default | does | role prompt |
|---|---|---|---|
| director | session model | plans, decides, final check | this file |
| scout | haiku | reads the repo once, fills `.project-shorthand.txt` | `references/roles/scout.md` |
| editor | haiku | runs record/render/probe commands, fixes plan JSON errors | `references/roles/editor.md` |
| writer | sonnet | angles, hooks, titles, captions, descriptions, plan JSON | `references/roles/writer.md` |
| reviewer | sonnet | looks at contact sheets, flags bad edits and AI-sounding copy | `references/roles/reviewer.md` |

Plans, the reasons behind them, and when to skip subagents: `references/model-routing.md`. **Small models** (haiku, or any subagent unsure what to do): give them `references/simple-rules.md`. It turns every judgment call into a number or an if-then rule, and `clip.py scaffold` builds the timed skeleton so they only write words.

## Hard rules

- **Pick the mode first.** `creator` (default) for the dev channel: memes, meme sounds, chunky captions, jokes. `pro` for anything a company would post (product demos, launches, client work, LinkedIn): clean presets (`pro`, `minimal`, `editorial`, `tech`), soft original sounds, sentence case, no memes. `config.mode`, or `mode` on a plan or a video. `check` fails meme assets in pro videos. `references/pro-mode.md`.
- **Pace follows length.** ≤ 22 s = fast (shots 0.6 to 3.2 s, something new every 2.5 s, 2 to 6 word captions), ≤ 60 s = medium, longer = slow (shots up to 10 s, sections, dissolves). `pace: auto` picks it; captions without `d` stay up their reading time; transitions take the pace's length. `check` prints `pace:` lines (and fails `pace!:`). `references/pacing.md`.
- **Standalone videos.** Each one makes sense to a viewer who saw nothing else. Use series (`-part-N`) only when a story really needs it, and still stand alone.
- **Faceless and voiceless.** No webcam, no TTS voice. On-screen text carries the story. Avoid low-effort and reused-content flags: `references/channel-rules.md`.
- **Human copy.** Short, specific, lowercase-casual where it fits, no AI tells. Some clickbait (`config.mix.clickbait_share`), never a lie. `references/copy-rules.md`. Every plan gets a humanizer pass (the sibling `humanizer` skill, "Short-video text") from the writer before `check` and from the reviewer after render.
- **Look at every recording, every render.** Exit 0, `ok: true`, a valid mp4 and a passing `check` prove nothing about the picture. After each `record-*`, run `clip.py sheet` on it and open the jpg; after each render, sheet the final. Write one `saw:` line per recording (what the frames actually show). A `warn: STILL n%` or `!!STILL` in `rec list` means the footage froze: fix and re-record, never ship it. A `record-web` warn about capture fps, or `!!CHOPPY` in `rec list`, means the capture was choppy: re-record. `references/recording-gate.md` has the seven rules, the checklist and the symptom table: **read it before the first recording of a project.**
- **Software doesn't play itself.** A game or app sits on its first state (title, menu, tutorial, consent banner) until something clicks or presses. Never record without a driver (`--steps` / `--autoplay`) that clears the blockers and then does the feature. Look at the first state with a 3 s probe recording before writing the steps. README claims and URL params (`?solo=pro`) are unverified until you've seen them on screen.
- **Move the camera to what's named.** If a caption talks about enemies, health, a button or a number, the frame must show it: cut to a clip with a different `focus`, glide with `track`, `zoomin` on it, or re-record it into view. Read positions with `clip.py sheet <rec> --grid`.
- **Captions look native (creator) or designed (pro).** Match the preset to the footage (`clip.py fonts`, `references/caption-look.md`): `game`/`bubble` for games, `pixel` for pixel art, `candy` for cozy, `dev`/`tech` for tools; pro uses `pro`, `minimal`, `editorial` or `tech`. For dev and game content the creator default is `bubble`: big rounded bold type, thick dark outline, soft shadow, one blue accent via `*word*`, mid-frame, 3 to 7 words a line, written like a person talking ("could you be a homie and press a few buttons"). A small `chip` caption (translucent rounded box, dark lowercase text) tags dates or labels low in the frame. `pop` = TikTok Classic (semibold white, thin black outline, one yellow accent); `label` for busy footage. On web UI and text-heavy recordings, never place unplated captions over paragraphs, tables, or the diagram node being explained; use `plate`, `box`, or `lower` in clean margins. No persistent `header` unless a video needs one. Never colours that clash with the background; render auto-fixes the worst cases (`contrast_fixed`). `references/caption-look.md`.
- **Frame by aspect ratio, full-bleed, aimed.** Leave `fit` out: `auto` picks by source shape. Same shape (phone recording → TikTok, landscape → YouTube) fills the frame; a wide game in a portrait video fills it too, with the crop aimed at the motion (auto focus) and `track: "auto"` following the action; a portrait phone in a landscape video floats over a blur (`float` in pro, `blurpad` in creator); a wide web UI keeps its width (record it `--portrait` instead when you can). `fit: "stack"` shows the whole shot and a close-up at once. The render result's `framing` says what auto chose: check it on the sheet. A small landscape strip in bars is a fail for gameplay. Sharpness: crop from the biggest source. `references/framing.md`, `references/recording-gate.md` rule 6.
- **Then-vs-now needs real old footage.** When a video says "it used to look like this", "day 1 vs now" or "version 1 vs 3", record the old build: `clip.py history <p>` to pick eras where the look changed, `clip.py worktree <p> add <sha>` (or `--before YYYY-MM-DD`; Godot projects are imported for you), record the same scene with the same driver in each era (`--era`, `--commit`), and label each side with a date chip. A text card that says "2 weeks earlier" is not a comparison. Only if an old commit won't build: old screenshots from git history or the repo's media, and say so (`failure-protocol.md`). `references/pipeline.md`, "Old versions".
- **Use the whole toolbox.** A video that is a raw recording plus a caption is a failed video. **Ask the user about music** (once per batch, with a recommendation and the tradeoffs: `references/music-audio.md` section 00), then every TikTok gets a **music decision** (a meme-music bed from `assets.py find --type music` on about 40% of them, more for jokes, fails and reveals), 2 to 5 SFX on beats, at least one pointing overlay or fx (arrow, ring, zoom, freeze) and a meme where it fits. If the project has its own music, mute it under the bed (render does this automatically) or keep it and add none: never two musics. Highlights follow the next bullet. **No phantom transition sounds**: whooshes and swooshes belong only on actual whip/push transitions or camera moves—never in the middle of static clips or over gentle crossfades. Audio must accompany an on-screen visual event, never random sound clutter. `check` prints `bare:` and `music:` notes; fix them, don't ignore them. Transitions mark a turn, 1 or 2 per TikTok: creator `whip` (motion-blurred slide + whoosh), `flash`, `zoom`, `glitch`; pro `dissolve`, `dip`, `push`, `smooth`. The default is a hard cut. One `grade` per video sets the colour look. Pro mode swaps memes and meme sounds for soft originals (`assets.py find --pro`). `references/music-audio.md` section 0 and 2, `references/effects-cookbook.md`.
- **Highlight exactly or not at all.** A pointer off its target is worse than none. Never type output `x,y` by guess: anchor the highlight to the source (`target` from a `record-web` `{"target":..,"sel":..}` step, or a `box` read off `clip.py sheet <rec> --grid`) with a `what`, and the render maps it through the crop/track/zoom and drops it if it can't land. Pick the type for the target (box/focus for UI, marker/bar for text, arrow for small things, ring only for round game objects; pro: no rings) and vary them. After every render open the `proof` sheet (one frame per highlight): each must sit on its `what`; read `overlay_notes` for what was dropped. `references/highlighting.md`.
- **Sound has jobs, not filler.** Every sound ties to a visible beat (open, point, turn, result, a bed), one layer at a time, 2 to 5 per TikTok and 2 to 4 in pro; the render levels every sound, ducks the bed under SFX and sets the final level from the measured mix, so `vol` is relative (SFX 0.5 to 0.8 creator / 0.35 to 0.6 pro, bed 0.10 to 0.18) and long sounds need a `dur`. Read `audio` in the render result. `references/music-audio.md` sections 4b and 5.
- **Show what's talked about.** The video is voiceless, so every named thing in a caption (a feature, a bug, a number, a file, a screen) must be on screen while the caption plays. If the caption says "the boss has 3 phases", the clip shows the boss. Text with no matching footage gets cut or re-timed.
- **Comparisons look different.** When a video compares versions or projects (then vs now, project A vs project B, old build vs new), the two sides must look visibly different: separate clips with distinct framing, a `bw`/`sepia` or colour difference, and a label on each side (`header`, `box` or a `hook`-style caption). Two near-identical screens side by side don't count as a comparison.
- **Never edit the user's project.** Use env/CLI toggles, `--autoplay` scripts, URL params and git worktrees (`clip.py worktree`). Edits to the project only with `permissions.edit_project_files`, and keep them minimal and reversible.
- **Never show secrets.** Check the shorthand's `never show` list. Blur them with `censor` overlays when they're on screen.
- **Env values** the user pastes go into the env of one command only. Never into files, plans, logs, descriptions or summaries.
- **Disk and RAM.** One render at a time. `clip.py clean <p> --segments` after a project's batch is reviewed. Remove worktrees when done.

## Ask, don't guess

Asking is part of the job, not a failure. If you're unsure what the user wants, can't verify something, hit a blocker, or are about to fake, skip, substitute or assume, **ask** (buzz first). The trigger list and the ask levels are in `references/failure-protocol.md`: read them once per session. Writing "probably fine" or "I assume" about something that changes the output is the cue to ask instead. Subagents can't ask: they return a `NEEDS_USER:` line and you relay it. Default level is `config.ask.level` = `when_unsure`.

## When something fails or needs the user

Exit code 3 / `NEED_ENV X` / missing tool / a recording that won't work → **buzz, then ask**:
`python S/scripts/buzz.py "shipreel needs you: <short reason>"`, then AskUserQuestion with **skip / fix (effort estimate) / fake it / paste env var**. Keep working on other projects while waiting when you can. Full protocol: `references/failure-protocol.md`.

**Every question to the user gets a buzz first** (the user's machine also has a global Claude Code hook that buzzes on AskUserQuestion; `buzz.py` skips a second buzz within 6 s, so calling it is always safe), including the questionnaire and mid-run questions: `python S/scripts/buzz.py "shipreel: <8 words, what you need>" -t 2`, then AskUserQuestion. One buzz per question. The buzz is the user's attention tool, not a sound in the video.

## Context

The ledger (`output/<p>/videos.csv`), the recordings cache (`temp/<p>/data.json`) and `output/_state.json` hold everything needed to resume. At each **project boundary**: write a `state note`. If the conversation is long, stop with a 5-line handoff or ask the user to `/compact`. A fresh session resumes with `state next`. Mid-project, keep going.

## References (load only when you reach that step)

- `references/simple-rules.md`: **the rulebook**: 10 steps per video, the numbers, if-then fixes, the self-check. Give it to every small-model subagent
- `references/pacing.md`: fast/medium/slow by length: shot lengths, reading time, what `check` enforces
- `references/framing.md`: which `fit` for which source shape, auto focus and auto track, `stack`/`float`
- `references/pro-mode.md`: the pro look, sounds, voice and structure
- `references/questionnaire.md`: first-run questions → `shipreel.config.json`
- `references/recording-gate.md`: **before recording**: blockers, drivers, framing, the post-record checklist, symptom table
- `references/pipeline.md`: commands per step, recording recipes (web, Godot, screen, worktree)
- `references/plan-schema.md`: plan JSON fields (clips, captions, overlays, sfx, music)
- `references/highlighting.md`: pointing at things exactly: anchored highlights, `target` steps, which type for which target, the proof sheet
- `references/effects-cookbook.md`: which effect for which moment, ready-made snippets, and camera moves that put the named thing in view
- `references/caption-look.md`: how captions should look (bubble, chip, TikTok Classic/Background), colours that don't clash, the auto-contrast fix
- `references/copy-rules.md`: hooks, titles, captions, descriptions, hashtags, links, mentions
- `../humanizer/SKILL.md`: AI-pattern scan and rewrite for captions, titles and descriptions (also works on any blog, LinkedIn, email or Slack text)
- `references/music-audio.md`: **music decision per video**, meme-music beds, muting the project's own music, SFX, loudness
- `references/tiktok-strategy.md`: why hooks/structure/pillars/sounds/CTAs work on TikTok, adapted to a faceless dev channel
- `references/channel-rules.md`: faceless channel, avoiding low-effort and reused-content flags
- `references/naming-and-files.md`: file names, folders, description files
- `references/failure-protocol.md`: buzz + options, env vars, effort estimates
- `templates/plan.example.json` (creator) and `templates/plan.pro.example.json` (pro): working plans to copy from. Faster: `clip.py scaffold`

## Assets

`python S/scripts/assets.py find --type image --mood smug` / `--q "this is fine"` / `vocab` / `--pro`. That covers 199 memes, 46 SFX (8 soft originals for pro), 21 music beds (`--type music`; 2 originals safe everywhere), overlays (arrows, rings, scribbles, X and check marks) and 25 fonts (`clip.py fonts`). `scripts/synth_sfx.py` regenerates the originals. Add more with `assets.py add` (or drop files in `assets/inbox/` and `assets.py scan`). New SFX: `sfx.py get "<name>"`; new meme music: `sfx.py get "<name>" --kind music` (myinstants). GIFs: `gif.py` (needs a key). NSFW-flagged memes stay out unless `--all-ratings`.

If the vendor skills `viral-hooks`, `viral-captions-and-ctas`, `viral-tiktok-content`, `viral-youtube-shorts`, `viral-short-form-ideas` or `tiktok-marketing` are installed, the writer may read them for more depth. `copy-rules.md` already holds what this skill needs from them.
