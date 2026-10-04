# Doppler setup for this kit

The kit needs exactly one secret: `GEMINI_API_KEY`.

## One time, in the Doppler dashboard
1. Create a project for the kit (any name) with a config, for example `dev`.
2. Add the secret `GEMINI_API_KEY`. Create the key at https://aistudio.google.com/apikey. Veo and the
   current image model normally need billing enabled on that Google project.
3. Optional secrets: `GEMINI_IMAGE_MODEL`, `GEMINI_TTS_MODEL`, `GEMINI_TEXT_MODEL`, `VEO_MODEL` to change
   models without touching code (defaults are in `tools/mv.py`).

## On each machine
```bash
doppler login
cd video-pipeline-kit
doppler setup                 # choose the project and config; this scopes the folder
doppler secrets get GEMINI_API_KEY --plain >/dev/null && echo ok
./run.sh tools/doctor.py      # includes a live check that the key is accepted
```
`run.sh` detects the Doppler scope of the folder and runs the tool through `doppler run`.
Scope without prompts: `doppler setup --no-interactive --project <p> --config <c>`.

## Without Doppler
Copy `.env.example` to `.env` and put the key in it. `.env` is git-ignored. `run.sh` uses it when the key
is not already in the environment. Never commit a key, never paste one into a recipe or scenes file.

## Order of precedence
Environment variable already set > `.env` > Doppler.
