# Instructions for the agent using this kit

You are making a film. This folder is a complete, self-contained video pipeline. Read this file first.
Details: `README.md` (setup), `docs/SCENES.md` (spec format), `docs/LESSONS.md` (read before touching AI video),
`docs/DOPPLER.md` (secrets).

## First run (do this before anything else)
```bash
bash bootstrap.sh              # installs ffmpeg, python, node, Doppler CLI, Playwright + Chromium, a font
doppler login && doppler setup # the human does the login; pick the project/config with GEMINI_API_KEY
./run.sh tools/doctor.py       # must end with READY, including "key accepted by the Gemini API"
bash examples/hello/run.sh     # offline smoke test; then open out/hello_review/contact.png
```
If `doctor` fails, its `fix:` line says what to run. Do not start a film until it says READY.

## Rules
1. **Always use `./run.sh`.** It activates the venv and injects the key. Never print, log, commit or paste
   `GEMINI_API_KEY`. Never write it into a spec, recipe, script or document.
2. **Ask before spending.** Stills, TTS and transcripts cost cents. Veo clips cost real money. Before any Veo run,
   run `veo_takes.py spec.json` WITHOUT `--yes` (it prints the clip count and the worst case) and get the human's
   approval for that number. Passed takes are cached; never regenerate a clip that passed its gate.
3. **The spec is the film.** All edits go in `scenes.json`; re-render. Never hand-edit `out/*.storyboard.md`.
4. **Review by frames.** You cannot watch video. Render with `--review`, read `contact.png`, and check specific
   moments by extracting frames. Fix, re-render (only changed scenes re-render), repeat. Show the human the
   contact sheet and the mp4 path, and say what you could not verify (audio sync, lip movement).
5. **Silent draft first.** Captions carry the story; add voiceover only after the silent cut is approved.
6. **Keep paid assets safe.** `work/` is persistent but local: copy new paid clips and voice files to durable
   storage as soon as they exist. Do not use `/tmp` for assets.
7. **Real sites.** Record only what you are allowed to. Use a test environment when a click has side effects.
   Never put credentials in recipes.
8. **Do not edit `tools/`** unless a tool is broken; if you fix one, say so. Project files (specs, recipes,
   prompts) live in your own folder, for example `projects/<film>/`, not in `tools/` or `examples/`.

## Workflow
1. **Brief.** Audience, message, length, tone, aspect (16:9 or 9:16), languages. Write the throughline in
   one sentence and the scene list in `projects/<film>/scenes.json` (copy `examples/hello/scenes.json`).
2. **Assets**, cheapest first:
   - Stills: `./run.sh tools/gemini_image.py "<prompt>" work/<film>/hero.png [reference.png ...]`
   - Recordings: write `projects/<film>/recipe.json` (format at the top of `tools/record.js`), then
     `./run.sh tools/record.js projects/<film>/recipe.json`
   - Voiceover: `./run.sh tools/gemini_tts.py "<line>" work/<film>/vo1.wav Kore "Say warmly:"`, then
     `./run.sh tools/gemini_transcribe.py work/<film>/vo1.wav work/<film>/vo1.json` for `caps_from`.
   - Video clips: `tools/veo_generate.py` for one clip, `tools/veo_takes.py` for gated batches (rule 2).
3. **Compose:** `./run.sh tools/compose.py projects/<film>/scenes.json --review`
4. **Iterate** until the human approves; then final render, backup, and hand over `out/<film>.mp4`.

## Tool reference
| Command | Purpose |
|---|---|
| `tools/doctor.py [--offline]` | verify setup and the key |
| `tools/gemini_image.py PROMPT OUT [REFS...]` | generate/edit an image |
| `tools/gemini_tts.py TEXT OUT [VOICE] [STYLE]` | speech to a 24 kHz WAV |
| `tools/gemini_transcribe.py AUDIO [OUT.json]` | timestamped phrases |
| `tools/veo_generate.py --prompt P --out F [--image I] [--aspect A] [--dry-run]` | one Veo clip |
| `tools/veo_takes.py SPEC.json [--yes]` | gated batch of Veo clips (spends only with `--yes`) |
| `tools/record.js RECIPE.json [--headed]` | Playwright screen recording to mp4 |
| `tools/compose.py SCENES.json [--review] [--only ids]` | render the film |

## Troubleshooting
| Symptom | Cause / fix |
|---|---|
| `No GEMINI_API_KEY` | run through `./run.sh`; check `doppler setup`; or create `.env` |
| `HTTP 403/404` from Gemini | key lacks access or billing; model renamed: set `GEMINI_*_MODEL`/`VEO_MODEL` (docs/DOPPLER.md) |
| `HTTP 429` | rate limit; the tools retry 3 times; wait a minute |
| Veo job "error" right away | the prompt mentions silence/audio, or a safety filter fired: reword and retake |
| Captions ghost over each other | overlap warning from compose: move `in` later or shorten `show` |
| `unknown kind` / `asset not found` | check `docs/SCENES.md`; paths resolve next to the spec, then kit root, then `work/` |
| Chromium will not launch | `npx playwright install chromium` (Linux: `--with-deps`) |
| Film is shorter than expected | transitions overlap: total = sum(dur) - sum(xfade); intended |
