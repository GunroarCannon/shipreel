# The rulebook: rules any model can follow

This file is for every model on the run, and written so the smallest one can follow it without judgment calls. Follow it top to bottom. When a rule here and your own idea disagree, the rule wins. When something isn't covered, ask the director (`NEEDS_USER:` line), don't improvise.

`C` = `python S/scripts/clip.py`.

## Build one video in 10 steps

1. **Mode.** `config.mode`, or the plan's `mode`. `pro` = client work, product demos, launches, LinkedIn, anything a company posts. `creator` = the dev channel: memes allowed. `slide` = viral photo slideshows & swipe carousels (target callout hooks on slide 1, consistent feed theme/character, value slides, app CTA on final slide; `slide-mode.md`). Don't mix inside one video.
2. **Find the moments.** For each recording you'll use: `C moments <rec-id> --project <p> --format tiktok`. It returns the best moving spans (`in`, `out`) and where the action is. `moments[0]` is the strongest: the video opens on it.
3. **Scaffold.** `C scaffold <p> --rec <id>[,<id>] --out temp/<p>/plans/p1_a.json --id t01 [--recipe ...] [--mode pro] [--format youtube]`. It writes clips, transitions, caption slots, sounds and pace for you. Pick the recipe from the table below.
4. **Write the words.** Replace every `TODO` (title, tags, description, hook_type, captions). Rules: "Captions" below and `copy-rules.md`. Don't move the times unless `check` asks.
5. **Point at things, exactly or not at all** (`highlighting.md`). If a caption names something (a button, an enemy, a key stat), anchor a highlight to it: a `target` measured by `record-web` (web) or a `box` read off `C sheet <rec> --grid` (games), plus `what`. Pick the type by the target (box/focus for UI, marker/bar for text, arrow for small things; not always a ring). After rendering, **open the `proof` sheet**: every highlight must sit on its target, and one missing from it was dropped (`overlay_notes` says why). Can't place it exactly? Use a camera move (`track`/`zoomin`) or nothing.
6. **Music.** Creator: follow the user's music answer (`music-audio.md` section 00). Pro: keep the scaffold's bed or use the user's licensed track.
7. **Delete the `todo` list** once each item is done.
8. **Check.** `C check <plan>`. Fix every line that is not marked soft. Fix soft lines too (`pace:`, `framing:`, `pro note:`) unless you have a reason you can write down.
9. **Render.** `C render <plan> --only t01`. Read `framing` (what auto framing chose) and `contrast_fixed`.
10. **Look.** `C sheet output/<p>/<file>.mp4 --n 6`, open the jpg, run the self-check at the bottom. Fix, `render --only t01 --force`. Two fix rounds at most.

## Which recipe

| the idea | recipe | hook_type | format |
|---|---|---|---|
| a feature, a cool moment, gameplay | `showcase` | flex, pov, number, middle-of-action | tiktok |
| old version vs new | `before-after` (`--rec old,new`) | before-after | tiktok |
| a bug, a fail | `showcase`, then put the fail clip first | fail | tiktok |
| a walkthrough, devlog, product tour | `tour` (one rec per section) | tutorial, process | youtube, or tiktok 30-45 s |
| pro product launch | `showcase --mode pro` | number, before-after | tiktok + youtube |
| photo slideshow / swipe carousel | `slide` (or `--mode slide`) | target-callout, forced-swipe | tiktok |

## Numbers (pace)

Pace comes from length. Short videos are fast, long videos are slow. `pace: auto` picks it; you rarely set it.

| pace | when | shot length | something new every | caption words | caption on screen | transition |
|---|---|---|---|---|---|---|
| fast | ≤ 22 s | 0.6 to 3.2 s (avg 1.8) | 2.5 s | 2 to 6 | 0.4 s + words ÷ 3.6 (min 0.9 s) | 0.22 s, mostly hard cuts |
| medium | 22 to 60 s | 1 to 5.5 s (avg 3) | 4 s | 3 to 8 | 0.4 s + words ÷ 3.0 (min 1.2 s) | 0.4 s |
| slow | > 60 s | 1.5 to 10 s (avg 5) | 8 s | 4 to 12 | 0.4 s + words ÷ 2.5 (min 1.8 s) | 0.7 s |

"Something new" = a cut, a caption, a zoom, a camera glide, an SFX or an overlay. Leave `d` out of a caption and render sizes it to the reading time. Details: `pacing.md`.

## Framing (which `fit`)

Leave `fit` out. `auto` does the right thing for the source shape:

| source → video | what auto does | when to override |
|---|---|---|
| phone portrait → TikTok/Shorts | `cover`: fills the frame | never |
| landscape game → TikTok | `cover` aimed at the action (auto focus); `track: "auto"` follows it in clips ≥ 2.5 s | `fit: "stack"` when the whole map matters too |
| landscape web UI → TikTok | `blurpad` (creator) / `float` (pro): the whole UI over a blur | better: record it `--portrait` |
| phone portrait → YouTube | `float` (pro) / `blurpad`: the phone centred over a blur | never cover it |
| landscape → YouTube / X | `cover`: fills | never |
| image / meme | `blurpad` / `float` | `cover` if it's already the frame's shape |

