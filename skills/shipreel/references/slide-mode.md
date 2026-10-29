# Slide Mode: Viral Photo Slideshows & Swipe Carousels

Creator mode makes dev-channel video TikToks with memes and sound effects; Pro mode makes polished SaaS/product launch clips. **Slide mode** creates high-converting, viral photo slideshows and swipe carousels (TikTok Photo Mode, Instagram Carousels, and auto-playing portrait slideshow videos).

Based on empirical studies of 500+ viral slideshow pages generating hundreds of millions of views, slideshows are the single most automatable, high-ROI format for driving app downloads, software adoption, and niche followings.

---

## Rule 0: NEVER Blindly Copy the Case Study (Niche Adaptation Principle)

> [!CAUTION]
> **Do NOT copy-paste case study phrases or songs into unrelated niches.**
> Blindly using phrases like *"for your lazy ass"*, *"traumatise these men back"*, or audio like *"In the Mood - Glenn Miller"* for a 3D ragdoll war game, developer tool, or SaaS product is a failure of basic thinking. `clip.py check` will reject plans with case study mimicry.

### The Case Study Explained
The empirical case study analyzed two specific niche accounts:
1. **A food & recipe app page (488M views)**:
   - Hook: *"5 weeknight dinners for your lazy ass"* worked because after an exhausting 9-to-5 workday, cooking dinner is a hated chore. The casual insult validated the viewer's fatigue.
   - Audio: *"In the Mood"* (Glenn Miller, 1940s big-band swing) worked because vintage swing creates a cozy, warm, nostalgic aesthetic that pairs naturally with simmering skillets and comfort food.
2. **A dating app page (PURE)**:
   - Hook: *"Sometimes you just gotta traumatise these men back"* worked because cringe dating app messages are a universal venting topic for young singles. The hook forced a swipe to read the unhinged screenshot reply.

### The Universal Formulas (To Adapt to YOUR Niche)
Instead of copying the words, copy the **underlying structure**:
- **Target Callout Formula**: `[High-Value Promise / Number] for [Specific Target Persona / Relatable Pain Point]`
- **Forced-Swipe Curiosity Gap Formula**: `[Unbelievable Scenario / Unhinged Experiment / Boundary-Pushing Twist] -> Swipe to see what happened`
- **Niche-Native Audio Formula**: Outlier audio must match the **emotional vibe** and **cultural expectations** of the target community.

---

### The Niche Audio & Hook Matrix

| Niche / Genre | Target Persona & Fantasy | Slide 1 Hook Formulas (Adapted) | Audio Vibe & Sound Multipliers |
|---|---|---|---|
| **Action / Sandbox / Physics Games** *(e.g. Stickbox 3D)* | Gamers who love ragdoll physics, sandbox chaos, or miss 2000s Flash games | • *"what happens when you give 500 stickmen real 3D ragdoll physics"*<br>• *"building the physics engine unity told me was impossible"*<br>• *"5 sandbox weapons that crash my physics engine"* | **Gaming Phonk, High-Energy Chiptune, Chaos Meme OST**<br>• Megalovania / Undertale remixes<br>• Kordhell / phonk bass drops<br>• *Crab Rave* / comedic speedrun themes |
| **Dev Tools / Open Source / CLI** | Developers seeking speed, automation, and terminal minimalism | • *"5 terminal CLI tools for devs who hate clicking"*<br>• *"why 90% of engineers configure git completely wrong"*<br>• *"the 1-file automation that replaced my 4-person deploy team"* | **Lo-fi Chill, Clean Tech Synth Pulse**<br>• `music:cool-chill-lofi`<br>• Minimalist ambient electronic beats<br>• Synthwave pulse (muffled low-pass) |
| **B2B SaaS / Productivity Apps** | Solopreneurs, freelancers, students drowning in disorganization | • *"the exact dashboard that replaced 5 monthly subscriptions"*<br>• *"if you can't focus for 20 minutes straight, build this system"*<br>• *"how solo founders track 10k users without hiring"* | **Polished Upbeat Electronic, Minimal Bounce**<br>• Modern clean synth pads<br>• Light melodic house<br>• Trending productivity aesthetic sounds |
| **Food & Cooking Apps** | Busy professionals, budget meal preppers, home cooks | • *"5 weeknight dinners for your lazy ass"*<br>• *"meals to make for your husband this week (with recipe)"*<br>• *"high protein meal prep under 15 minutes"* | **Cozy Vintage Swing, Acoustic Jazz**<br>• Glenn Miller - *In the Mood*<br>• *Dinner Is Served*<br>• Warm acoustic guitar & kitchen beats |
| **Dating & Social Apps** | Young singles navigating modern relationship chaos | • *"sometimes you just gotta traumatise these men back"*<br>• *"pov: he thought you wouldn't find his secret profile"*<br>• *"the 3 red flags you should screenshot immediately"* | **Sassy Alt-Pop, Moody Trap Beats, Trending Dialogue**<br>• Fast hip-hop remixes<br>• Trending female alt-pop drops |

