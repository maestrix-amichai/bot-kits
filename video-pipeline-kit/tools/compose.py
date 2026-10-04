#!/usr/bin/env python3
"""Compose a film from a scenes.json spec: ffmpeg + Pillow caption pills, xfade transitions, mixed audio.

  ./run.sh tools/compose.py examples/hello/scenes.json            # render -> out/<name>.mp4 + storyboard
  ./run.sh tools/compose.py scenes.json --review                  # also dump one frame per scene + a contact sheet
  ./run.sh tools/compose.py scenes.json --only intro,demo         # render just those scenes' segments (fast iteration)

The spec is the single source of truth: the same file drives the render AND the storyboard, so they
cannot drift. Segments are cached by content hash (work/seg/), so only changed scenes re-render.
Full field reference: docs/SCENES.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import mv  # noqa: E402

IMG_EXT = {".png", ".jpg", ".jpeg", ".webp"}


class Film:
    def __init__(self, spec_path: pathlib.Path):
        self.spec_path = spec_path.resolve()
        self.dir = self.spec_path.parent
        self.spec = json.loads(spec_path.read_text())
        s = self.spec
        self.name = s.get("name") or self.spec_path.parent.name
        self.W, self.H = s.get("size", [1920, 1080])
        self.FPS = int(s.get("fps", 30))
        self.XF = float(s.get("xfade", 0.4))
        self.TRANS = s.get("transition", "fade")
        self.BG = mv.hex_rgb_str(s.get("bg", "#0d0d10"))
        cap = s.get("caption", {})
        self.cap_size = int(cap.get("size", round(self.H * 0.048)))
        self.cap_y = float(cap.get("y", 0.80))
        self.cap_fg = mv.hex_rgba(cap.get("fg"), (255, 255, 255, 255))
        self.cap_bg = mv.hex_rgba(cap.get("bg"), (13, 13, 16, 220))
        self._warned: set = set()
        self.seg_dir = mv.WORK / "seg" / self.name
        self.png_dir = mv.WORK / "png" / self.name
        for d in (self.seg_dir, self.png_dir, mv.OUT):
            d.mkdir(parents=True, exist_ok=True)

    # ── paths ──
    def resolve(self, p: str) -> pathlib.Path:
        q = pathlib.Path(p)
        if q.is_absolute():
            return q
        for base in (self.dir, mv.KIT, mv.WORK):
            if (base / q).exists():
                return base / q
        return self.dir / q

    def asset(self, sc: dict, key: str = "asset") -> pathlib.Path:
        if key not in sc:
            raise SystemExit(f"scene '{sc['id']}' ({sc['kind']}) needs an '{key}'")
        p = self.resolve(sc[key])
        if not p.exists():
            raise SystemExit(f"scene '{sc['id']}': {key} not found: {sc[key]} (looked relative to {self.dir}, {mv.KIT}, {mv.WORK})")
        return p

    # ── captions ──
    def caps_of(self, sc: dict) -> list:
        caps = []
        for c in sc.get("caps", []):
            if isinstance(c, dict):
                caps.append((c["text"], float(c.get("in", 0.4)), float(c.get("show", 3.0))))
            else:
                caps.append((c[0], float(c[1]), float(c[2])))
        if sc.get("caps_from"):
            offset = float(sc.get("caps_offset", 0.0))
            phrases = [p for p in json.loads(self.resolve(sc["caps_from"]).read_text())
                       if str(p.get("text", "")).strip() and not str(p["text"]).strip().startswith("[")]
            for i, ph in enumerate(phrases):
                tin = float(ph["start"]) + offset
                show = max(1.2, float(ph["end"]) - float(ph["start"]) + 0.3)
                if i + 1 < len(phrases):  # finish fading out before the next phrase appears
                    show = max(0.6, min(show, float(phrases[i + 1]["start"]) + offset - tin - 0.5))
                caps.append((str(ph["text"]).strip(), tin, show))
        ordered = sorted(caps, key=lambda c: c[1])
        for a, b in zip(ordered, ordered[1:]):
            if b[1] < a[1] + a[2] + 0.45 and (sc["id"], a[0]) not in self._warned:
                self._warned.add((sc["id"], a[0]))
                print(f"  warning: scene '{sc['id']}': caption \"{a[0][:30]}\" is still fading when \"{b[0][:30]}\" starts "
                      f"(needs in >= {a[1] + a[2] + 0.45:.2f})")
        return caps

    def layer(self, sid: str, tag: str, text: str, tin, show, y: int, x: int = 0, width: int | None = None,
              size: int | None = None, fg=None, plain: bool = False):
        png = self.png_dir / f"{sid}_{tag}.png"
        h = mv.pill(text, png, width or self.W, size or self.cap_size, fg or self.cap_fg, self.cap_bg, plain=plain)
        return dict(png=png, tin=tin, show=show, x=x, y=y, h=h)

    def caption_layers(self, sid: str, sc: dict, width: int | None = None, x: int = 0) -> list:
        y = int(self.H * float(sc.get("capy", self.cap_y)))
        return [self.layer(sid, f"c{i}", t, tin, sd, y, x, width) for i, (t, tin, sd) in enumerate(self.caps_of(sc))]

    # ── ffmpeg assembly for one segment ──
    def encode(self, sid: str, base_inputs: list, base_parts: list, base_label: str, layers: list, dur: float,
               out: pathlib.Path) -> None:
        inputs, parts = list(base_inputs), list(base_parts)
        n0 = sum(1 for a in inputs if a == "-i")
        last = base_label
        for i, L in enumerate(layers):
            inputs += ["-loop", "1", "-t", f"{dur}", "-i", str(L["png"])]
            idx = n0 + i
            fade = "format=rgba"
            if L["tin"] is not None:
                fade += f",fade=t=in:st={L['tin']}:d=0.4:alpha=1,fade=t=out:st={L['tin'] + L['show']}:d=0.45:alpha=1"
            parts.append(f"[{idx}:v]{fade}[l{i}]")
            parts.append(f"[{last}][l{i}]overlay={L['x']}:{L['y']}[o{i}]")
            last = f"o{i}"
        parts.append(f"[{last}]format=yuv420p[v]")
        mv.run(sid, ["ffmpeg", "-y", "-nostdin", "-v", "error", *inputs, "-filter_complex", ";".join(parts), "-map", "[v]",
                     "-an", "-t", f"{dur}", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                     "-r", str(self.FPS), str(out)], quiet=True)

    def video_in(self, path: pathlib.Path, dur: float, start: float = 0.0) -> list:
        if path.suffix.lower() in IMG_EXT:
            return ["-loop", "1", "-t", f"{dur}", "-i", str(path)]
        return (["-ss", f"{start:.2f}"] if start else []) + ["-i", str(path)]

    def fit_filter(self, idx: int, out_label: str, mode: str, dur: float, w: int | None = None, speed: float = 1.0) -> str:
        W, H = w or self.W, self.H
        if mode == "cover":
            sc = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"
        else:  # fit / letterbox
            sc = f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color={self.BG}"
        sp = f",setpts=PTS/{speed}" if speed != 1.0 else ""
        return f"[{idx}:v]{sc}{sp},setsar=1,fps={self.FPS},tpad=stop_mode=clone:stop_duration={dur}[{out_label}]"

    # ── scene kinds ──
    def seg_still(self, sc, out):
        src, dur = self.asset(sc), float(sc["dur"])
        self.encode(sc["id"], self.video_in(src, dur), [self.fit_filter(0, "bg", "cover", dur)], "bg",
                    self.caption_layers(sc["id"], sc), dur, out)

    def seg_clip(self, sc, out):  # clip = fit (letterbox), fill = cover crop, raw = fit without captions
        src, dur = self.asset(sc), float(sc["dur"])
        mode = "cover" if sc["kind"] == "fill" else "fit"
        layers = [] if sc["kind"] == "raw" else self.caption_layers(sc["id"], sc)
        self.encode(sc["id"], self.video_in(src, dur, float(sc.get("start", 0.0))),
                    [self.fit_filter(0, "bg", mode, dur, speed=float(sc.get("speed", 1.0)))], "bg", layers, dur, out)

    def seg_card(self, sc, out):
        dur = float(sc["dur"])
        bg = mv.hex_rgb_str(sc.get("bg", "#12162a"))
        layers = []
        for i, ln in enumerate(sc.get("lines", [])):
            L = self.layer(sc["id"], f"t{i}", ln["text"], float(ln.get("in", 0.3)), float(ln.get("show", dur - 0.9)), 0,
                           size=int(ln.get("size", round(self.H * 0.09))), fg=mv.hex_rgba(ln.get("color"), (255, 255, 255, 255)), plain=True)
            L["y"] = int(self.H * float(ln.get("y", 0.5)) - L["h"] / 2)
            layers.append(L)
        layers += self.caption_layers(sc["id"], sc)
        self.encode(sc["id"], ["-f", "lavfi", "-i", f"color=c={bg}:s={self.W}x{self.H}:d={dur}:r={self.FPS}"], [], "0:v", layers, dur, out)

    def seg_waveform(self, sc, out):
        """Audio-driven scene (a call, a voiceover): title, live waveform, pills from a transcript."""
        dur, aud = float(sc["dur"]), self.asset(sc, "audio")
        col = mv.hex_rgb_str(sc.get("color", "#89dcb7"))
        wh, wy = int(self.H * 0.22), int(self.H * 0.42)
        ww = min(int(self.W * 0.75), 1200)   # showwaves needs >= 1 audio sample per pixel column: 48000 / (fps * ww)
        bg_in = self.video_in(self.asset(sc, "bg_asset"), dur) if sc.get("bg_asset") else ["-f", "lavfi", "-i", f"color=c={mv.hex_rgb_str(sc.get('bg', '#12162a'))}:s={self.W}x{self.H}:d={dur}:r={self.FPS}"]
        parts = [self.fit_filter(0, "bg", "cover", dur)] if sc.get("bg_asset") else ["[0:v]null[bg]"]
        # colour the wave by alpha-merging a white wave over a solid colour: showwaves' own colours are unreliable
        parts += [f"[1:a]aresample=48000,showwaves=s={ww}x{wh}:mode=cline:rate={self.FPS}:colors=white,format=gray[g]",
                  f"color=c={col}:s={ww}x{wh}:r={self.FPS}:d={dur},format=rgba[col]",
                  "[col][g]alphamerge[wv]", f"[bg][wv]overlay=(W-w)/2:{wy}[b0]"]
        layers = []
        if sc.get("title"):
            L = self.layer(sc["id"], "title", sc["title"], None, None, int(self.H * 0.18), size=int(self.H * 0.07), plain=True)
            layers.append(L)
        if sc.get("subtitle"):
            L = self.layer(sc["id"], "sub", sc["subtitle"], None, None, int(self.H * 0.27), size=int(self.H * 0.035),
                           fg=(200, 210, 205, 255), plain=True)
            layers.append(L)
        layers += self.caption_layers(sc["id"], sc)
        self.encode(sc["id"], [*bg_in, "-t", f"{dur}", "-i", str(aud)], parts, "b0", layers, dur, out)

    def seg_split(self, sc, out):
        """Side by side, e.g. BEFORE | AFTER, each cover-cropped to half the frame."""
        dur, half = float(sc["dur"]), self.W // 2
        left, right = self.asset(sc, "left"), self.asset(sc, "right")
        st = sc.get("start", [0.0, 0.0])
        inputs = self.video_in(left, dur, float(st[0])) + self.video_in(right, dur, float(st[1]))
        parts = [self.fit_filter(0, "l", "cover", dur, w=half), self.fit_filter(1, "r", "cover", dur, w=half), "[l][r]hstack=inputs=2[bg]"]
        layers = []
        for i, label in enumerate(sc.get("labels", ["BEFORE", "AFTER"])):
            layers.append(self.layer(sc["id"], f"lab{i}", label, 0.2, dur - 0.6, int(self.H * 0.05), x=i * half, width=half,
                                     size=int(self.H * 0.035)))
        layers += self.caption_layers(sc["id"], sc)
        self.encode(sc["id"], inputs, parts, "bg", layers, dur, out)

    KINDS = {"still": "seg_still", "clip": "seg_clip", "fill": "seg_clip", "raw": "seg_clip", "card": "seg_card",
             "waveform": "seg_waveform", "split": "seg_split"}

    # ── caching ──
    def scene_hash(self, sc: dict) -> str:
        deps = []

        def walk(v):
            if isinstance(v, str) and len(v) < 300:
                p = self.resolve(v)
                if p.is_file():
                    st = p.stat()
                    deps.append((str(p), st.st_mtime_ns, st.st_size))
            elif isinstance(v, dict):
                for x in v.values():
                    walk(x)
            elif isinstance(v, list):
                for x in v:
                    walk(x)
        walk(sc)
        style = [self.W, self.H, self.FPS, self.BG, self.cap_size, self.cap_y, self.cap_fg, self.cap_bg]
        return hashlib.sha1(json.dumps([sc, deps, style], sort_keys=True, default=str).encode()).hexdigest()[:10]

    def segment(self, sc: dict) -> pathlib.Path:
        kind = sc["kind"]
        if kind not in self.KINDS:
            raise SystemExit(f"scene '{sc['id']}': unknown kind '{kind}'. Kinds: {', '.join(self.KINDS)}")
        out = self.seg_dir / f"{sc['id']}.{self.scene_hash(sc)}.mp4"
        if out.exists():
            print("cached", sc["id"])
            return out
        for old in self.seg_dir.glob(f"{sc['id']}.*.mp4"):
            old.unlink()
        print(f"rendering {sc['id']} ({kind}, {sc['dur']}s)...", flush=True)
        getattr(self, self.KINDS[kind])(sc, out)
        return out

    # ── whole film ──
    def build(self, only: list | None = None, review: bool = False) -> pathlib.Path | None:
        mv.need_ffmpeg()
        scenes = self.spec["scenes"]
        ids = [s["id"] for s in scenes]
        if len(set(ids)) != len(ids):
            raise SystemExit("scene ids must be unique")
        for s in scenes:
            if not re.fullmatch(r"[A-Za-z0-9_\-]+", s["id"]):
                raise SystemExit(f"scene id '{s['id']}' may only contain letters, digits, _ and -")
        if only:
            for s in scenes:
                if s["id"] in only:
                    print("->", self.segment(s))
            return None

        segs = [self.segment(s) for s in scenes]
        durs = [float(s["dur"]) for s in scenes]
        xfs = [0.0] + [0.04 if s.get("xin") == "cut" else float(s.get("xf", self.XF)) for s in scenes[1:]]
        trans = [self.TRANS] + [("fade" if s.get("xin") == "cut" else s.get("xin", self.TRANS)) for s in scenes[1:]]
        starts = [0.0]
        for i in range(1, len(scenes)):
            starts.append(starts[-1] + durs[i - 1] - xfs[i])
        total = starts[-1] + durs[-1]

        inputs = []
        for sg in segs:
            inputs += ["-i", str(sg)]
        parts = [f"[{i}:v]fps={self.FPS},settb=AVTB,format=yuv420p[v{i}]" for i in range(len(segs))]
        prev = "v0"
        length = durs[0]
        for i in range(1, len(segs)):
            off = length - xfs[i]
            parts.append(f"[{prev}][v{i}]xfade=transition={trans[i]}:duration={xfs[i]}:offset={off:.3f}[x{i}]")
            prev = f"x{i}"
            length = length + durs[i] - xfs[i]
        silent = mv.WORK / f"{self.name}_silent.mp4"
        mv.run("video", ["ffmpeg", "-y", "-nostdin", "-v", "error", *inputs, "-filter_complex", ";".join(parts), "-map", f"[{prev}]",
                         "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", str(silent)])

        tracks = self.audio_tracks(scenes, starts)
        final = mv.OUT / self.spec.get("out", f"{self.name}.mp4")
        music = self.spec.get("music")
        if tracks or music:
            self.mux(silent, final, tracks, music, length)
        else:
            mv.run("copy", ["ffmpeg", "-y", "-nostdin", "-v", "error", "-i", str(silent), "-c", "copy", str(final)])
        print(f"DONE -> {final}  (~{length:.1f}s, {len(scenes)} scenes)")
        self.storyboard(scenes, starts, durs, length, final)
        if review:
            self.review_frames(final, scenes, starts, durs)
        return final

    def audio_tracks(self, scenes, starts) -> list:
        tracks = []
        for a in self.spec.get("audio_tracks", []):
            tracks.append((self.resolve(a["file"]), float(a.get("at", 0.0)), float(a.get("gain", 1.0))))
        for sc, st in zip(scenes, starts):
            if sc["kind"] == "waveform":
                tracks.append((self.asset(sc, "audio"), st + float(sc.get("audio_offset", 0.0)), float(sc.get("gain", 1.0))))
            for a in sc.get("tracks", []):   # extra sounds for any scene: [{"file","offset","gain"}] or ["file", offset]
                f, off, g = (a["file"], a.get("offset", 0.0), a.get("gain", 1.0)) if isinstance(a, dict) else (a[0], a[1], 1.0)
                tracks.append((self.resolve(f), st + float(off), float(g)))
        for f, _, _ in tracks:
            if not f.exists():
                raise SystemExit(f"audio file not found: {f}")
        return tracks

    def mux(self, silent, final, tracks, music, length):
        ain, ach, labels = [], [], []
        for j, (f, at, gain) in enumerate(tracks):
            ain += ["-i", str(f)]
            ms = int(at * 1000)
            ach.append(f"[{j + 1}:a]aresample=44100,aformat=channel_layouts=stereo,volume={gain},adelay={ms}|{ms}[a{j}]")
            labels.append(f"[a{j}]")
        if music:
            mf = self.resolve(music["file"])
            ain += ["-stream_loop", "-1", "-i", str(mf)]
            k = len(tracks)
            g = float(music.get("gain", 0.15))
            ach.append(f"[{k + 1}:a]aresample=44100,aformat=channel_layouts=stereo,volume={g},atrim=0:{length:.2f},afade=t=out:st={max(0, length - 2):.2f}:d=2[a{k}]")
            labels.append(f"[a{k}]")
        ach.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0:dropout_transition=0,apad=whole_dur={length:.2f}[a]")
        mv.run("mux", ["ffmpeg", "-y", "-nostdin", "-v", "error", "-i", str(silent), *ain, "-filter_complex", ";".join(ach), "-map", "0:v",
                       "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", f"{length:.2f}", str(final)])

    def storyboard(self, scenes, starts, durs, total, final):
        rows = []
        for i, sc in enumerate(scenes):
            caps = "<br>".join(f'"{c[0]}"' for c in self.caps_of(sc)) or "-"
            asset = sc.get("asset") or sc.get("audio") or sc.get("left") or "(generated)"
            rows.append(f"| {i + 1} | {sc.get('act', '')} | `{sc['id']}` | {sc['kind']} | {starts[i]:.1f}s | {durs[i]:.1f}s | {caps} | `{asset}` | {sc.get('note', '')} |")
        doc = (f"# {self.name} - storyboard\n\n> AUTO-GENERATED by tools/compose.py from {self.spec_path.name}. Do not hand-edit the table:\n"
               f"> edit the spec and re-render.\n\n**Film:** `{final}`  (~{total:.1f}s, {len(scenes)} scenes, {self.W}x{self.H} @ {self.FPS}fps)\n\n"
               "| # | Act | id | kind | start | dur | captions | asset | note |\n|---|-----|----|------|-------|-----|----------|-------|------|\n" + "\n".join(rows) + "\n")
        sb = mv.OUT / f"{self.name}.storyboard.md"
        sb.write_text(doc)
        print("storyboard ->", sb)

    def review_frames(self, final, scenes, starts, durs):
        """One frame per scene (mid-scene) + a contact sheet, because an agent cannot watch an mp4."""
        from PIL import Image, ImageDraw
        d = mv.OUT / f"{self.name}_review"
        d.mkdir(exist_ok=True)
        frames = []
        for i, (sc, st, du) in enumerate(zip(scenes, starts, durs)):
            p = d / f"{i + 1:02d}_{sc['id']}.png"
            mv.run("frame", ["ffmpeg", "-y", "-nostdin", "-v", "error", "-ss", f"{st + du * 0.55:.2f}", "-i", str(final),
                             "-frames:v", "1", "-vf", "scale=640:-1", str(p)], quiet=True)
            frames.append((sc["id"], p))
        cols = min(3, len(frames))
        rows = (len(frames) + cols - 1) // cols
        thumbs = [Image.open(p) for _, p in frames]
        w, h = thumbs[0].size
        sheet = Image.new("RGB", (cols * w, rows * (h + 26)), (20, 20, 24))
        dr = ImageDraw.Draw(sheet)
        for i, ((sid, _), im) in enumerate(zip(frames, thumbs)):
            x, y = (i % cols) * w, (i // cols) * (h + 26)
            sheet.paste(im, (x, y + 26))
            dr.text((x + 8, y + 6), f"{i + 1}. {sid}", fill=(230, 230, 230))
        sheet.save(d / "contact.png")
        print("review frames ->", d, "(contact.png = all scenes at a glance)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec")
    ap.add_argument("--only", help="comma-separated scene ids: render just those segments")
    ap.add_argument("--review", action="store_true", help="dump a frame per scene and a contact sheet")
    a = ap.parse_args()
    mv.ensure_dirs()
    Film(pathlib.Path(a.spec)).build(a.only.split(",") if a.only else None, a.review)


if __name__ == "__main__":
    main()
