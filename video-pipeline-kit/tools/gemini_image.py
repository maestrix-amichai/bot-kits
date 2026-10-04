#!/usr/bin/env python3
"""Generate or edit an image with Gemini.

  ./run.sh tools/gemini_image.py "<prompt>" work/hero.png [ref1.png ref2.png ...]

With reference images the model edits or builds on them (keep a canonical still and reuse it
as the reference for every variation: it is the only reliable way to hold a face or a mark
constant). Model: GEMINI_IMAGE_MODEL (default gemini-3-pro-image-preview).
"""
import argparse
import base64
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import mv  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prompt")
    ap.add_argument("out")
    ap.add_argument("refs", nargs="*", help="optional reference images")
    a = ap.parse_args()

    parts = [{"inlineData": {"mimeType": mv.mime_for(r), "data": mv.b64_file(r)}} for r in a.refs]
    parts.append({"text": a.prompt})
    try:
        r = mv.generate(mv.IMAGE_MODEL, parts, {"responseModalities": ["TEXT", "IMAGE"]}, timeout=180)
    except RuntimeError as e:
        raise SystemExit(f"image generation failed: {e}")
    for p in r.get("candidates", [{}])[0].get("content", {}).get("parts", []):
        inline = p.get("inlineData") or p.get("inline_data")
        if inline and str(inline.get("mimeType", inline.get("mime_type", ""))).startswith("image/"):
            out = pathlib.Path(a.out)
            out.parent.mkdir(parents=True, exist_ok=True)
            data = base64.b64decode(inline["data"])
            try:  # the API often returns JPEG bytes; write the format the file name promises
                import io
                from PIL import Image
                img = Image.open(io.BytesIO(data))
                if out.suffix.lower() in (".jpg", ".jpeg"):
                    img.convert("RGB").save(out, quality=95)
                else:
                    img.save(out)
            except Exception:  # noqa: BLE001
                out.write_bytes(data)
            print(f"saved {out} ({out.stat().st_size // 1024} KiB)")
            return
    raise SystemExit("no image in the reply: " + str(r)[:400])


if __name__ == "__main__":
    main()
