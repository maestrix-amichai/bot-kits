#!/usr/bin/env python3
"""Captioned footage reel from a JSON spec: title cards, footage with caption states, end card.

  ./run.sh tools/reel.py examples/hello/reel.json [--canvas 1600x1160] [--out out/other.mp4]

Spec (paths relative to the kit folder or absolute):
{
  "brand": "brand/brand.json",            optional
  "canvas": [1080, 1350], "fps": 30,
  "out": "out/reel.mp4",
  "credit": "FOOTAGE: ...",               shown on every caption page unless a state overrides it
  "layout": { "top": 216, "window_h": 608 },   optional; defaults: top = 20% of width when a title is used else 0,
                                                window_h = width * 9/16. Caption area is everything below the window.
  "segments": [
    { "type": "card", "template": "title", "fields": { "kicker": "...", "headline": "..." }, "seconds": 3 },
    { "type": "footage", "src": "clip.mp4", "start": 0, "seconds": 8, "hold": 3, "crop": "W:H:x:y",
      "title": "Section title shown above the footage",
      "states": [ { "at": 0, "kicker": "THE RALLY", "body": "What is on screen" },
                  { "at": 8, "kicker": "THE CALL", "headline": "Point to *the near pair*", "body": "Why", "badge": "Checked" } ] }
  ],
  "audio": { "file": "vo.m4a" },           optional, muxed at the end
  "stills": [ { "segment": 1, "at": 9.0, "out": "out/poster.png" } ]   optional, frames for posters / email
}
A state shows from its "at" (seconds into the segment) until the next state's "at". Fields: kicker, headline, body, badge, credit.
The same spec renders in any shape: pass --canvas 1080x1920 for 9:16, 1600x1160 for an article column.
"""
import argparse, json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
import card


def caption_html(b, W, H, top, wh, title, st, credit):
    y0 = top + wh
    ph = H - y0
    strip = ph < 0.3 * W
    css = base_css(b, W, H) + """
.t{position:absolute;left:calc(56*var(--u));right:calc(56*var(--u));font-family:var(--display);font-weight:600;line-height:1.05;letter-spacing:-.01em}
.panel{position:absolute;left:calc(56*var(--u));right:calc(56*var(--u))}
.body{line-height:1.28}
"""
    parts = ''
    if top > 0:
        parts += f'<div style="position:absolute;left:calc(56*var(--u));top:calc(40*var(--u))">{bar_html(b)}</div>'
        if title:
            parts += f'<div class="t" style="top:calc(100*var(--u));font-size:calc(54*var(--u))">{esc(title)}</div>'
    kick = f'<div class="kicker" style="margin-bottom:calc(14*var(--u))">{esc(st.get("kicker"))}</div>' if st.get('kicker') else ''
    if strip:
        head = f'<div class="headline" style="font-size:calc(60*var(--u))">{esc(st["headline"])}</div>' if st.get('headline') else ''
        body = f'<div class="body" style="font-size:calc(34*var(--u));color:var(--fg)">{esc(st["body"])}</div>' if st.get('body') else ''
        right = (f'<div class="badge">{esc(st["badge"])}</div>' if st.get('badge') else '') + bar_html(b)
        parts += (f'<div class="panel" style="left:calc(48*var(--u));right:calc(48*var(--u));top:{y0}px;height:{ph}px;display:flex;align-items:center;justify-content:space-between;gap:calc(48*var(--u))">'
                  f'<div style="min-width:0">{kick}{head}{body}</div>'
                  f'<div style="flex:none;display:flex;flex-direction:column;align-items:flex-end;gap:calc(14*var(--u))">{right}<div class="credit">{esc(credit)}</div></div></div>')
    else:
        head = f'<div class="headline" style="font-size:calc(88*var(--u));margin-bottom:calc(22*var(--u))">{esc(st["headline"])}</div>' if st.get('headline') else ''
        bsz = 36 if st.get('headline') else 46
        body = f'<div class="body" style="font-size:calc({bsz}*var(--u))">{esc(st["body"])}</div>' if st.get('body') else ''
        badge = f'<div style="margin-top:calc(28*var(--u))"><span class="badge">{esc(st["badge"])}</span></div>' if st.get('badge') else ''
        parts += (f'<div class="panel" style="top:{y0 + round(44 * W / 1080)}px">{kick}{head}{body}{badge}</div>'
                  f'<div class="credit" style="position:absolute;left:calc(56*var(--u));bottom:calc(30*var(--u))">{esc(credit)}</div>')
    return css, parts


