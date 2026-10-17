# Music

Put **music you're allowed to use on YouTube** here, then index it:

    python ../../scripts/assets.py add path/to/track.mp3 --type music --name lofi-rainy --moods chill --themes devlog,background --source "YouTube Audio Library (no attribution)"

Good sources: YouTube Studio → Audio Library (free, cleared for YouTube; some tracks need attribution, so put that in `--source` and the plan's description), your own tracks, or your game's own soundtrack.

Meme music (myinstants) lives here too, as short copyrighted loops for quiet TikTok beds: `python ../../scripts/sfx.py seed-music` downloads the starter set and `sfx.py get "<name>" --kind music` adds more. Their index entries say so in `license`. Keep them off YouTube. Don't add other popular songs. On TikTok, also add a trending sound in-app (`sound_note` in the plan). See `references/music-audio.md`.

Each entry's `source` should say the license and any attribution line, so descriptions can credit it.
