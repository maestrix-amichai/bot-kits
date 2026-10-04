# Social visuals playbook

How to make, check and publish the images and videos a marketing/social manager needs. Project-neutral: your brand
comes from `brand/brand.json`. The method in one line: **design in HTML, render with a headless browser, compose with
ffmpeg, check by looking at frames, publish through the real editor only on approval, verify on the live page.**

## 1. The format ladder (cheapest asset that does the job)

| Format | Use it for | Tool | Shape |
|---|---|---|---|
| Single card | one claim, one stat, one quote, a before/after | `card.py` | 1080x1350 or 1080x1080 |
| Carousel | a short explanation, 4 to 8 cards, one idea each, last card = call to action | `card.py` in a loop | 1080x1350 |
| Footage reel | a product in action, a result, a demo with captions | `reel.py` | 1080x1350, 1080x1920, article-wide |
| Annotated footage | pointing at something moving: a ring, a trail, slow motion | `annotate.py` then `reel.py` | as footage |
| Explainer with voiceover | a story you want people to hear, 30 to 60 s | `vo.py` + `record.py` | 1080x1920 |
| Cover / link card | the preview image of an article or post | `card.py --size og` | 1200x630 |

Rule: a video only earns its cost if motion is the point. If a card says it, ship the card.

## 2. Design system (from `brand.json`)
- Tokens: `colors` (bg, fg, muted, accent, accent_ink, panel, rule, soft) and `fonts` (display, body, mono) are the
  only styling inputs. Google Fonts by name, or a local font file embedded as a data URI. Add a logo file.
- Emphasis: wrap words in `*asterisks*` to colour them with the accent. Use it once per card at most.
- One visual per beat of the story, placed where the story needs it. Original and designed; no screenshots of
  internal tools, no internal vocabulary on a card. A comparison says what it compares on the card itself.
- Captions: plain words, two lines at most, readable on a phone, and burned in (most people watch muted).
- A mock-up says it is an illustration. Licensed footage is credited on the visual (`credit` field).
- Accessibility: every posted image gets alt text that says what it shows and what it says; every video gets its
  captions burned in; never put the only copy of important text in the image.

## 3. Recipes

### 3.1 A card
```bash
./run.sh tools/card.py title   --size portrait --out out/c1.png --set kicker="New" --set headline="Ship the *simple* version" --set sub="Then improve it"
./run.sh tools/card.py stat    --size square   --out out/c2.png --set number="3x" --set label="faster reviews"
./run.sh tools/card.py compare --size portrait --out out/c3.png --set title="Before and *after*" \
        --set left_label=Before --set left="Slow\nManual" --set right_label=After --set right="Fast\nAutomatic"
```
Sizes: `square portrait story landscape linkedin og wide` or `WxH`. `--scale 2` for a sharper still. Fields per
template are listed at the top of `tools/card.py`. Carousel: one JSON of cards, loop, number them in the file names.

### 3.2 A captioned footage reel
Write a spec (copy `examples/hello/reel.json`): title card, footage segments with caption **states**, end card.
A state shows from its `at` second until the next one. Typical story: hook card 3 s, footage with a "what you see"
state then a "what it means" state with a badge, one turning-point card, an end card with the call to action.
Keep it under 40 s unless there is a reason.
```bash
./run.sh tools/reel.py projects/launch/reel.json                       # the shape in the spec
./run.sh tools/reel.py projects/launch/reel.json --canvas 1080x1920 --out out/launch_vertical.mp4
./run.sh tools/reel.py projects/launch/reel.json --canvas wide --out out/launch_article.mp4
```
One spec, every shape. Use the footage window and caption area as designed: the caption area is below the footage and
never covers it. Add `"audio": {"file": "vo.m4a"}` once the silent cut is approved, and `stills` to export posters.

### 3.3 Highlights on footage
`annotate.py in.mp4 spec.json out.mp4` draws a glowing trail through points you give it, a ring that pulses where
something lands, boxes, and slow motion from a chosen frame. It writes `out.mp4.json` with the output frame of each
ring and the slow-motion start (seconds = frame / fps) so caption states switch at the right moment. No text goes on
the footage: captions belong on the caption pages. Pick clips where the decisive moment is inside the frame.

### 3.4 An explainer with voiceover (9:16, 30 to 60 s)
1. Write the script as one line per beat (JSON of `{id, text}`); the hook is the first line and says what the video is
   about. End on the call to action.
