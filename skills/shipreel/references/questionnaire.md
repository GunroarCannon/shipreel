# First-run questionnaire

Goal: get the setup answers in one sitting so the run mostly flows, while staying free to ask again whenever something is unclear (`failure-protocol.md`, "When to ask"). Before each round, buzz the user: `python S/scripts/buzz.py "shipreel: answer 3 quick questions" -t 2`. Use AskUserQuestion (max 4 questions per call, so 3 rounds). Put the recommended option first. Skip anything the user already answered in their request. Write the answers to `<workspace>/shipreel.config.json`, which uses the same keys as `config/defaults.json` and only needs the overrides.

## Round 1: cost and scope

1. **Model plan** (header "Models")
   - `balanced (Recommended)`: scout/editor = haiku, writer/reviewer = sonnet, director = this session. Good copy, cheap grunt work.
   - `quality`: writer = opus, reviewer = sonnet. For channels that already have traction, or for YouTube passes.
   - `budget`: everything haiku, and the director polishes titles and hooks itself. Cheapest, but the copy gets more generic.
   - `single`: no subagents. Use when the session model is already cheap or the batch is tiny.
2. **Projects** (header "Projects"; free text via Other): the paths to each project, in priority order. If the user points at a parent folder, list the repos it contains and confirm.
3. **First pass size** (header "Pass 1"): `10 TikToks per project (Recommended)` / `5` / `3 to test the look first`.
4. **Meme level** (header "Memes"): `medium (Recommended)`: a meme or meme SFX in about 1 in 3 videos / `heavy`: most videos / `light`: rare, clean only.

(Add a fifth question in the next round if you have room, otherwise put it in Round 2 and drop "Same channel for all projects?" to the default.)

**How often to ask** (header "Check-ins"): `when I'm unsure or stuck (Recommended)`: asks on blockers, fakes, guesses and unverifiable claims / `often`: also check in at each project's slate, first recording and first video / `rarely`: only when blocked. Maps to `ask.level` = `when_unsure` / `often` / `rarely`. Tell the user they can change it any time by saying "ask me more" or "stop asking".

## Round 2: channel and links

5. **Handles** (header "Accounts"; Other for free text): TikTok, YouTube, X, LinkedIn, GitHub. Used for @mentions and links. "None yet" is fine; then link nothing social.
6. **Links in descriptions** (header "Links", multiSelect): `GitHub repo if public (Recommended)` / `Live site if it's up (Recommended)` / `X profile` / `LinkedIn`. Only suggest X/LinkedIn if the user posts dev content there.
7. **Clickbait share** (header "Clickbait"): `about 1 in 5 (Recommended)` / `none` / `about 1 in 3`. Clickbait means a curiosity-gap hook that the video still pays off. It never means a false claim.
8. **Same channel for all projects?** (header "Channel"): `yes, one dev channel (Recommended)` / `separate per project`. With yes, cross-project references are allowed.

## Round 3: permissions (what can run unattended)

9. **Allowed actions** (header "Permissions", multiSelect):
   - `launch the projects (dev servers, game builds) (Recommended)`
   - `simulate input (scripted clicks, keys, autoplay) (Recommended)`
   - `check out old commits in temp worktrees (Recommended)`
   - `edit project files (minimal, reverted after)`: off by default
10. **Music** (header "Music"): `TikTok: meme-music bed + trending sound in-app, YouTube: product music or none (Recommended)` / `burn in meme music everywhere (Content ID risk on YouTube)` / `no music, SFX only`. Maps to `music.meme_bed` = `"tiktok"` / `"all"` / `"off"`. Follow with: `ask me about music each batch (Recommended)` / `ask once and reuse` / `never ask, use the defaults` -> `music.ask` = `"each-batch"` / `"once"` / `"never"`. Also ask when a project turns out to have its own music: keep it, or mute it under the meme bed?
11. **Where to write** (header "Output"): `this folder (Recommended)` / `another drive (tell me the path)`. If doctor showed low disk, recommend another drive first.
12. **Shorthand file location** (header "Shorthand"): `temp/<project>/ (Recommended, repo untouched)` / `in each repo as .project-shorthand.txt` (handy if the user commits it).

## After the answers

- Write `shipreel.config.json`. Example:

```json
{
  "projects": [{"name": "voidrunner", "path": "D:/dev/voidrunner"}, {"name": "snaplist", "path": "D:/dev/snaplist"}],
  "channel": {"same_channel": true, "handles": {"tiktok": "@devbyx", "github": "devbyx"}},
  "models": {"plan": "balanced", "scout": "haiku", "writer": "sonnet", "editor": "haiku", "reviewer": "sonnet"},
  "quota": {"first_pass": {"tiktok": 10}},
  "mix": {"clickbait_share": 0.2, "meme_intensity": "medium"},
  "ask": {"level": "when_unsure"},
  "permissions": {"launch_apps": true, "simulate_input": true, "old_commits_via_worktree": true, "edit_project_files": false}
}
```

- `clip.py init <name> --path <repo>` for each project (add `--shorthand-in-repo` if the user picked that).
- Tell the user in 3 lines: the plan, the expected output count and that you'll buzz when you need them (and how to change the check-in level). Then start the loop without asking for confirmation.

Never ask for API keys up front. Ask only when a step needs one (failure protocol). Most runs never need one.
