(() => {
  const video = document.getElementById("gcie-review-video");
  document.querySelectorAll(".gcie-checkpoint[data-checkpoint-time]").forEach((button) => {
    const time = Number(button.dataset.checkpointTime);
    if (!Number.isFinite(time)) {
      button.disabled = true;
      return;
    }
    button.addEventListener("click", () => {
      if (!video) return;
      const seek = () => {
        video.currentTime = Math.max(0, Math.min(time, Number.isFinite(video.duration) ? video.duration : time));
        video.play().catch(() => {});
      };
      if (video.readyState >= 1) seek();
      else video.addEventListener("loadedmetadata", seek, { once: true });
    });
  });

  const chart = document.getElementById("gcie-turn-chart");
  const historyNode = document.getElementById("gcie-onform-history");
  if (!chart || !historyNode) return;
  let history = [];
  try { history = JSON.parse(historyNode.textContent || "[]"); } catch { history = []; }
  const order = ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "P10"];
  const latestByPoint = new Map();
  history.forEach((row) => {
    if (row && order.includes(row.checkpoint) && row.metrics && typeof row.metrics === "object") latestByPoint.set(row.checkpoint, row.metrics);
  });
  const points = order.filter((point) => latestByPoint.has(point));
  const series = [
    { key: "pelvis_rotation", color: "#d3a337" },
    { key: "torso_rotation", color: "#348368" },
    { key: "x_factor", color: "#77a2bc", dash: "5 4" },
  ];
  const ns = "http://www.w3.org/2000/svg";
  const add = (tag, attrs, content) => {
    const el = document.createElementNS(ns, tag);
    Object.entries(attrs).forEach(([key, value]) => el.setAttribute(key, value));
    if (content !== undefined) el.textContent = content;
    chart.appendChild(el);
    return el;
  };
  chart.innerHTML = "";
  [40, 80, 120, 160].forEach((y) => add("line", { x1: 34, x2: 490, y1: y, y2: y, stroke: "#e7ece9", "stroke-width": 1 }));
  if (!points.length) {
    add("text", { x: 250, y: 94, "text-anchor": "middle", fill: "#77877f", "font-size": 12 }, "Save Onform data at P-positions to chart the swing");
    return;
  }
  const values = series.flatMap((s) => points.map((p) => Number(latestByPoint.get(p)[s.key])).filter(Number.isFinite));
  const low = Math.min(0, ...values);
  const high = Math.max(1, ...values);
  const span = high - low || 1;
  const xy = (index, value) => ({ x: points.length === 1 ? 262 : 38 + index * (448 / (points.length - 1)), y: 158 - ((value - low) / span) * 112 });
  series.forEach((s) => {
    const vals = points.map((p, index) => {
      const value = Number(latestByPoint.get(p)[s.key]);
      return Number.isFinite(value) ? { ...xy(index, value), value } : null;
    });
    const defined = vals.filter(Boolean);
    if (defined.length > 1) {
      add("polyline", {
        points: defined.map((p) => `${p.x},${p.y}`).join(" "),
        fill: "none", stroke: s.color, "stroke-width": 2.5,
        ...(s.dash ? { "stroke-dasharray": s.dash } : {}),
      });
    }
    defined.forEach((p) => add("circle", { cx: p.x, cy: p.y, r: 3.5, fill: s.color }));
  });
  points.forEach((point, index) => {
    const pos = xy(index, low);
    add("text", { x: pos.x, y: 183, "text-anchor": "middle", fill: "#74847b", "font-size": 9 }, point);
  });
})();
