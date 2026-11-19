(() => {
  "use strict";
  const root = document.querySelector("[data-swing-simulator]");
  if (!root) return;

  const parse = (id) => {
    try { return JSON.parse(document.getElementById(id)?.textContent || "{}"); }
    catch { return {}; }
  };
  const images = parse("gcie-onform-position-images");
  const flightRoot = root.closest(".gcie-simulations-tab") || root;
  const metrics = parse("gcie-onform-position-metrics");
  const frames = images
    .filter((item) => item && item.available !== false && item.position && item.url)
    .sort((a, b) => Number(String(a.position).replace("P", "")) - Number(String(b.position).replace("P", "")));
  if (!frames.length) return;

  const image = root.querySelector("[data-sim-frame-image]");
  const imageLink = root.querySelector("[data-sim-frame-link]");
  const positionLabel = root.querySelector("[data-sim-position]");
  const range = root.querySelector("[data-sim-range]");
  const playButton = root.querySelector("[data-sim-play]");
  const controlNames = ["torso", "pelvis", "spine", "sway", "arms", "bend", "elevation", "wrist"];
  const control = (name) => root.querySelector('[data-sim-control="' + name + '"]');
  const output = (name) => root.querySelector('[data-sim-output="' + name + '"]');
  let frameIndex = 0;
  let timer = null;

  const number = (value) => {
    if (value === null || value === undefined || value === "") return null;
    const found = String(value).replace(",", ".").match(/-?\d+(?:\.\d+)?/);
    return found ? Number(found[0]) : null;
  };
  const formatted = (value, digits = 1) => {
    if (!Number.isFinite(value)) return "—";
    return (Number.isInteger(value) ? String(value) : value.toFixed(digits));
  };
  const signed = (value, unit) => (value > 0 ? "+" : "") + formatted(value) + unit;
  const currentFrame = () => frames[frameIndex];
  const currentMetrics = () => metrics[String(currentFrame().position).toUpperCase()] || {};
  const baseValue = (key) => number(currentMetrics()[key]);

  const bodyRenderer = window.SwingGeometry?.mount(root.querySelector('[data-body-geometry]'));
  root.querySelectorAll('[data-body-view]').forEach(button => button.addEventListener('click', () => {
    root.querySelectorAll('[data-body-view]').forEach(b => b.setAttribute('aria-pressed', String(b === button)));
    bodyRenderer?.setView(button.dataset.bodyView);
  }));
  function samplePose() {
    const phase = Number(String(currentFrame().position).replace('P', ''));
    const examples = window.SwingGeometry?.presets || {};
    if (examples['P'+phase]) return {...examples['P'+phase]};
    const key = phase < 4 ? 'P1' : phase < 6 ? 'P4' : phase < 7 ? 'P6' : 'P7';
    return {...examples[key]};
  }
  function turnValue(key, fallback) {
    const value = baseValue(key); if (value === null) return fallback;
    const direction = String(currentMetrics()[key+'_direction'] || '').toLowerCase();
    if (value < 0) return value;
    if (/closed|away|back/.test(direction)) return -Math.abs(value);
    if (/open|toward/.test(direction)) return Math.abs(value);
    return Number(String(currentFrame().position).replace('P','')) <= 4 ? -Math.abs(value) : value;
  }
  function updateFigure(values, baseline) {
    if (bodyRenderer) bodyRenderer.setPose(values, baseline);
  }

  function render() {
    const frame = currentFrame();
    const values = currentMetrics();
    const url = frame.url;
    image.src = url;
    image.alt = frame.position + " Onform screenshot";
    imageLink.href = url;
    root.querySelectorAll("[data-sim-position]").forEach((node) => { node.textContent = frame.position; });
    range.value = String(frameIndex);
    range.max = String(frames.length - 1);
    root.querySelector("[data-sim-range-output]").textContent = (frameIndex + 1) + " / " + frames.length;
    root.querySelectorAll("[data-sim-position-button]").forEach((button, index) => {
      const selected = index === frameIndex;
      button.classList.toggle("is-selected", selected);
      button.setAttribute("aria-pressed", String(selected));
    });

    const sample = samplePose();
    const baseline = {...sample,
      torso: turnValue('torso_rotation', sample.torso),
      pelvis: turnValue('pelvis_rotation', sample.pelvis),
      side: baseValue('spine_tilt') ?? sample.side,
      sway: baseValue('torso_sway') ?? sample.sway,
      bend: baseValue('torso_forward_bend') ?? sample.bend,
    };
    const projected = {...baseline};
    const keys = {torso:'torso', pelvis:'pelvis', spine:'side', sway:'sway', arms:'arms', bend:'bend', elevation:'elevation', wrist:'wrist'};
    controlNames.forEach((name) => {
      const delta = Number(control(name).value);
      projected[keys[name]] += delta;
      output(name).textContent = signed(delta, name === 'sway' ? ' in' : '°');
    });
    [['torso','torso','torso_rotation'],['pelvis','pelvis','pelvis_rotation'],['spine','side','spine_tilt'],['sway','sway','torso_sway']].forEach(([readout,key,source])=>{
      root.querySelector('[data-sim-readout="'+readout+'"]').textContent = (baseValue(source) === null ? 'Example ' : '') + formatted(projected[key]) + (key === 'sway' ? ' in' : '°');
    });
    root.querySelector('[data-sim-readout="xfactor"]').textContent = formatted(Math.abs(projected.torso-projected.pelvis))+'°';
    updateFigure(projected, baseline);

    const pelvisDelta = Number(control("pelvis").value);
    const torsoDelta = Number(control("torso").value);
    const spineDelta = Number(control("spine").value);
    const armsDelta = Number(control("arms").value);
    const enabled = flightRoot.querySelector('[data-sim-link-enabled]')?.checked;
    const coefficient = key => number(flightRoot.querySelector('[data-sim-coeff="'+key+'"]').value) ?? 0;
    const pathDelta = enabled ? coefficient('pelvisPath')*pelvisDelta + coefficient('torsoPath')*torsoDelta + coefficient('armsPath')*armsDelta : 0;
    const faceDelta = enabled ? coefficient('wristFace')*Number(control('wrist').value) : 0;
    const basePath = number(flightRoot.querySelector('[data-sim-base="path"]').value) ?? 0;
    const baseFace = number(flightRoot.querySelector('[data-sim-base="face"]').value) ?? 0;
    const estimatedPath = basePath + pathDelta;
    const estimatedFace = baseFace + faceDelta;
    const faceToPath = estimatedFace - estimatedPath;
    flightRoot.querySelector('[data-sim-delivery="path"]').textContent = signed(estimatedPath, "°");
    flightRoot.querySelector('[data-sim-delivery="face"]').textContent = signed(estimatedFace, "°");
    flightRoot.querySelector('[data-sim-delivery="f2p"]').textContent = signed(faceToPath, "°");
    updateFlight(estimatedPath, estimatedFace, faceToPath);

    const metricButton = document.querySelector('.gcie-metrics-card [data-position="' + frame.position + '"]');
    if (metricButton) metricButton.click();
  }

  function updateFlight(path, face, faceToPath) {
    const clamp = (value, low, high) => Math.max(low, Math.min(high, value));
    const launch = 0.8 * face + 0.2 * path;
    const startX = clamp(160 + launch * 2.4, 48, 272);
    const endX = clamp(startX + faceToPath * 3.2, 36, 284);
    const c1x = clamp(160 + launch * 1.0, 42, 278);
    const c2x = clamp(startX + faceToPath * 1.7, 36, 284);
    flightRoot.querySelector("[data-sim-flight-path]").setAttribute("d", "M160 200 C" + c1x + " 154 " + c2x + " 82 " + endX + " 30");
    flightRoot.querySelector("[data-sim-flight-end]").setAttribute("cx", String(endX));
    const shape = faceToPath > 0.5 ? "FADE / CUT" : faceToPath < -0.5 ? "DRAW" : "STRAIGHT";
    flightRoot.querySelector("[data-sim-flight-shape]").textContent = shape;
    flightRoot.querySelector("[data-sim-flight-start]").textContent = Math.abs(launch) < 0.5 ? "Starts close to the target line" : "Starts " + (launch > 0 ? "right" : "left") + " of the target";
    flightRoot.querySelector("[data-sim-flight-curve]").textContent = Math.abs(faceToPath) < 0.5
      ? "Face and path are nearly matched"
      : Math.abs(faceToPath).toFixed(1) + "° face-to-path suggests " + (faceToPath > 0 ? "fade" : "draw") + " curvature";
  }

  function stop() {
    if (timer) window.clearInterval(timer);
    timer = null;
    playButton.textContent = "▶ Play sequence";
    playButton.setAttribute("aria-pressed", "false");
  }

  range.addEventListener("input", () => { stop(); frameIndex = Number(range.value); render(); });
  root.querySelectorAll("[data-sim-position-button]").forEach((button, index) => {
    button.addEventListener("click", () => { stop(); frameIndex = index; render(); });
  });
  root.querySelectorAll("[data-sim-control]").forEach((input) => input.addEventListener("input", render));
  root.querySelector("[data-sim-reset]").addEventListener("click", () => {
    controlNames.forEach((name) => { control(name).value = "0"; });
    render();
  });
  flightRoot.querySelectorAll("[data-sim-base]").forEach((input) => input.addEventListener("input", render));
  playButton.addEventListener("click", () => {
    if (timer) { stop(); return; }
    playButton.textContent = "Ⅱ Pause";
    playButton.setAttribute("aria-pressed", "true");
    timer = window.setInterval(() => {
      frameIndex = (frameIndex + 1) % frames.length;
      render();
    }, 700);
  });
  flightRoot.querySelectorAll("[data-sim-coeff], [data-sim-link-enabled]").forEach(input => input.addEventListener("input", render));
  render();
})();