#!/usr/bin/env python3
"""Setup check. Ends with READY or says what to run.   ./run.sh tools/doctor.py"""
import os, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); KIT = os.path.dirname(HERE)
bad = 0


def row(ok, name, fix=''):
    global bad
    bad += (not ok)
    print(('ok    ' if ok else 'FAIL  ') + name + ('' if ok else f'\n      fix: {fix}'))


def run(*c):
    try:
        return subprocess.run(c, capture_output=True, text=True, timeout=60, cwd=KIT)
    except Exception as e:
        return subprocess.CompletedProcess(c, 1, '', str(e))


row(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'ffmpeg + ffprobe', 'bash bootstrap.sh')
row(shutil.which('node') is not None, 'node', 'bash bootstrap.sh')
for mod in ('PIL', 'numpy', 'cv2'):
    try:
        __import__(mod); row(True, f'python: {mod}')
    except Exception:
        row(False, f'python: {mod}', 'bash bootstrap.sh (installs requirements.txt into .venv; run through ./run.sh)')
t = os.path.join(tempfile.mkdtemp(), 'x.png')
with open(os.path.join(os.path.dirname(t), 'x.html'), 'w') as f:
    f.write('<html><body style="background:#123">ok</body></html>')
import json
json.dump([{'html': os.path.join(os.path.dirname(t), 'x.html'), 'out': t, 'w': 200, 'h': 120}], open(os.path.join(os.path.dirname(t), 'j.json'), 'w'))
r = run('node', os.path.join(HERE, 'render.js'), 'shot', os.path.join(os.path.dirname(t), 'j.json'))
row(r.returncode == 0 and os.path.exists(t), 'headless browser renders a page',
    'bash bootstrap.sh, or set PW_MODULE / CHROME_BIN to an existing Playwright install. ' + (r.stderr or '')[-200:])
print('info  keys (names only, values never shown): ' + ', '.join(
    f'{k}={"set" if os.environ.get(k) else "not set"}' for k in ('ELEVENLABS_API_KEY', 'GEMINI_API_KEY', 'XAI_API_KEY')))
print('info  brand file: ' + ('brand/brand.json' if os.path.exists(os.path.join(KIT, 'brand', 'brand.json')) else 'brand/brand.example.json (copy it to brand.json and fill it in: see brand/BRAND-INTAKE.md)'))
print('\nREADY' if not bad else f'\nNOT READY: {bad} problem(s)')
sys.exit(1 if bad else 0)
