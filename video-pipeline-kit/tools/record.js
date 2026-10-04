#!/usr/bin/env node
/*
 * Record a browser scene with Playwright and cut it to an mp4 between two marks.
 *
 *   ./run.sh tools/record.js examples/hello/recipe.json [--headed]
 *
 * recipe.json:
 * {
 *   "name": "hello_rec",                       // output: work/<name>.mp4 (override with "out")
 *   "viewport": {"width": 1440, "height": 810},   // desktop; or "device": "iPhone 14" for mobile emulation
 *   "cursor": true,                            // draw a visible cursor dot (Playwright videos have none)
 *   "trim": ["start", "end"],                  // marks to cut between (default: whole recording)
 *   "steps": [
 *     {"do": "goto", "url": "page.html"},      // relative paths are resolved next to the recipe (file://)
 *     {"do": "wait", "ms": 1200},
 *     {"do": "mark", "name": "start"},
 *     {"do": "click", "selector": "#go"},
 *     {"do": "type", "selector": "#name", "text": "Ada", "delay": 60},
 *     {"do": "press", "key": "Enter"},
 *     {"do": "hover", "selector": ".card"},
 *     {"do": "scroll", "by": 900, "ms": 3000},  // smooth wheel scroll (1 step ~ 60 ms)
 *     {"do": "waitFor", "selector": ".done", "timeout": 20000},
 *     {"do": "screenshot", "name": "final"},   // work/<name>_final.png
 *     {"do": "eval", "js": "document.title"},
 *     {"do": "mark", "name": "end"}
 *   ]
 * }
 * Real sites: mind logins and terms of use; never put credentials in a recipe that is shared.
 */
const { chromium, devices } = require('playwright');
const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');
const { execFileSync } = require('child_process');

const KIT = path.resolve(__dirname, '..');
const WORK = process.env.KIT_WORK || path.join(KIT, 'work');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const args = process.argv.slice(2);
const recipePath = args.find((a) => !a.startsWith('--'));
const headed = args.includes('--headed');
if (!recipePath) { console.error('usage: record.js <recipe.json> [--headed]'); process.exit(2); }
const recipeDir = path.dirname(path.resolve(recipePath));
const recipe = JSON.parse(fs.readFileSync(recipePath, 'utf8'));
fs.mkdirSync(path.join(WORK, 'rec'), { recursive: true });

function resolveUrl(u) {
  if (/^(https?|file|data):/.test(u)) return u;
  const p = path.resolve(recipeDir, u);
  if (fs.existsSync(p)) return pathToFileURL(p).href;
  return u;
}

async function wheelScroll(page, total, ms, x = 400, y = 400) {
  await page.mouse.move(x, y);
  const steps = Math.max(1, Math.round(ms / 60)), per = total / steps;
  for (let i = 0; i < steps; i++) { await page.mouse.wheel(0, per); await sleep(60); }
}

const CURSOR_JS = `(() => {
  const d = document.createElement('div');
  d.style.cssText = 'position:fixed;z-index:2147483647;width:22px;height:22px;margin:-11px 0 0 -11px;border-radius:50%;' +
    'background:rgba(255,80,60,.55);border:2px solid #fff;pointer-events:none;transition:transform .05s;left:-50px;top:-50px';
  const add = () => document.documentElement.appendChild(d);
  document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', add) : add();
  addEventListener('mousemove', (e) => { d.style.left = e.clientX + 'px'; d.style.top = e.clientY + 'px'; }, true);
})();`;

(async () => {
  const name = recipe.name || path.basename(recipePath, '.json');
  const deviceOpts = recipe.device ? devices[recipe.device] : null;
  if (recipe.device && !deviceOpts) { console.error('unknown Playwright device: ' + recipe.device); process.exit(2); }
  const viewport = deviceOpts ? deviceOpts.viewport : (recipe.viewport || { width: 1440, height: 810 });
  const browser = await chromium.launch({ headless: !headed });
  const ctx = await browser.newContext({
    ...(deviceOpts || {}), viewport, recordVideo: { dir: path.join(WORK, 'rec'), size: viewport },
  });
  if (recipe.cursor !== false) await ctx.addInitScript(CURSOR_JS);
  const page = await ctx.newPage();
  const t0 = Date.now();
  const marks = {};
  let failed = null;
  try {
    for (const [i, s] of (recipe.steps || []).entries()) {
      const sel = s.selector ? page.locator(s.selector).first() : null;
      switch (s.do) {
        case 'goto': await page.goto(resolveUrl(s.url), { waitUntil: s.waitUntil || 'load' }); break;
        case 'wait': await sleep(s.ms || 1000); break;
        case 'waitFor': await page.waitForSelector(s.selector, { timeout: s.timeout || 30000 }); break;
        case 'click': await sel.click(); break;
        case 'dblclick': await sel.dblclick(); break;
        case 'hover': await sel.hover(); break;
        case 'type': await sel.click(); await sel.pressSequentially(s.text, { delay: s.delay || 50 }); break;
        case 'press': await page.keyboard.press(s.key); break;
        case 'scroll': await wheelScroll(page, s.by || 600, s.ms || 2000, s.x, s.y); break;
        case 'mark': marks[s.name] = Date.now() - t0; break;
        case 'eval': console.log('eval:', await page.evaluate(s.js)); break;
        case 'screenshot': await page.screenshot({ path: path.join(WORK, `${name}_${s.name || i}.png`) }); break;
        default: throw new Error(`step ${i}: unknown action "${s.do}"`);
      }
    }
  } catch (e) { failed = e; }
  const video = page.video();
  await ctx.close();
  const vpath = video ? await video.path() : null;
  await browser.close();
  if (failed) { console.error(`${name} FAILED: ${failed.message}`); process.exit(1); }

  const [a, b] = recipe.trim || [];
  const startMs = a ? marks[a] : 0;
  const endMs = b ? marks[b] : null;
  if ((a && startMs === undefined) || (b && endMs === undefined)) { console.error('trim marks not found in steps: ' + (recipe.trim || []).join(', ')); process.exit(1); }
  const out = recipe.out ? path.resolve(recipeDir, recipe.out) : path.join(WORK, `${name}.mp4`);
  fs.mkdirSync(path.dirname(out), { recursive: true });
  const ff = ['-y', '-v', 'error', '-ss', (startMs / 1000).toFixed(2), '-i', vpath];
  if (endMs !== null) ff.push('-t', ((endMs - startMs) / 1000 + 0.3).toFixed(2));
  ff.push('-vf', `crop=${viewport.width}:${viewport.height - 2}:0:0,fps=30`, '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', '-an', out);
  execFileSync('ffmpeg', ff);
  console.log('saved', out);
})();
