import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { resolve } from 'node:path';

// Reuse the browser driver already supplied by the Storybook test runner.
const require = createRequire(import.meta.url);
const runnerRequire = createRequire(require.resolve('@storybook/test-runner/package.json'));
const { chromium } = runnerRequire('playwright');
const target = process.argv[2] || 'http://127.0.0.1:13161';
const output = resolve(process.argv[3] || '/tmp/issue-161-png-browser');
await mkdir(output, { recursive: true });
const browser = await chromium.launch({
  headless: true,
  executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH || undefined,
});

try {
  const page = await browser.newPage({ viewport: { width: 700, height: 240 }, deviceScaleFactor: 1 });
  const requests = [];
  page.on('request', (request) => {
    if (/^\/(?:studio-backend\/)?api\//.test(new URL(request.url()).pathname)) requests.push(request.url());
  });
  page.setDefaultTimeout(15000);
  const story = (name) => `${target}/iframe.html?id=traindata-traindatathumb--${name}&viewMode=story`;
  await page.goto(story('png-masks'));
  await page.getByRole('figure', { name: 'invalid-bytes', exact: true }).waitFor();
  await page.waitForFunction(() => [...document.querySelectorAll('img')].every((img) => img.complete));
  assert.equal(await page.locator('[style*="mask-image"]').count(), 4);

  // Sample the browser-composited tile screenshot, rather than recreating CSS in a
  // canvas. Canvas only reads this 96px screenshot in the test, never source images.
  const sample = async (name) => {
    const tile = page.getByRole('button', { name: `${name}.png 열기`, exact: true });
    const screenshot = await tile.screenshot();
    return page.evaluate(async (base64) => {
      const image = new Image(); image.src = `data:image/png;base64,${base64}`;
      await image.decode();
      const canvas = document.createElement('canvas'); canvas.width = image.width; canvas.height = image.height;
      const context = canvas.getContext('2d'); context.drawImage(image, 0, 0);
      return [[24, 24], [72, 24], [24, 72], [72, 72]].map(([x, y]) =>
        [...context.getImageData(x, y, 1, 1).data].slice(0, 3));
    }, screenshot.toString('base64'));
  };
  const gray = (pixel) => pixel.every((channel) => Math.abs(channel - 128) <= 3);
  const red = ([r, g, b]) => Math.abs(r - 218) <= 6 && Math.abs(g - 38) <= 6 && Math.abs(b - 38) <= 6;
  for (const theme of ['light', 'dark']) {
    await page.evaluate((dark) => document.documentElement.classList.toggle('dark', dark), theme === 'dark');
    const wide = await sample('wide'); const tall = await sample('tall');
    assert.ok(red(wide[0]) && red(wide[1]) && gray(wide[2]) && red(wide[3]), `wide ${theme}: ${JSON.stringify(wide)}`);
    assert.ok(red(tall[0]) && gray(tall[1]) && red(tall[2]) && red(tall[3]), `tall ${theme}: ${JSON.stringify(tall)}`);
    assert.ok((await sample('empty')).every(gray), 'transparent mask must leave the base unchanged');
    assert.ok((await sample('invalid-bytes')).every(gray), 'failed PNG must not expose a red rectangle');
    await page.screenshot({ path: `${output}/png-masks-${theme}.png` });
  }
  await page.goto(story('hidden'));
  await page.getByRole('button', { name: 'preview.png 열기', exact: true }).waitFor();
  assert.equal(await page.locator('[style*="mask-image"]').count(), 0);
  assert.equal(await page.getByTitle('마스크 등록됨').count(), 1);

  await page.goto(story('page-of-masks'));
  await page.getByRole('button', { name: 'Show previews', exact: true }).waitFor();
  const toggleMs = await page.evaluate(async () => {
    const start = performance.now();
    [...document.querySelectorAll('button')].find((button) => button.textContent === 'Show previews').click();
    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    return performance.now() - start;
  });
  assert.equal(await page.locator('[style*="mask-image"]').count(), 24);
  await page.getByRole('button', { name: 'Hide previews', exact: true }).click();
  assert.equal(await page.locator('[style*="mask-image"]').count(), 0);
  assert.equal(await page.locator('canvas').count(), 0);
  console.log(`24-tile fixture toggle + two animation frames: ${toggleMs.toFixed(1)} ms (single local sample)`);

  // Simulate a browser without either mask implementation before React renders.
  await page.addInitScript(() => { CSS.supports = () => false; });
  await page.goto(story('png-masks'));
  await page.getByRole('figure', { name: 'wide', exact: true }).waitFor();
  assert.equal(await page.locator('[style*="mask-image"]').count(), 0);
  assert.ok((await sample('wide')).every(gray));
  assert.deepEqual(requests, [], 'inline thumbnails must not request editor, original, or legacy data');
  console.log(`PNG crop, alpha, theme, failure, hidden and unsupported-browser checks passed. Screenshots: ${output}`);
} finally {
  await browser.close();
}

