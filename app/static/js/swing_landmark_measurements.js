(function (root, factory) {
    const api = factory();
    if (typeof module === "object" && module.exports) module.exports = api;
    if (root) root.SwingLandmarkMeasurements = api;
})(typeof window !== "undefined" ? window : globalThis, function () {
    "use strict";

    const ORDER = ["left_shoulder", "right_shoulder", "left_hip", "right_hip"];
    const LABELS = {
        left_shoulder: "player's left shoulder joint",
        right_shoulder: "player's right shoulder joint",
        left_hip: "player's left hip joint",
        right_hip: "player's right hip joint",
    };

    function degrees(radians) { return radians * 180 / Math.PI; }
    function round1(value) { const rounded = Math.round(value * 10) / 10; return Object.is(rounded, -0) ? 0 : rounded; }
    function midpoint(a, b) { return {x: (a.x + b.x) / 2, y: (a.y + b.y) / 2}; }

    function lineTilt(a, b) {
        return round1(degrees(Math.atan2(-(b.y - a.y), b.x - a.x)));
    }

    function spineTilt(leftShoulder, rightShoulder, leftHip, rightHip) {
        const shoulder = midpoint(leftShoulder, rightShoulder);
        const hip = midpoint(leftHip, rightHip);
        const dx = shoulder.x - hip.x;
        const dyUp = hip.y - shoulder.y;
        return round1(degrees(Math.atan2(dx, dyUp)));
    }

    function calculate2D(points) {
        for (const key of ORDER) {
            if (!points || !points[key] || !Number.isFinite(points[key].x) || !Number.isFinite(points[key].y)) {
                return null;
            }
        }
        return {
            shoulder_tilt: lineTilt(points.left_shoulder, points.right_shoulder),
            hip_tilt: lineTilt(points.left_hip, points.right_hip),
            spine_tilt: spineTilt(points.left_shoulder, points.right_shoulder, points.left_hip, points.right_hip),
        };
    }

    function parseObject(value) {
        if (!value) return {};
        if (typeof value === "object") return value;
        try {
            const parsed = JSON.parse(value);
            return parsed && typeof parsed === "object" ? parsed : {};
        } catch (_) { return {}; }
    }

    function latestOnformMetrics(analysis, checkpointPosition) {
        const extra = parseObject(analysis && analysis.extra_metrics_json);
        const imports = Array.isArray(extra.onform_screenshot_imports) ? extra.onform_screenshot_imports : [];
        for (let i = imports.length - 1; i >= 0; i -= 1) {
            const item = imports[i] || {};
            if ((item.checkpoint_position || "").toUpperCase() === (checkpointPosition || "").toUpperCase()) {
                return item.metrics && typeof item.metrics === "object" ? item.metrics : {};
            }
        }
        return {};
    }

    return {ORDER, LABELS, lineTilt, spineTilt, calculate2D, parseObject, latestOnformMetrics};
});

