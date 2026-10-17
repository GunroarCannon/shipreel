# Failure protocol: buzz, then ask

A wrong guess costs more than a question: a batch of videos filmed from the wrong screen wastes an hour of renders and the user's trust, while a question costs them ten seconds. **When in doubt, ask.** The user chose this plan knowing they'd be buzzed; they never asked for silence. Try **one** cheap fix first only for purely mechanical problems (wrong path, a port in use, a missing `npm i` the shorthand mentions). Everything below is a trigger to ask instead of pushing on.

## When to ask (any one is enough)

- A recording failed twice, or its sheet doesn't show the feature it's named for (`recording-gate.md`).
- You can't get past a blocker (login, paywall, data you don't have, a tutorial that won't dismiss, an app that won't start).
- You're about to **fake it**, skip a feature, drop a video, or substitute a different feature or angle than the slate.
- A caption wants to name something that isn't on any recording and you'd have to guess, invent or re-time around it.
- Two reasonable framings, angles or tones and you can't tell which the user would pick (portrait vs `blurpad`, serious vs jokey, which version counts as "old").
- A claim in a title or caption (a count, a date, "first", "fastest") isn't backed by the shorthand or git history.
- Something might be private (names, emails, keys, unreleased work) and the shorthand's `never show` list doesn't settle it.
- The user's request has a gap you filled with an assumption. Say the assumption in the question and offer the alternative.
- You notice you're about to write "probably", "should be fine", "I assume" about something that changes the output. Ask instead.

Never silently pick the easy path. A "faked" or "assumed" step that the user wasn't told about is the failure this protocol exists to stop.

Always ask (at any ask level except `config.music.ask = never`): **music for the TikTok batch** (`music-audio.md`, section 00).

Also ask when: a project has its own music and the licence or intent is unclear (keep it, mute it under a meme bed, or drop the bed?).

## Ask level (`config.ask.level`, set in the questionnaire)

- `often`: also check in at the **slate** (features × angles per project), after the **first recording sheet** of each project, and after the **first rendered video** of each project (show the sheet path, ask "ship the style, or change X?").
- `when_unsure` (default): ask on the triggers above.
- `rarely`: ask only on hard blocks (exit 3, `NEED_ENV`, nothing recordable). Even then, never fake a feature without telling the user in the summary.

If the user says "ask me more" or "stop asking" mid-run, switch level and write it to `shipreel.config.json`.

## Subagents can't ask: they escalate

Scout, editor, writer and reviewer return a report to the director; they have no way to question the user. When they hit any trigger above they must **not** pick a workaround. They stop that item and put this line first in their return:

`NEEDS_USER: <one-sentence problem> | options: skip / fix (~N min) / fake it (what exactly) / <their own idea> | recommend: <one>`

The director collects every `NEEDS_USER` line, buzzes once, and asks them in one AskUserQuestion call (max 4). A subagent report that says `ok` while its own notes say "couldn't verify", "seems stuck", or "used placeholder" counts as a `NEEDS_USER` the director must raise.

## 1. Buzz

```
python S/scripts/buzz.py "shipreel: <8 words max, what's needed>" -t 3
```

Windows: a flashing red border on every screen + a sound + a banner (`tools/buzzer/buzzer.exe`; non-blocking, click-through). macOS and Linux get a notification + a sound. Set `SHIPREEL_BUZZ=0` to silence it. Buzz once per question, not per retry.

**Any question to the user buzzes first**, not only failures: the questionnaire, mid-run decisions, env values, the effort choice. Run buzz.py right before the AskUserQuestion call, with the same message shape. Never buzz for progress updates or finished work.

## 2. Ask (AskUserQuestion, one question, these options)

Header: the project name. Question: what failed, in one sentence, plus the last error line (no secrets). Options:

1. **Skip it**: drop this recording or video and pick another feature/angle (state what will replace it).
2. **Fix it (~N min, what)**: with an honest estimate and whether it touches the project, e.g. "Fix (~5 min): install deps in a temp worktree, the repo stays clean" / "Fix (~20 min, edits project): patch the missing asset path, reverted after".
3. **Fake it**: a believable stand-in that still shows real things: mock data in the UI via URL params/`eval` steps, the live site instead of local, old screenshots from git history, a static screenshot with zoom/pan, an existing trailer. Say exactly which. Never fake a feature that doesn't exist.
4. **Paste env var**: only when the error is `NEED_ENV <NAME>` or the app clearly needs a key. "Paste `<NAME>` in chat; it's only used for this one command."

Put the recommended option first, marked `(Recommended)`. Usually: skip if the batch has plenty of other material, fix if it's cheap and high-value.

**Asking doesn't have to stall the run**: buzz and ask right away (AskUserQuestion shows immediately), then while waiting continue only with work that doesn't depend on the answer. Batch several open questions into one call (max 4). Do not defer a question until you've "run out of other work": ask when the trigger happens.

## 3. Env values the user pastes

- Use them for one command only: Bash `NAME='value' python ...`, or PowerShell `$env:NAME='value'; ...; Remove-Item Env:NAME`.
- Never write them to any file (config, plan, shorthand, steps, .env, notes, state), never echo them, never include them in summaries, descriptions or commit messages. If a command prints one (debug output), don't repeat it.
- Don't store them for later; ask again in a new session if needed. The user said this run's env values are throwaway, but nothing should leak anyway.
- If a value appears on screen in a recording (dev tools, a settings page), add a `censor` overlay or re-record.

## Exit codes from scripts

| code | meaning | action |
|---|---|---|
| 0 | ok | |
| 1 | failed (`error` in the JSON) | read the stderr tail, try one fix, then protocol |
| 3 | needs the user (`NEED_ENV X`, missing chrome/godot) | protocol, option 4 or 2 |
| `NEED_DISK` in error | disk below the limit | `clean --segments`; still low → protocol (ask to free space or move `SHIPREEL_HOME`) |

## Effort estimate guide

| fix | typical |
|---|---|
| install npm/pip deps in a worktree | 2 to 10 min, 100 MB to 1 GB of disk (check free space first) |
| build an old commit that fails | 10 to 30 min, often not worth it → fake it with old media |
| missing API key the app needs to show data | 1 min if the user has it; else fake it with mock data |
| a Godot scene that needs a save file or login | 5 to 15 min via an autoplay `call`/`set` |
| a desktop app that won't launch | ask; usually skip |
