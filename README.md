# Bot kits

Two self-contained toolkits for an agent that produces marketing images and video. Each has an `AGENT.md`
(read first), a bootstrap script, and an offline smoke test. They contain no keys or credentials: secrets are
injected at run time by the human's secrets manager.

| Kit | For | Needs |
|---|---|---|
| [`social-visuals-kit`](social-visuals-kit) | A marketing / social media manager: designed cards, captioned footage reels in any shape, highlights on footage, animated explainers with voiceover, QA by frames, export presets, publishing and verification rules. Project-neutral; the brand lives in one file. | Nothing paid to start. Optional ElevenLabs key for voiceover. |
| [`video-pipeline-kit`](video-pipeline-kit) | AI-assisted films: Gemini stills, voiceover and transcripts, Veo clips with quality gates, Playwright screen recordings, a scene composer. | A Gemini API key. |

## Get a kit

```bash
# one kit, as a zip
curl -LO https://github.com/maestrix-amichai/bot-kits/raw/main/dist/social-visuals-kit.zip
curl -LO https://github.com/maestrix-amichai/bot-kits/raw/main/dist/video-pipeline-kit.zip
unzip social-visuals-kit.zip && cd social-visuals-kit

# or the whole repo
git clone https://github.com/maestrix-amichai/bot-kits.git
```

## Start

```bash
cat AGENT.md                        # the rules and the workflow
bash bootstrap.sh                   # ffmpeg, python venv, node, Playwright + Chromium
./run.sh tools/doctor.py            # must end with READY
bash examples/hello/run.sh          # offline smoke test (social-visuals-kit), then look at out/hello_sheet.png
```

The agent needs a shell, image viewing (it checks video by reading frames), network access, a secrets manager, and
a human who approves every publish. Details are in each kit's `AGENT.md`.
`dist/*.zip` are built from the two kit folders; rebuild them after any change.
