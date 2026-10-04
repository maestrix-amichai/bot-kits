#!/usr/bin/env python3
"""Designed still cards from the brand kit: title, quote, stat, compare, feature.

  ./run.sh tools/card.py title --size portrait --out out/c1.png \
      --set kicker="New this week" --set headline="Ship the *simple* version first" --set sub="And keep building"
  ./run.sh tools/card.py stat --size square --out out/c2.png --set number="3x" --set label="faster reviews"
  ./run.sh tools/card.py compare --json fields.json --out out/c3.png

Templates and fields (all optional unless noted):
  title    kicker, headline (required), sub
  quote    quote (required), who
  stat     number (required), label, note
  compare  title, left_label, left (lines), right_label, right (lines)      lines separated by \\n
  feature  kicker, headline (required), body, image (path)
Text: *word* is shown in the accent colour. Sizes: square portrait story landscape linkedin og wide, or WxH.
Brand: --brand path/to/brand.json (default brand/brand.json, else brand.example.json, or $BRAND).
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *


def _wrap(b, inner, css):
    foot_l = esc(b.get('handle') or b.get('site') or '')
    return css, f'<div class="wrap"><div class="top">{bar_html(b)}</div>{inner}<div class="foot"><div class="credit">{foot_l}</div><div class="credit">{esc(b.get("_credit", ""))}</div></div></div>'


CARD_CSS = """
.wrap{position:absolute;inset:0;padding:calc(72*var(--u));display:flex;flex-direction:column;background:var(--bg)}
.main{flex:1;display:flex;flex-direction:column;justify-content:center;gap:calc(30*var(--u))}
.foot{display:flex;justify-content:space-between;align-items:flex-end}
.sub{font-size:calc(46*var(--u));line-height:1.3;color:var(--muted);max-width:92%}
.body{font-size:calc(40*var(--u));line-height:1.35;color:var(--fg)}
.num{font-family:var(--display);font-weight:600;font-size:calc(300*var(--u));line-height:.9;letter-spacing:-.03em;color:var(--accent)}
.qmark{font-family:var(--display);font-size:calc(220*var(--u));line-height:.6;color:var(--accent)}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:calc(28*var(--u))}
.col{background:var(--panel);border:1px solid var(--rule);border-radius:calc(22*var(--u));padding:calc(34*var(--u));display:flex;flex-direction:column;gap:calc(18*var(--u))}
.col .kicker.m{color:var(--muted)}
.col p{font-size:calc(36*var(--u));line-height:1.3}
.shot{flex:none;height:46%;border-radius:calc(22*var(--u));background-size:cover;background-position:center;border:1px solid var(--rule)}
"""


def html_for(template, b, W, H, f):
    b = dict(b)
    b['_credit'] = f.get('credit', b.get('credit_default', ''))
    if template == 'title':
        inner = (f'<div class="main"><div class="kicker">{esc(f.get("kicker"))}</div>'
                 f'<div class="headline" style="font-size:calc(104*var(--u))">{esc(f["headline"])}</div>'
                 + (f'<div class="sub">{esc(f["sub"])}</div>' if f.get('sub') else '') + '</div>')
    elif template == 'quote':
        inner = (f'<div class="main"><div class="qmark">&ldquo;</div>'
                 f'<div class="headline" style="font-size:calc(76*var(--u))">{esc(f["quote"])}</div>'
                 + (f'<div class="kicker">{esc(f["who"])}</div>' if f.get('who') else '') + '</div>')
    elif template == 'stat':
        inner = (f'<div class="main"><div class="num">{esc(f["number"])}</div>'
                 f'<div class="headline" style="font-size:calc(70*var(--u))">{esc(f.get("label"))}</div>'
                 + (f'<div class="sub">{esc(f["note"])}</div>' if f.get('note') else '') + '</div>')
    elif template == 'compare':
        def col(label, lines, cls):
            ps = ''.join(f'<p>{esc(x)}</p>' for x in str(lines or '').split('\n') if x.strip())
            return f'<div class="col"><div class="kicker {cls}">{esc(label)}</div>{ps}</div>'
        inner = (f'<div class="main">' + (f'<div class="headline" style="font-size:calc(64*var(--u))">{esc(f["title"])}</div>' if f.get('title') else '')
                 + f'<div class="cols">{col(f.get("left_label"), f.get("left"), "m")}{col(f.get("right_label"), f.get("right"), "")}</div></div>')
    elif template == 'feature':
        img = ''
        if f.get('image'):
            img = f'<div class="shot" style="background-image:url({data_uri(f["image"])})"></div>'
        inner = (f'<div class="main" style="justify-content:flex-start;padding-top:calc(30*var(--u))">{img}'
                 f'<div class="kicker">{esc(f.get("kicker"))}</div>'
                 f'<div class="headline" style="font-size:calc(72*var(--u))">{esc(f["headline"])}</div>'
                 + (f'<div class="body">{esc(f["body"])}</div>' if f.get('body') else '') + '</div>')
    else:
        raise SystemExit(f'unknown template {template}; use title quote stat compare feature')
    css, body = _wrap(b, inner, CARD_CSS)
    return base_css(b, W, H) + CARD_CSS, body


def render(template, b, W, H, f, out, scale=1):
    css, body = html_for(template, b, W, H, f)
    page = write_html(os.path.splitext(out)[0] + '.html', body, css)
    shoot([{'html': page, 'out': out, 'w': W, 'h': H, 'scale': scale}])
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('template')
    ap.add_argument('--size', default='portrait')
    ap.add_argument('--out', required=True)
    ap.add_argument('--brand')
    ap.add_argument('--json', help='file with the fields')
    ap.add_argument('--set', action='append', default=[], help='key=value (repeatable)')
    ap.add_argument('--scale', type=float, default=1, help='2 for a sharper still')
    a = ap.parse_args()
    fields = json.load(open(a.json)) if a.json else {}
    for kv in a.set:
        k, v = kv.split('=', 1)
        fields[k] = v.replace('\\n', '\n')
    W, H = parse_size(a.size)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    print(render(a.template, load_brand(a.brand), W, H, fields, a.out, a.scale))
