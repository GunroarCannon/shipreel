# Music

Put **music you're allowed to use on YouTube** here, then index it:

    python ../../scripts/assets.py add path/to/track.mp3 --type music --name lofi-rainy --moods chill --themes devlog,background --source "YouTube Audio Library (no attribution)"

Good sources: YouTube Studio → Audio Library (free, cleared for YouTube; some tracks need attribution, so put that in `--source` and the plan's description), your own tracks, or your game's own soundtrack.

Don't add popular songs or TikTok trending sounds. On TikTok, add sounds in-app (`sound_note` in the plan). See `references/music-audio.md`.

Each entry's `source` should say the license and any attribution line, so descriptions can credit it.
