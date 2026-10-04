#!/usr/bin/env python3
"""Draw highlights on footage: glowing trails, pulsing rings, boxes, and slow motion. No text on the picture
(captions belong on the caption pages, tools/reel.py).

  ./run.sh tools/annotate.py in.mp4 spec.json out.mp4

spec.json (coordinates in the source video's pixels, frames are source frame numbers):
{
  "color": "#FF8A3D", "ring_color": "#FFFFFF",
  "trails": [ { "points": [[120, 400, 300], [121, 410, 296]], "tail": 0, "width": 6 } ],   [frame, x, y]; tail 0 = whole path so far
  "rings":  [ { "frame": 150, "x": 700, "y": 480, "r": 30 } ],                              appears at that frame and pulses once
  "boxes":  [ { "from": 100, "to": 160, "x": 600, "y": 300, "w": 120, "h": 200 } ],
  "slow":   { "from": 140, "factor": 3 }                                                    every frame from there is written 3 times
}
Also writes <out>.json with the output-frame index of each ring and the slow-motion start, so captions can switch at
the right second: seconds = index / fps. Needs opencv-python and numpy.
"""
import json, os, subprocess, sys
import cv2
import numpy as np


def bgr(h):
    h = h.lstrip('#')
    return (int(h[4:6], 16), int(h[2:4], 16), int(h[0:2], 16))


def glow(im, pts, color, width):
    if len(pts) < 2:
        return
    layer = np.zeros_like(im)
    for a, b in zip(pts, pts[1:]):
        cv2.line(layer, a, b, color, width + 10, cv2.LINE_AA)
    layer = cv2.GaussianBlur(layer, (0, 0), 8)
    cv2.addWeighted(im, 1.0, layer, 0.55, 0, im)
    for a, b in zip(pts, pts[1:]):
        cv2.line(im, a, b, (20, 22, 20), width + 4, cv2.LINE_AA)
    for a, b in zip(pts, pts[1:]):
        cv2.line(im, a, b, color, width, cv2.LINE_AA)


def main(src, spec_file, out):
    spec = json.load(open(spec_file))
    col, rcol = bgr(spec.get('color', '#FF8A3D')), bgr(spec.get('ring_color', '#FFFFFF'))
    cap = cv2.VideoCapture(src)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    W, H = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    tmp = out + '.tmp.mp4'
    vw = cv2.VideoWriter(tmp, cv2.VideoWriter_fourcc(*'mp4v'), fps, (W, H))
    slow = spec.get('slow')
    n_out, marks, f = 0, {'rings': {}}, 0
    while True:
        ok, im = cap.read()
        if not ok:
            break
        for t in spec.get('trails', []):
            pts = [(int(x), int(y)) for fr, x, y in t['points'] if fr <= f]
            if t.get('tail'):
                pts = pts[-t['tail']:]
            glow(im, pts, col, t.get('width', 6))
            if pts:
                cv2.circle(im, pts[-1], 12, (20, 22, 20), -1, cv2.LINE_AA)
                cv2.circle(im, pts[-1], 9, col, -1, cv2.LINE_AA)
        for k, r in enumerate(spec.get('rings', [])):
            if f >= r['frame']:
                g = min(1.0, (f - r['frame']) / 6.0)
                rr = int(r.get('r', 30) * (0.55 + 0.45 * g))
                cv2.circle(im, (int(r['x']), int(r['y'])), rr, (20, 22, 20), 8, cv2.LINE_AA)
                cv2.circle(im, (int(r['x']), int(r['y'])), rr, rcol, 4, cv2.LINE_AA)
        for bx in spec.get('boxes', []):
            if bx['from'] <= f <= bx['to']:
                cv2.rectangle(im, (bx['x'], bx['y']), (bx['x'] + bx['w'], bx['y'] + bx['h']), col, 4, cv2.LINE_AA)
        for k, r in enumerate(spec.get('rings', [])):
            if f == r['frame']:
                marks['rings'][k] = n_out
        if slow and f == slow['from']:
            marks['slow'] = n_out
        reps = slow['factor'] if slow and f >= slow['from'] else 1
        for _ in range(reps):
            vw.write(im)
            n_out += 1
        f += 1
    vw.release()
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', tmp, '-c:v', 'libx264', '-crf', '19', '-pix_fmt', 'yuv420p', out], check=True)
    os.unlink(tmp)
    marks.update({'fps': fps, 'frames': n_out})
    json.dump(marks, open(out + '.json', 'w'), indent=1)
    print(f'wrote {out}: {n_out} frames at {fps:g} fps; marks in {out}.json')


if __name__ == '__main__':
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
