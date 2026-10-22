# Pro mode

Creator mode makes dev-channel TikToks: memes, meme sounds, chunky captions, jokes. Pro mode makes what a company would post: product demos, launch clips, feature announcements, case studies, portfolio pieces, LinkedIn and YouTube explainers. Same pipeline, same quality rules, a different look and voice.

## Turn it on

- For everything: `"mode": "pro"` in `shipreel.config.json` (the questionnaire asks).
- For one plan: `"mode": "pro"` at the plan's top level. For one video: `"mode": "pro"` on the video.
- `C scaffold <p> --rec ... --mode pro` builds a pro skeleton (pro style, clean grade, soft sounds, a calm bed).
- Optional brand colour: `"brand": {"accent": "#4F8CFF"}` in the config (pro videos use it for `*accent*` words), or `"accent"` on one video.

## What changes by itself

- Default caption style `pro` (Inter SemiBold, white, a soft dark halo, fades in), lower in the frame.
- Box, plate, lower-third, header, title and card text switch to Inter. Callouts take the accent colour.
- Cards fade instead of pop. Transition sounds are the soft ones (`swoosh-fast`, `whoosh-soft`).
- `check` adds `pro:` (hard) and `pro note:` (soft) lines.

## The look

| preset | font | for |
|---|---|---|
| `pro` (default) | Inter SemiBold | product demos, SaaS, client work |
| `minimal` | Manrope ExtraBold | startups, landing-page feel |
| `editorial` | Instrument Serif | stories, case studies, founder videos, documentaries |
| `tech` | Space Grotesk Bold | dev tools, APIs, infra |
| `headline` | Archivo Black | a single strong claim, news style |
| `condensed` | Oswald SemiBold (caps) | stats, countdowns, sports-style numbers |
| `clean`, `label`, `cinema` | TikTok Sans / Bebas Neue | also allowed |

- One preset per video, one accent colour, no outlines thicker than a halo.
- **Grade**: `"grade": "clean"` (light contrast and saturation; the scaffold's default) for UI and product; `cinematic` for story pieces; `mono` for the "before" side of a comparison; `warm` / `cool` to match a brand. Never `film` on UI (the grain blurs small text).
- **Framing**: same rules (`framing.md`), with `float` instead of `blurpad`: phone recordings and UI screens become a rounded card with a soft shadow.
- **Overlays**: Avoid circles and rings unless coordinates are verified with certainty from the contact sheet grid. Floating, misaligned rings look clumsy and broken. If you cannot get the exact target accurately, avoid circles entirely: use a subtle camera zoom (`zoomin:1.15@x,y`), a spotlight, or leave the UI clean and unadorned. Clean `box`, `underline`, and straight `arrow` work well when needed. Hand-drawn `scribble` and `arrow-curved` are creator looks.
- **Effects**: `zoom`, `zoomin`/`zoomout`, `freeze`, `slowmo`, `speed`, `contrast`, `sat`, `dim`, `vignette`, `fadein`/`fadeout`. Never `glitch`, `vhs`, `shake`, `pixelate`, `mirror`, `reverse`.
- **Transitions**: hard cuts, `dissolve`, `dip`, `push`, `smooth`, `zoom`. One `whip` at most. Pace sets their length (`pacing.md`).

## Sound

- SFX: `assets.py find --type sfx --pro`. The originals made for pro (`whoosh-soft`, `swoosh-fast`, `riser`, `impact-soft`, `tick`, `ui-click`, `pop-soft`, `shimmer`) plus the clean library sounds (`whoosh`, `pop`, `ding`, `mouse-click`, `camera-shutter`, `keyboard-typing`).
- Keep SFX sparse: 2 to 4 per video at volume 0.4 to 0.6. Every sound must tie directly to an on-screen visual event (e.g. `impact-soft` under the title, `ui-click` on a button press, `shimmer` on a finished result).
- **No phantom transition sounds**: Never play a `whoosh` or `swoosh` when no transition or fast camera move occurs. Never put whooshes on gentle dissolves, fades, or static text.
- Beds: `assets.py find --type music --pro`: `ambient-pad` (calm, 32 s loop) and `soft-pulse` (96 bpm plucks, 20 s loop) are generated originals, safe everywhere. Library tracks marked `yt:ok`/`yt:credit` pass too (add the credit line). Best: the brand's own licensed track, dropped in `assets/music/` and indexed. Volume 0.10 to 0.14, ducked.
- Never meme sounds or meme music (`pro:` fails them). Regenerate or add originals with `scripts/synth_sfx.py`.

## The voice

- Sentence case for titles and captions. Product names capitalized.
- Lead with the outcome: "Export a report in one click", "From 40 minutes to 4", "Same dashboard on phone and desktop".
- Concrete beats clever: real numbers, real feature names, what the viewer gets.
- No slang (bro, lol, ngl...), no caps shouting, no emoji, no clickbait. One soft CTA at the end at most ("Try it at example.com").
- The humanizer still applies: no AI vocabulary, no "revolutionize your workflow", no stacked triplets.

## Structure

| part | fast (≤ 22 s) | medium / slow |
|---|---|---|
| hook | 0 to 2 s: the outcome in 3 to 6 words over the best frame | 0 to 3 s, same |
| problem | optional, 1 beat | 1 beat: the pain, shown |
| the product doing it | 2 to 4 beats, one feature each, each with a label and a pointer | 3 to 6 beats or sections with `lower` thirds and chapters |
| result | a number or the finished state | the same, held longer |
| end | product name + URL as a `chip` or `lower` (1.5 to 2.5 s) | the same, plus one CTA line |

## What check enforces in pro mode

- Hard (`pro:`): a creator preset, meme clips or stickers, meme SFX, meme music, `glitch`/`vhs`/`shake`/`pixelate`/`mirror`/`reverse`.
- Soft (`pro note:`): slang, caps shouting, a lowercase title, a clickbait hook, emoji in the description, scribbles and curved arrows.

A channel can mix: the dev channel's TikToks in creator mode, a launch video for the same project in pro. Set `mode` per video.
