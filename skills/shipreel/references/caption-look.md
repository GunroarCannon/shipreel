# Caption look: what native TikTok text looks like

Captions that look like TikTok's own text tools get read; heavy, glowing, clashing text reads as an ad or a template. The reference looks are TikTok's **Classic** (white text, thin black outline, one yellow accent line) and **Background** (black text in a white box).

## The two looks that read as a person made them (default for dev and game content)

- **`bubble`**: the "could you be a homie and press a few buttons" look. Rounded bold face (Fredoka Bold, about 10% of the frame width), white fill, thick near-black outline, soft drop shadow, mid-frame (`mid`, or `cap` at 40% from the bottom), centred, 2 to 4 short lines. One accent word in blue via `*word*` ("a *ROBLOX* developer"). Written in a human voice, like something said out loud. The thick outline keeps it readable on any footage, so auto-contrast never puts a plate behind it.
- **`chip`**: the "cool sticks." look. A small translucent light-grey rounded box with dark bold lowercase text (Nunito ExtraBold), low in the frame. Use it as a tag or a deadpan aside ("sept 5", "oct 12", "wrecked."): `style: "chip"` on a caption works inside a video of any preset, and `chip` as the video preset makes every caption a chip.

Pair them: the big `bubble` line says the thing, the `chip` labels the moment. Footage runs full-bleed under both (SKILL.md, "Frame for portrait, full-bleed").

## The rules

1. **Weight and size**: semibold, not black. About 7 to 8% of the frame width (`pop` is 82 px on a 1080 frame). Two lines max, 3 to 7 words per line, centred, balanced lines. If it needs three lines, cut words.
2. **Outline**: thin and crisp (about 5 px at 1080), pure black, no glow, no blurry shadow. The outline carries legibility, so don't thicken it to fake contrast.
3. **Colour**: white by default. **One** accent colour per caption: yellow (`#FFE600`). Highlight the single word or line that matters (`"it took *3 rewrites*"`, or a second line `\n*#10: 4.2 million views*`). Never a rainbow, never two accents, never pink/green/cyan text over footage of the same hue.
4. **Boxes**: on busy, detailed or mid-tone footage use `label` (black text, white box) or the `box` caption style. Boxes stay readable on anything; outlined text doesn't. Boxes are drawn as rounded rectangles, one per line (like TikTok's own), never square.
5. **Placement**: the middle-to-lower third, above the bottom UI. Don't sit on the subject or the thing the caption names; move with `x,y` or pick a quieter region. A header (`header`) and a `hook` never share a spot (the hook drops under the header automatically).
6. **One thing at a time**: don't show two captions of the same style at once. Stack lines in one caption instead (`check` flags overlaps).
7. **Mixed case** reads human. All caps only for presets that are built for it (`hormozi`, `meme`, `comic`, `cinema`).
8. **Same look across a video**; vary the preset between videos, not inside one.

## What shipreel does for you

- `bubble` and `chip` are the game-dev-TikTok looks above; `pop` is the Classic look; `label` is the Background look; `punch` is the old extra-heavy style for a loud moment.
- **Auto-contrast** (on by default): at render it samples the real footage behind each `hook`/`cap`/`mid` caption. Busy → dark plate; accent or tinted text that matches the background → white or a colour that doesn't. Look at `contrast_fixed` in the render result: if it fixes a lot, the footage is busy at that spot, so move the caption (`x,y`) or use `label` for the video.
- It can't judge taste. The reviewer still opens the final's sheet and checks the text is readable at phone size, not under UI, and not fighting the background.

## Reviewer checklist for captions

- Readable in the sheet thumbnail without squinting?
- Outline thin and black, not a glow or a thick blob?
- At most one accent colour, and it contrasts with what's behind it?
- Two lines or fewer, centred, not covering the subject?
- Anything colourful over a same-colour background? → `label`/`box`, or white text.
