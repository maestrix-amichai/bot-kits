# Lessons from building films with this pipeline

Hard-won, in the order you will hit them. Most cost real money or hours to learn.

## Structure
- **The spec is the film.** One `scenes.json` drives the render and the storyboard. Never hand-edit a
  generated storyboard; edit the spec and re-render.
- **Build a silent draft first.** Captions carry the story. Add voiceover only after the silent cut is approved:
  re-recording voice for a changed script is the most common waste.
- **Cut only at logical places** (new speaker, new language, new topic). A dissolve on every beat reads as noise.
- **Keep the work folder persistent** (`work/`), not `/tmp`: operating systems purge temp folders and paid
  generations disappear. Back up every paid clip to durable storage the moment it exists.

## Captions and copy
- Pillow renders the caption PNGs; ffmpeg only overlays them. Many ffmpeg builds have no `drawtext`.
- One caption treatment everywhere (dark rounded pill, lower third). One idea per pill. Keep lines parallel.
- Leave 0.45 s between a caption fading out and the next fading in, or two pills ghost over each other.
- Default copy rules used so far: no em dashes (use commas), short sentences. Change them in your brief, not in code.

## Static stills, real motion
- Static stills beat slow zooms (Ken Burns looks templated). Motion should come from real UI recordings,
  caption fades and cuts.
- Generate a canonical still once and reuse it as the reference image for every variation. It is the only
  reliable way to keep a face, a logo or a palette constant.

## Recording real web pages (Playwright)
- Viewport 1440x810 for desktop, `device: "iPhone 14"` for mobile. Use `mark` steps and `trim` so the
  loading lead-in is cut.
- Scroll with smooth wheel steps (`scroll`), not jumps; sit still for a beat before and after each move.
- Playwright videos have no cursor: keep `"cursor": true` so viewers can follow the action.
- A recorder that clicks "Book" on a live site creates a real booking. Point recorders at a test environment.
- After any click, a timeout usually means a dialog opened. Wait and read the page again; do not open new tabs.
- Do not put logins in a recipe that gets shared. Respect a site's terms of use.

## AI video with people (Veo)
- **Hold the reference constant.** Every clip starts from the same still. Chaining "last frame of the previous
  clip" gives seamless joins for a few links, then the face grows in frame and the colour drifts (skin orange,
  blue highlights) and post colour correction cannot fix it. Keep chains under about 5 clips and reset to the
  canonical still at each speaker turn.
- **One line per clip**, 8 seconds or less of speech, generated in parallel.
- **Gate every take.** Transcribe the clip and require the words to equal the script exactly (`veo_takes.py`
  does this). Veo invents filler words, reads punctuation aloud, and sometimes speaks past the line.
- **No dashes in spoken lines.** A dash is sometimes voiced as a stray word ("sure man"). `mv.spoken()` swaps
  dashes for commas.
- **Silent listening clips are picture-only prompts.** Never write "silent", "no voices", "not talking" or
  "no music" in a prompt: it trips Veo's audio stage and the job fails. Describe what the picture shows
  ("she listens, small nods"). Veo cannot deliver a truly silent beat, so mute and replace the audio when
  assembling.
- **Eyes and lips.** Add a sentence such as "steady eye contact with the camera" or people close their eyes
  and look down. A word-perfect transcript does NOT prove the lips moved: check speech windows frame by frame
  at the exact timestamps before assembling.
- **Expect random rejections** ("real person likeness", audio filter). Re-take with reworded wording.
- **Veo bills at submit time.** A polling timeout still costs a render. Quote the clip count (worst case =
  clips x max_takes) and get approval before generating; passed takes are cached and never regenerated.
- If Veo cannot hold a face over a long scene, use a layout that does not need it: a portrait in a circle
  plus a waveform on the active speaker (the `waveform` scene) reads well and costs nothing per second.

## Voice
- `gemini_tts.py` voices: Kore, Aoede, Leda, Zephyr (female); Puck, Charon, Orus, Fenrir (male). Steer delivery
  with a style prefix. Generate one WAV per line so a single line can be redone.
- Captions that follow speech: transcribe the WAV, then use the scene field `caps_from`.
- Mixing is `adelay` per track then `amix normalize=0`, so levels are exactly what you set; keep a music bed
  around 0.15 gain.

## ffmpeg
- `xfade` needs identical size, fps and timebase on both inputs; the compositor normalises every segment.
- An xfade offset past the end of a clip truncates the film; segments are padded by cloning the last frame.
- `showwaves` draws a gap-filled line only if there is at least one audio sample per pixel column
  (`48000 / (fps x width)`); colours are unreliable, so the compositor draws white and alpha-merges a colour.
- Always pass `-nostdin` to ffmpeg in scripts, or it can eat the terminal.
- You cannot watch an mp4. Use `--review` and read the contact sheet; for a specific moment extract a frame
  with `ffmpeg -ss 12.3 -i out/film.mp4 -frames:v 1 frame.png`.

## Spend discipline
- Set a billing cap in the provider console, not in code.
- Fix only what was flagged. Do not regenerate a whole batch for one bad take.
- Prefer a cheaper path first: still + captions before video, one still before ten variations.
- Record what you generated (prompt, model, date) in the spec's `note` fields so a reviewer can trace it.
