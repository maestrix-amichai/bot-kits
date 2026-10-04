# scenes.json reference

```jsonc
{
  "name": "myfilm",                 // output name: out/myfilm.mp4, out/myfilm.storyboard.md (default: folder name)
  "size": [1920, 1080],             // [1080, 1920] for vertical
  "fps": 30,
  "xfade": 0.4,                     // seconds each transition overlaps the previous scene
  "transition": "fade",             // any ffmpeg xfade name: fade, dissolve, fadeblack, wipeleft, slideleft, ...
  "bg": "#0d0d10",                  // letterbox colour
  "caption": { "size": 52, "y": 0.80, "fg": "#ffffff", "bg": "#0d0d10dc" },   // one style for every caption
  "out": "myfilm.mp4",              // optional output file name
  "audio_tracks": [ { "file": "work/vo.wav", "at": 0.0, "gain": 1.0 } ],      // absolute film time
  "music": { "file": "work/bed.mp3", "gain": 0.15 },                          // looped, faded out over the last 2 s
  "scenes": [ ... ]
}
```
Asset paths resolve relative to the spec's folder, then the kit root, then `work/`.

## Scene fields common to all kinds
`id` (letters, digits, `_`, `-`; unique), `kind`, `dur` (seconds), and optionally:
- `caps`: `[["text", fade_in_s, show_s], ...]` or `[{"text","in","show"}]`. Captions are lower-third pills.
  Leave 0.45 s between one caption's end (`in + show`) and the next one's `in`; the compositor warns if they overlap.
- `caps_from` (+ `caps_offset`): a transcript JSON from `gemini_transcribe.py`; one pill per phrase, timed to it.
- `capy`: caption vertical position for this scene (fraction of height).
- `xin`: transition INTO this scene (`"cut"` for a near-hard cut, or an xfade name). `xf`: its length.
- `tracks`: extra audio for this scene, `[{"file","offset","gain"}]` (offset from the scene start).
- `act`, `note`: free text for the storyboard only.

## Kinds
| kind | fields | what it is |
|---|---|---|
| `card` | `bg`, `lines: [{text,size,y,in,show,color}]` | text on a solid colour; `y` is the vertical centre as a fraction |
| `still` | `asset` | image, cover-cropped to the frame, static (no Ken Burns) |
| `clip` | `asset`, `start`, `speed` | video, fitted (letterboxed) into the frame; holds its last frame if shorter than `dur` |
| `fill` | `asset`, `start`, `speed` | video, cover-cropped to fill the frame (dashboards, phone captures) |
| `raw` | `asset`, `start` | pass-through video with no captions (logo stings, finished clips) |
| `waveform` | `audio`, `title`, `subtitle`, `color`, `bg`/`bg_asset`, `audio_offset`, `gain` | a call or voiceover: live waveform, title, transcript pills; its audio is mixed in automatically |
| `split` | `left`, `right`, `labels`, `start:[l,r]` | side by side (BEFORE / AFTER), each half cover-cropped |

## Iterating
- `--only id1,id2` renders just those segments (prints their paths).
- Segments are cached in `work/seg/<name>/` by a hash of the scene, its assets and the caption style.
- `--review` writes `out/<name>_review/` with one frame per scene and `contact.png`.
