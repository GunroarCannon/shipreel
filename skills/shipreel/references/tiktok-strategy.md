# TikTok strategy: what the algorithm rewards, adapted for shipreel

Imported from a TikTok content-strategy skill, then adapted. shipreel makes faceless, voiceless dev videos for the user's own projects, so "app downloads" becomes "people try / follow / wishlist the project". Voice, titles, hooks and hashtags live in `copy-rules.md`; this file is the *why* and the structure. Where the two disagree, `copy-rules.md` and `channel-rules.md` win.

Core formula: **hook (3 s) + value + one soft call to action**, built for completion rate.

## 1. The 3-second hook

The first 3 seconds decide everything. Patterns that work (each maps to a `hook_type` in the plan):

| pattern | example for a dev channel |
|---|---|
| problem / pain | "my game crashed on level 1 for 3 weeks" |
| shocking number | "this bug cost me 40 hours" |
| pattern interrupt | "stop making your menu first" |
| quick win | "a lava shader in 60 seconds" |
| relatable POV | "POV: it works on your machine" |

Hook mistakes: slow intro ("hey guys, today..."), logo or branding first, text-heavy slides, "wait for it". Frame 1 must already be the most interesting frame (see the writer role).

## 2. Structure (15 to 30 s)

| time | beat | for a dev video |
|---|---|---|
| 0 to 3 s | hook | the strangest / best frame + hook caption |
| 3 to 10 s | problem | what was broken, hard or funny |
| 10 to 20 s | solution | the fix / feature working **on screen** (look at the sheet) |
| 20 to 25 s | proof | a number, a before/after, the result. Real ones only |
| 25 to 30 s | soft CTA or loop | "full devlog on my channel", or a line that loops back to the hook |

Length: 15 to 30 s has the best completion rate; 30 to 60 s for tutorials; 60 to 90 s only for a story with strong retention. 90% completion of a short clip beats 50% of a long one.

## 3. Sounds

Trending sounds help reach, but only when added **in TikTok's sound picker**. Burned-in sound is a different tool: shipreel's `music` field puts a quiet meme track under the video (`music-audio.md`). Use both ideas this way:
- `sound_note` tells the user which trending sound to add in-app (match the energy; prefer sounds early in their trend, under ~50k uses; skip ones over ~1M).
- A burned-in meme bed from `assets.py find --type music` is the fallback and works for the textless re-cut too.

## 4. Content pillars (mix across a batch)

| pillar | share | dev-channel version |
|---|---|---|
| problem to solution | ~50% | the bug, the fix; the slow thing, the fast thing |
| proof | ~20% | real numbers, before/after builds, real milestones. Never invent a testimonial or a stat |
| education | ~20% | one trick, "did you know", how a feature works |
| trend / entertainment | ~10% | meme formats, relatable dev humour |

## 5. Viral patterns

1. **Transformation**: day 1 vs day 30, old build vs new. Two sides must *look* different (SKILL.md "Comparisons look different").
2. **Secret hack**: "the setting nobody finds", a hidden feature. Show it in under 10 s.
3. **Relatable struggle**: "things only solo devs understand", a list, each item with its own clip.
4. **Tutorial**: "how to X in under 60 seconds". Fast, clear, one thing.
5. **Series / challenge**: "day 47 of making a roguelike" as the persistent `header`. Each video still stands alone.

## 6. What the algorithm prioritises

1. **Completion rate**: short, strong hook, no dead time (the `check` and probe catch static spans).
2. **Engagement**: a question in the description, a take people can disagree with. Never engagement bait ("like if...").
3. **Rewatches**: dense or looping videos; put the payoff late so a second watch finds more.
4. **Shares**: relatable or useful ("send this to your co-dev").
5. **Watch time** per view, not raw length.

## 7. Calls to action

Good: "link in bio", "full devlog on my channel", "comment 'GAME' and I'll send the link" (only if the user will actually reply). Bad: long URLs in the caption, "click the link in bio" with no reason, pushy sales language. Links and mentions follow `copy-rules.md` and `config.links`.

## 8. Posting and analytics (for the notes the user gets)

- Frequency: 3 to 5 a week minimum, 1 to 2 a day best, 3 a day max. Shipreel batches ten, so tell the user to spread them out.
- Times (ET): 6 to 9 AM, 12 to 1 PM, 7 to 9 PM. Their own analytics beat this: try different slots, double down on winners.
- Track: views, completion (>50%), engagement (>5%), profile visits (>2%), link clicks. Feed what worked back into `state note` ("hook type X got the best completion") so the next pass leans on it.
- Quick wins: keywords in the on-screen text and description (TikTok search), stitch or duet with a trending creator in the niche, behind-the-scenes and sneak peeks (this is the whole channel).

## Where this clashes with shipreel (don't copy blindly)

- Hashtags: the source suggests `#fyp #foryou`. shipreel bans them (`check` fails them); use 3 to 5 niche tags.
- Testimonials and "results": only real ones from the project. No made-up quotes, users or numbers.
- Creator collaboration, paid posts and posting-calendar scheduling are the user's job, not the pipeline's. Mention them in the final report only if relevant.
- App-store CTAs: replace with whatever the project actually has (itch page, repo, site, wishlist) from the shorthand.