---

## Why Slideshows Win (The Economics)

- **Cost & Speed**: Traditional UGC video requires a creator to film, an editor to cut, and costs $15 to $25 per video. A slideshow needs just a few photos, a magnetic hook, and an app CTA.
- **Volume**: You can easily produce and publish 2 to 3 slideshows a day per page at near-zero marginal cost.
- **Conversion to Revenue**: Views don't pay bills—conversions do. Data shows **~5M views generates roughly $2,000 to $5,000 in app revenue**, depending on onboarding and funnel quality.
- **Dual Output**: `clip.py render` in slide mode produces **both**:
  1. An auto-playing **1080×1920 MP4 video** with crisp slide transitions, captions, and audio for TikTok/Reels/Shorts feeds.
  2. A directory of **native 1080×1920 PNG slides** (`output/<project>/slides/<video_name>/slide_{01..N}.png`) ready for native TikTok Photo Mode uploads.

---

## Golden Rule: Always Start With a Question (Buzz First)

Whenever you begin a slide-mode session or start planning a slideshow batch:

1. **Buzz first**:
   ```bash
   python S/scripts/buzz.py "shipreel: what winning page in your niche should we model?" -t 2
   ```
2. **Ask the user for the winning page/accounts in their niche**:
   Never guess formats in a vacuum. Start by asking the user to identify 1 to 3 accounts currently winning in their target niche.
3. **Equip the user with research tools**:
   - **ViewTrack** (Recommended): Analyzes 100s of posts on target pages to isolate outlier formats (e.g., formats averaging 6M views vs 1.4M page average) and identify sound multipliers.
   - **TikTok Creative Center / Trend Discovery**: Free official tool to discover trending songs, hashtags, and viral breakout formats by country and category.
   - **TokCount / Exolyt / Shoreditch**: Account and sound analytics tracking view distributions and follower conversion.
   - **TikTok Search with Filters**: Search niche keywords, filter by Date: "Last 3 months", Sort by: "Most liked" to reveal outlier hooks.
   - **Apify TikTok Scrapers**: Scrape competitor handles to compute median vs top-decile view counts.

From the top competitor page, find the **top 3 formats** that drive 80%+ of the views, their hook formulas, and their top sound tracks.

---

## The 5 Pillars of a Viral Slideshow

### 1. A Strong Hook on Slide 1 (The Swipe Decider)
The first slide is the **only thing people see** before deciding whether to swipe. If Slide 1 doesn't compel the swipe, nothing else gets seen.

- **Call out exactly who it's for**:
  Target a specific persona, their frustration, or their fantasy.
  - Gaming: *"for gamers who miss 2008 flash stick games"* or *"what happens when 1,000 stickmen fight 1 giant boss"*
  - Dev: *"5 terminal commands for developers who hate slow deploys"*
  - Fitness: *"5 ways to get abs with this lazy 5 minute workout"*
- **Create a curiosity gap that forces the swipe**:
  Make the first slide so intriguing or shocking that the viewer is physically compelled to swipe to Slide 2.
- **Once you find a winning hook structure, keep repeating it**:
  You do not need a brand new hook archetype every day. Winning pages reuse the exact same winning hook formula across dozens of posts with fresh body content.