After render, `framing` in the result says what auto chose. On the sheet, the thing the caption names must be in frame. If it isn't: set `focus: [x, y]` (from `sheet --grid`) or `track` keys. Details: `framing.md`.

## Captions

- The first caption starts at `t: 0`. It is the promise of the video in 3 to 6 words.
- One idea per caption. At most 2 lines. Words per caption: see the pace table.
- Name what the viewer is seeing or what they can't see (the why, the number, the joke). Never "here is the menu".
- At most one `*accent*` word per caption.
- Two captions of the same style never overlap in time.
- Style per video, not per caption: creator rotates `bubble`, `pop`, `game`, `label`, `trendy`...; pro uses `pro`, `minimal`, `editorial` or `tech`. `chip` for dates and labels works in both.
- Creator: lowercase is fine. Pro: sentence case, no slang.
- Never: emoji in captions, "follow for more", AI words (`copy-rules.md` "Never").

## Effects budget

| | fast creator | medium creator | pro (any pace) | slow (YouTube) |
|---|---|---|---|---|
| SFX | 3 to 5 | 2 to 5 | 2 to 4 soft ones | 1 per 10 s |
| pointing overlays (box, focus, marker, arrow...) | 1 to 2 | 1 to 2 | 1 | 1 per section |
| zooms (zoomin / zoom) | 1 to 2 | 1 to 2 | 1 | 1 per section |
| memes | 0 to 1 | 0 to 1 | **0** | 0 to 1 (creator) |
| transitions (not cuts) | 0 to 1 whip/flash | 1 to 2 | 1 to 2 dissolve/push/dip | at section changes |

## Transitions

- Default is a hard cut. Most joins stay cuts.
- Creator: `whip` (a fast blurred slide with a whoosh), `flash` (white), `zoom`, `glitch` for a bug. Use 1 or 2 per video.
- Pro: `dissolve`, `dip` (through black), `push`, `smooth` (soft wipe), `zoom`. Use 1 or 2 per video, more only at section changes.
- Slow / YouTube: `dissolve` or `dip` at section changes.
- Never one on every cut. Never `fadein` on a TikTok.

## Sounds

- Creator: SFX from `assets.py find --type sfx --mood <m>`. Start an SFX 0.05 s before the beat it marks. Volume 0.5 to 0.8 (sounds are levelled at render, so `vol` is relative; `music-audio.md` section 4b gives every sound a job).
- Pro: only `assets.py find --type sfx --pro` (whoosh-soft, swoosh-fast, riser, impact-soft, tick, ui-click, pop-soft, shimmer, ding, pop, mouse-click, camera-shutter, keyboard-typing). Beds: `assets.py find --type music --pro`. Volume 0.10 to 0.14.
- One music bed per video. If the recording has its own music, render mutes it under the bed.

## If X, then Y

- A clip is longer than the pace allows → split it into two clips with different `focus`, or `track: "auto"`, or `speed: 2` for the boring part.
- Nothing happens for longer than the pace's gap → add a cut, zoomin, SFX or caption there.
- A caption is up for less than its reading time → cut words first; only then raise `d`.
- The named thing is off-frame on the sheet → `focus` on it, a `track`, or `zoomin:1.4@x,y`. Still not there → change the caption.
- The sheet shows the same frame six times → the recording froze; re-record (`recording-gate.md`).
- Captions are hard to read → `label` style (creator) or let auto-contrast add a plate; never a coloured text on the same colour.
- A caption covers the thing it names → move it with `x`, `y` (keep y between 0.12 and 0.70) or use `hook` (top) instead of `cap`.
- Before/after looks the same on both sides → `bw` (creator) or `sat:0.35` (pro) on the old side, plus a `chip` date on each side.
- `check` says `pro:` → remove that item; pro videos never have memes, meme sounds or meme music.
- You don't know a fact (a number, a date) → don't write it. Ask, or write a caption that doesn't need it.

## Never

- Never ship a render you didn't look at (`sheet`).
- Never write a caption about something that isn't on screen at that moment.
- Never place unplated `title` or `mid` captions over dense text, paragraphs, or data tables; use `plate`, `box`, or `lower` positioned in clean negative space.
- Never place a highlight by guessing output coordinates. Anchor it (`target`/`box`/`at`) and read the `proof` sheet; if it can't land exactly, use no highlight. Don't use the same highlight type for every pointer.
- Never play transition sounds (`whoosh`, `swoosh`, `whip`) when no transition, cut, or fast camera move happens. Never play whooshes on gentle dissolves, fades, or static footage.
- Never scatter random clicks, pops, or whooshes simply to fill pacing gaps. Sounds must always accompany a visible on-screen beat.
- Never use a recording with `!!STILL` or `!!CHOPPY` in `rec list`.
- Never leave `TODO` text or the `todo` list in a plan you render.
- Never put a landscape game in a thin strip with bars in a portrait video (`framing:` warns).
- Never put meme assets in a `pro` video.

## Self-check before you say done (answer each, in writing)

1. Frame 1 of the sheet: does it show action and the hook text?
2. Every caption: is the thing it names visible in that frame?
3. Is the subject big and in frame in every shot (not cut off, not tiny)?
4. Can every caption be read at phone size, without overlapping the subject?
5. Does `check` print OK or only soft lines you can justify?
6. Pro: no memes, no slang, sentence case, soft sounds only?

Any "no" → fix and re-render.
