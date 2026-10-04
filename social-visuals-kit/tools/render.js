// Headless-browser runner. Two modes, both driven by a JSON file.
//   node tools/render.js shot  jobs.json   jobs: [{html, out, w, h, scale?, transparent?, wait?}]
//   node tools/render.js video job.json    job:  {html, out, w, h, seconds, dir, init?}   (records the page, silent webm)
// Env: PW_MODULE (path to a playwright install, optional), CHROME_BIN (browser binary, optional).
const pw = require(process.env.PW_MODULE || 'playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  const [mode, file] = process.argv.slice(2);
  const spec = JSON.parse(fs.readFileSync(file));
  const opts = process.env.CHROME_BIN ? { executablePath: process.env.CHROME_BIN } : {};
  const browser = await pw.chromium.launch(opts);
  if (mode === 'shot') {
    for (const j of spec) {
      const page = await browser.newPage({ viewport: { width: j.w, height: j.h }, deviceScaleFactor: j.scale || 1 });
      await page.goto('file://' + path.resolve(j.html));
      await page.evaluate(() => document.fonts.ready);
      await page.waitForTimeout(j.wait || 700);
      await page.screenshot({ path: j.out, omitBackground: !!j.transparent });
      await page.close();
    }
  } else if (mode === 'video') {
    fs.mkdirSync(spec.dir, { recursive: true });
    const ctx = await browser.newContext({
      viewport: { width: spec.w, height: spec.h },
      recordVideo: { dir: spec.dir, size: { width: spec.w, height: spec.h } },
    });
    const page = await ctx.newPage();
    if (spec.init) await page.addInitScript(spec.init);
    await page.goto('file://' + path.resolve(spec.html));
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(Math.round(spec.seconds * 1000));
    const video = page.video();
    await ctx.close();
    fs.copyFileSync(await video.path(), spec.out);
  } else {
    throw new Error('mode must be shot or video');
  }
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