### 2. Consistency: Stick to 1 Visual Character or Theme
Most creators fail because they grab random pictures off Pinterest or Unsplash; their profile feed ends up looking chaotic and untrustworthy, so nobody follows.

- **The Feed Consistency Rule**:
  Pick **1 visual theme, 1 recurring character, or 1 fixed template layout** and stick to it on every post:
  - **Stickbox 3D**: Hand-drawn stickmen on clean parchment/grid backgrounds with bold black-and-white silhouettes.
  - **Arise**: Same anime hero with *"we built a leveling system in real life"* on every cover.
  - **GoTall**: Same boxers and skeleton with a tape measure every time.
  - **Pure**: Same selfie girl + dark mode iMessage chat screenshot.
  - **Recipe page**: Same overhead stainless pan with centered bold white typography.
- **The Profile Conversion Test**:
  When a viewer clicks through to your profile from a viral slide, the grid must look like a cohesive, legitimate publication. Consistent visual identity turns 1-time viewers into followers and app users.

### 3. Repurpose Existing Content Into Slides
Never reinvent content from scratch when proven content already exists:
- Gameplay physics experiments, level showcases, code snippets, chat logs, bug fixes, and feature walk-throughs are ready-made slideshow content.
- **Standard 4-to-7 Slide Structure**:
  - **Slide 1 (Hook)**: Intriguing visual + target callout / curiosity gap.
  - **Slides 2 to N-1 (Value/Progression)**: Step-by-step demonstrations, escalating chaos, or features. Clean, high contrast, one point per slide.
  - **Slide N (Final Slide)**: Direct CTA showcasing your app/game (where to play/download).

### 4. The Sound Matters Enormously (10x View Multiplier)
Most people treat audio as a random afterthought in slideshows. In reality, **sound is a primary retention and viral multiplier**:
- People swipe through slides *just to keep listening to a trending or vibe-matching song*.
- **Rule**: When an audio track works in your niche, **keep using it repeatedly across your batch**.
- Include `sound_note` in your plan JSON to instruct the user which in-app trending track to select on TikTok, or burn an appropriate background track.

### 5. Conversion to Sales & App Downloads
Views don't pay the bills. The entire purpose of the slideshow engine is driving app installs and customers:
- **The Last Slide Must Be Your App/Product**:
  The final slide of every single slideshow must show your app UI, logo, and a direct value proposition/CTA (e.g. *"Play Stickbox free on itch.io - Link in bio"*).
- **Include the Full App Name in the Caption**:
  Especially when launching or before ranking #1 on App Stores or search engines, algorithms need the exact app name in the caption text. When viewers search for the app after seeing your slideshow, your app must appear.

---

## Slide Plan Schema (Multi-Niche Examples)

In slide mode, each clip in the plan represents a distinct slide.

### Example 1: Action Game (Stickbox 3D Ragdoll Simulator)
```json
{
  "project": "stickbox",
  "pass": 1,
  "mode": "slide",
  "videos": [
    {
      "id": "s01",
      "format": "tiktok",
      "style": "slide",
      "hook_type": "target-callout",
      "title": "what happens when you give 500 stickmen real 3D physics",
      "tags": ["gamedev", "indiegame", "godotengine", "ragdoll", "gaming"],
      "sound_note": "High-energy gaming phonk or chiptune battle OST (e.g. Megalovania / Kordhell style)",
      "music": {"asset": "music:crab-rave", "vol": 0.16, "duck": false},
      "description": "500 stickmen vs real Godot 3D physics engine. Play Stickbox free on itch.io!\n\nfull app: Stickbox 3D Game",
      "clips": [
        {
          "src": "rec:skirmish",
          "in": 1.0,
          "dur": 2.8,
          "caption": "what happens when you give 500 stickmen real 3D ragdoll physics"
        },
        {
          "src": "rec:physics",
          "in": 2.0,
          "dur": 2.8,
          "transition": "push",
          "caption": "1. full momentum transfer on impact"
        },
        {
          "src": "rec:explosions",
          "in": 3.0,
          "dur": 2.8,
          "transition": "push",
          "caption": "2. explosive blast radius with cartoon gore dial"
        },
        {
          "src": "rec:monsters",
          "in": 1.5,
          "dur": 2.8,
          "transition": "push",
          "caption": "3. procedural horde AI swarming giant bosses"
        },
        {
          "src": "rec:city",
          "in": 2.0,
          "dur": 3.2,
          "transition": "push",
          "caption": "clone Stickbox free on GitHub\n*link in bio to start building*"
        }
      ]
    }
  ]
}
```

