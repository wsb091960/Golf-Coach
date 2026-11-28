// Compact dial interaction, shared presets, live 3D and offline installation.
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const {once} = require('node:events');
(async () => {
  const root = path.resolve(__dirname, '../app/static/simulators');
  const server = http.createServer((req,res) => {
    const name = new URL(req.url, 'http://localhost').pathname;
    const file = path.resolve(root, '.' + name);
    if (!file.startsWith(root + path.sep)) {res.writeHead(403).end();return;}
    try {
      const types = {'.html':'text/html','.js':'application/javascript','.css':'text/css','.webmanifest':'application/manifest+json'};
      res.writeHead(200, {'Content-Type':types[path.extname(file)] || 'application/octet-stream'});
      res.end(fs.readFileSync(file));
    } catch {res.writeHead(404).end();}
  });
  let browser;
  try {
    server.listen(0,'127.0.0.1'); await once(server,'listening');
    browser = await chromium.launch({headless:true, ...(process.env.PLAYWRIGHT_EXECUTABLE_PATH ? {executablePath:process.env.PLAYWRIGHT_EXECUTABLE_PATH} : {})});
    const base = `http://127.0.0.1:${server.address().port}`;
    for (const viewport of [{width:1180,height:820},{width:820,height:1180},{width:393,height:852},{width:844,height:390}]) {
      const context = await browser.newContext({viewport,hasTouch:true,isMobile:true});
      const page = await context.newPage(), errors=[];
      page.on('pageerror',e=>errors.push(e.message));
      await page.goto(base+'/d-plane.html');
      await page.locator('#leanDial').waitFor();
      assert.equal(await page.locator('[role=slider]').count(),7);
      assert.equal(await page.locator('input[type=range]:visible').count(),0);
      const before = await page.locator('#scene').evaluate(e=>e.toDataURL());
      await page.getByRole('button',{name:'Increase Shaft lean',exact:true}).click();
      assert.equal(await page.locator('#leanNumber').inputValue(),'0.1');
      await page.locator('#leanDial').press('ArrowUp');
      assert.equal(await page.locator('#leanNumber').inputValue(),'0.2');
      await page.locator('#leanDial').press('Shift+ArrowUp');
      assert.equal(await page.locator('#leanNumber').inputValue(),'1.2');
      const box = await page.locator('#leanDial').boundingBox();
      await page.mouse.move(box.x+box.width/2,box.y+box.height/2); await page.mouse.down();
      assert.equal(await page.locator('#leanNumber').inputValue(),'1.2','Touch down never jumps');
      await page.mouse.move(box.x+box.width/2,box.y+box.height/2-40,{steps:8}); await page.mouse.up();
      assert.equal(await page.locator('#leanNumber').inputValue(),'3.2','40px gives 2 degrees');
      assert.equal(await page.locator('#leanDial').getAttribute('aria-valuenow'),'3.2');
      assert.notEqual(await page.locator('#scene').evaluate(e=>e.toDataURL()),before);
      await page.locator('#leanDial').press('End');
      await page.getByRole('button',{name:'Increase Shaft lean',exact:true}).click();
      assert.equal(await page.locator('#leanNumber').inputValue(),'25','Upper limit clamps');
      await page.locator('#leanNumber').fill('8');
      await page.locator('#planeRotationDial').press('ArrowDown');
      assert.equal(await page.locator('#planeRotationNumber').inputValue(),'-0.1');
      await page.locator('.preset-drawer > summary').click();
      await page.locator('#preset-name').fill('Dial example'); await page.locator('#save-preset').click();
      await page.locator('#reset').click();
      assert.equal(await page.locator('#leanDial').getAttribute('aria-valuenow'),'0');
      await page.locator('#load-preset').click();
      assert.equal(await page.locator('#leanDial').getAttribute('aria-valuenow'),'8');
      assert.equal(await page.locator('#planeRotationDial').getAttribute('aria-valuenow'),'-0.1');
      await page.locator('.preset-drawer > summary').click();
      await page.locator('#reset').click();
      await page.locator('#offline-status').filter({hasText:'Available offline'}).waitFor();
      await context.setOffline(true); await page.reload();
      await page.locator('#leanDial').waitFor();
      assert.equal(await page.locator('[role=slider]').count(),7);
      await page.getByRole('button',{name:'Increase Shaft lean',exact:true}).click();
      assert.equal(await page.locator('#leanDial').getAttribute('aria-valuenow'),'0.1');
      await page.screenshot({path:`/tmp/d-plane-dials-${viewport.width}.png`});
      const scene=await page.locator('#scene').boundingBox();
      assert(scene.height>=100 && scene.y+scene.height<=viewport.height+1,`3D remains visible: ${JSON.stringify(scene)}`);
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false,'No horizontal overflow');
      assert.deepEqual(errors,[]);
      await context.close();
      console.log(`PASS compact dials, bounds, slow drag, presets, 3D and offline ${viewport.width}x${viewport.height}`);
    }
  } finally {if(browser)await browser.close();server.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
