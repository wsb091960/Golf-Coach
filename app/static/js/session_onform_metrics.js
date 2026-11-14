(function () {
  "use strict";

  const definitions = [
    { key: "torso_rotation", label: "Torso turn", unit: "°", direction: "torso_rotation_direction" },
    { key: "pelvis_rotation", label: "Pelvis turn", unit: "°", direction: "pelvis_rotation_direction" },
    { key: "x_factor", label: "X-Factor", unit: "°" },
    { key: "torso_sway", label: "Torso sway", unit: '"', direction: "torso_sway_direction" },
    { key: "pelvis_sway", label: "Pelvis sway", unit: '"', direction: "pelvis_sway_direction" },
    { key: "pelvis_lift", label: "Pelvis lift", unit: '"', direction: "pelvis_lift_direction" },
    { key: "torso_lift", label: "Torso lift", unit: '"', direction: "torso_lift_direction" },
    { key: "torso_forward_bend", label: "Torso forward bend", unit: "°", direction: "torso_forward_bend_direction" },
  ];
  const positions = Array.from({ length: 8 }, (_, index) => `P${index + 1}`);
  const series = [
    { key: "pelvis_rotation", color: "#d3a337" },
    { key: "torso_rotation", color: "#348368" },
    { key: "x_factor", color: "#77a2bc", dash: "5 4" },
  ];
  const svgNS = "http://www.w3.org/2000/svg";
  const format = (value) => {
    const number = Number(value);
    if (!Number.isFinite(number)) return "—";
    return Number.isInteger(number) ? String(number) : number.toFixed(1);
  };
  const parse = (node) => { try { return JSON.parse(node?.textContent || "{}"); } catch (_) { return {}; } };

  document.querySelectorAll("[data-session-onform-package]").forEach((packageNode) => {
    const card = packageNode.querySelector("[data-session-onform-metrics]");
    if (!card) return;
    const data = parse(card.querySelector(".session-onform-metrics-data"));
    const imageData = parse(card.querySelector(".session-onform-images-data"));
    const sequenceData = parse(card.querySelector(".session-onform-sequence-data"));
    const chart = card.querySelector(".session-onform-chart");

    function renderChart() {
      if (!chart) return;
      chart.replaceChildren();
      const add = (tag, attrs, textValue) => {
        const node = document.createElementNS(svgNS, tag);
        Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, value));
        if (textValue !== undefined) node.textContent = textValue;
        chart.appendChild(node);
        return node;
      };
      [40, 80, 120, 160].forEach((y) => add("line", { x1: 34, x2: 490, y1: y, y2: y, stroke: "#e7ece9", "stroke-width": 1 }));
      const values = series.flatMap((item) => positions.map((position) => Number(data[position]?.[item.key])).filter(Number.isFinite));
      if (!values.length) {
        add("text", { x: 250, y: 100, "text-anchor": "middle", fill: "#77877f", "font-size": 12 }, "No readable turn values in the saved OCR data");
        positions.forEach((position, index) => add("text", { x: 38 + index * (448 / 7), y: 183, "text-anchor": "middle", fill: "#74847b", "font-size": 9 }, position));
        return;
      }
      const low = Math.min(0, ...values);
      const high = Math.max(1, ...values);
      const span = high - low || 1;
      const xFor = (index) => 38 + index * (448 / 7);
      const yFor = (value) => 158 - ((value - low) / span) * 112;
      series.forEach((item) => {
        let segment = [];
        const flush = () => {
          if (segment.length > 1) add("polyline", { points: segment.map((point) => `${point.x},${point.y}`).join(" "), fill: "none", stroke: item.color, "stroke-width": 2.5, ...(item.dash ? { "stroke-dasharray": item.dash } : {}) });
          segment.forEach((point) => add("circle", { cx: point.x, cy: point.y, r: 3.5, fill: item.color }));
          segment = [];
        };
        positions.forEach((position, index) => {
          const value = Number(data[position]?.[item.key]);
          if (Number.isFinite(value)) segment.push({ x: xFor(index), y: yFor(value) }); else flush();
        });
        flush();
      });
      positions.forEach((position, index) => add("text", { x: xFor(index), y: 183, "text-anchor": "middle", fill: "#74847b", "font-size": 9 }, position));
    }

    function selectPosition(position) {
      const values = data[position] || {};
      packageNode.querySelectorAll("[data-position]").forEach((button) => {
        const selected = button.dataset.position === position;
        button.classList.toggle("is-selected", selected);
        button.setAttribute("aria-pressed", selected ? "true" : "false");
      });
      const image = imageData.find((item) => item.position === position);
      const imageNode = packageNode.querySelector("[data-current-position-image]");
      const imageLink = packageNode.querySelector("[data-current-image-link]");
      if (image && imageNode) {
        imageNode.src = image.url;
        imageNode.alt = `${position} Onform screenshot`;
        imageLink.href = image.url;
        imageLink.hidden = false;
      } else if (imageLink) imageLink.hidden = true;
      const positionLabel = packageNode.querySelector("[data-current-position-label]");
      if (positionLabel) positionLabel.textContent = position;
      const caption = packageNode.querySelector("[data-current-image-caption]");
      if (caption) caption.textContent = image?.label || position;
      const metricCount = definitions.filter((definition) => values[definition.key] !== undefined && values[definition.key] !== null && values[definition.key] !== "" && Number.isFinite(Number(values[definition.key]))).length;
      const countNode = packageNode.querySelector("[data-ocr-metric-count]");
      if (countNode) countNode.textContent = metricCount ? `${metricCount} of ${definitions.length} values` : "No values read";
      const sequenceText = String(sequenceData[position] || "").trim();
      const sequenceNode = packageNode.querySelector("[data-ocr-sequence-text]");
      if (sequenceNode) sequenceNode.textContent = sequenceText || "No sequence text was saved for this position.";
      const sequenceStatus = packageNode.querySelector("[data-ocr-sequence-status]");
      if (sequenceStatus) sequenceStatus.textContent = sequenceText ? "Text saved" : "No text saved";
      definitions.forEach((definition) => {
        const tile = card.querySelector(`[data-metric-tile="${definition.key}"]`);
        if (!tile) return;
        const raw = values[definition.key];
        const hasValue = raw !== undefined && raw !== null && raw !== "" && Number.isFinite(Number(raw));
        tile.querySelector("[data-metric-value]").textContent = hasValue ? `${format(raw)}${definition.unit}` : "—";
        const direction = definition.direction ? values[definition.direction] : "";
        tile.querySelector("[data-metric-detail]").textContent = !hasValue ? "No readable value" : direction ? String(direction).replaceAll("_", " ").toLowerCase() : "Onform screenshot value";
        tile.dataset.state = !hasValue ? "bad" : card.dataset.verified === "true" ? "good" : "warning";
      });
    }
    packageNode.querySelectorAll("[data-position]").forEach((button) => button.addEventListener("click", () => selectPosition(button.dataset.position)));
    renderChart();
    selectPosition("P1");
  });
})();