### Example 2: Recipe / Food App
```json
{
  "project": "cookease",
  "pass": 1,
  "mode": "slide",
  "videos": [
    {
      "id": "s01",
      "format": "tiktok",
      "style": "slide",
      "hook_type": "target-callout",
      "title": "5 weeknight dinners for your lazy ass",
      "tags": ["recipes", "dinnerideas", "easycooking", "mealprep"],
      "sound_note": "In the Mood - Glenn Miller (or Dinner Is Served)",
      "description": "5 dinners you can make in 15 mins with CookEase. Get the app in bio!\n\nfull app: CookEase Recipe App",
      "clips": [
        {
          "src": "rec:dish-01-cover",
          "dur": 2.8,
          "caption": "5 weeknight dinners for your lazy ass\n*(with recipes)*"
        },
        {
          "src": "rec:dish-02-pasta",
          "dur": 2.6,
          "transition": "push",
          "caption": "1. 10-minute creamy garlic chicken pasta"
        },
        {
          "src": "rec:app-store-cta",
          "dur": 3.2,
          "transition": "push",
          "caption": "get all 5 recipes on CookEase\n*link in bio (free)*"
        }
      ]
    }
  ]
}
```

---

## Pace and Durations
- For the generated video, each slide displays for **2.5 to 3.2 seconds** (total video length: 12 to 20 seconds).
- Transition between slides: `push`, `whip`, `slide`, or crisp cut (simulating a horizontal swipe).
- For native TikTok Photo Mode, users swipe at their own pace; the rendered PNG images in `output/<project>/slides/<id>/` capture each slide at full 1080×1920 fidelity with captions burned in.

---

## What `clip.py check` Enforces in Slide Mode

Running `clip.py check <plan.json>` enforces these hard and soft rules for slide mode:

1. **Anti-Mimicry Linter**:
   - Rejects case study phrases (*"lazy ass"*, *"traumatise"*) on non-food / non-dating projects.
   - Rejects 1940s swing audio (*"In the Mood"*, *"Glenn Miller"*) on non-food projects.
2. **Slide Count**: Minimum 2 slides, recommended 4 to 7 slides. Warns if > 12 slides (swipe fatigue).
3. **Slide 1 Hook**: Fails if Slide 1 has no hook caption/text.
4. **Target Callout / Curiosity Gap**: Checks whether Slide 1 calls out who it's for or triggers curiosity.
5. **Last Slide App CTA**: Checks whether the final slide showcases the app/product with a CTA (`app`, `try`, `link`, `download`, `get it`, `github`, `itch.io`).
6. **Full App Name in Description**: Ensures the full application name is present in the description for search discoverability.
7. **Sound Recommendation**: Requires `sound_note` or `music` bed (audio is a 10x retention driver).
8. **Consistent Feed Style**: Uses the `"slide"` preset (Montserrat Bold with clean outline and soft shadow) or approved sans presets.

---

## Summary Checklist for Slide Mode
- [ ] Buzzed user and asked for winning competitor page in the niche.
- [ ] Researched top formats and sounds with ViewTrack / TikTok Creative Center.
- [ ] Selected hook formula and audio native to the project's niche (NO case study mimicry).
- [ ] Picked 1 consistent visual theme/character across the whole batch.
- [ ] Slide 1 hook calls out the exact target audience or forces a swipe.
- [ ] Repurposed content into 4-7 clean, high-contrast slides.
- [ ] Recommended a repeatable, niche-native high-retention audio track.
- [ ] Showcased the app/game on the last slide with a clear CTA.
- [ ] Included full app name in the caption for search indexing.
- [ ] Verified both MP4 video and native PNG slides in `output/<project>/slides/`.
