#!/usr/bin/env python3
"""Controlled Veo takes with quality gates: every clip starts from the SAME still, one line per clip,
generated in parallel, and each take must pass before it is kept (re-taken up to max_takes):
  - transcript gate: what the clip says must equal the script word for word (silent clips must be silent)
  - picture gate (optional): Gemini looks at 4 frames and answers a yes/no question set you define

  ./run.sh tools/veo_takes.py spec.json            # print the plan and the worst-case clip count
  ./run.sh tools/veo_takes.py spec.json --yes      # actually generate (this spends money)

spec.json:
{
  "still": "work/portrait.png",                  // reference first frame (or null for text-to-video)
  "aspect": "16:9",
  "out_dir": "work/veo",
  "voice": "in a calm, warm mid-range female voice",
  "style": "Steady camera, same framing as the reference, soft daylight.",
  "max_takes": 3, "workers": 3,
  "picture_check": {"prompt": "one person visible, holding a phone", "keys": ["one_person", "holds_phone"]},
  "takes": [
    {"name": "a1", "line": "Welcome, I am glad you called."},                 // spoken clip
    {"name": "l1", "line": null, "prompt": "She listens attentively, small nods."},   // silent listening clip
    {"name": "a2", "line": "Yes of course.", "prompt": "She smiles and says, {voice}, exactly these words and nothing else: \\"{line}\\" {style}"}
  ]
}
Prompt placeholders: {line} {voice} {style}. Spoken clips default to a "says exactly these words" prompt.
Silent clips MUST describe the picture only: any mention of silence, "no voices" or "not talking"
makes Veo's audio stage fail the job. Output: <out_dir>/<name>.mp4 plus <name>.ok.json on success;
rejected takes are kept as <name>.bad<N>.mp4 for inspection.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import mv  # noqa: E402
from veo_generate import generate_clip  # noqa: E402

DEFAULT_SPOKEN = 'The person looks into the camera. They listen for a moment, then say warmly, {voice}, exactly these words and nothing else: "{line}" Then they keep listening quietly. {style}'
DEFAULT_SILENT = "The person listens attentively for the whole clip: small nods, a slight smile, attentive eyes. {style}"


def sh(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True)


def speech_of(clip: pathlib.Path):
    wav = clip.with_suffix(".wav")
    sh(["ffmpeg", "-y", "-v", "error", "-i", str(clip), "-vn", "-ac", "1", "-ar", "16000", str(wav)])
    try:
        phrases = mv.transcribe(wav)
    except Exception:  # noqa: BLE001
        return None, ""
    spoken = [p for p in phrases if not str(p.get("text", "")).strip().startswith("[")]
    if not spoken:
        return None, ""
    return (min(p["start"] for p in spoken), max(p["end"] for p in spoken)), " ".join(p["text"] for p in spoken)


def picture_ok(clip: pathlib.Path, check: dict):
    grid = clip.with_suffix(".grid.jpg")
    sh(["ffmpeg", "-y", "-v", "error", "-i", str(clip), "-vf", "select='not(mod(n,40))',scale=480:-1,tile=4x1",
        "-frames:v", "1", "-q:v", "4", str(grid)])
    keys = check["keys"]
    q = (f"These are 4 frames from one video clip. Requirement: {check['prompt']}. Answer ONLY JSON with a boolean per key "
         f"({', '.join(keys)}) and a short 'note'. Judge every frame; any frame that fails makes the key false.")
    try:
        r = mv.generate(mv.TEXT_MODEL, [{"inlineData": {"mimeType": "image/jpeg", "data": mv.b64_file(grid)}}, {"text": q}],
                        {"responseMimeType": "application/json"}, timeout=120)
        d = mv.first_json(mv.reply_text(r))
    except Exception as e:  # noqa: BLE001
        return True, f"picture check skipped ({e})"
    return all(bool(d.get(k)) for k in keys), str(d.get("note", ""))


def take(spec: dict, beat: dict) -> str:
    out_dir = pathlib.Path(spec["out_dir"])
    name, line = beat["name"], beat.get("line")
    out = out_dir / f"{name}.mp4"
    if out.exists() and out.with_suffix(".ok.json").exists():
        return f"{name}: cached"
    fill = dict(voice=spec.get("voice", "in a calm, natural voice"), style=spec.get("style", ""), line=mv.spoken(line or ""))
    template = beat.get("prompt") or (DEFAULT_SPOKEN if line else DEFAULT_SILENT)
    prompt = template.format(**fill)
    log = []
    for t in range(1, int(spec.get("max_takes", 3)) + 1):
        try:
            generate_clip(prompt, out, spec.get("aspect", "16:9"), spec.get("still"))
        except RuntimeError as e:
            log.append(f"take{t}: veo failed {str(e)[:160]}")
            continue
        win, said = speech_of(out)
        ok_t = (win is None or (win[1] - win[0]) < 0.6) if not line else mv.norm_words(said) == mv.norm_words(line)
        ok_p, note = picture_ok(out, spec["picture_check"]) if spec.get("picture_check") else (True, "no picture check")
        log.append(f"take{t}: text={'ok' if ok_t else 'BAD'} “{said}” | picture={'ok' if ok_p else 'BAD'} {note}")
        if ok_t and ok_p:
            out.with_suffix(".ok.json").write_text(json.dumps({"speech": win, "said": said, "line": line}))
            return f"{name}: OK (take {t})\n  " + "\n  ".join(log)
        out.rename(out.with_name(f"{name}.bad{t}.mp4"))
    return f"{name}: FAILED after {spec.get('max_takes', 3)} takes\n  " + "\n  ".join(log)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec")
    ap.add_argument("--yes", action="store_true", help="confirm the spend and generate")
    a = ap.parse_args()
    spec = json.loads(pathlib.Path(a.spec).read_text())
    pathlib.Path(spec["out_dir"]).mkdir(parents=True, exist_ok=True)
    todo = [b for b in spec["takes"] if not (pathlib.Path(spec["out_dir"]) / f"{b['name']}.ok.json").exists()]
    worst = len(todo) * int(spec.get("max_takes", 3))
    print(f"{len(spec['takes'])} clips in the spec, {len(todo)} still to generate, worst case {worst} Veo renders "
          f"({mv.VEO_MODEL}, ~8 s each). Passed clips are reused, never regenerated.")
    if not a.yes:
        print("Nothing generated. Get approval for that clip count, then re-run with --yes.")
        return
    with ThreadPoolExecutor(max_workers=int(spec.get("workers", 3))) as ex:
        for res in ex.map(lambda b: take(spec, b), todo):
            print(res, flush=True)
    print("TAKESDONE")


if __name__ == "__main__":
    main()