def build(spec, canvas=None, out=None):
    b = load_brand(spec.get('brand'))
    W, H = parse_size(canvas) if canvas else tuple(spec.get('canvas', [1080, 1350]))
    fps = spec.get('fps', 30)
    lay = spec.get('layout', {})
    has_title = any(s.get('title') for s in spec['segments'] if s['type'] == 'footage')
    top = lay.get('top', round(W * 0.2) if has_title else 0)
    wh = lay.get('window_h', round(W * 9 / 16))
    bg = b['colors']['bg'].lstrip('#')
    work = os.path.join(KIT, 'out', 'reel_work')
    os.makedirs(work, exist_ok=True)
    out = out or spec.get('out', 'out/reel.mp4')
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)

    jobs, plan = [], []
    for i, s in enumerate(spec['segments']):
        if s['type'] == 'card':
            f = dict(s.get('fields', {}))
            f.setdefault('credit', spec.get('credit', ''))
            css, body = card.html_for(s['template'], b, W, H, f)
            png = os.path.join(work, f'card_{i}.png')
            jobs.append({'html': write_html(os.path.join(work, f'card_{i}.html'), body, css), 'out': png, 'w': W, 'h': H})
            plan.append({'i': i, 'png': png})
        else:
            pages = []
            for k, st in enumerate(s['states']):
                css, body = caption_html(b, W, H, top, wh, s.get('title'), st, st.get('credit', s.get('credit', spec.get('credit', ''))))
                png = os.path.join(work, f'cap_{i}_{k}.png')
                jobs.append({'html': write_html(os.path.join(work, f'cap_{i}_{k}.html'), body, css), 'out': png, 'w': W, 'h': H, 'transparent': True})
                pages.append(png)
            plan.append({'i': i, 'pages': pages})
    shoot(jobs)

    segfiles = []
    for p in plan:
        i = p['i']; s = spec['segments'][i]; seg = os.path.join(work, f'seg_{i}.mp4')
        enc = ['-c:v', 'libx264', '-preset', 'medium', '-crf', '19', '-pix_fmt', 'yuv420p', '-r', str(fps), '-an']
        if s['type'] == 'card':
            sec = s.get('seconds', 3)
            ff('-loop', '1', '-t', str(sec), '-i', p['png'], '-vf', f'fps={fps},fade=in:st=0:d=0.4,format=yuv420p', *enc, seg)
        else:
            start = s.get('start', 0)
            secs = s.get('seconds') or max(0.1, probe(s['src'])['duration'] - start)
            hold = s.get('hold', 0)
            dur = round(secs + hold, 3)
            vf = (f"crop={s['crop']}," if s.get('crop') else '') + \
                 f"scale={W}:{wh}:force_original_aspect_ratio=decrease,pad={W}:{wh}:(ow-iw)/2:(oh-ih)/2:color=0x{bg}"
            if hold:
                vf += f',tpad=stop_mode=clone:stop_duration={hold}'
            vf += f',fps={fps},setsar=1'
            ins = ['-f', 'lavfi', '-i', f'color=c=0x{bg}:s={W}x{H}:r={fps}:d={dur}', '-ss', str(start), '-t', str(secs), '-i', s['src']]
            sts = sorted(s['states'], key=lambda x: x.get('at', 0))
            for png in p['pages']:
                ins += ['-loop', '1', '-t', str(dur), '-i', png]
            fc = f'[1:v]{vf}[v];[0:v][v]overlay=0:{top}:eof_action=pass[b0]'
            for k, st in enumerate(sts):
                a = 0 if k == 0 else st.get('at', 0)
                z = sts[k + 1].get('at', dur) if k + 1 < len(sts) else dur
                chain = 'format=rgba' + (f',fade=in:st={a}:d=0.2:alpha=1' if a > 0 else '')
                fc += f";[{k + 2}:v]{chain}[o{k}];[b{k}][o{k}]overlay=0:0:enable='between(t,{a},{z})'[b{k + 1}]"
            ff(*ins, '-filter_complex', fc, '-map', f'[b{len(sts)}]', '-t', str(dur), *enc, seg)
        segfiles.append(seg)

    lst = os.path.join(work, 'list.txt')
    with open(lst, 'w') as f:
        f.write(''.join(f"file '{os.path.abspath(x)}'\n" for x in segfiles))
    audio = spec.get('audio', {}).get('file')
    tmp = out if not audio else os.path.join(work, 'noaudio.mp4')
    ff('-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', '-movflags', '+faststart', tmp)
    if audio:
        ff('-i', tmp, '-i', audio, '-c:v', 'copy', '-c:a', 'aac', '-shortest', '-movflags', '+faststart', out)
    for st in spec.get('stills', []):
        os.makedirs(os.path.dirname(os.path.abspath(st['out'])), exist_ok=True)
        ff('-ss', str(st['at']), '-i', segfiles[st['segment']], '-frames:v', '1', st['out'])
    info = probe(out)
    print(f"wrote {out}  {info['width']}x{info['height']}  {info['duration']:.1f}s  {info['mb']} MB")
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('spec')
    ap.add_argument('--canvas')
    ap.add_argument('--out')
    a = ap.parse_args()
    os.chdir(KIT)
    build(json.load(open(a.spec)), a.canvas, a.out)
