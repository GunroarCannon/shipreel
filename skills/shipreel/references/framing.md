# Framing: fill the frame, aim at the action

The output shape is fixed (9:16 TikTok, 16:9 YouTube, 1:1 square); the source can be any shape. Framing is choosing what part of the source ends up on screen. Two rules decide it:

1. **Fill the frame.** A native video uses the whole screen. A thin strip floating in bars looks like a screen recording someone forgot to edit.
2. **Aim at the action.** When the source is wider (or taller) than the frame, the crop must sit on what's happening, not the dead centre.

`fit: "auto"` (what you get when you leave `fit` out) applies both, by source shape. Override only when the sheet shows a miss.

## What auto does, by source and output

`r` = source aspect ÷ output aspect. `r` near 1 = same shape.

| source | output | r | auto picks | why |
|---|---|---|---|---|
| phone portrait recording (1080x1920, 1080x2400) | TikTok / Shorts / Reels | ~1 | `cover` | same shape: fill it edge to edge, at most a sliver (status bar) is cropped |
| landscape 16:9 (game, desktop, 1280x720) | TikTok | 3.2 | `cover` + auto focus; `track: "auto"` on clips ≥ 2.5 s if scaffolded | a 9:16 window keeps 32% of the width: it must sit on the action |
| phone landscape (2408x1080, 2.2:1) | TikTok | 3.9 | `cover` + auto focus / track | even narrower window (25%): `track: "auto"` follows the action |
| 4:3 or square (1:1) | TikTok | 1.8 to 2.4 | `cover` + auto focus | keeps 42 to 56% of the width |
| landscape web UI (`record-web` landscape) | TikTok | 3.2 | `blurpad` (creator) / `float` (pro) | a UI needs its whole width; better: record it `--portrait` |
| landscape | YouTube / X / landscape | 1 | `cover` | same shape |
| phone portrait | YouTube / X | 0.32 | `float` (pro) / `blurpad` | a phone cropped to 16:9 loses 68% of it: show the whole phone over a blur of itself |
| anything | square | varies | same rules | |
| image / meme | any | not ~1 | `blurpad` / `float` | the whole image, over its own blur |

## The `fit` values

| fit | what it does | use for |
|---|---|---|
| `auto` (default) | the table above | almost always |
| `cover` | scale to fill, crop the rest at `focus` | same-shape sources; action you've aimed with `focus`/`track` |
| `stack` | portrait only: a blurred strip under TikTok's tabs, the **whole** landscape shot (with a thin divider), and a **close-up** of the action filling the rest | strategy, RTS, sports, "watch the whole map and the fight": both matter |
| `float[:s]` | the whole source as a rounded card with a soft shadow over a darkened blur of itself, scaled to `s` of the frame (default 0.86) | pro: phone recordings in landscape, UI screens, screenshots |
| `blurpad[:z]` | the whole source over a blur of itself; `z` > 1 enlarges the sharp copy (crops its sides) so less blur shows | creator: UI screens, memes, images |
| `contain` | the whole source with black bars | almost never (looks unedited) |
| `crop:x,y,w,h` | cut a region first (fractions), then cover | a fixed panel: the minimap, a code editor pane |

## Aim: `focus` and `track`

- `focus: [x, y]`: where the crop window sits (0 = left/top edge, 1 = right/bottom edge). `focus: "auto"` (or no focus) on a cropped `cover`/`stack` = **auto focus**.
- `track: [{t, x, y, move}, ...]`: a moving camera; x,y = the point to centre on, as fractions of the source. `track: "auto"` = **auto track**: a follow-cam.
- **How auto works.** shipreel watches the clip's span at low resolution and slides the crop window to where the most motion is. If almost nothing moves, it aims at the most detail (edges, text). If motion is spread evenly (a camera pan, a full-screen effect), it stays centred. Auto track does this per second and only moves when the action really moved (a median, so one-second blips don't jerk the camera), gliding 0.6 s.
- **What it gets wrong.** A flickering HUD number, rain or particles can pull the aim; a teleport mid-clip leaves the camera behind for a moment. Read the render result's `framing` (`{"clip": 0, "fit": "cover", "focus": [0.91, 0.5], "aim": "motion"}`) and the sheet. If it missed, set `focus` from `C sheet <rec> --grid` by hand.
- **`moments` tells you up front.** `C moments <rec> --project <p> --format tiktok` returns each strong span with the `focus` auto would use.
- A `track` needs a source bigger than the window (it replaces `fit`). `zoom` (≥ 1) tightens the window for a closer shot.

## Captions and the frame

- Portrait: captions stay inside y 0.12 to 0.70 and x ≤ 0.80 (TikTok's tabs on top, the caption and buttons at the bottom and right). The styles already do.
- `stack`: the caption sits on the close-up, under the divider. Don't put text on the overview strip.
- `float`: captions go over the blur, not the card, when they can (`x`, `y`), so the UI stays readable.
- Landscape: `lower` thirds bottom-left, `hook`/`title` centred; keep text out of the bottom 8%.
- A caption must not cover the thing it names: move it (`x`, `y`) or use `hook` (top) instead of `cap`.

## Checks

`check` prints `framing:` notes: a centre `cover` that keeps a third of a wide source with no aim, a tall source cropped into a wide frame, gameplay in a strip with bars, and a same-shape source letterboxed for nothing. After render, open the final's sheet: the subject must be in frame and at least about a quarter of the frame tall.
