#!/usr/bin/env python3
"""Voiceover: one audio file per line, measured, joined with gaps; writes the timeline an animation follows.

  ./run.sh tools/vo.py say "Text" out/line.mp3 [--voice ID]
  ./run.sh tools/vo.py timeline script.json --out-dir work/vo [--voice ID] [--gap 0.8] [--fake]

script.json: [ {"id": "hook", "text": "..."}, {"id": "turn", "text": "..."} ]
Writes <out-dir>/vo-<id>.mp3 (skipped if already present: never pay twice for a line you have), <out-dir>/vo.m4a
and <out-dir>/timeline.json  {"beats": {"hook": {"start": 0.0, "dur": 2.1}, ...}, "total": 12.3}.
--fake makes silent placeholders sized by word count so layouts and timing can be tested without spending anything.

Provider: ElevenLabs, key in env ELEVENLABS_API_KEY (inject it with your secrets manager; never put it in a file).
Voice: --voice or env VOICE_ID. Model: env VOICE_MODEL (default eleven_multilingual_v2). To use another provider,
replace tts() only: it must write an mp3 for a text.
"""
import argparse, json, os, subprocess, sys, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ff, probe


def tts(text, out, voice, fake=False):
    if fake:
        secs = max(0.8, 0.38 * len(text.split()))
        ff('-f', 'lavfi', '-i', 'anullsrc=r=24000:cl=mono', '-t', f'{secs:.2f}', '-c:a', 'libmp3lame', out)
        return
    key = os.environ.get('ELEVENLABS_API_KEY')
    if not key:
        sys.exit('ELEVENLABS_API_KEY is not set (inject it through your secrets manager) or use --fake')
    if not voice:
        sys.exit('pass --voice <voice id> or set VOICE_ID')
    req = urllib.request.Request(
        f'https://api.elevenlabs.io/v1/text-to-speech/{voice}', method='POST',
        headers={'xi-api-key': key, 'Content-Type': 'application/json', 'Accept': 'audio/mpeg'},
        data=json.dumps({'text': text, 'model_id': os.environ.get('VOICE_MODEL', 'eleven_multilingual_v2')}).encode())
    with urllib.request.urlopen(req, timeout=120) as r, open(out, 'wb') as f:
        f.write(r.read())


def timeline(script, out_dir, voice, gap, fake):
    os.makedirs(out_dir, exist_ok=True)
    start, t, files, beats = {}, 0.0, [], {}
    for line in script:
        mp3 = os.path.join(out_dir, f"vo-{line['id']}.mp3")
        if not os.path.exists(mp3):
            tts(line['text'], mp3, voice, fake)
        d = probe(mp3)['duration']
        beats[line['id']] = {'start': round(t, 3), 'dur': round(d, 3)}
        files.append((mp3, t))
        t += d + gap
    total = round(t + 0.6, 3)
    ins, fc = [], []
    for k, (f, s) in enumerate(files):
        ins += ['-i', f]
        ms = int(s * 1000)
        fc.append(f'[{k}:a]adelay={ms}|{ms}[a{k}]')
    mix = ''.join(f'[a{k}]' for k in range(len(files))) + f'amix=inputs={len(files)}:normalize=0[a]'
    ff(*ins, '-filter_complex', ';'.join(fc) + ';' + mix, '-map', '[a]', '-c:a', 'aac', os.path.join(out_dir, 'vo.m4a'))
    tl = {'beats': beats, 'total': total}
    with open(os.path.join(out_dir, 'timeline.json'), 'w') as f:
        json.dump(tl, f, indent=1)
    return tl


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('say'); s.add_argument('text'); s.add_argument('out'); s.add_argument('--voice', default=os.environ.get('VOICE_ID')); s.add_argument('--fake', action='store_true')
    t = sub.add_parser('timeline'); t.add_argument('script'); t.add_argument('--out-dir', default='work/vo'); t.add_argument('--voice', default=os.environ.get('VOICE_ID')); t.add_argument('--gap', type=float, default=0.8); t.add_argument('--fake', action='store_true')
    a = ap.parse_args()
    if a.cmd == 'say':
        tts(a.text, a.out, a.voice, a.fake); print(a.out)
    else:
        print(json.dumps(timeline(json.load(open(a.script)), a.out_dir, a.voice, a.gap, a.fake), indent=1))
