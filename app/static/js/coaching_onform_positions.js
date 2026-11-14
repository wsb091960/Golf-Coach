(() => {
  const review = document.querySelector("[data-coaching-onform-package]");
  if (!review) return;
  const read = (id) => { try { return JSON.parse(document.getElementById(id)?.textContent || "{}"); } catch { return {}; } };
  const metrics = read("gcie-onform-position-metrics");
  const images = read("gcie-onform-position-images");
  const sequence = read("gcie-onform-sequence-text");
  if (!metrics || typeof metrics !== "object" || !Object.keys(metrics).length) return;
  const positions = Array.from({ length: 8 }, (_, i) => `P${i + 1}`);
  const definitions = [
    ["torso_rotation", "°", "torso_rotation_direction"], ["pelvis_rotation", "°", "pelvis_rotation_direction"],
    ["x_factor", "°", null], ["torso_sway", " in", "torso_sway_direction"],
    ["pelvis_sway", " in", "pelvis_sway_direction"], ["pelvis_lift", " in", "pelvis_lift_direction"],
    ["torso_lift", " in", "torso_lift_direction"], ["torso_forward_bend", "°", "torso_forward_bend_direction"],
    ["shoulder_tilt", "°", null], ["hip_tilt", "°", null], ["spine_tilt", "°", null], ["shaft_angle", "°", null],
  ];
  const numberText = (value) => {
    const n = Number(value);
    return Number.isFinite(n) ? (Number.isInteger(n) ? String(n) : n.toFixed(1)) : "—";
  };
  const chart = document.getElementById("gcie-turn-chart");
  const ns = "http://www.w3.org/2000/svg";

  function renderChart() {
    if (!chart) return;
    chart.replaceChildren();
    const add = (tag, attrs, value) => {
      const node = document.createElementNS(ns, tag);
      Object.entries(attrs).forEach(([key, val]) => node.setAttribute(key, val));
      if (value !== undefined) node.textContent = value;
      chart.appendChild(node);
      return node;
    };
    [40, 80, 120, 160].forEach((y) => add("line", { x1: 34, x2: 490, y1: y, y2: y, stroke: "#e7ece9", "stroke-width": 1 }));
    const series = [
      { key: "pelvis_rotation", color: "#d3a337" },
      { key: "torso_rotation", color: "#348368" },
      { key: "x_factor", color: "#77a2bc", dash: "5 4" },
    ];
    const values = series.flatMap((s) => positions.map((p) => metrics[p]?.[s.key]).filter((v) => v !== null && v !== undefined && v !== "" && Number.isFinite(Number(v))).map(Number));
    if (!values.length) {
      add("text", { x: 250, y: 100, "text-anchor": "middle", fill: "#77877f", "font-size": 12 }, "No readable turn values in the OCR data");
      positions.forEach((p, i) => add("text", { x: 38 + i * 64, y: 183, "text-anchor": "middle", fill: "#74847b", "font-size": 9 }, p));
      return;
    }
    const low = Math.min(0, ...values), high = Math.max(1, ...values), span = high - low || 1;
    const x = (i) => 38 + i * 64, y = (v) => 158 - ((v - low) / span) * 112;
    series.forEach((s) => {
      let segment = [];
      const flush = () => {
        if (segment.length > 1) add("polyline", { points: segment.map((p) => `${p.x},${p.y}`).join(" "), fill: "none", stroke: s.color, "stroke-width": 2.5, ...(s.dash ? { "stroke-dasharray": s.dash } : {}) });
        segment.forEach((p) => add("circle", { cx: p.x, cy: p.y, r: 3.5, fill: s.color }));
        segment = [];
      };
      positions.forEach((p, i) => { const raw = metrics[p]?.[s.key], val = Number(raw); if (raw !== null && raw !== undefined && raw !== "" && Number.isFinite(val)) segment.push({ x: x(i), y: y(val) }); else flush(); });
      flush();
    });
    positions.forEach((p, i) => add("text", { x: x(i), y: 183, "text-anchor": "middle", fill: "#74847b", "font-size": 9 }, p));
  }

  function select(position) {
    const vals = metrics[position] || {};
    review.querySelectorAll("[data-position]").forEach((button) => {
      const selected = button.dataset.position === position;
      button.classList.toggle("is-selected", selected);
      button.setAttribute("aria-pressed", String(selected));
    });
    review.querySelectorAll("[data-position-card]").forEach((card) => {
      card.classList.toggle("is-selected", card.dataset.positionCard === position);
    });
    const count = definitions.filter(([key]) => vals[key] !== undefined && vals[key] !== null && vals[key] !== "" && Number.isFinite(Number(vals[key]))).length;
    const countNode = review.querySelector("[data-coaching-ocr-count]"); if (countNode) countNode.textContent = `${count} of ${definitions.length} values`;
    const sequenceText = String(sequence[position] || "").trim();
    const seqNode = review.querySelector("[data-coaching-sequence-text]"); if (seqNode) seqNode.textContent = sequenceText || "No sequence text was readable for this position.";
    const seqStatus = review.querySelector("[data-coaching-sequence-status]"); if (seqStatus) seqStatus.textContent = sequenceText ? "Text read" : "No text read";
    const seqPosition = review.querySelector("[data-coaching-sequence-position]"); if (seqPosition) seqPosition.textContent = position;
    const metricPosition = review.querySelector("[data-selected-metric-position]"); if (metricPosition) metricPosition.textContent = position;
    const video = document.getElementById("gcie-review-video");
    const timedPoint = [...review.querySelectorAll("[data-checkpoint-time]")].find((button) => button.dataset.position === position && button.dataset.checkpointTime !== "" && Number.isFinite(Number(button.dataset.checkpointTime)));
    if (video && timedPoint) {
      video.pause();
      const seek = () => { video.currentTime = Math.max(0, Math.min(Number(timedPoint.dataset.checkpointTime), Number.isFinite(video.duration) ? video.duration : Number(timedPoint.dataset.checkpointTime))); };
      if (video.readyState >= 1) seek(); else video.addEventListener("loadedmetadata", seek, { once: true });
    }
    definitions.forEach(([key, unit, directionKey]) => {
      const tile = review.querySelector(`[data-metric-tile="${key}"]`); if (!tile) return;
      const raw = vals[key], has = raw !== undefined && raw !== null && raw !== "" && Number.isFinite(Number(raw));
      const valueNode = tile.querySelector("[data-metric-value]"), detail = tile.querySelector("[data-metric-detail]");
      if (valueNode) valueNode.textContent = has ? `${numberText(raw)}${unit}` : "—";
      const direction = directionKey ? vals[directionKey] : "";
      if (detail) detail.textContent = !has ? "Not read in this screenshot" : direction ? String(direction).replaceAll("_", " ").toLowerCase() : "OCR reading · review";
      tile.dataset.state = has ? (review.dataset.verified === "true" ? "good" : "warning") : "warning";
    });
  }

  review.dataset.verified = document.querySelector(".gcie-metrics-card .gcie-data-badge")?.textContent?.includes("VERIFIED") ? "true" : "false";
  review.querySelectorAll("[data-position]").forEach((button) => button.addEventListener("click", () => select(button.dataset.position)));
  renderChart();
  select(images.find((item) => item.available !== false)?.position || "P1");
})();
