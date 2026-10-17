# Copy rules (titles, on-screen text, descriptions, hashtags)

Why hooks, structure, pillars and sounds work on TikTok: `tiktok-strategy.md`.

Distilled from the vendor skills `viral-hooks`, `viral-captions-and-ctas`, `viral-tiktok-content`, `viral-youtube-shorts`, `viral-short-form-ideas` and `tiktok-marketing` (humanizer and voice rules), adapted for faceless, voiceless dev content. These are patterns that tend to work, not guarantees.

## The voice

Write like a dev texting a friend about their project. Not like a brand, not like a press release, not like an AI.

- Specific beats clever: "3 rewrites", "47 fps → 144 fps", "day 212", "my 2014 laptop". Real numbers from the shorthand, never invented.
- Lowercase-casual is fine for TikTok on-screen text and titles. YouTube titles use sentence case. Product names always capitalized (Godot, Next.js, Supabase).
- Fragments are good. "no engine. no assets. one weekend."
- One idea per video.
- Self-deprecating > bragging. Struggle > success. "I thought this would take a day" beats "check out my amazing feature".
- Allowed and good: dev in-jokes, mild sarcasm, "it works on my machine".

### Never (clip.py check lints most of these)

- AI vocabulary: delve, leverage, utilize, seamless(ly), robust, elevate, unlock, unleash, harness, empower, streamline, comprehensive, transformative, cutting-edge, game-changer, landscape, realm, tapestry, journey, testament, crucial, furthermore, moreover, supercharge, next-level, effortlessly.
- AI shapes: "It's not just X, it's Y", "No X. No Y. Just Z." for rhythm, "The result?" reveals, "Here's the thing", "Let that sink in", stacked triplets ("faster, cleaner, smarter"), "In today's fast-paced world", "Ever wondered".
- More than 1 em dash per description; none on screen.
- Engagement bait: "follow for more", "like for part 2", "comment YES", "tag a friend", "smash that", "stay tuned". Using "part 2 is up" or "full devlog on my channel" instead is fine.
- Hype without proof: "insane", "mind-blowing", "you won't believe" (vague tease).
- Greetings, intros, "welcome back", logo stings.
- Emoji in burned-in text (stripped anyway). In descriptions: 0 to 2.

## Hooks (first 1 to 3 s)

Three layers at second 0: the **visual** (the most interesting frame first, cutting to the action), the **on-screen text** (3 to 7 words, `hook` style or `header`) and the **sound** (an SFX hit or product audio). The video is muted-first, so the text must carry the promise alone.

Archetypes. Rotate across a batch; label each video's `hook_type`:
- **contrarian**: "unity devs won't like this"
- **before-after / then-now**: "day 1 vs day 300"
- **number**: "1 line of code fixed 40 fps"
- **fail / bug**: "my enemies learned to fly. I didn't code that"
- **pov**: "pov: the physics finally works"
- **question**: "why does this only crash on Tuesdays"
- **flex (earned)**: "I made this in 48 hours". Only if it's true.
- **process / tutorial**: "how I made the water shader"
- **middle-of-action**: no text setup, the clip starts mid-explosion and the header carries the context
- **clickbait** (≤ `config.mix.clickbait_share`): a curiosity gap that the video pays off: "this bug made my game better". Clickbait means withholding the answer, never making a false claim. Same rule for thumbnails.

Bad hooks: setup sentences ("so I've been working on..."), vague teases, brand-first ("introducing X"), a hook that resolves after second 3.

## On-screen text

- Headline + body pattern: persistent `header` (TikTok's persistent caption: topic or series, e.g. "day 47 of making a roguelike") + timed `captions` for beats.
- 2 to 6 words per caption beat, ≤9 words max. One beat per 1.5 to 2.5 s. Text that sits longer than it takes to read → cut it.
- Don't repeat the header in the first caption. Don't narrate what the viewer can see ("here is the menu"). Add what they can't see: the why, the struggle, the number, the joke.
- Last beat: loop-back line, a payoff or a single soft CTA ("full devlog on my channel" on YouTube-linked accounts). No "thanks for watching".

## Titles = file names

- TikTok: 3 to 8 words; it's the caption's first line and the file name. Example: `the bug was a feature the whole time`.
- YouTube: 40 to 70 characters, sentence case, specific and searchable: "I rebuilt my game's core loop 3 times (here's what stuck)". Parentheses and a number help. No ALL CAPS words except one for emphasis at most.
- Check `clip.py ledger <p> --titles` and never reuse a title or its first 3 words in the same project.

## Descriptions (`description` → `<name>.txt`)

- **TikTok**: 1 to 3 short lines. Line 1 adds context the video doesn't say (it shows before "more", and TikTok indexes it). Optionally a real question with a stance ("which version would you ship?"). Then links, mentions, hashtags.
- **YouTube**: 2 to 4 sentences with the main keyword early (first 125 characters), chapters (auto-added), links, 3 to 5 hashtags.
- Don't echo the title or the hook text.
- Skip the description entirely (empty marker file) when the video speaks for itself and there's nothing to add. That's fine for some TikToks.

## Hashtags (`tags`)

3 to 5, niche first: one broad dev tag (`gamedev`, `webdev`, `indiedev`, `buildinpublic`, `programming`), one or two stack/genre tags (`godot`, `nextjs`, `roguelike`, `pixelart`) and one video-specific tag (`shaders`, `bugfix`, `devlog`). Never `fyp`, `foryou`, `viral` or `trending` (check fails them). The same tags appear in the file name; keep them short.

## Links and mentions

From `config.channel` and the shorthand:
- GitHub only if `public: yes` (verify with `git -C <repo> remote -v` + an HTTP 200 on the URL).
- Live site only if it returns 200 now (`curl -sI`).
- X/LinkedIn only if the user gave handles and said to link them.
- @mention tools or engines only when it's natural and they're featured ("made with @godotengine"); max 2. Mention other projects of the same channel only when they actually relate.
- Format: `play it: <url>`, `code: <url>`. Lowercase labels, no "🔗 Link below 👇".

## Batch variety (10 TikToks)

Different hook types (≥5 distinct), different features, ≥2 eras if the history has them, 2 fancy edits, 1 to 2 clickbait, 3 meme moments total across the batch, ≥3 caption presets, mixed lengths (some 10 to 15 s loops, some 20 to 30 s stories). Read the batch's titles together at the end: if they sound like one template, rewrite the worst 3.
