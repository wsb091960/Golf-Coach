/* Generated with a complete allowlist: this worker never caches Golf Coach data. */
'use strict';
const VERSION = '420cdfa105f23003';
const FILES = ["app.css", "app.js", "assets/d_plane_lab.css", "assets/d_plane_lab.js", "assets/d_plane_model.js", "assets/gcie_what_if.js", "assets/session_performance.css", "assets/simulator_display.js", "assets/simulator_workbench.css", "assets/standalone_flight_simulator.js", "d-plane.html", "flight.html", "icon-180.png", "icon-192.png", "icon-512.png", "icon.svg", "index.html", "manifest.webmanifest"];
const PREFIX = 'wsbco-simulators-' + self.registration.scope;
const CACHE = PREFIX + VERSION;
const urls = FILES.map(path => new URL(path, self.registration.scope).href);
async function download(cache, missingOnly = false) {
  const results = await Promise.allSettled(urls.map(async url => {
    if (missingOnly && await cache.match(url)) return;
    const response = await fetch(new Request(url, {cache: 'reload', credentials: 'omit'}));
    if (!response.ok || response.redirected) throw new Error('Incomplete simulator download');
    await cache.put(url, response);
  }));
  if (results.some(result => result.status === 'rejected')) throw new Error('Incomplete simulator download');
}
self.addEventListener('install', event => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    try {
      await download(cache);
    } catch (error) { await caches.delete(CACHE); throw error; }
  })());
});
self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    for (const name of await caches.keys()) if (name.startsWith(PREFIX) && name !== CACHE) await caches.delete(name);
    await self.clients.claim();
  })());
});
self.addEventListener('message', event => {
  if (event.data?.type === 'ACTIVATE_UPDATE') self.skipWaiting();
  if (event.data?.type === 'OFFLINE_READY' && event.ports[0]) {
    event.waitUntil((async () => {
      const cache = await caches.open(CACHE);
      if (event.data.repair) { try { await download(cache, true); } catch (_) { /* Report incomplete below. */ } }
      const ready = (await Promise.all(urls.map(url => cache.match(url)))).every(Boolean);
      event.ports[0].postMessage({ready, version: VERSION});
    })());
  }
});
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  const url = new URL(event.request.url);
  url.search = ''; url.hash = '';
  if (url.href === self.registration.scope) url.pathname += 'index.html';
  if (!urls.includes(url.href)) return;
  event.respondWith((async () => {
    const cached = await (await caches.open(CACHE)).match(url.href);
    return cached || fetch(event.request);
  })());
});
