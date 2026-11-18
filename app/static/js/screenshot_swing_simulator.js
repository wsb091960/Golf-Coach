(() => {
  "use strict";
  const root = document.querySelector("[data-swing-simulator]");
  if (!root) return;

  const parse = (id) => {
    try { return JSON.parse(document.getElementById(id)?.textContent || "{}"); }
    catch { return {}; }
  };
  const images = parse("gcie-onform-position-images");
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
  const controlNames = ["torso", "pelvis", "spine", "sway", "arms"];
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

  function updateFigure(values) {
    const torso = Math.max(-90, Math.min(90, values.torso));
    const pelvis = Math.max(-90, Math.min(90, values.pelvis));
    const spine = Math.max(-35, Math.min(35, values.spine));
    const sway = Math.max(-8, Math.min(8, values.sway));
    const width = (turn) => Math.max(11, 34 * (0.42 + 0.58 * Math.abs(Math.cos(turn * Math.PI / 180))));
    const torsoRx = width(torso), pelvisRx = width(pelvis);
    const centerX = 160 + sway * 3.4;
    root.querySelector("[data-figure-torso]").setAttribute("transform", "rotate(" + spine + " " + centerX + " 125)");
    root.querySelector("[data-figure-shoulders]").setAttribute("rx", torsoRx);
    root.querySelector("[data-figure-shoulders]").setAttribute("cx", centerX);
    root.querySelector("[data-figure-pelvis]").setAttribute("rx", pelvisRx);
    root.querySelector("[data-figure-pelvis]").setAttribute("cx", centerX);
    root.querySelector("[data-figure-spine]").setAttribute("x1", centerX);
    root.querySelector("[data-figure-spine]").setAttribute("x2", centerX);
    root.querySelector("[data-figure-neck]").setAttribute("x1", centerX);
    root.querySelector("[data-figure-neck]").setAttribute("x2", centerX);
    root.querySelector("[data-figure-head]").setAttribute("cx", centerX);
    root.querySelector("[data-figure-left-arm]").setAttribute("d", "M" + centerX + " 91 L" + (centerX - torsoRx * 0.78) + " 132 L" + centerX + " 166");
    root.querySelector("[data-figure-right-arm]").setAttribute("d", "M" + centerX + " 91 L" + (centerX + torsoRx * 0.78) + " 132 L" + centerX + " 166");
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

    const torso = baseValue("torso_rotation") ?? 0;
    const pelvis = baseValue("pelvis_rotation") ?? 0;
    const spine = baseValue("spine_tilt") ?? 0;
    const sway = baseValue("torso_sway") ?? 0;
    const projected = {
      torso: torso + Number(control("torso").value),
      pelvis: pelvis + Number(control("pelvis").value),
      spine: spine + Number(control("spine").value),
      sway: sway + Number(control("sway").value),
    };
    controlNames.forEach((name) => {
      const delta = Number(control(name).value);
      output(name).textContent = signed(delta, name === "sway" ? " in" : "°");
    });
    root.querySelector("[data-sim-readout='torso']").textContent = formatted(projected.torso) + "°";
    root.querySelector("[data-sim-readout='pelvis']").textContent = formatted(projected.pelvis) + "°";
    root.querySelector("[data-sim-readout='spine']").textContent = formatted(projected.spine) + "°";
    root.querySelector("[data-sim-readout='sway']").textContent = formatted(projected.sway) + " in";
    const baseX = baseValue("x_factor");
    const deltaX = Number(control("torso").value) - Number(control("pelvis").value);
    root.querySelector("[data-sim-readout='xfactor']").textContent = baseX === null ? "—" : signed(baseX + deltaX, "°");
    updateFigure(projected);

    const pelvisDelta = Number(control("pelvis").value);
    const torsoDelta = Number(control("torso").value);
    const spineDelta = Number(control("spine").value);
    const armsDelta = Number(control("arms").value);
    const pathDelta = -0.10 * pelvisDelta - 0.06 * torsoDelta + 0.025 * spineDelta + 0.12 * armsDelta;
    const faceDelta = -0.025 * pelvisDelta - 0.035 * torsoDelta + 0.075 * armsDelta;
    const basePath = number(root.querySelector('[data-sim-base="path"]').value) ?? 0;
    const baseFace = number(root.querySelector('[data-sim-base="face"]').value) ?? 0;
    const estimatedPath = basePath + pathDelta;
    const estimatedFace = baseFace + faceDelta;
    const faceToPath = estimatedFace - estimatedPath;
    root.querySelector('[data-sim-delivery="path"]').textContent = signed(estimatedPath, "°");
    root.querySelector('[data-sim-delivery="face"]').textContent = signed(estimatedFace, "°");
    root.querySelector('[data-sim-delivery="f2p"]').textContent = signed(faceToPath, "°");
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
    root.querySelector("[data-sim-flight-path]").setAttribute("d", "M160 200 C" + c1x + " 154 " + c2x + " 82 " + endX + " 30");
    root.querySelector("[data-sim-flight-end]").setAttribute("cx", String(endX));
    const shape = faceToPath > 2.5 ? "FADE / CUT" : faceToPath < -2.5 ? "DRAW" : "STRAIGHT";
    root.querySelector("[data-sim-flight-shape]").textContent = shape;
    root.querySelector("[data-sim-flight-start]").textContent = Math.abs(launch) < 0.5 ? "Starts close to the target line" : "Starts " + (launch > 0 ? "right" : "left") + " of the target";
    root.querySelector("[data-sim-flight-curve]").textContent = Math.abs(faceToPath) < 0.5
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
  root.querySelectorAll("[data-sim-base]").forEach((input) => input.addEventListener("input", render));
  playButton.addEventListener("click", () => {
    if (timer) { stop(); return; }
    playButton.textContent = "Ⅱ Pause";
    playButton.setAttribute("aria-pressed", "true");
    timer = window.setInterval(() => {
      frameIndex = (frameIndex + 1) % frames.length;
      render();
    }, 700);
  });
  render();
})();