if (typeof document !== "undefined") {
    document.addEventListener("DOMContentLoaded", () => {
        "use strict";
        const api = window.SwingLandmarkMeasurements;
        const page = document.querySelector(".swing-analysis-page");
        const video = document.getElementById("original-swing-video");
        const canvas = document.getElementById("p-position-landmark-canvas");
        const start = document.getElementById("landmark-start");
        const clear = document.getElementById("landmark-clear");
        const status = document.getElementById("landmark-status");
        const dataNode = document.getElementById("analysis-data");
        if (!api || !page || !video || !canvas || !dataNode) return;

        let analysis = {};
        try { analysis = JSON.parse(dataNode.textContent || "{}"); } catch (_) { analysis = {}; }
        let measuring = false;
        let points = {};
        let nextIndex = 0;

        function activePosition() {
            return document.querySelector(".p-position-button.active")?.dataset.position || "P1";
        }

        function checkpoint() {
            return (analysis.checkpoints || []).find(cp => cp.position === activePosition()) || {};
        }

        function loadStored() {
            const extra = api.parseObject(checkpoint().extra_metrics_json);
            const saved = extra.golf_coach_2d || {};
            points = saved.landmarks && typeof saved.landmarks === "object" ? saved.landmarks : {};
            nextIndex = Math.min(api.ORDER.length, Object.keys(points).filter(k => api.ORDER.includes(k)).length);
            render();
        }

        function canvasGeometry() {
            const rect = canvas.getBoundingClientRect();
            const dpr = window.devicePixelRatio || 1;
            const width = Math.max(1, Math.round(rect.width * dpr));
            const height = Math.max(1, Math.round(rect.height * dpr));
            if (canvas.width !== width || canvas.height !== height) { canvas.width = width; canvas.height = height; }
            const contain = window.VideoCoordinates?.containRect(
                {left: 0, top: 0, width: rect.width, height: rect.height},
                video.videoWidth || 1,
                video.videoHeight || 1
            ) || {left: 0, top: 0, width: rect.width, height: rect.height};
            return {rect, dpr, contain};
        }

        function render() {
            const {dpr, contain} = canvasGeometry();
            const ctx = canvas.getContext("2d");
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.save();
            ctx.scale(dpr, dpr);
            ctx.lineWidth = 2.5;
            ctx.strokeStyle = "white";
            ctx.fillStyle = "white";
            ctx.font = "12px sans-serif";
            const coords = {};
            for (const key of api.ORDER) {
                const p = points[key];
                if (!p) continue;
                const x = contain.left + p.x * contain.width;
                const y = contain.top + p.y * contain.height;
                coords[key] = {x, y};
                ctx.beginPath(); ctx.arc(x, y, 6, 0, Math.PI * 2); ctx.fill();
                ctx.fillText(api.LABELS[key].replace("player's ", ""), x + 9, y - 8);
            }
            function line(a, b) {
                if (!coords[a] || !coords[b]) return;
                ctx.beginPath(); ctx.moveTo(coords[a].x, coords[a].y); ctx.lineTo(coords[b].x, coords[b].y); ctx.stroke();
            }
            line("left_shoulder", "right_shoulder"); line("left_hip", "right_hip");
            if (coords.left_shoulder && coords.right_shoulder && coords.left_hip && coords.right_hip) {
                const sm = {x:(coords.left_shoulder.x+coords.right_shoulder.x)/2, y:(coords.left_shoulder.y+coords.right_shoulder.y)/2};
                const hm = {x:(coords.left_hip.x+coords.right_hip.x)/2, y:(coords.left_hip.y+coords.right_hip.y)/2};
                ctx.beginPath(); ctx.moveTo(hm.x, hm.y); ctx.lineTo(sm.x, sm.y); ctx.stroke();
            }
            ctx.restore();
            updateResults();
        }

        function fmt(value) { return Number.isFinite(Number(value)) ? `${Number(value).toFixed(1)}°` : "—"; }
        function updateResults() {
            const calc = api.calculate2D(points);
            document.getElementById("gc-landmark-count").textContent = `${Object.keys(points).filter(k=>api.ORDER.includes(k)).length} / 4`;
            document.getElementById("gc-shoulder-tilt").textContent = fmt(calc?.shoulder_tilt);
            document.getElementById("gc-hip-tilt").textContent = fmt(calc?.hip_tilt);
            document.getElementById("gc-spine-tilt").textContent = fmt(calc?.spine_tilt);
            const onform = api.latestOnformMetrics(analysis, activePosition());
            const values = calc || {};
            document.querySelectorAll("[data-compare]").forEach(row => {
                const key = row.dataset.compare;
                const gc = values[key];
                const of = onform[key];
                const gcCell = row.querySelector("[data-gc]");
                const ofCell = row.querySelector("[data-onform]");
                const deltaCell = row.querySelector("[data-delta]");
                if (["shoulder_tilt","hip_tilt","spine_tilt"].includes(key)) gcCell.textContent = fmt(gc);
                ofCell.textContent = fmt(of);
                deltaCell.textContent = Number.isFinite(Number(gc)) && Number.isFinite(Number(of)) ? fmt(Number(gc)-Number(of)) : "—";
            });
        }

        async function persist() {
            const calc = api.calculate2D(points);
            if (!calc) return;
            const cp = checkpoint();
            const extra = api.parseObject(cp.extra_metrics_json);
            extra.golf_coach_2d = {
                version: "5.2.5C",
                source: "coach_marked_2d_landmarks",
                landmarks: points,
                calculated: calc,
                video_time_seconds: Number.isFinite(video.currentTime) ? Number(video.currentTime.toFixed(3)) : null,
            };
            const response = await fetch(`/swing-analysis/${encodeURIComponent(page.dataset.analysisId)}/workspace/checkpoint/${encodeURIComponent(activePosition())}`, {
                method: "PATCH",
                headers: {"Content-Type":"application/json"},
                body: JSON.stringify({extra_metrics_json: JSON.stringify(extra)}),
            });
            const saved = await response.json();
            if (!response.ok) throw new Error(saved.detail || "Landmark measurements could not be saved.");
            const index = (analysis.checkpoints || []).findIndex(item => item.position === activePosition());
            if (index >= 0) analysis.checkpoints[index] = {...analysis.checkpoints[index], ...saved};
            status.textContent = `${activePosition()} Golf Coach 2D landmarks saved for Onform validation.`;
        }

        start.addEventListener("click", event => {
            event.preventDefault();
            video.pause();
            measuring = true; points = {}; nextIndex = 0; canvas.classList.add("is-measuring");
            status.textContent = `Video paused. Click ${api.LABELS[api.ORDER[0]]}.`;
            render();
        });
        clear.addEventListener("click", () => {
            measuring = false; points = {}; nextIndex = 0; canvas.classList.remove("is-measuring");
            status.textContent = "Landmarks cleared locally. Start a new 4-point measurement when ready."; render();
        });
        canvas.addEventListener("pointerdown", event => {
            if (!measuring) return;
            event.preventDefault();
            event.stopPropagation();
        });
        canvas.addEventListener("click", async event => {
            if (!measuring || nextIndex >= api.ORDER.length) return;
            event.preventDefault();
            event.stopPropagation();
            video.pause();
            const mapped = window.VideoCoordinates?.clientToMediaPoint(
                event.clientX, event.clientY, canvas.getBoundingClientRect(), video.videoWidth || 1, video.videoHeight || 1
            );
            if (!mapped) { status.textContent = "Click inside the visible video image—not the black side bars."; return; }
            const key = api.ORDER[nextIndex]; points[key] = {x:mapped[0], y:mapped[1]}; nextIndex += 1; render();
            if (nextIndex < api.ORDER.length) status.textContent = `Click ${api.LABELS[api.ORDER[nextIndex]]}.`;
            else {
                measuring = false; canvas.classList.remove("is-measuring");
                status.textContent = "4 landmarks measured. Saving Golf Coach 2D calculations…";
                try { await persist(); } catch (error) { status.textContent = error.message; }
            }
        });

        document.querySelectorAll(".p-position-button").forEach(button => button.addEventListener("click", () => setTimeout(loadStored, 0)));
        video.addEventListener("loadedmetadata", render);
        window.addEventListener("resize", render);
        loadStored();
    });
}
