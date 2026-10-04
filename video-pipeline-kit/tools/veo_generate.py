#!/usr/bin/env python3
"""Generate one video clip with Veo (Gemini API): text-to-video, or image-to-video with a first frame.

  ./run.sh tools/veo_generate.py --prompt "..." --out work/clip.mp4 [--image still.png] [--aspect 16:9]
  ./run.sh tools/veo_generate.py ... --dry-run      # print the request, spend nothing

Veo bills at SUBMIT time: a poll timeout still costs a render. The default fast model renders a
fixed ~8 s clip. Model: VEO_MODEL (default veo-3.1-fast-generate-preview). Read docs/LESSONS.md
before writing prompts for people or speech.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import mv  # noqa: E402


def generate_clip(prompt: str, out: str | pathlib.Path, aspect: str = "16:9", image: str | None = None,
                  timeout_s: int = 600, dry_run: bool = False) -> pathlib.Path:
    inst: dict = {"prompt": prompt}
    if image:
        inst["image"] = {"bytesBase64Encoded": mv.b64_file(image), "mimeType": mv.mime_for(image)}
    body = {"instances": [inst], "parameters": {"aspectRatio": aspect}}
    if dry_run:
        shown = json.loads(json.dumps(body))
        if image:
            shown["instances"][0]["image"]["bytesBase64Encoded"] = "<%d bytes of %s>" % (len(inst["image"]["bytesBase64Encoded"]), image)
        print(f"POST {mv.API}/models/{mv.VEO_MODEL}:predictLongRunning\n{json.dumps(shown, indent=1)}")
        return pathlib.Path(out)

    print(f"submitting Veo job ({mv.VEO_MODEL}, {aspect}{', image-to-video' if image else ', text-to-video'})...", flush=True)
    sub = mv.api(f"models/{mv.VEO_MODEL}:predictLongRunning", body, timeout=90)
    op = sub.get("name")
    if not op:
        raise RuntimeError(f"no operation name in reply: {str(sub)[:300]}")
    t0 = time.time()
    uri = ""
    while time.time() - t0 < timeout_s:
        time.sleep(8)
        pj = mv.api(f"{mv.API}/{op}", None, timeout=60)
        if pj.get("error"):
            raise RuntimeError(f"veo error: {pj['error']}")
        if pj.get("done"):
            r = pj.get("response", {})
            samples = r.get("generateVideoResponse", {}).get("generatedSamples") or r.get("generatedVideos") or [{}]
            uri = samples[0].get("video", {}).get("uri", "")
            reasons = r.get("generateVideoResponse", {}).get("raiMediaFilteredReasons")
            if not uri and reasons:
                raise RuntimeError(f"veo filtered the clip: {reasons}")
            print(f"  done in {int(time.time() - t0)}s", flush=True)
            break
        print(f"  ...rendering ({int(time.time() - t0)}s)", flush=True)
    if not uri:
        raise RuntimeError("timeout or no video uri in the reply")
    req = urllib.request.Request(uri, headers={"x-goog-api-key": mv.gemini_key()})
    try:
        data = urllib.request.urlopen(req, timeout=180).read()
    except urllib.error.HTTPError:  # older URIs want the key as a query parameter
        data = urllib.request.urlopen(uri + ("&" if "?" in uri else "?") + "key=" + mv.gemini_key(), timeout=180).read()
    out = pathlib.Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    print(f"saved {out} ({len(data) // 1024} KiB)")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--image", help="first-frame reference image (image-to-video)")
    ap.add_argument("--aspect", default="16:9", choices=["16:9", "9:16"])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    try:
        generate_clip(a.prompt, a.out, a.aspect, a.image, dry_run=a.dry_run)
    except RuntimeError as e:
        raise SystemExit(str(e))


if __name__ == "__main__":
    main()
