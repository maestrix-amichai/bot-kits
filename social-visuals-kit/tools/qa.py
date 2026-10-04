#!/usr/bin/env python3
"""Look at a video you cannot watch, and check it against an export preset.

  ./run.sh tools/qa.py probe  file.mp4
  ./run.sh tools/qa.py sheet  file.mp4 out/sheet.png [--every 2.5] [--cols 6] [--width 480]
  ./run.sh tools/qa.py frames file.mp4 out/frames 1.0 4.5 9.0
  ./run.sh tools/qa.py check  file.mp4 feed_portrait        (presets in tools/platforms.json)

Read the sheet and frames with your image viewer. Check: captions wrap cleanly, nothing important is cut off or
hidden, overlays sit inside the frame, the first frame already says what the post is about, the last frame has the
call to action, and the duration and size are what you meant. State plainly what you could not verify (audio sync,
playback in the real app).
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *


def check(path, preset):
    pf = json.load(open(os.path.join(HERE, 'platforms.json')))
    if preset not in pf or preset.startswith('_'):
        sys.exit('presets: ' + ', '.join(k for k in pf if not k.startswith('_')))
    p, i = pf[preset], probe(path)
    is_img = path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
    rows = [('size', [i['width'], i['height']] == p['size'], f"{i['width']}x{i['height']} (want {p['size'][0]}x{p['size'][1]})")]
    if not is_img:
        rows += [('duration', 0 < i['duration'] <= p['house_max_seconds'], f"{i['duration']:.1f}s (house max {p['house_max_seconds']}s)"),
                 ('codec', i['vcodec'] == 'h264' and i['pix_fmt'] == 'yuv420p', f"{i['vcodec']} {i['pix_fmt']} (want h264 yuv420p)"),
                 ('audio', i['acodec'] in (None, 'aac'), f"{i['acodec']} (want aac or none)")]
    rows.append(('file size', i['mb'] <= p['house_max_mb'], f"{i['mb']} MB (house max {p['house_max_mb']} MB)"))
    ok = True
    for name, good, msg in rows:
        ok &= good
        print(('PASS ' if good else 'FAIL ') + name + ': ' + msg)
    print('OK for ' + p['label'] if ok else 'NOT READY: fix the FAIL lines above')
    return ok


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('probe').add_argument('file')
    s = sub.add_parser('sheet'); s.add_argument('file'); s.add_argument('out'); s.add_argument('--every', type=float, default=2.5); s.add_argument('--cols', type=int, default=6); s.add_argument('--width', type=int, default=480)
    fr = sub.add_parser('frames'); fr.add_argument('file'); fr.add_argument('outdir'); fr.add_argument('times', nargs='+', type=float)
    c = sub.add_parser('check'); c.add_argument('file'); c.add_argument('preset')
    a = ap.parse_args()
    if a.cmd == 'probe':
        print(json.dumps(probe(a.file), indent=1))
    elif a.cmd == 'sheet':
        i = probe(a.file)
        h = round(a.width * i['height'] / i['width'] / 2) * 2
        n = max(1, int(i['duration'] / a.every) + 1)
        rows = -(-n // a.cols)
        ff('-i', a.file, '-vf', f'fps=1/{a.every},scale={a.width}:{h},tile={a.cols}x{rows}', '-frames:v', '1', a.out)
        print(a.out)
    elif a.cmd == 'frames':
        os.makedirs(a.outdir, exist_ok=True)
        for t in a.times:
            out = os.path.join(a.outdir, f'frame_{t:07.2f}.png')
            ff('-ss', str(t), '-i', a.file, '-frames:v', '1', out)
            print(out)
    else:
        sys.exit(0 if check(a.file, a.preset) else 1)
