# Failure protocol: buzz, then ask

The run is meant to be unattended, so a question is expensive: the user may be away. Before asking, try **one** cheap fix yourself (wrong path, missing `npm i` the shorthand mentions, a port in use). If that fails, or the fix would touch the user's project, ask.

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

**Don't block the run**: while waiting, continue with other videos or projects that don't depend on the answer (render what's planned, scout the next project). Ask with AskUserQuestion only when you've run out of independent work, or batch several open questions into one call (max 4).

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
