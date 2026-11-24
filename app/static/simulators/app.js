/* Installation, bounded offline cache and device-local demonstration presets. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const status = $('offline-status'), help = $('install-help');
  let installPrompt = null, registration = null;
  function showHelp() { help.hidden = false; help.scrollIntoView({block: 'start'}); }
  $('close-install-help').onclick = () => { help.hidden = true; $('install-app').focus(); };
  $('show-install-help')?.addEventListener('click', showHelp);
  window.addEventListener('beforeinstallprompt', event => {
    event.preventDefault(); installPrompt = event;
  });
  $('install-app').onclick = async () => {
    if (!installPrompt) { showHelp(); return; }
    const prompt = installPrompt; installPrompt = null;
    try { await prompt.prompt(); await prompt.userChoice; } catch (_) { showHelp(); }
  };
  window.addEventListener('appinstalled', () => { $('install-app').textContent = 'Installation help'; });
  let offlineReady = false;
  function renderStatus() {
    status.textContent = offlineReady
      ? `Available offline${navigator.onLine ? ' · updates when online' : ' · using downloaded app'}`
      : navigator.onLine ? 'Downloading both simulators for offline use…' : 'Not downloaded yet · connect to finish offline setup';
  }
  async function checkReady(repair = false) {
    if (!registration?.active) return;
    const worker = registration.active;
    const ready = await new Promise(resolve => {
      const channel = new MessageChannel();
      const timer = setTimeout(() => { channel.port1.close(); resolve(false); }, 30000);
      channel.port1.onmessage = event => { clearTimeout(timer); channel.port1.close(); resolve(event.data?.ready === true); };
      worker.postMessage({type: 'OFFLINE_READY', repair}, [channel.port2]);
    });
    offlineReady = ready; renderStatus();
    $('retry-offline').hidden = ready;
  }
  function watchUpdate() {
    if (registration.waiting) $('update-app').hidden = false;
    registration.addEventListener('updatefound', () => {
      const worker = registration.installing;
      worker?.addEventListener('statechange', () => {
        if (worker.state === 'installed' && navigator.serviceWorker.controller) $('update-app').hidden = false;
        if (worker.state === 'redundant' && !offlineReady) {
          status.textContent = 'Download incomplete · reconnect and retry offline setup';
          $('retry-offline').hidden = false;
        }
      });
    });
  }
  async function setupOffline(repair = false) {
    if (!('serviceWorker' in navigator)) {
      status.textContent = 'Offline installation needs a supported browser over HTTPS'; return;
    }
    renderStatus();
    try {
      registration = await navigator.serviceWorker.register('./sw.js', {scope: './', updateViaCache: 'none'});
      watchUpdate();
      if (registration.active) await checkReady(repair && navigator.onLine);
      navigator.serviceWorker.ready.then(async active => { registration = active; await checkReady(); });
    } catch (_) {
      status.textContent = 'Offline setup incomplete · reconnect and retry'; $('retry-offline').hidden = false;
    }
  }
  $('retry-offline').onclick = () => setupOffline(true);
  let applyingUpdate = false;
  $('update-app').onclick = () => {
    if (!registration?.waiting) return;
    applyingUpdate = true;
    registration.waiting.postMessage({type: 'ACTIVATE_UPDATE'});
  };
  navigator.serviceWorker?.addEventListener('controllerchange', () => {
    if (applyingUpdate) location.reload(); else checkReady();
  });
  window.addEventListener('online', () => { renderStatus(); if (!offlineReady) setupOffline(); else registration?.update().catch(() => {}); });
  window.addEventListener('offline', renderStatus);
  setupOffline();

  if (!$('save-preset')) return;
  const kind = document.body.dataset.simulator;
  const storageKey = 'wsbco-simulator-presets-v1-' + kind;
  const presetStatus = text => { $('preset-status').textContent = text; };
  let presets = [];
  try {
    const stored = JSON.parse(localStorage.getItem(storageKey) || '[]');
    if (Array.isArray(stored)) presets = stored.filter(p => p && typeof p.name === 'string' && p.values && typeof p.values === 'object').slice(0, 30);
  } catch (_) { presetStatus('Saved presets unavailable. You can still use both simulators.'); }
  function populate() {
    $('saved-presets').replaceChildren(new Option('Choose a preset', ''));
    presets.forEach((p, i) => $('saved-presets').add(new Option(p.name, String(i))));
  }
  function persist() {
    try { localStorage.setItem(storageKey, JSON.stringify(presets)); return true; }
    catch (_) { presetStatus('Unable to save. Device storage may be full or blocked.'); return false; }
  }
  const root = document.querySelector(kind === 'flight' ? '#flight-input-form' : '#d-plane-lab');
  function fields() { return [...root.querySelectorAll('input, select')].filter(el => !el.readOnly && !el.disabled && (el.name || el.id)); }
  const key = el => el.name || el.id;
  function capture() { return Object.fromEntries(fields().map(el => [key(el), el.type === 'checkbox' ? el.checked : el.value])); }
  function restore(values) {
    if (kind === 'd-plane' && !Object.hasOwn(values, 'planeRotation')) {
      values = {...values, planeRotation: '0', planeRotationNumber: '0'};
    }
    // Presets saved before shaft lean existed represent zero-lean delivery.
    if (kind === 'd-plane' && !Object.hasOwn(values, 'lean')) {
      for (const id of ['lean', 'leanNumber']) {
        const field = document.getElementById(id);
        if (field) { field.value = '0'; field.dispatchEvent(new Event('input', {bubbles: true})); }
      }
    }
    // Only existing, editable simulator fields can be restored; no HTML or URLs.
    for (const el of fields()) {
      if (!Object.hasOwn(values, key(el))) continue;
      const value = values[key(el)];
      if (el.type === 'checkbox') { if (typeof value !== 'boolean') continue; el.checked = value; }
      else if (el.tagName === 'SELECT') { if (![...el.options].some(o => o.value === value)) continue; el.value = value; }
      else {
        if (typeof value !== 'string' || value.length > 40) continue;
        if (value !== '' && (!Number.isFinite(Number(value)) || (el.min !== '' && +value < +el.min) || (el.max !== '' && +value > +el.max))) continue;
        el.value = value;
      }
      if (kind === 'd-plane') { el.dispatchEvent(new Event('input', {bubbles: true})); el.dispatchEvent(new Event('change', {bubbles: true})); }
    }
    if (kind === 'flight') root.dispatchEvent(new Event('portable-restore'));
  }
  $('save-preset').onclick = () => {
    const name = $('preset-name').value.trim();
    if (!name) { presetStatus('Give this example a name first.'); $('preset-name').focus(); return; }
    if (kind === 'flight' && !root.reportValidity()) return;
    if (presets.length >= 30) { presetStatus('30 presets saved. Delete one to make room.'); return; }
    const old = presets;
    presets = [...presets, {name, values: capture()}];
    if (!persist()) { presets = old; return; }
    populate(); $('saved-presets').value = String(presets.length - 1);
    presetStatus('Preset saved on this device.');
  };
  $('load-preset').onclick = () => {
    const selected = $('saved-presets').value;
    if (selected === '' || !presets[+selected]) { presetStatus('Choose a saved preset first.'); return; }
    const preset = presets[+selected]; restore(preset.values); $('preset-name').value = preset.name;
    presetStatus('Loaded ' + preset.name + '.');
  };
  $('delete-preset').onclick = () => {
    const selected = $('saved-presets').value;
    if (selected === '' || !presets[+selected]) { presetStatus('Choose a saved preset first.'); return; }
    const old = presets; presets = presets.filter((_, i) => i !== +selected);
    if (!persist()) { presets = old; return; }
    populate(); presetStatus('Preset deleted from this device.');
  };
  populate();
})();
