#!/usr/bin/env python3
"""Record an animated HTML page to mp4, optionally with voiceover and a timeline the page follows.

  ./run.sh tools/record.py --html templates/explainer.html --size 1080x1920 \
      --timeline work/vo/timeline.json --audio work/vo/vo.m4a --out out/explainer.mp4

The page animates itself with JavaScript and reads window.TIMELINE ({"beats": {id: {start, dur}}, "total": s}),
injected before the page loads; see templates/explainer.html. Recording length = timeline total (or --seconds).
Silent draft first: omit --audio to check the animation, add voiceover once the silent cut is approved.
"""
import argparse, json, os, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--html', required=True)
    ap.add_argument('--size', default='story')
    ap.add_argument('--seconds', type=float)
    ap.add_argument('--timeline')
    ap.add_argument('--audio')
    ap.add_argument('--out', required=True)
    ap.add_argument('--fps', type=int, default=30)
    a = ap.parse_args()
    W, H = parse_size(a.size)
    tl = json.load(open(a.timeline)) if a.timeline else {'beats': {}, 'total': a.seconds or 10}
    secs = a.seconds or tl['total']
    work = tempfile.mkdtemp(prefix='rec_')
    raw = os.path.join(work, 'raw.webm')
    job = {'html': a.html, 'out': raw, 'w': W, 'h': H, 'seconds': secs, 'dir': work,
           'init': f'window.TIMELINE={json.dumps(tl)};'}
    jf = os.path.join(work, 'job.json')
    json.dump(job, open(jf, 'w'))
    subprocess.run(['node', os.path.join(HERE, 'render.js'), 'video', jf], check=True)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    cmd = ['-i', raw] + (['-i', a.audio] if a.audio else []) + \
          ['-c:v', 'libx264', '-crf', '19', '-pix_fmt', 'yuv420p', '-r', str(a.fps)] + \
          (['-c:a', 'aac', '-af', 'apad', '-t', f'{secs:.3f}'] if a.audio else ['-an']) + ['-movflags', '+faststart', a.out]
    ff(*cmd)
    i = probe(a.out)
    print(f"wrote {a.out}  {i['width']}x{i['height']}  {i['duration']:.1f}s  {i['mb']} MB")
