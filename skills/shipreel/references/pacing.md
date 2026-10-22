# Pacing: fast for short videos, slow for long ones

A 12-second TikTok and a 3-minute YouTube video are not the same edit at different lengths. Short videos live on momentum: a new picture every second or two, short captions, hard cuts. Long videos need room: shots that hold long enough to see what's happening, captions you can read without rushing, transitions that mark sections. shipreel makes this a number, not a feeling.

## The pace follows the length

`pace` on a video (or `config.pace`): `auto` (default), `fast`, `medium`, `slow`. `auto` picks by the edit's length (the clips added up, before transition overlaps):

| length | pace |
|---|---|
| ≤ 22 s | fast |
| 22 to 60 s | medium |
| > 60 s | slow |

Set it by hand only for a deliberate exception: a 15 s calm "satisfying" loop can be `medium`, a 45 s montage can be `fast`. Mode doesn't change the pace: a pro launch video can be fast too. Pro changes *which* transitions and sounds, not how often things happen.

## The numbers

| | fast | medium | slow |
|---|---|---|---|
| shot length: min / average / max | 0.6 / 1.8 / 3.2 s | 1.0 / 3.0 / 5.5 s | 1.5 / 5.0 / 10 s |
| a shot with `track` or `zoomin` may run | 4.8 s | 8.2 s | 15 s |
| longest stretch with nothing new | 2.5 s | 4 s | 8 s |
| first cut (or camera move) by | 3 s | 4.5 s | 8 s |
| caption reading speed | 3.6 words/s | 3.0 words/s | 2.5 words/s |
| shortest caption | 0.9 s | 1.2 s | 1.8 s |
| words per caption (max) | 6 | 8 | 12 |
| default transition length | 0.22 s | 0.4 s | 0.7 s |
| `words: true` group size | 2 | 3 | 4 |
| caption entrance | pop | pop | fade |

Reading time = 0.4 s + words ÷ reading speed, never under the shortest caption. "the boss has 3 phases" (5 words) needs 1.8 s fast, 2.1 s medium, 2.4 s slow.

## What render does with the pace

- A caption without `d` stays up exactly its reading time.
- A transition without `transition_dur` gets the pace's length. Whips, flashes and glitches stay short (≤ 0.22 s) at any pace, and a default that's too long for a short clip shrinks to fit.
- `words: true` groups words by the pace's group size.
- Slow pace fades captions in instead of popping them.
- The render result prints `"pace"`.

## What check enforces

`check` prints `fast/creator` (pace/mode) on every video line. It adds:

- `pace!:` (hard, exit 1): a shot more than twice the max, or a caption up for less than 60% of its reading time. These are always wrong.
- `pace:` (soft): a shot over the max, a flicker shot under the min in the middle of the video, a first cut later than the pace allows, a caption a bit short or too wordy, and the longest stretch with nothing new. Fix them unless you can write down why not.

| message | fix |
|---|---|
| `clips[2] runs 6.2s (> 3.2s for fast)` | split it: two clips of the same recording with different `focus` (one on the player, one on the enemies); or `track: "auto"`; or trim; or `speed: 2` on the boring half |
| `nothing new from 8.0s to 13.5s` | put a cut, a caption, a `zoomin`, an SFX or an overlay in that gap |
| `caption '...' is up 0.8s but 7 words need 2.3s` | cut words first ("the boss has three different phases" → "3 boss phases"), then raise `d` |
| `first cut at 4.1s` | open on a shorter span of the best moment, or start a `track` glide in the first clip |
| `clips[3] is 0.4s, a flicker` | lengthen it to the min, or drop it |

## Rhythm per pace

**Fast (TikTok 10 to 22 s).** 0 s: the best frame plus a 3 to 6 word hook and a sound hit. Then a new shot every 1 to 2 s, something marked (SFX, zoom, arrow) every 2 to 3 s, one transition at most (a whip or flash on the turn). The last 1 to 2 s: the payoff, or a frame that loops back to the first.

**Medium (TikTok 22 to 60 s, X, short YouTube).** A hook in 2 s, then 3 to 5 beats of 4 to 8 s each, every beat with a caption and one marked moment. Transitions at the 1 or 2 turns of the story. Progress bar on TikToks over 20 s.

**Slow (YouTube 1 to 5 min).** Sections of 20 to 60 s, each opening with a `lower` third or a section title, with chapters at those points. Shots hold 3 to 8 s, with `track` or `zoomin` keeping long shots alive. One marked moment per 8 to 10 s. `dissolve` or `dip` between sections, hard cuts inside them. `fadein` at the start and `fadeout` at the end are fine here.

## Music and pace

Pick the bed by tempo too: fast videos get driving tracks (crab-rave, phonk, soft-pulse), slow ones calm beds (wii-shop, ambient-pad, lofi). Cuts that land on the beat feel twice as tight: put the important cuts on a beat if the track has a clear one. Don't stretch a fast track under a slow devlog.
