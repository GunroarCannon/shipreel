# Channel rules: faceless, voiceless, not "low effort"

Faceless dev channels work. Footage of a real product the user built is original by nature. The risk is looking **mass-produced**: YouTube's "inauthentic content" (formerly "repetitious content") rule in the Partner Program, TikTok's "unoriginal / low-quality content" ineligibility for For You, and Instagram's "unoriginal content" demotion. All of them target templated, near-duplicate, low-transformation uploads. These rules keep each video clearly original and edited by a person.

## Every video

- **Real footage of the user's own project** is the main content (≥60% of runtime). Memes, cards and stickers are seasoning.
- **A distinct idea.** Different feature, angle, era or story from every other video of the same project. Same recording is OK, but use a different span or a different angle on it. The writer checks `ledger --titles` and `rec` usage.
- **Visible editing**: cuts on beats, a zoom or crop on the point of interest, captions written for this video, at least one effect or overlay that serves the idea. Raw 30 s screen recording + caption = low effort.
- **No dead air.** No frame frozen > 3 s unless intentional (`probe` → `static_spans`), no loading screens or blank pages (speed them up or cut them), no idle cursor.
- **No watermark** from another app; no TikTok-downloaded clips re-uploaded to YouTube. The render's output is clean; keep it that way.
- **Text carries it.** Voiceless means captions + header must tell the story muted. Don't use TTS voices (that's the most flagged faceless pattern) unless the user explicitly asks.
- **Honest.** Clickbait = curiosity, never a false claim about what the product does. "Fake it" recordings (mock data, staged demo) show real UI; never present unbuilt features as working.

## Across a batch / the channel

- Rotate caption presets, hook types and lengths (`check` warns on sameness).
- Vary structure: some single-shot satisfying loops, some stories with 4 to 6 cuts, some before/after, some POV.
- Avoid formula titles ("Day X of..." in every video). A series header is fine for a few in a row, but not all ten.
- YouTube long-form: a narrative (problem → attempts → result), chapters, new footage or new framing. Never a stitched compilation of the TikToks.
- Same recording in max 3 videos per project, and never the same span twice in one pass.
- Post cadence and scheduling are the user's call; the skill only produces files.

## Shorts and TikTok specifics

- TikTok: 10 to 30 s (`LIMITS`), first frame = action, loopable endings are a bonus. No "follow for more".
- YouTube Shorts: the same TikTok files work (≤60 s); the end card can say "full devlog on my channel" once a related long-form exists.
- Keep the `textless/` versions: they're the source for re-cuts, other languages and other platforms, and a defense if a platform asks for proof of originality.

## Memes and third-party material

- Reaction memes as short (1 to 2 s) transformative inserts are standard on these platforms, but not risk-free. Stay `rating: clean` or `mild`; `nsfw`-flagged items never ship.
- No movie or TV clips, no copyrighted songs, no other creators' videos.
- GIFs from GIPHY/KLIPY/Tenor are fine within their terms as short reaction inserts.
