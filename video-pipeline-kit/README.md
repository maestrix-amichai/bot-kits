# Video pipeline kit

A standalone toolkit for making marketing, product and explainer films with an AI agent driving it.
It has no dependency on any repo: it installs what it needs, reads one secret (`GEMINI_API_KEY`) from
Doppler, and keeps all of its files inside this folder.

| Piece | Tool | Uses |
|---|---|---|
| Stills, hero images, edits of a reference image | `tools/gemini_image.py` | Gemini image model |
| Voiceover | `tools/gemini_tts.py` | Gemini TTS (8 voices) |
| Phrase-level transcripts with timestamps | `tools/gemini_transcribe.py` | Gemini |
| Video clips, text-to-video or image-to-video | `tools/veo_generate.py` | Veo |
| Many clips with automatic quality gates | `tools/veo_takes.py` | Veo + Gemini checks |
| Screen recordings of real web pages | `tools/record.js` | Playwright + Chromium |
| The film: scenes, captions, transitions, audio, storyboard | `tools/compose.py` | ffmpeg + Pillow |
| Setup check | `tools/doctor.py` | |

## Set up on a new machine

macOS (Homebrew) or Ubuntu/Debian. On Windows use WSL2.

```bash
unzip video-pipeline-kit.zip && cd video-pipeline-kit     # or copy the folder from Drive
bash bootstrap.sh                # installs ffmpeg, python, node, Doppler CLI, Playwright + Chromium, a font
doppler login                    # one time per machine
doppler setup                    # pick the Doppler project/config that holds GEMINI_API_KEY (docs/DOPPLER.md)
./run.sh tools/doctor.py         # everything should say ok, including "key accepted by the Gemini API"
bash examples/hello/run.sh       # offline end to end: record a page, compose a film (no API spend)
```

Optional live check of the Gemini tools (about a few cents): `bash examples/live/run.sh`.

Use `./run.sh` for everything. It activates the Python environment and injects the key from Doppler
(or from `.env`, see `.env.example`, on a machine without Doppler).

## Make a film

1. Write `scenes.json` (see `docs/SCENES.md`, copy `examples/hello/scenes.json`).
2. Produce the assets it names: stills, voiceover, recordings, Veo clips.
3. `./run.sh tools/compose.py scenes.json --review`
4. Look at `out/<name>_review/contact.png` (one frame per scene), fix the spec, repeat.
   Only changed scenes re-render.

Everything an agent needs to work this way, including the rules that keep spend and quality under
control, is in **`AGENT.md`**. Hard-won lessons about AI video are in **`docs/LESSONS.md`**.

## Where files go

- `work/`  intermediate files and generated assets (persistent, unlike `/tmp`; back up anything paid for)
- `out/`   finished films, storyboards, review frames
- Point them elsewhere with `KIT_WORK=/path KIT_OUT=/path ./run.sh ...`

## Requirements

Python 3.9+, Node 18+, ffmpeg (with xfade, showwaves, alphamerge, libx264, aac), a Gemini API key.
Veo and the current image model normally require a billing-enabled Google AI Studio project.
Caption font: Inter (SIL Open Font License, included in `assets/fonts/`).
