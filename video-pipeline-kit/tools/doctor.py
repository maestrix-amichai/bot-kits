#!/usr/bin/env python3
"""Verify the kit is ready: toolchain, ffmpeg features, Playwright, fonts, and (unless --offline) the Gemini key.

  ./run.sh tools/doctor.py            # includes a live key check (free: lists one model)
  .venv/bin/python tools/doctor.py --offline
Exit code 1 if a required check fails.
"""
from __future__ import annotations

import argparse
import os
import pathlib
import shutil
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import mv  # noqa: E402

bad = 0


def ok(msg):
    print(f"  ok    {msg}")


def fail(msg, fix=""):
    global bad
    bad += 1
    print(f"  FAIL  {msg}" + (f"\n        fix: {fix}" if fix else ""))


def info(msg):
    print(f"  info  {msg}")


def sh(cmd, cwd=None, timeout=60):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        return subprocess.CompletedProcess(cmd, 1, "", str(e))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="skip the live Gemini key check")
    a = ap.parse_args()
    mv.load_dotenv()

    print("Python")
    (ok if sys.version_info >= (3, 9) else fail)(f"python {sys.version.split()[0]}")
    try:
        import PIL
        ok(f"Pillow {PIL.__version__}")
    except ImportError:
        fail("Pillow missing", "bash bootstrap.sh")

    print("ffmpeg")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        fail("ffmpeg/ffprobe not found", "bash bootstrap.sh")
    else:
        ok(sh(["ffmpeg", "-version"]).stdout.splitlines()[0])
        filters = sh(["ffmpeg", "-hide_banner", "-filters"]).stdout
        for f in ("xfade", "showwaves", "alphamerge", "overlay", "hstack", "tpad", "fade", "amix", "adelay"):
            (ok if f" {f} " in filters else fail)(f"filter {f}" if f" {f} " in filters else f"ffmpeg lacks filter {f}")
        enc = sh(["ffmpeg", "-hide_banner", "-encoders"]).stdout
        for e in ("libx264", "aac"):
            (ok if e in enc else fail)(f"encoder {e}" if e in enc else f"ffmpeg lacks encoder {e}")
        if " drawtext " not in filters:
            info("no drawtext filter (fine: captions are rendered with Pillow, never drawtext)")

    print("Node and Playwright")
    node = sh(["node", "--version"])
    if node.returncode:
        fail("node not found", "bash bootstrap.sh")
    else:
        ok(f"node {node.stdout.strip()}")
        r = sh(["node", "-e", "require('playwright'); console.log(require('playwright/package.json').version)"], cwd=str(mv.KIT))
        if r.returncode:
            fail("playwright package not installed", "bash bootstrap.sh")
        else:
            ok(f"playwright {r.stdout.strip()}")
            js = "const {chromium}=require('playwright');(async()=>{const b=await chromium.launch();await b.close();console.log('launched')})().catch(e=>{console.error(e.message.split('\\n')[0]);process.exit(1)})"
            r = sh(["node", "-e", js], cwd=str(mv.KIT), timeout=90)
            (ok if r.returncode == 0 else fail)("chromium launches headless" if r.returncode == 0 else f"chromium will not launch: {r.stderr.strip()[:160]}")
            if r.returncode:
                print("        fix: npx playwright install chromium   (Linux: npx playwright install --with-deps chromium)")

    print("Fonts")
    cands = [p for p in mv._font_candidates() if p and os.path.exists(p)]
    if cands:
        ok(f"caption font: {cands[0]}")
        try:
            from PIL import Image, ImageDraw
            mv.pill("Hello", "/tmp/_kit_doctor.png", 800, 48)
            ok("caption rendering works")
        except Exception as e:  # noqa: BLE001
            fail(f"caption rendering failed: {e}")
    else:
        fail("no usable font", "bash bootstrap.sh (downloads Inter) or set KIT_FONT")

    print("Gemini key")
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if a.offline:
        info("skipped (--offline). Run ./run.sh tools/doctor.py once Doppler is set up.")
    elif not key:
        fail("GEMINI_API_KEY not in the environment", "doppler login && doppler setup, then use ./run.sh (docs/DOPPLER.md), or create .env")
    else:
        ok(f"key present ({key[:4]}...{key[-3:]})")
        try:
            mv.api("models?pageSize=1", None, timeout=30, retries=1)
            ok("key accepted by the Gemini API")
        except RuntimeError as e:
            fail(f"Gemini API rejected the request: {str(e)[:200]}", "check the key in Doppler; enable the Generative Language API for its project")

    print("Doppler (only needed on the machine that fetches the key)")
    info("doppler " + (sh(["doppler", "--version"]).stdout.strip() or "not installed"))
    print()
    print("READY" if not bad else f"{bad} problem(s) above")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
