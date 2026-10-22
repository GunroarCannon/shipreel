# Highlighting: point at the thing, exactly, or not at all

A highlight that lands on the wrong spot is worse than no highlight. Viewers read an off-target ring as "this video is broken". So the rule is **measure, don't guess**, and the renderer enforces it: a highlight it can't place exactly is dropped and reported, never drawn in the wrong place.

## Why positions used to go wrong

`x, y` on an overlay are fractions of the **output frame**, but the only thing you can read positions off is the **source recording** (`clip.py sheet --grid`). A 16:9 game in a 9:16 TikTok keeps about a third of its width, so every source coordinate shifts, and a `track` glide or a `zoomin` moves it again. Hand-converting that is where the misses came from.

## Anchored highlights (the way to do it)

Give the highlight a place in the **source** frame; the render maps it through that clip's crop, focus, track, zoom and layout.

| field | meaning |
|---|---|
| `target` | name of an element `record-web` measured from the page (web apps: exact, no guessing) |
| `box` | `[x, y, w, h]` of the thing, fractions of the source frame (read off `clip.py sheet <rec> --grid`) |
| `at` | `[x, y]` for a single point (arrow tip, small ring) |
| `what` | what it points at, in words ("Export button"). Required: the reviewer checks the proof frame against it |
| `clip` | which clip it sits on (optional: taken from `t`) |
| `pad` | extra margin round a box, as a fraction of width (default 0.012) |

```json
{"type": "focus", "t": 2.2, "d": 1.6, "target": "export", "what": "Export button"}
{"type": "arrow",  "t": 4.5, "d": 2,   "box": [0.58, 0.40, 0.14, 0.08], "what": "boss health bar", "color": "yellow"}
```

### Web apps: measure the element

Add a `target` step where the element is on screen, then use the name in the plan:

```json
{"target": "export", "sel": "text=Export report", "pad": 6}
```

`sel` is a CSS selector or `text=...` (same as `click`). The step records the element's box and the time; it appears as `targets` in the recording's entry. The element must be visible (scroll first); a target that isn't is skipped with a message. A target is tied to the moment it was measured: use it on a span of the clip that covers that time, since pages move (the render drops it otherwise, or pass `any_time: true` when the page is static).

### Games and anything else: read a box off a grid sheet

1. `clip.py sheet <rec> --grid --times <t>` at the moment you'll highlight.
2. Read the left, top, right, bottom of the thing in tenths and write `box: [left, top, right-left, bottom-top]`.
3. Render, then **open the proof sheet** (below). If it's off, fix the box and re-render.

## What the render does with it

- Maps the box through the clip's real framing (`cover` + focus, `track`, `blurpad`, `float`, `contain`, static `zoom`, `mirror`).
- **Waits for the camera**: if a `track` glide is moving at `t`, the highlight starts when the camera has settled (and says so in `overlay_notes`). It needs about 0.8 s of steady camera.
- **Drops it** (`overlay_notes`, one line each, with the reason) when the target is outside the frame, the camera never holds, or the clip uses `stack`/`crop`, `zoomin`/`zoomout` or `shake`. Fixes: aim the camera at it (`focus`, or a `track` that ends on it), split the clip, or choose a steadier moment.
- Writes **`proof`**: a sheet with one frame per highlight, from the finished video (`temp/<project>/proof/<id>.jpg`). Open it. Each highlight must sit on the thing named in its `what`. A highlight that is missing from the proof was dropped: read `overlay_notes`.

Hand-placed `x, y` overlays still work, but `check` fails them (`overlay:`) unless you set `"verified": true` after the proof sheet showed them on target.

## Pick the highlight

Match the highlight to the target. Using the same one every time (always a ring) is the tell of a template.

| the target is | use | why |
|---|---|---|
| a button, field, card, panel, tile | `box` (outline) or `focus` (dim everything else) | rectangles follow UI shapes; a small error still reads as correct |
| a line of text, a number, a label | `marker` (highlighter swipe) or `bar` (clean underline) | covers the text without hiding it |
| one busy area on a dense screen | `focus` | quiets everything around it; best for tutorials and YouTube |
| a small thing in a big frame (a sprite, an icon, a cursor spot) | `arrow` (tip on the thing), or a static `zoom:1.5@x,y` | an arrow needs only a point; zoom needs no overlay at all |
| a game object or enemy | `ring` at its centre (creator mode), or an `arrow` | round things take a ring; keep it to one per video |
| a before/after verdict | `x` and `check` | big, centred, no precision needed |
| a hard-to-place or moving thing | **nothing**, or a camera move (`track` ending on it) | no highlight beats a wrong one |

Pro mode: `box`, `bar`, `marker`, `focus`, straight `arrow`. No `ring`, `scribble`, `arrow-curved`. Creator mode: anything, but vary it across a batch and within a video.

## Budget and timing

- 1 to 2 highlights in a 15 s TikTok, 1 per section in a YouTube video. They mark a caption's subject: start it with the caption (or 0.1 s after), keep it 1.2 to 2.5 s, end before the cut.
- A highlight on a clip that is moving constantly (fast camera, scrolling) is dropped by the render. Highlight on holds.
- Pair it with one sound at most (`pop-soft`/`ui-click` for pro, `ding`/`pop` for creator), or none.

## Types

| type | needs | looks like |
|---|---|---|
| `box` | `box`/`target` | rounded outline with a faint tint, fades in and out |
| `marker` | `box`/`target` | translucent highlighter over the text |
| `bar` | `box`/`target` | clean rounded underline as wide as the target |
| `focus` | `box`/`target` | frame dimmed except a rounded window with a thin edge |
| `arrow`, `arrow-curved` | `box`/`target`/`at` | the tip touches the target (a box: its nearest edge); picks a direction that stays in frame unless you give `angle` |
| `ring`, `scribble` | `box`/`target`/`at` | circle round the target (`r` to override) |
| `underline` | `box`/`target`/`at` | the hand-drawn underline png |
| `spotlight` | `box`/`target`/`at` | dims everything but a circle |
| `x`, `check` | `x`, `y` | big wrong/right marks, not precision pointers |

`color`: `yellow` `red` `green` `white` `blue` `orange` `pink`, or `#RRGGBB` (rect types). Pro: use the brand accent hex or white.