2. `./run.sh tools/vo.py timeline script.json --out-dir work/vo --fake` first: free placeholder audio to test timing.
3. Copy `templates/explainer.html`, make a `<section data-beat="id">` per beat; it reads `window.TIMELINE`.
4. `./run.sh tools/record.py --html projects/x/page.html --timeline work/vo/timeline.json --out out/x_silent.mp4`;
   review the sheet; fix.
5. After approval and cost sign-off: `vo.py timeline ... --voice <id>` for real, then record with `--audio`.
Pitfalls: ffmpeg zoom effects (`zoompan`) can silently produce enormous files, so animate in HTML instead; a typed
query is unreadable on a phone unless a large caption repeats it; the last beat must say where to follow or click.

### 3.5 Generated images and AI video (paid, optional)
Only when a designed card or real footage cannot do it. Quote the count and worst-case cost first. Generate with the
tool your human approves (Gemini image, an xAI/Grok or Veo video model), reuse takes that passed, fix only the flagged
moments, back up every paid file at once. Label generated imagery as such when it could be mistaken for a photo of a
real thing. Never generate real people's likenesses without consent.

## 4. QA (you cannot watch it, so read it)
```bash
./run.sh tools/qa.py sheet  out/x.mp4 out/x_sheet.png --every 2     # contact sheet: read it as an image
./run.sh tools/qa.py frames out/x.mp4 out/frames 1.0 8.0 20.0       # exact moments
./run.sh tools/qa.py check  out/x.mp4 feed_portrait                 # size, length, codec, file size vs the preset
```
Checklist: the first frame already says what the post is about; captions wrap cleanly (no single orphan word);
nothing important is cut off or covered; overlays sit inside the frame; every claim and number matches its source;
the last frame has the call to action; duration and file size are what you meant; credits are on screen.

## 5. Export presets (`tools/platforms.json`)
`feed_portrait` 1080x1350, `square` 1080x1080, `vertical` 1080x1920, `landscape` 1920x1080, `article_wide` 1600x1160,
`link_card` 1200x630. The size limits in that file are **house limits** (our own caps), not the platforms' rules.
Platform limits change: before uploading anything unusual, read the platform's current help page and update the file.
Always export h264 + yuv420p + aac with `+faststart`; the tools do.

## 6. Writing the post that carries the visual
- First line is the hook and must work on its own (it is all that shows before "see more").
- One idea per post. Plain words. Specific beats clever. No claims the visual cannot back up.
- A call to action that names the one thing to do next. Put links where the platform rewards them (often the first
  comment or the bio), not in the body, and say so in the post.
- Draft two or three variants for taste calls (hook lines, titles, covers), say which you would pick, let the human
  choose. Never post the same text on every platform: shape it to each.
- Hashtags and tagging: few, relevant; never tag people or companies without the human's say-so.

## 7. Publishing and verification
- **Always a draft first.** Put the item in the platform's editor or scheduler in draft state, show the human a
  screenshot and the text, and wait for the yes. Publishing, scheduling and sending are the human's decision.
- **Signed-in accounts only through the human.** If a platform shows a login or an "are you sure it's you" step,
  stop and ask the human to complete it. Do not work around it.
- **Uploads.** Upload images and videos through the platform's own dialog from files on disk. Linked external images
  are dropped by some editors on publish: upload them. Some editors read a video's length in the browser, so the tab
  must be **visible on screen** during a video upload; hidden tabs silently stall.
- **Email and some feeds cannot play video:** supply a poster still (`stills` in the reel spec) where one is needed.
- **Verify live.** Reopen the public URL (add `?t=<n>` to skip caches), wait for it to load, count images and videos
  against the source, screenshot two places, and check that videos report as processed. Report the link, what is
  live, anything that differs between platforms. If anything is wrong, tell the human at once so they can pull it.
- **Ledger.** Append to `ledger.md`: date, item, file path, platform, URL, status (drafted, approved, live).

## 8. A weekly rhythm that works
1. Agree this week's one idea and the proof (a number, a clip, a before/after) with the human.
2. Produce the hero asset (a reel or an explainer) plus its cuts: a card for the idea, a still poster, a cover.
3. Repurpose one source into each shape needed (4:5 feed, 9:16, article-wide) by changing `--canvas`, not by rebuilding.
4. Write the platform-specific posts and first comments; show everything together in one review.
5. On approval: publish, verify, log, and note what to learn for next week (what was unclear, what was cut).
