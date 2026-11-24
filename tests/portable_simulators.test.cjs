// Browser integration: node tests/portable_simulators.test.cjs (requires Playwright).
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
const http = require('node:http');
const fs = require('node:fs');
const {once} = require('node:events');

(async () => {
  const root = path.resolve(__dirname, '..');
  let brokenAsset = false, revision = '';
  const server = http.createServer((req, res) => {
    const pathname = new URL(req.url, 'http://localhost').pathname;
    if (!pathname.startsWith('/static/simulators/')) { res.writeHead(404); res.end('Not found'); return; }
    if (brokenAsset && pathname.endsWith('/assets/d_plane_model.js')) { res.writeHead(503); res.end('Simulated interrupted download'); return; }
    const file = path.resolve(root, 'app', '.' + pathname);
    if (!file.startsWith(path.join(root, 'app/static/simulators') + path.sep)) { res.writeHead(403); res.end(); return; }
    try {
      let bytes = fs.readFileSync(file);
      if (pathname.endsWith('/sw.js') && revision) bytes = Buffer.from(bytes.toString().replace(/const VERSION = '([^']+)'/, (_, v) => `const VERSION = '${v}${revision}'`));
      const types = {'.html': 'text/html', '.css': 'text/css', '.js': 'application/javascript', '.png': 'image/png', '.svg': 'image/svg+xml', '.webmanifest': 'application/manifest+json'};
      res.writeHead(200, {'Content-Type': types[path.extname(file)] || 'application/octet-stream', 'Cache-Control': 'no-cache'}); res.end(bytes);
    } catch (_) { res.writeHead(404); res.end(); }
  });
  let browser;
  try {
    server.listen(0, '127.0.0.1');
    await once(server, 'listening');
    const port = server.address().port;
    const base = `http://127.0.0.1:${port}/static/simulators/`;
    browser = await chromium.launch({headless: true, ...(process.env.PLAYWRIGHT_EXECUTABLE_PATH ? {executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH} : {})});
    for (const viewport of [{width: 820, height: 1180}, {width: 1180, height: 820}, {width: 393, height: 852}]) {
      const context = await browser.newContext({viewport, hasTouch: true, isMobile: true});
      const page = await context.newPage(), errors = [], external = [];
      page.on('pageerror', e => errors.push(e.message));
      page.on('request', r => { if (!r.url().startsWith(`http://127.0.0.1:${port}/`)) external.push(r.url()); });
      await page.goto(base + 'index.html');
      await page.locator('#offline-status').filter({hasText: 'Available offline'}).waitFor();
      assert.equal(await page.evaluate(() => navigator.serviceWorker.controller.scriptURL.endsWith('/static/simulators/sw.js')), true);
      const cached = await page.evaluate(async () => {
        const keys = await caches.keys();
        return (await Promise.all(keys.map(async name => (await (await caches.open(name)).keys()).map(r => r.url)))).flat();
      });
      assert(cached.length >= 16);
      assert(cached.every(url => url.startsWith(base)), 'No workspace/private URL cached');
      const manifest = await (await page.request.get(base + 'manifest.webmanifest')).json();
      assert.equal(manifest.display, 'standalone');
      assert.equal(manifest.scope, './');
      await page.getByRole('button', {name: 'Install app', exact: true}).click();
      assert(await page.locator('#install-help').isVisible());
      await page.getByRole('button', {name: 'Close instructions'}).click();
      await context.setOffline(true);
      await page.goto(base + 'flight.html');
      await page.locator('#offline-status').filter({hasText: 'Available offline'}).waitFor();
      assert.equal(await page.locator('#start-coaching-analysis').count(), 0);
      await page.locator('[name=club_face]').fill('-2');
      await page.locator('[name=club_path]').fill('4');
      await page.locator('[name=carry_distance]').fill('123');
      await page.locator('[name=total_distance]').fill('145');
      await page.getByRole('button', {name: 'Update Flight', exact: true}).click();
      assert.equal(await page.locator('[data-readout=facePath]').innerText(), '-6.0°');
      await page.locator('#preset-name').fill('Range draw');
      await page.locator('#save-preset').click();
      await page.locator('[name=club_face]').fill('3');
      await page.locator('#load-preset').click();
      assert.equal(await page.locator('[name=club_face]').inputValue(), '-2');
      assert.equal(await page.locator('[name=carry_distance]').inputValue(), '123');
      await page.locator('#flight-replay').click();
      await page.getByRole('button', {name: 'Side', exact: true}).click();
      await page.locator('#analyze-laws-principles').click();
      assert((await page.locator('#laws-principles-results').innerText()).includes('The six laws'));
      await page.reload();
      await page.locator('#saved-presets').selectOption('0');
      await page.locator('#load-preset').click();
      assert.equal(await page.locator('[name=carry_distance]').inputValue(), '123');
      await page.getByRole('link', {name: 'D-plane', exact: true}).click();
      assert.equal(await page.locator('#f2p').innerText(), '−2.0°');
      await page.locator('#hand').selectOption('left');
      await page.locator('#club').selectOption('driver');
      await page.locator('#faceNumber').fill('-5');
      await page.locator('#faceNumber').dispatchEvent('input');
      await page.locator('#preset-name').fill('Left-handed driver');
      await page.locator('#save-preset').click();
      await page.locator('#reset').click();
      await page.locator('#load-preset').click();
      assert.equal(await page.locator('#hand').inputValue(), 'left');
      assert.equal(await page.locator('#club').inputValue(), 'driver');
      assert.equal(await page.locator('#faceNumber').inputValue(), '-5');
      await page.locator('#scene').focus();
      await page.keyboard.press('ArrowRight');
      await page.getByRole('button', {name: 'Top', exact: true}).click();
      await page.locator('#replay').click();
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), false, 'No horizontal overflow');
      await page.screenshot({path: path.join('/tmp', `golf-simulators-${viewport.width}.png`), fullPage: true});
      await page.locator('#delete-preset').click();
      assert.equal(await page.locator('#saved-presets option').count(), 1);
      await page.goto(base + 'index.html');
      await page.reload();
      assert(await page.getByRole('heading', {name: 'See the flight. Shape the lesson.'}).isVisible());
      assert.deepEqual(errors, []);
      assert.deepEqual(external, []);
      await context.close();
      console.log(`PASS offline navigation, both engines, presets, touch layout ${viewport.width}×${viewport.height}`);
    }
    // Failed initial precache, recovery, cache eviction repair, then explicit update.
    brokenAsset = true;
    const failure = await browser.newContext();
    const failedPage = await failure.newPage();
    await failedPage.goto(base + 'index.html');
    await failedPage.locator('#retry-offline').waitFor();
    assert(!(await failedPage.locator('#offline-status').innerText()).includes('Available offline'));
    brokenAsset = false;
    await failedPage.locator('#retry-offline').click();
    await failedPage.locator('#offline-status').filter({hasText: 'Available offline'}).waitFor();
    await failedPage.evaluate(async () => {
      for (const name of await caches.keys()) await (await caches.open(name)).delete(new URL('./flight.html', location.href).href);
    });
    await failedPage.reload();
    await failedPage.locator('#retry-offline').waitFor();
    await failedPage.locator('#retry-offline').click();
    await failedPage.locator('#offline-status').filter({hasText: 'Available offline'}).waitFor();
    revision = '-update-test';
    await failedPage.evaluate(async () => (await navigator.serviceWorker.getRegistration()).update());
    await failedPage.locator('#update-app').waitFor();
    await Promise.all([failedPage.waitForEvent('load'), failedPage.locator('#update-app').click()]);
    await failedPage.locator('#offline-status').filter({hasText: 'Available offline'}).waitFor();
    assert.equal(await failedPage.evaluate(async () => (await caches.keys()).filter(k => k.startsWith('wsbco-simulators-')).length), 1);
    await failure.setOffline(true);
    await failedPage.goto(base + 'd-plane.html');
    assert.equal(await failedPage.locator('#f2p').innerText(), '−2.0°');
    await failure.close();
    console.log('PASS interrupted download, retry, eviction repair, explicit update and old-cache cleanup');
    console.log('PASS all requested offline/touch browser checks');
  } finally { if (browser) await browser.close(); server.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
