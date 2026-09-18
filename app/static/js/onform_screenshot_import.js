(function () {
  "use strict";

  const root = document.getElementById("onform-screenshot-import");
  if (!root) return;

  const analysisId = document.querySelector(".swing-analysis-page")?.dataset.analysisId;
  const file1 = document.getElementById("onform-screenshot-file-1");
  const file2 = document.getElementById("onform-screenshot-file-2");
  const file3 = document.getElementById("onform-screenshot-file-3");
  const preview1 = document.getElementById("onform-screenshot-preview-1");
  const preview2 = document.getElementById("onform-screenshot-preview-2");
  const preview3 = document.getElementById("onform-screenshot-preview-3");
  const extractButton = document.getElementById("onform-screenshot-extract");
  const saveButton = document.getElementById("onform-screenshot-save");
  const status = document.getElementById("onform-screenshot-status");
  const verified = document.getElementById("onform-screenshot-verified");
  const shotSelect = document.getElementById("onform-screenshot-shot");
  const checkpointSelect = document.getElementById("onform-screenshot-checkpoint");
  const conflictsBox = document.getElementById("onform-screenshot-conflicts");
  const savedImportNode = document.getElementById("onform-saved-import");
  const primaryGoalNode = document.getElementById("student-primary-goal");
  let primaryGoal = "";
  try {
    primaryGoal = primaryGoalNode ? JSON.parse(primaryGoalNode.textContent || '""') : "";
  } catch (_error) {
    primaryGoal = "";
  }
  primaryGoal = String(primaryGoal || "").trim();

  let savedImport = null;
  try {
    savedImport = savedImportNode ? JSON.parse(savedImportNode.textContent || "null") : null;
  } catch (_error) {
    savedImport = null;
  }

  let ocrText1 = "";
  let ocrText2 = "";
  let ocrText3 = "";
  let conflicts = [];

  const definitions = [
    { key: "face_to_path", aliases: ["FACE TO PATH", "FACE-TO-PATH", "F2P"], signedDirection: true },
    { key: "club_path", aliases: ["CLUB PATH"], signedDirection: true },
    { key: "club_face", aliases: ["FACE ANGLE", "CLUB FACE"], signedDirection: true },
    { key: "attack_angle", aliases: ["ATTACK ANGLE", "ANGLE OF ATTACK", "AOA"], signedDirection: true },
    { key: "launch_direction", aliases: ["LAUNCH DIRECTION", "START DIRECTION"], signedDirection: true },
    { key: "spin_rate", aliases: ["BACK SPIN", "BACKSPIN", "SPIN RATE"] },
    { key: "ball_speed", aliases: ["BALL SPEED"] },
    { key: "club_speed", aliases: ["CLUB SPEED"] },
    { key: "launch_angle", aliases: ["LAUNCH ANGLE"] },
    { key: "side_spin_rpm", aliases: ["SIDE SPIN", "SIDESPIN"] },
    { key: "spin_axis", aliases: ["SPIN AXIS"] },
    { key: "carry_distance", aliases: ["CARRY DISTANCE", "CARRY"] },
    { key: "total_distance", aliases: ["TOTAL DISTANCE", "TOTAL"] },
    { key: "apex_height", aliases: ["APEX HEIGHT", "APEX"] },
    { key: "offline_distance", aliases: ["OFFLINE DISTANCE", "OFFLINE"], signedDirection: true },
    { key: "smash_factor", aliases: ["SMASH FACTOR", "SMASH"] },
    { key: "torso_rotation", aliases: ["TORSO TURN", "TORSO ROTATION"], keepDirection: true },
    { key: "pelvis_rotation", aliases: ["PELVIS TURN", "PELVIS ROTATION"], keepDirection: true },
    { key: "x_factor", aliases: ["XFACTOR", "X-FACTOR", "X FACTOR"] },
    { key: "torso_sway", aliases: ["TORSO SWAY"], keepDirection: true },
    { key: "pelvis_sway", aliases: ["PELVIS SWAY"], keepDirection: true },
    { key: "pelvis_lift", aliases: ["PELVIS LIFT"], keepDirection: true },
    { key: "shoulder_tilt", aliases: ["SHOULDER TILT"] },
    { key: "hip_tilt", aliases: ["HIP TILT", "PELVIS TILT"] },
    { key: "spine_tilt", aliases: ["SPINE TILT"] },
    { key: "shaft_angle", aliases: ["SHAFT ANGLE"] }
  ];

  const directionWords = new Set(["LEFT", "RIGHT", "UP", "DOWN", "OPEN", "CLOSED", "AWAY", "TOWARDS", "TOWARD"]);

  function normalizeText(value) {
    return String(value || "")
      .toUpperCase()
      .replace(/[|]/g, "I")
      .replace(/[–—]/g, "-")
      .replace(/\s+/g, " ")
      .trim();
  }

  function signedValue(value, suffix, direction) {
    let n = Number(value);
    if (!Number.isFinite(n)) return null;
    const d = String(direction || suffix || "").toUpperCase();
    if (["L", "LEFT", "D", "DOWN"].includes(d)) n = -Math.abs(n);
    if (["R", "RIGHT", "U", "UP"].includes(d)) n = Math.abs(n);
    return n;
  }

  function cleanOcrToken(value) {
    return normalizeText(value)
      .replace(/[“”]/g, '"')
      .replace(/[^A-Z0-9.+\-"°]/g, "");
  }

  function tokenCenter(word) {
    const box = word.bbox || {};
    return {
      x: ((box.x0 || 0) + (box.x1 || 0)) / 2,
      y: ((box.y0 || 0) + (box.y1 || 0)) / 2,
      h: Math.max(1, (box.y1 || 0) - (box.y0 || 0)),
    };
  }

  function numericToken(value) {
    const cleaned = String(value || "")
      .replace(/,/g, "")
      .replace(/[Oo](?=\d)/g, "0")
      .replace(/[−–—]/g, "-")
      .trim();
    const match = cleaned.match(/([+-]?\d+(?:\.\d+)?)/);
    if (!match) return null;
    const number = Number(match[1]);
    if (!Number.isFinite(number)) return null;
    const suffixMatch = cleaned.toUpperCase().match(/(?:°)?\s*([LRUD])\b/);
    return { value: number, suffix: suffixMatch ? suffixMatch[1] : "" };
  }

  function aliasTokens(alias) {
    return normalizeText(alias).split(/\s+/).filter(Boolean).map(cleanOcrToken);
  }

  function wordsMatchAlias(words, startIndex, alias) {
    const wanted = aliasTokens(alias);
    if (!wanted.length || startIndex + wanted.length > words.length) return false;
    for (let i = 0; i < wanted.length; i += 1) {
      const got = cleanOcrToken(words[startIndex + i].text);
      if (got === wanted[i]) continue;
      // Permit common OCR loss of punctuation/hyphen in labels, but never fuzzy-match values.
      if (got.replace(/-/g, "") === wanted[i].replace(/-/g, "")) continue;
      return false;
    }
    return true;
  }

  function clusterLines(words) {
    const usable = (words || [])
      .filter((w) => w && w.text && (w.confidence == null || w.confidence >= 25) && w.bbox)
      .map((w) => ({ ...w, center: tokenCenter(w) }))
      .sort((a, b) => a.center.y - b.center.y || a.center.x - b.center.x);
    if (!usable.length) return [];

    const heights = usable.map((w) => w.center.h).sort((a, b) => a - b);
    const medianH = heights[Math.floor(heights.length / 2)] || 18;
    const tolerance = Math.max(8, medianH * 0.65);
    const lines = [];
    usable.forEach((word) => {
      let line = lines.find((candidate) => Math.abs(candidate.y - word.center.y) <= tolerance);
      if (!line) {
        line = { y: word.center.y, words: [] };
        lines.push(line);
      }
      line.words.push(word);
      line.y = line.words.reduce((sum, item) => sum + item.center.y, 0) / line.words.length;
    });
    lines.forEach((line) => line.words.sort((a, b) => a.center.x - b.center.x));
    return lines.sort((a, b) => a.y - b.y);
  }

  function detectSpatialLabels(words) {
    const lines = clusterLines(words);
    const labels = [];
    lines.forEach((line) => {
      definitions.forEach((def) => {
        def.aliases.forEach((alias) => {
          const wanted = aliasTokens(alias);
          for (let i = 0; i <= line.words.length - wanted.length; i += 1) {
            if (!wordsMatchAlias(line.words, i, alias)) continue;
            const slice = line.words.slice(i, i + wanted.length);
            const x0 = Math.min(...slice.map((w) => w.bbox.x0));
            const x1 = Math.max(...slice.map((w) => w.bbox.x1));
            const y0 = Math.min(...slice.map((w) => w.bbox.y0));
            const y1 = Math.max(...slice.map((w) => w.bbox.y1));
            labels.push({ def, x0, x1, y0, y1, centerX: (x0 + x1) / 2, confidence: Math.min(...slice.map((w) => w.confidence ?? 100)) });
            break;
          }
        });
      });
    });

    // Deduplicate aliases for the same metric; keep the best-confidence / widest label.
    const byKey = new Map();
    labels.forEach((label) => {
      const prior = byKey.get(label.def.key);
      if (!prior || label.confidence > prior.confidence || (label.confidence === prior.confidence && (label.x1-label.x0) > (prior.x1-prior.x0))) {
        byKey.set(label.def.key, label);
      }
    });
    return [...byKey.values()].sort((a, b) => a.centerX - b.centerX);
  }

  function normalizeDirection(value) {
    const d = normalizeText(value).replace(/[^A-Z]/g, "");
    if (d === "TOWARD") return "TOWARDS";
    return directionWords.has(d) ? d : "";
  }

  function parseSpatialWords(words, canvasWidth) {
    const labels = detectSpatialLabels(words);
    if (!labels.length) return { metrics: {}, labelsFound: 0, matches: [] };
    const usable = (words || []).filter((w) => w && w.text && w.bbox && (w.confidence == null || w.confidence >= 20));
    const metrics = {};
    const matches = [];

    labels.forEach((label, index) => {
      const prev = labels[index - 1];
      const next = labels[index + 1];
      const left = prev ? (prev.centerX + label.centerX) / 2 : Math.max(0, label.centerX - (next ? (next.centerX-label.centerX)/2 : canvasWidth * 0.06));
      const right = next ? (label.centerX + next.centerX) / 2 : Math.min(canvasWidth || Number.MAX_SAFE_INTEGER, label.centerX + (prev ? (label.centerX-prev.centerX)/2 : canvasWidth * 0.06));
      const candidates = usable
        .map((w) => ({ w, center: tokenCenter(w), num: numericToken(w.text), dir: normalizeDirection(w.text) }))
        .filter((item) => item.center.x >= left && item.center.x <= right && item.w.bbox.y0 > label.y1 - 2)
        .sort((a, b) => a.w.bbox.y0 - b.w.bbox.y0 || Math.abs(a.center.x-label.centerX)-Math.abs(b.center.x-label.centerX));

      const numberItem = candidates.find((item) => item.num);
      if (!numberItem) return;
      // Spatial safety: reject numbers that are far horizontally from their detected label.
      const columnWidth = Math.max(20, right-left);
      if (Math.abs(numberItem.center.x - label.centerX) > columnWidth * 0.48) return;

      const directionItem = candidates.find((item) => item.dir && item.w.bbox.y0 >= numberItem.w.bbox.y0 - 2);
      const direction = directionItem ? directionItem.dir : numberItem.num.suffix;
      const def = label.def;
      const value = def.signedDirection ? signedValue(numberItem.num.value, numberItem.num.suffix, direction) : numberItem.num.value;
      metrics[def.key] = value;
      if (def.keepDirection && direction) metrics[`${def.key}_direction`] = direction;
      matches.push({ key: def.key, value, direction, labelX: label.centerX, valueX: numberItem.center.x });
    });
    return { metrics, labelsFound: labels.length, matches };
  }

  function parseAdjacent(text) {
    // Conservative fallback only: values must be immediately adjacent to their labels.
    // Do NOT assign numbers by overall OCR order; that caused metric cross-wiring in 5.2.5A.
    const found = {};
    const upper = normalizeText(text);
    definitions.forEach((def) => {
      for (const alias of def.aliases) {
        const escaped = alias.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        const re = new RegExp(escaped + "\\s*[:=]?\\s*([+-]?\\d+(?:\\.\\d+)?)\\s*(?:°)?\\s*([LRUD])?(?:\\s+(LEFT|RIGHT|UP|DOWN|OPEN|CLOSED|AWAY|TOWARDS|TOWARD))?", "i");
        const m = upper.match(re);
        if (!m) continue;
        const direction = (m[3] || m[2] || "").toUpperCase();
        found[def.key] = def.signedDirection ? signedValue(m[1], m[2], direction) : Number(m[1]);
        if (def.keepDirection && direction) found[`${def.key}_direction`] = direction === "TOWARD" ? "TOWARDS" : direction;
        break;
      }
    });
    return found;
  }

  function parseRibbonText(text) {
    return parseAdjacent(text);
  }

  async function ribbonCanvas(file) {
    const bitmap = await createImageBitmap(file);
    // Onform's metric ribbon occupies roughly the bottom 10-12% of the screenshots.
    // Keep a small margin above it, but exclude the swing image/body-overlay numbers.
    const cropRatio = 0.15;
    const sourceY = Math.max(0, Math.floor(bitmap.height * (1 - cropRatio)));
    const sourceH = bitmap.height - sourceY;
    const scale = 2.5;
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(bitmap.width * scale);
    canvas.height = Math.round(sourceH * scale);
    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    ctx.fillStyle = "black";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(bitmap, 0, sourceY, bitmap.width, sourceH, 0, 0, canvas.width, canvas.height);

    // High-contrast monochrome preprocessing improves the white-on-black ribbon OCR
    // and suppresses most photographic detail above the ribbon.
    const image = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const data = image.data;
    for (let i = 0; i < data.length; i += 4) {
      const lum = 0.2126 * data[i] + 0.7152 * data[i+1] + 0.0722 * data[i+2];
      const value = lum >= 150 ? 255 : 0;
      data[i] = value; data[i+1] = value; data[i+2] = value; data[i+3] = 255;
    }
    ctx.putImageData(image, 0, 0);
    bitmap.close();
    return canvas;
  }

  async function readScreenshot(file, number) {
    const canvas = await ribbonCanvas(file);
    const result = await window.Tesseract.recognize(canvas, "eng", {
      logger: (m) => {
        if (m.status === "recognizing text") {
          status.textContent = `Reading screenshot ${number}… ${Math.round((m.progress || 0) * 100)}%`;
        }
      }
    });
    const text = result?.data?.text || "";
    const spatial = parseSpatialWords(result?.data?.words || [], canvas.width);
    // 5.2.5B safety rule: never fall back to row-order or plain-text inference.
    // If Tesseract cannot spatially pair a label with its value, leave that field blank.
    const metrics = spatial.metrics;
    return { text, metrics, spatial };
  }

  function nearlyEqual(a, b) {
    if (typeof a === "number" && typeof b === "number") return Math.abs(a - b) <= 0.05;
    return String(a).trim().toUpperCase() === String(b).trim().toUpperCase();
  }

  function mergeMetrics(a, b) {
    const merged = { ...a };
    const disagreement = [];
    Object.entries(b).forEach(([key, value]) => {
      if (!(key in merged) || merged[key] === "" || merged[key] == null) {
        merged[key] = value;
      } else if (!nearlyEqual(merged[key], value)) {
        disagreement.push({ key, first: merged[key], second: value });
      }
    });
    return { merged, disagreement };
  }

  function fillMetrics(metrics) {
    root.querySelectorAll("[data-onform-metric]").forEach((input) => {
      input.classList.remove("metric-conflict");
      if (Object.prototype.hasOwnProperty.call(metrics, input.dataset.onformMetric)) {
        input.value = metrics[input.dataset.onformMetric];
      }
    });
  }

  function showConflicts(items) {
    conflicts = items;
    if (!items.length) {
      conflictsBox.hidden = true;
      conflictsBox.innerHTML = "";
      return;
    }
    const names = items.map((item) => item.key.replaceAll("_", " ")).join(", ");
    conflictsBox.hidden = false;
    conflictsBox.innerHTML = `<strong>Coach review required:</strong> screenshots disagree on ${names}. Screenshot 1 values remain in the fields until you review and edit them.`;
    items.forEach((item) => {
      const input = root.querySelector(`[data-onform-metric="${item.key}"]`);
      if (input) input.classList.add("metric-conflict");
    });
  }

  function collectMetrics() {
    const metrics = {};
    root.querySelectorAll("[data-onform-metric]").forEach((input) => {
      const value = input.value.trim();
      if (value === "") return;
      metrics[input.dataset.onformMetric] = input.type === "number" ? Number(value) : value;
    });
    return metrics;
  }

  function collectSequence() {
    const sequence = {};
    root.querySelectorAll("[data-onform-sequence]").forEach((input) => {
      const value = input.value.trim();
      if (value === "") return;
      sequence[input.dataset.onformSequence] = input.type === "number" ? Number(value) : value;
    });
    return sequence;
  }

  async function readSequenceScreenshot(file) {
    if (!window.Tesseract) return "";
    const result = await Tesseract.recognize(file, "eng");
    return result?.data?.text || "";
  }

  function updateCoachingGoalRead() {
    const get = (key) => {
      const el = root.querySelector(`[data-onform-metric="${key}"]`);
      if (!el || el.value === "") return null;
      const n = Number(el.value);
      return Number.isFinite(n) ? n : null;
    };

    const path = get("club_path");
    const face = get("club_face");
    const ftp = get("face_to_path");
    const launch = get("launch_direction");
    const order = (
      root.querySelector('[data-onform-sequence="peak_order"]')?.value || ""
    ).trim();

    const output = document.getElementById("coaching-goal-text");
    if (!output) return;

    const goal = primaryGoal.toLowerCase();
    const parts = [];

    if (!primaryGoal) {
      parts.push(
        "No Student Primary Goal is set. Add the coaching objective on the Student page so Golf Coach can evaluate these measurements against the intended ball flight or movement change."
      );
    } else {
      parts.push(`Analysis objective: ${primaryGoal}.`);
    }

    const wantsDraw = /\bdraw\b|right[- ]to[- ]left/.test(goal);
    const wantsFade = /\bfade\b|left[- ]to[- ]right/.test(goal);
    const wantsPush = /\bpush\b|start right|right start/.test(goal);
    const wantsPull = /\bpull\b|start left|left start/.test(goal);
    const wantsStraight = /\bstraight\b|neutral/.test(goal);

    if (path !== null && face !== null) {
      if (wantsDraw) {
        if (path > face) {
          parts.push(
            `Current face/path geometry can support draw curvature: path ${path.toFixed(1)}° is farther right than face ${face.toFixed(1)}°.`
          );
        } else {
          parts.push(
            `For the student's draw goal, the path needs to be farther right than the face. Current path ${path.toFixed(1)}° and face ${face.toFixed(1)}° do not yet create that relationship.`
          );
        }
        if (wantsPush && launch !== null) {
          parts.push(
            launch > 0
              ? `Launch direction ${launch.toFixed(1)}° right supports the requested push start.`
              : `Launch direction ${launch.toFixed(1)}° does not yet support the requested push start.`
          );
        }
      } else if (wantsFade) {
        if (path < face) {
          parts.push(
            `Current face/path geometry can support fade curvature: face ${face.toFixed(1)}° is open to path ${path.toFixed(1)}°.`
          );
        } else {
          parts.push(
            `For the student's fade goal, the face generally needs to remain open to the path. Current path ${path.toFixed(1)}° and face ${face.toFixed(1)}° do not yet create that relationship.`
          );
        }
      } else if (wantsStraight) {
        parts.push(
          `For a straighter pattern, face and path should remain closely matched. Current path is ${path.toFixed(1)}° and face is ${face.toFixed(1)}°.`
        );
      } else {
        parts.push(
          `Current delivery: club path ${path.toFixed(1)}°, club face ${face.toFixed(1)}°. Interpret the required change against the Student Primary Goal above.`
        );
      }

      if (wantsPull && launch !== null) {
        parts.push(
          launch < 0
            ? `Launch direction ${launch.toFixed(1)}° left is consistent with a left-start objective.`
            : `Launch direction ${launch.toFixed(1)}° is not currently producing the requested left-start pattern.`
        );
      }
    } else if (ftp !== null) {
      parts.push(`Current face-to-path relationship is ${ftp.toFixed(1)}°.`);
    }

    if (order) {
      const normalized = order.toLowerCase().replace(/[^a-z]+/g, " ");
      const pelvis = normalized.indexOf("pelvis");
      const torso = normalized.indexOf("torso");
      const arm = normalized.indexOf("arm");
      const club = normalized.indexOf("club");

      if (pelvis >= 0 && torso > pelvis && arm > torso && club > arm) {
        parts.push(
          "Verified peak order is proximal-to-distal: pelvis → torso → lead arm → club. Preserve useful sequencing while changing the delivery required by the student's goal."
        );
      } else {
        parts.push(
          "Verified peak order differs from the usual pelvis → torso → lead arm → club reference. Review transition timing before prescribing the movement change."
        );
      }
    }

    parts.push(
      "Use the sequence and P-position body data to explain the delivery; do not label a single body measurement good or bad in isolation."
    );

    output.textContent = parts.join(" ");
  }

  function savedScreenshot(slot) {
    const items = Array.isArray(savedImport?.screenshots) ? savedImport.screenshots : [];
    return items.find((item) => Number(item.slot) === Number(slot) && item.available);
  }

  async function resolveEvidenceFile(slot, input) {
    const selected = input?.files?.[0];
    if (selected) return selected;

    const saved = savedScreenshot(slot);
    if (!saved?.url) return null;

    const response = await fetch(saved.url, {
      method: "GET",
      credentials: "same-origin",
      cache: "no-store",
    });
    if (!response.ok) {
      throw new Error(`Unable to load saved screenshot ${slot} (${response.status}).`);
    }

    const blob = await response.blob();
    const filename =
      saved.original_filename ||
      saved.stored_filename ||
      `onform-screenshot-${slot}.png`;

    return new File([blob], filename, {
      type: blob.type || saved.content_type || "image/png",
    });
  }

  function hydrateSavedImport() {
    if (!savedImport) return;
    const metrics = savedImport.metrics || {};
    Object.entries(metrics).forEach(([key, value]) => {
      if (value === null || value === undefined || value === "") return;
      const input = root.querySelector(`[data-onform-metric="${key}"]`);
      if (input) input.value = value;
    });
    const sequence = savedImport.kinematic_sequence || {};
    Object.entries(sequence).forEach(([key, value]) => {
      if (value === null || value === undefined || value === "") return;
      const input = root.querySelector(`[data-onform-sequence="${key}"]`);
      if (input) input.value = value;
    });
    if (savedImport.shot_id && shotSelect) shotSelect.value = String(savedImport.shot_id);
    if (savedImport.checkpoint_position && checkpointSelect) {
      checkpointSelect.value = String(savedImport.checkpoint_position);
    }
    status.textContent = savedImport.verified
      ? "Saved verified Onform metrics and screenshot evidence loaded."
      : "Saved draft metrics and screenshot evidence loaded — awaiting Shot Table verification.";
    updateCoachingGoalRead();
  }

  function bindPreview(input, preview) {
    input.addEventListener("change", () => {
      const file = input.files?.[0];
      if (!file) {
        const slot = Number(input.id.split("-").pop());
        const saved = savedScreenshot(slot);
        if (saved) {
          preview.src = saved.url;
          preview.hidden = false;
        }
        return;
      }
      preview.src = URL.createObjectURL(file);
      preview.hidden = false;
      verified.checked = false;
      status.textContent = "Screenshots ready. Extract and combine metrics, then verify every visible value.";
    });
  }

  bindPreview(file1, preview1);
  bindPreview(file2, preview2);
  if (file3 && preview3) bindPreview(file3, preview3);

  // Restore the most recently saved draft/verified metrics when the coach
  // returns to the Onform Import page.
  hydrateSavedImport();

  if (typeof root.addEventListener === "function") {
    root.addEventListener("input", (event) => {
      if (event.target.matches("[data-onform-metric], [data-onform-sequence]")) updateCoachingGoalRead();
    });
  }

  function buildImportForm(verifiedValue) {
    const first = file1.files?.[0];
    const second = file2.files?.[0];
    const third = file3?.files?.[0];

    const form = new FormData();
    if (first) form.append("screenshot_1", first);
    if (second) form.append("screenshot_2", second);
    if (third) form.append("screenshot_3", third);

    form.append("metrics_json", JSON.stringify(collectMetrics()));
    form.append("sequence_json", JSON.stringify(collectSequence()));
    form.append("shot_id", shotSelect.value || "");
    form.append("checkpoint_position", checkpointSelect.value || "P7");
    form.append("verified", verifiedValue ? "true" : "false");
    form.append("ocr_text_1", ocrText1);
    form.append("ocr_text_2", ocrText2);
    form.append("ocr_text_3", ocrText3);
    form.append("conflicts_json", JSON.stringify(conflicts));
    return form;
  }

  function applySavedImport(payload) {
    if (!payload?.saved_import) return;
    savedImport = payload.saved_import;

    // File inputs cannot retain files across reloads. Once server evidence is
    // confirmed, clear the local selections so subsequent saves reuse the
    // persisted copies rather than uploading duplicates.
    [file1, file2, file3].forEach((input) => {
      if (input) input.value = "";
    });

    [1, 2, 3].forEach((slot) => {
      const saved = savedScreenshot(slot);
      const preview = slot === 1 ? preview1 : slot === 2 ? preview2 : preview3;
      if (saved?.url && preview) {
        preview.src = saved.url;
        preview.hidden = false;
      }
    });
  }

  async function saveEvidenceDraft() {
    const form = buildImportForm(false);
    const response = await fetch(
      `/swing-analysis/${analysisId}/workspace/onform-screenshot`,
      {
        method: "POST",
        body: form,
        credentials: "same-origin",
      }
    );
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Unable to auto-save screenshot evidence");
    }
    applySavedImport(payload);
    return payload;
  }

  extractButton.addEventListener("click", async () => {
    const hasFirst = Boolean(file1.files?.[0] || savedScreenshot(1));
    const hasSecond = Boolean(file2.files?.[0] || savedScreenshot(2));
    if (!hasFirst || !hasSecond) {
      status.textContent = "Choose screenshots 1 and 2 at least once before extraction.";
      return;
    }
    if (!window.Tesseract) {
      status.textContent = "OCR library did not load. You can still enter the values manually and save the screenshots as evidence.";
      return;
    }

    extractButton.disabled = true;
    verified.checked = false;
    showConflicts([]);
    try {
      status.textContent = "Loading Onform screenshot evidence…";

      const first = await resolveEvidenceFile(1, file1);
      const second = await resolveEvidenceFile(2, file2);
      const third = await resolveEvidenceFile(3, file3);

      if (!first || !second) {
        status.textContent = "Screenshots 1 and 2 are required for extraction.";
        return;
      }

      const one = await readScreenshot(first, 1);
      const two = await readScreenshot(second, 2);
      ocrText1 = one.text;
      ocrText2 = two.text;
      ocrText3 = third ? await readSequenceScreenshot(third) : "";

      const combined = mergeMetrics(one.metrics, two.metrics);
      fillMetrics(combined.merged);
      showConflicts(combined.disagreement);

      const count = Object.keys(combined.merged).filter((k) => !k.endsWith("_direction")).length;
      const conflictText = combined.disagreement.length
        ? ` ${combined.disagreement.length} disagreement(s) need coach review.`
        : "";
      const spatialLabels =
        (one.spatial?.labelsFound || 0) +
        (two.spatial?.labelsFound || 0);

      updateCoachingGoalRead();

      const evidenceText =
        file1.files?.[0] || file2.files?.[0] || file3?.files?.[0]
          ? "Selected files and saved evidence were used."
          : "Saved evidence was re-used; no file re-selection was required.";

      status.textContent = "Metrics extracted. Saving screenshots as evidence…";
      const evidencePayload = await saveEvidenceDraft();
      const savedCount = Array.isArray(evidencePayload?.saved_import?.screenshots)
        ? evidencePayload.saved_import.screenshots.filter((item) => item.available).length
        : 0;

      status.textContent =
        `${savedCount} screenshot${savedCount === 1 ? "" : "s"} saved as evidence. ` +
        `Spatially matched and combined ${count} metric(s) from 2 screenshots ` +
        `(${spatialLabels} metric labels detected).${conflictText} ` +
        `Metrics extracted — awaiting coach verification.`;
    } catch (error) {
      console.error(error);
      status.textContent =
        "Automatic extraction failed while reading the selected or saved evidence. " +
        "The saved screenshots remain available for coach review.";
    } finally {
      extractButton.disabled = false;
    }
  });

  async function commitVerifiedImport() {
    const first = file1.files?.[0];
    const second = file2.files?.[0];
    const hasFirst = Boolean(first || savedScreenshot(1));
    const hasSecond = Boolean(second || savedScreenshot(2));

    if (!hasFirst || !hasSecond) {
      status.textContent = "Screenshots 1 and 2 must be saved before Shot Table commit.";
      return;
    }

    verified.checked = true;
    const form = buildImportForm(true);

    if (saveButton) saveButton.disabled = true;
    status.textContent = "Verifying metrics and saving to Shot Table…";

    try {
      const response = await fetch(
        `/swing-analysis/${analysisId}/workspace/onform-screenshot`,
        {
          method: "POST",
          body: form,
          credentials: "same-origin",
        }
      );
      const payload = await response.json();

      if (!response.ok) {
        throw new Error(
          payload.detail || `Shot Table save failed (${response.status}).`
        );
      }

      applySavedImport(payload);

      if (!payload.shot_committed) {
        throw new Error(
          "Verified import was saved, but no Shot Table record was selected."
        );
      }

      status.textContent = "Verified metrics saved to Shot Table. Reloading…";
      window.setTimeout(() => window.location.reload(), 900);
    } catch (error) {
      console.error(error);
      status.textContent =
        error.message || "Unable to save verified metrics to Shot Table.";
      if (saveButton) saveButton.disabled = false;
    }
  }

  if (saveButton) {
    saveButton.addEventListener("click", function (event) {
      event.preventDefault();
      event.stopPropagation();
      commitVerifiedImport();
    });
  }

  const workspaceSaveButton = document.getElementById("save-analysis");
  if (workspaceSaveButton) {
    workspaceSaveButton.addEventListener(
      "click",
      function (event) {
        event.preventDefault();
        event.stopImmediatePropagation();
        commitVerifiedImport();
      },
      true
    );
  }


  window.OnformScreenshotParser = { parseRibbonText, parseSpatialWords, detectSpatialLabels, mergeMetrics };
})();
