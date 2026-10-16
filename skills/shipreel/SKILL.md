---
name: shipreel
description: "Turn the user's software and game projects into faceless, voiceless short-form and long-form videos: records select parts of each project (web apps through headless Chrome, Godot games through Movie Maker, anything through screen capture, old versions through git worktrees), then edits them with ffmpeg into captioned TikToks/Shorts (10-30s portrait) and YouTube videos (1-5 min) with trending caption fonts, memes, SFX, arrows, freeze frames and human-sounding titles, descriptions and hashtags. Use when the user wants devlog/showcase content, TikToks or YouTube videos of their projects, a content batch for a dev channel, or asks to continue a shipreel run."
license: MIT
---

# shipreel

You are the **director**. You plan, delegate cheap work to cheaper models, and check results. Scripts do the heavy lifting and print one-line JSON, so read outputs, not files.

`S` = this skill's folder. Run scripts as `python S/scripts/clip.py ...`. Outputs land in the **workspace** (`$SHIPREEL_HOME`, else the cwd): `output/<project>/` and `temp/<project>/`.

## Start of every session

1. `clip.py doctor`. Any `warn` → fix or tell the user (low disk: suggest `SHIPREEL_HOME` on another drive).
2. No `shipreel.config.json` in the workspace → run the **questionnaire** (`references/questionnaire.md`). It picks the model plan, projects, handles and permissions. Ask it all up front so the run can go unattended.
3. `clip.py state show`. If a run is in progress, resume from it; don't redo work the ledger already has.

## The loop

```
state next → {project, pass, need:{tiktok:10}}            # pass 1: 10 TikToks per project, then next project
  brief    → read .project-shorthand.txt (scout fills it if it's the template or stale)
  record   → rec list; record only what's missing (editor)
  write    → plan JSON for ≤5 videos at a time (writer)
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

Plans, the reasons behind them, and when to skip subagents: `references/model-routing.md`.

## Hard rules

- **Standalone videos.** Each one makes sense to a viewer who saw nothing else. Use series (`-part-N`) only when a story really needs it, and still stand alone.
- **Faceless and voiceless.** No webcam, no TTS voice. On-screen text carries the story. Avoid low-effort and reused-content flags: `references/channel-rules.md`.
- **Human copy.** Short, specific, lowercase-casual where it fits, no AI tells. Some clickbait (`config.mix.clickbait_share`), never a lie. `references/copy-rules.md`.
- **Never edit the user's project.** Use env/CLI toggles, `--autoplay` scripts, URL params and git worktrees (`clip.py worktree`). Edits to the project only with `permissions.edit_project_files`, and keep them minimal and reversible.
- **Never show secrets.** Check the shorthand's `never show` list. Blur them with `censor` overlays when they're on screen.
- **Env values** the user pastes go into the env of one command only. Never into files, plans, logs, descriptions or summaries.
- **Disk and RAM.** One render at a time. `clip.py clean <p> --segments` after a project's batch is reviewed. Remove worktrees when done.

## When something fails or needs the user

Exit code 3 / `NEED_ENV X` / missing tool / a recording that won't work → **buzz, then ask**:
`python S/scripts/buzz.py "shipreel needs you: <short reason>"`, then AskUserQuestion with **skip / fix (effort estimate) / fake it / paste env var**. Keep working on other projects while waiting when you can. Full protocol: `references/failure-protocol.md`.

## Context

The ledger (`output/<p>/videos.csv`), the recordings cache (`temp/<p>/data.json`) and `output/_state.json` hold everything needed to resume. At each **project boundary**: write a `state note`. If the conversation is long, stop with a 5-line handoff or ask the user to `/compact`. A fresh session resumes with `state next`. Mid-project, keep going.

## References (load only when you reach that step)

- `references/questionnaire.md`: first-run questions → `shipreel.config.json`
- `references/pipeline.md`: commands per step, recording recipes (web, Godot, screen, worktree)
- `references/plan-schema.md`: plan JSON fields (clips, captions, overlays, sfx, music)
- `references/effects-cookbook.md`: which effect for which moment, ready-made snippets
- `references/copy-rules.md`: hooks, titles, captions, descriptions, hashtags, links, mentions
- `references/music-audio.md`: product audio, music, SFX, loudness
- `references/channel-rules.md`: faceless channel, avoiding low-effort and reused-content flags
- `references/naming-and-files.md`: file names, folders, description files
- `references/failure-protocol.md`: buzz + options, env vars, effort estimates
- `templates/plan.example.json`: a working plan to copy from

## Assets

`python S/scripts/assets.py find --type image --mood smug` / `--q "this is fine"` / `vocab`. That covers 199 memes, 38 SFX, overlays (arrows, rings, scribbles, X and check marks) and 11 fonts. Add more with `assets.py add` (or drop files in `assets/inbox/` and `assets.py scan`). New SFX: `sfx.py get "<name>"` (myinstants). GIFs: `gif.py` (needs a key). NSFW-flagged memes stay out unless `--all-ratings`.

If the vendor skills `viral-hooks`, `viral-captions-and-ctas`, `viral-tiktok-content`, `viral-youtube-shorts`, `viral-short-form-ideas` or `tiktok-marketing` are installed, the writer may read them for more depth. `copy-rules.md` already holds what this skill needs from them.
