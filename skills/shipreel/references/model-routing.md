# Model routing

The expensive part of a run is not rendering. It's an expensive model reading repos, command output and images. Route each job to the cheapest model that does it well.

## Who does what

| job | why this model | model (balanced) |
|---|---|---|
| Scout a repo → `.project-shorthand.txt` | Reading lots of files and summarizing is mechanical | haiku |
| Run recordings, renders, probes; fix JSON/ffmpeg errors | Command running plus reading short JSON | haiku |
| Angles, hooks, titles, captions, descriptions, plan JSON | Copy quality decides views; cheap models sound generic | sonnet (opus on `quality`) |
| Review contact sheets + copy | Needs taste and visual judgment | sonnet |
| Pick which features and eras, final call on each batch | Needs the whole picture | director (session) |

## How to delegate

- Agent tool, `subagent_type: general-purpose`, `model: <from config.models>`.
- Prompt = the role file (`references/roles/<role>.md`) + the concrete inputs (project slug, shorthand path, plan path, video ids). Never paste the shorthand or plan contents into the prompt when a path will do.
- Ask for terse returns: the role files define the return format (a path + a ≤5 line summary). Don't ask subagents to "explain".
- Run independent subagents in parallel: for example, scout the next project while the current project renders.
- Do not spawn a subagent for a single command. Run it yourself.
- Tell a haiku editor to follow `references/roles/editor.md` in order and treat each check error line as the fix.

## Plans

- **balanced** (default): as in the table.
- **quality**: writer = opus, reviewer = sonnet. Use on YouTube passes or once a channel has traction.
- **budget**: writer = haiku, then the director rewrites only the titles and first captions (the hook) of each video. That's about 10% of the tokens and most of the value.
- **single**: no subagents; the director does everything. Best when the session model is already Haiku or Sonnet, or for 1 to 3 videos.

## Token habits (all roles)

- Read `clip.py` outputs (one-line JSON), not the files they write.
- To see a video: `clip.py sheet file.mp4 --n 6` → one jpg. Never extract frames one by one.
- To see assets: `assets.py find` (text) first; `assets.py sheet` only when choosing between visuals.
- Read the shorthand, not the repo. Refresh the shorthand only when `git log <scouted_sha>..HEAD --oneline | wc -l` > 0 and the new commits matter.
- Ledger titles (`clip.py ledger <p> --titles`) instead of re-reading old plans.
- Plans hold ≤5 videos, so a fix touches a small file.
