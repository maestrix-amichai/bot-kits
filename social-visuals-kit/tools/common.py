#!/usr/bin/env python3
"""Shared helpers: brand loading, HTML building blocks, Playwright rendering, ffmpeg helpers."""
import base64, html, json, mimetypes, os, re, subprocess, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
SIZES = {'square': (1080, 1080), 'portrait': (1080, 1350), 'story': (1080, 1920),
         'landscape': (1600, 900), 'linkedin': (1200, 627), 'og': (1200, 630), 'wide': (1600, 1160)}
FALL = {'display': 'Georgia,serif', 'body': 'system-ui,sans-serif', 'mono': 'ui-monospace,Menlo,monospace'}


def parse_size(s):
    if s in SIZES:
        return SIZES[s]
    w, h = s.lower().split('x')
    return int(w), int(h)


def load_brand(path=None):
    path = path or os.environ.get('BRAND') or os.path.join(KIT, 'brand', 'brand.json')
    if not os.path.exists(path):
        path = os.path.join(KIT, 'brand', 'brand.example.json')
    with open(path) as f:
        b = json.load(f)
    b['_dir'] = os.path.dirname(os.path.abspath(path))
    return b


def resolve(b, p):
    return p if os.path.isabs(p) else os.path.join(b['_dir'], p)


def data_uri(path):
    mime = mimetypes.guess_type(path)[0] or 'application/octet-stream'
    with open(path, 'rb') as f:
        return f'data:{mime};base64,' + base64.b64encode(f.read()).decode()


def esc(t):
    """Escape text for HTML. *word* becomes accent-coloured emphasis, newline becomes a line break."""
    t = html.escape(str(t if t is not None else ''))
    t = re.sub(r'\*(.+?)\*', r'<b>\1</b>', t)
    return t.replace('\n', '<br>')


def fonts_css(b):
    fams, faces = [], ''
    for _, f in b['fonts'].items():
        if f.get('file'):
            faces += (f"@font-face{{font-family:'{f['family']}';src:url({data_uri(resolve(b, f['file']))});"
                      f"font-weight:{f.get('weight', '400')}}}")
        else:
            fams.append(f"family={f['family'].replace(' ', '+')}:wght@{f.get('weights', '400;600')}")
    imp = ("@import url('https://fonts.googleapis.com/css2?" + '&'.join(fams) + "&display=swap');") if fams else ''
    return imp + faces


def base_css(b, W, H):
    c = b['colors']
    u = W / 1080
    fam = ''.join(f"--{r}:'{f['family']}',{f.get('fallback', FALL.get(r, 'sans-serif'))};" for r, f in b['fonts'].items())
    return fonts_css(b) + f"""
:root{{--u:{u:.4f}px;{fam}--bg:{c['bg']};--fg:{c['fg']};--muted:{c['muted']};--accent:{c['accent']};--accent-ink:{c['accent_ink']};--panel:{c['panel']};--rule:{c['rule']};--soft:{c['soft']}}}
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:{W}px;height:{H}px}}
body{{position:relative;overflow:hidden;color:var(--fg);font-family:var(--body)}}
.bar{{display:flex;align-items:center;gap:calc(14*var(--u));font:500 calc(19*var(--u)) var(--mono);letter-spacing:.16em;text-transform:uppercase;color:var(--muted);white-space:nowrap}}
.bar img{{height:calc(46*var(--u));width:auto;border-radius:calc(10*var(--u))}}
.kicker{{font:500 calc(22*var(--u)) var(--mono);letter-spacing:.16em;text-transform:uppercase;color:var(--accent)}}
.headline{{font-family:var(--display);font-weight:600;letter-spacing:-.015em;line-height:1.04}}
.headline b,.body b{{color:var(--accent);font-weight:inherit}}
.badge{{display:inline-block;font:500 calc(22*var(--u)) var(--mono);letter-spacing:.08em;color:var(--accent-ink);background:var(--soft);border-radius:999px;padding:calc(11*var(--u)) calc(22*var(--u));white-space:nowrap}}
.credit{{font:400 calc(16*var(--u)) var(--mono);letter-spacing:.06em;color:var(--muted)}}
"""


def bar_html(b):
    logo = ''
    p = b.get('logo')
    if p and os.path.exists(resolve(b, p)):
        logo = f'<img src="{data_uri(resolve(b, p))}">'
    return f'<div class="bar">{logo}{esc(b.get("name", ""))}</div>'


def shoot(jobs):
    """jobs: [{html, out, w, h, scale?, transparent?}] -> PNG files, one browser launch (tools/render.js)."""
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as jf:
        json.dump(jobs, jf)
    try:
        subprocess.run(['node', os.path.join(HERE, 'render.js'), 'shot', jf.name], check=True)
    finally:
        os.unlink(jf.name)


def write_html(path, body_html, css):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'w') as f:
        f.write(f'<!doctype html><html><head><meta charset="utf-8"><style>{css}</style></head><body>{body_html}</body></html>')
    return path


def ff(*args):
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', *args], check=True)


def probe(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries',
                          'stream=codec_type,codec_name,width,height,r_frame_rate,pix_fmt:format=duration,size',
                          '-of', 'json', path], capture_output=True, text=True, check=True).stdout
    j = json.loads(out)
    v = next((s for s in j['streams'] if s['codec_type'] == 'video'), {})
    a = next((s for s in j['streams'] if s['codec_type'] == 'audio'), None)
    n, d = (v.get('r_frame_rate') or '0/1').split('/')
    return {'width': v.get('width'), 'height': v.get('height'), 'fps': round(int(n) / max(int(d), 1), 2),
            'vcodec': v.get('codec_name'), 'pix_fmt': v.get('pix_fmt'), 'acodec': a and a.get('codec_name'),
            'duration': float(j['format'].get('duration', 0)), 'mb': round(int(j['format'].get('size', 0)) / 1e6, 2)}
