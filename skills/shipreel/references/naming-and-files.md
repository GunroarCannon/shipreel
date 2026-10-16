# Naming and files

## Video file name = title + hashtags

```
<title_words_with_underscores>_#tag1_#tag2_#tag3.mp4
<series>-part-<N>_<title_words>_#tags.mp4          (series only)
```

- Underscores between words. Dashes only for special markers (`-part-N`), and inside words that naturally have them.
- Characters illegal on Windows/macOS are dropped; the title keeps its case and punctuation otherwise (`?`, `:` are removed, `(` and `!` stay).
- Built by `common.video_name` (`clip.py name "title" --tags a,b` to preview). The writer never hand-writes file names.
- Every video is **standalone**. A series part still makes sense alone.

## Per video, in `output/<project>/`

| file | what |
|---|---|
| `<name>.mp4` | final: captions burned in (TikTok: persistent header + beats; YouTube: more overlays and lower thirds) |
| `textless/<name>.mp4` | the same edit without captions or text (overlays and effects stay) |
| `<name>.txt` | description, ready to paste: body, chapters, links, mentions, hashtags, then the posting note marked "not part of caption" |
| `<name>` (no extension, empty) | when there's no description: marks "intentionally none" |
| `<name>.jpg` | thumbnail, when the plan has `thumb` (always for YouTube) |
| `videos.csv` | ledger: id, date, pass, format, dur, title, tags, file, sources, hook, style, plan hash |

## Workspace layout

```
<workspace>/
  shipreel.config.json            questionnaire answers (overrides config/defaults.json)
  output/
    _state.json                   pass + current project + notes (resume point)
    <project>/ ...                deliverables only
  temp/
    _sheets/                      contact sheets (safe to delete)
    <project>/
      data.json                   recordings cache index: id → file, dur, size, feature, era, commit, marks
      .project-shorthand.txt      (unless kept in the repo)
      rec/<rec-id>.mp4            raw recordings, named by id, reused across passes
      seg/<hash>.mp4              normalized segments, content-hashed (cache; clean --segments)
      build/<video-id>/           per-render scratch (auto-removed)
      plans/p<pass>_<batch>.json  plans
      steps/<rec-id>.json         web steps / godot autoplay timelines
      wt/<sha>/                   git worktrees of old commits (clean --worktrees)
```

The cache names are deterministic: recordings by id, segments by the hash of (clip spec, size, fps, source mtime and size). Re-running a plan re-uses everything that didn't change, and the ledger skips unchanged videos.

## Disk

- Recordings: about 1 to 3 MB per 10 s at 1080p (x264 CRF 18 ultrafast for screen; veryfast for Godot).
- Segments are the biggest temp item; `clip.py clean <p> --segments` after each reviewed batch.
- Godot's MJPEG `.avi` is deleted right after conversion.
- `doctor` and `render` refuse to start below `limits.min_free_gb` / 2 (`NEED_DISK`).
