(() => {
    "use strict";

    const page = document.querySelector(".swing-analysis-page");
    const video = document.getElementById("original-swing-video");
    const detectButton = document.getElementById("p-detect-run");
    if (!page || !video || !detectButton) return;

    const fpsSelect = document.getElementById("p-detection-fps");
    const rateSelect = document.getElementById("p-playback-rate");
    const status = document.getElementById("p-detect-status");
    const list = document.getElementById("p-detection-list");
    const frameStatus = document.getElementById("p-frame-status");
    const analysisId = page.dataset.analysisId;
    const ANALYSIS_VERSION = "pose-timing-candidates-v1";
    let visionTask = null;
    let candidates = [];

    const POSITIONS = [
        ["P1", "Address / motion start"],
        ["P2", "Early backswing"],
        ["P3", "Lead-arm backswing checkpoint"],
        ["P4", "Top / direction change"],
        ["P5", "Early downswing"],
        ["P6", "Delivery checkpoint"],
        ["P7", "Impact"],
        ["P8", "Early follow-through"],
        ["P9", "Follow-through checkpoint"],
        ["P10", "Balanced finish"],
    ];

    function setStatus(message, error = false) {
        status.textContent = message;
        status.dataset.error = error ? "1" : "0";
    }

    function fps() {
        const value = Number(fpsSelect?.value || 120);
        return Number.isFinite(value) && value > 0 ? value : 120;
    }

    function updateFrameStatus() {
        if (!frameStatus || !Number.isFinite(video.currentTime)) return;
        const frame = Math.max(0, Math.round(video.currentTime * fps()));
        frameStatus.textContent = `Frame ${frame} · ${video.currentTime.toFixed(3)}s`;
    }

    function nudgeFrame(direction) {
        video.pause();
        const next = Math.max(0, Math.min(video.duration || Infinity, video.currentTime + direction / fps()));
        video.currentTime = next;
        updateFrameStatus();
    }

    document.getElementById("p-frame-back")?.addEventListener("click", () => nudgeFrame(-1));
    document.getElementById("p-frame-forward")?.addEventListener("click", () => nudgeFrame(1));
    fpsSelect?.addEventListener("change", updateFrameStatus);
    rateSelect?.addEventListener("change", () => {
        video.playbackRate = Number(rateSelect.value || 1);
    });
    video.addEventListener("timeupdate", updateFrameStatus);
    video.addEventListener("seeked", updateFrameStatus);
    video.addEventListener("loadedmetadata", () => {
        const end = document.getElementById("p-detect-end");
        if (end && !end.value) end.value = video.duration.toFixed(3);
        updateFrameStatus();
    });

    async function loadVision() {
        if (visionTask) return visionTask;
        visionTask = (async () => {
            const { FilesetResolver, PoseLandmarker } = await import(
                "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.22/vision_bundle.mjs"
            );
            const wasm = await FilesetResolver.forVisionTasks(
                "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.22/wasm"
            );
            const model = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task";
            try {
                return await PoseLandmarker.createFromOptions(wasm, {
                    baseOptions: { modelAssetPath: model, delegate: "GPU" },
                    runningMode: "VIDEO",
                    numPoses: 1,
                    minPoseDetectionConfidence: 0.35,
                    minPosePresenceConfidence: 0.35,
                    minTrackingConfidence: 0.35,
                });
            } catch (_) {
                return await PoseLandmarker.createFromOptions(wasm, {
                    baseOptions: { modelAssetPath: model, delegate: "CPU" },
                    runningMode: "VIDEO",
                    numPoses: 1,
                    minPoseDetectionConfidence: 0.35,
                    minPosePresenceConfidence: 0.35,
                    minTrackingConfidence: 0.35,
                });
            }
        })();
        try {
            return await visionTask;
        } catch (error) {
            visionTask = null;
            throw error;
        }
    }

    function waitForSeek(target) {
        if (Math.abs(video.currentTime - target) < 0.0005 && !video.seeking) return Promise.resolve();
        return new Promise((resolve, reject) => {
            const timer = setTimeout(() => {
                video.removeEventListener("seeked", onSeeked);
                reject(new Error("Video seek timed out. Try a shorter clip or reload the video."));
            }, 5000);
            function onSeeked() {
                clearTimeout(timer);
                resolve();
            }
            video.addEventListener("seeked", onSeeked, { once: true });
            video.currentTime = target;
        });
    }

    function midpoint(a, b) {
        return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
    }

    function frameMetrics(result) {
        const pose = result?.landmarks?.[0];
        if (!pose || pose.length < 29) return null;
        const visible = indices => indices.every(index => Number(pose[index]?.visibility ?? 0) >= 0.25);
        if (!visible([11, 12, 15, 16, 23, 24])) return null;
        const shoulder = midpoint(pose[11], pose[12]);
        const hip = midpoint(pose[23], pose[24]);
        const hands = midpoint(pose[15], pose[16]);
        const torso = Math.hypot(shoulder.x - hip.x, shoulder.y - hip.y);
        if (!Number.isFinite(torso) || torso < 0.04) return null;
        const visibility = [11, 12, 15, 16, 23, 24].reduce((sum, i) => sum + Number(pose[i].visibility || 0), 0) / 6;
        return { hands, shoulder, hip, torso, visibility };
    }

    function addSpeeds(samples) {
        return samples.map((sample, index) => {
            if (!index) return { ...sample, speed: 0 };
            const prev = samples[index - 1];
            const dt = sample.time - prev.time;
            if (dt <= 0) return { ...sample, speed: 0 };
            const pixels = Math.hypot(sample.hands.x - prev.hands.x, sample.hands.y - prev.hands.y);
            const scale = (sample.torso + prev.torso) / 2;
            return { ...sample, speed: pixels / Math.max(scale, 0.04) / dt };
        });
    }

    function nearestProgressSample(samples, startIndex, endIndex, fraction) {
        if (endIndex <= startIndex) return samples[Math.max(0, Math.min(samples.length - 1, startIndex))];
        const path = [0];
        for (let i = startIndex + 1; i <= endIndex; i++) {
            const a = samples[i - 1].hands;
            const b = samples[i].hands;
            path.push(path[path.length - 1] + Math.hypot(b.x - a.x, b.y - a.y));
        }
        const target = path[path.length - 1] * fraction;
        let best = 0;
        for (let i = 1; i < path.length; i++) {
            if (Math.abs(path[i] - target) < Math.abs(path[best] - target)) best = i;
        }
        return samples[startIndex + best];
    }

    function makeCandidates(samples, sampleRate) {
        if (samples.length < 8) throw new Error("The pose model could not track enough frames. Keep the full golfer visible and try another camera angle.");
        const firstTime = samples[0].time;
        const baseline = samples.slice(0, Math.min(6, samples.length));
        const baseHands = baseline.reduce((sum, s) => sum + s.hands.y, 0) / baseline.length;
        const movingIndex = samples.findIndex((s, i) => i > 1 && s.speed > 0.34 && Math.abs(s.hands.y - baseHands) > 0.025);
        const addressIndex = movingIndex > 0 ? Math.max(0, movingIndex - 1) : 0;
        const startIndex = Math.max(addressIndex + 1, movingIndex);
        if (startIndex >= samples.length - 3) throw new Error("No clear swing motion was found in this range. Trim to include the backswing through finish.");

        let topIndex = startIndex;
        for (let i = startIndex + 1; i < samples.length; i++) {
            if (samples[i].hands.y < samples[topIndex].hands.y) topIndex = i;
        }
        if (topIndex <= startIndex + 1 || topIndex >= samples.length - 2) {
            throw new Error("Could not find a clear backswing top. Try a clip that includes address and the complete swing.");
        }

        let impactIndex = topIndex + 1;
        for (let i = topIndex + 1; i < samples.length; i++) {
            if (samples[i].speed > samples[impactIndex].speed) impactIndex = i;
        }
        impactIndex = Math.max(topIndex + 1, Math.min(impactIndex, samples.length - 3));

        let finishIndex = samples.length - 1;
        const finishSearchStart = Math.min(samples.length - 2, impactIndex + Math.max(2, Math.round(sampleRate * 0.12)));
        for (let i = finishSearchStart; i < samples.length - 2; i++) {
            if (samples[i].speed < 0.12 && samples[i + 1].speed < 0.12 && samples[i + 2].speed < 0.12) {
                finishIndex = i + 1;
                break;
            }
        }
        if (finishIndex <= impactIndex) finishIndex = samples.length - 1;

        const points = [
            samples[addressIndex],
            nearestProgressSample(samples, addressIndex, topIndex, 0.2),
            nearestProgressSample(samples, addressIndex, topIndex, 0.62),
            samples[topIndex],
            nearestProgressSample(samples, topIndex, impactIndex, 0.22),
            nearestProgressSample(samples, topIndex, impactIndex, 0.68),
            samples[impactIndex],
            nearestProgressSample(samples, impactIndex, finishIndex, 0.28),
            nearestProgressSample(samples, impactIndex, finishIndex, 0.68),
            samples[finishIndex],
        ];
        const reasons = [
            "Stable address / first-motion cue",
            "Early-backswing timing cue; verify club shaft",
            "Lead-arm checkpoint cue; verify club and arm position",
            "Top-of-backswing / direction-change cue",
            "Early-downswing timing cue; verify shaft shallowing",
            "Delivery timing cue; verify P6 club position",
            "Peak wrist-speed proxy only; locate exact ball contact manually",
            "Early follow-through timing cue",
            "Follow-through timing cue; verify shaft position",
            "Finish-stability cue",
        ];
        const quality = samples.reduce((sum, s) => sum + s.visibility, 0) / samples.length;
        return POSITIONS.map(([position, label], index) => ({
            position,
            label,
            time: points[index].time,
            frame: Math.round(points[index].time * fps()),
            quality,
            reason: reasons[index],
            sampleRate,
            confidenceLabel: index === 6 ? "Impact proxy · verify contact frame" : "Timing candidate · coach review required",
        }));
    }

    function formatCandidate(candidate) {
        const number = Math.max(0, Math.round(candidate.time * fps()));
        return `Frame ${number} · ${candidate.time.toFixed(3)} sec`;
    }

    function updateCheckpointStrip(candidate, data) {
        const button = document.querySelector(`.p-position-button[data-position="${candidate.position}"]`);
        if (button) {
            const label = button.querySelector("span");
            if (label) label.textContent = data.time_seconds !== null && data.time_seconds !== undefined
                ? `${Number(data.time_seconds).toFixed(3)}s`
                : "Set";
            button.classList.add("is-coach-confirmed");
            button.title = "Pose-assisted candidate confirmed by coach";
        }
    }

    async function confirmCandidate(candidate, button) {
        button.disabled = true;
        const node = document.getElementById("analysis-data");
        let analysis = {};
        try { analysis = JSON.parse(node?.textContent || "{}"); } catch (_) {}
        const oldCheckpoint = (analysis.checkpoints || []).find(cp => cp.position === candidate.position) || {};
        let extra = {};
        try {
            const parsed = JSON.parse(oldCheckpoint.extra_metrics_json || "{}");
            if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) extra = parsed;
        } catch (_) {}
        extra.pose_assisted_candidate = {
            version: ANALYSIS_VERSION,
            suggested_time_seconds: Number(candidate.time.toFixed(4)),
            sample_rate_fps: candidate.sampleRate,
            pose_visibility: Number(candidate.quality.toFixed(3)),
            coach_confirmed: true,
            review_note: candidate.reason,
            confirmed_at: new Date().toISOString(),
        };
        try {
            const response = await fetch(
                `/swing-analysis/${encodeURIComponent(analysisId)}/workspace/checkpoint/${encodeURIComponent(candidate.position)}`,
                {
                    method: "PATCH",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        time_seconds: Number(candidate.time.toFixed(4)),
                        frame_number: candidate.frame,
                        measurement_source: "Pose-assisted · coach confirmed",
                        extra_metrics_json: JSON.stringify(extra),
                    }),
                }
            );
            const saved = await response.json();
            if (!response.ok) throw new Error(saved.detail || "Checkpoint could not be saved.");
            candidate.confirmed = true;
            updateCheckpointStrip(candidate, saved);
            button.textContent = "Confirmed";
            button.classList.add("confirm");
            const card = button.closest(".p-candidate");
            card?.classList.add("is-confirmed");
            setStatus(`${candidate.position} saved at ${Number(saved.time_seconds).toFixed(3)} sec. Review and confirm the remaining candidates.`);
        } catch (error) {
            button.disabled = false;
            setStatus(error.message, true);
        }
    }

    function renderCandidates() {
        list.replaceChildren();
        candidates.forEach(candidate => {
            const card = document.createElement("article");
            card.className = `p-candidate${candidate.confirmed ? " is-confirmed" : ""}`;
            const heading = document.createElement("strong");
            heading.textContent = `${candidate.position} · ${candidate.label}`;
            const detail = document.createElement("small");
            detail.textContent = `${formatCandidate(candidate)} · Pose tracking visibility ${Math.round(candidate.quality * 100)}%. ${candidate.reason}.`;
            const actions = document.createElement("div");
            actions.className = "p-candidate-actions";
            const preview = document.createElement("button");
            preview.type = "button";
            preview.textContent = "Preview frame";
            preview.addEventListener("click", () => {
                video.pause();
                video.currentTime = candidate.time;
                updateFrameStatus();
            });
            const confirm = document.createElement("button");
            confirm.type = "button";
            confirm.className = "confirm";
            confirm.textContent = candidate.confirmed ? "Confirmed" : `Confirm ${candidate.position}`;
            confirm.disabled = Boolean(candidate.confirmed);
            confirm.addEventListener("click", () => confirmCandidate(candidate, confirm));
            actions.append(preview, confirm);
            card.append(heading, detail, actions);
            list.append(card);
        });
    }

    async function runDetection() {
        detectButton.disabled = true;
        const clearButton = document.getElementById("p-detect-clear");
        if (clearButton) clearButton.disabled = true;
        video.pause();
        const originalTime = video.currentTime;
        try {
            if (!Number.isFinite(video.duration) || video.readyState < 2) {
                throw new Error("Wait for the swing video to finish loading, then try again.");
            }
            const startInput = document.getElementById("p-detect-start");
            const endInput = document.getElementById("p-detect-end");
            const start = Math.max(0, Number(startInput?.value || 0));
            const end = Math.min(video.duration, Number(endInput?.value || video.duration));
            if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) {
                throw new Error("Choose a valid start and end time that includes one complete swing.");
            }
            const sampleRate = Math.min(fps(), 24);
            const interval = 1 / sampleRate;
            const frameCount = Math.floor((end - start) / interval) + 1;
            if (frameCount < 8) throw new Error("The selected clip is too short. Include at least a third of a second.");
            if (frameCount > 720) throw new Error("Trim the video to one swing (30 seconds or less) before analysis.");
            setStatus("Loading the on-device pose model…");
            const detector = await loadVision();
            const samples = [];
            for (let index = 0; index < frameCount; index++) {
                const time = Math.min(end, start + index * interval);
                await waitForSeek(time);
                const result = detector.detectForVideo(video, Math.max(1, Math.round(time * 1000)));
                const metrics = frameMetrics(result);
                if (metrics) samples.push({ time, ...metrics });
                if (index % 8 === 0 || index === frameCount - 1) {
                    setStatus(`Analyzing pose frames: ${index + 1} / ${frameCount}. Keep this page open.`);
                    await new Promise(resolve => requestAnimationFrame(() => resolve()));
                }
            }
            const tracked = addSpeeds(samples);
            candidates = makeCandidates(tracked, sampleRate);
            const oldData = JSON.parse(document.getElementById("analysis-data")?.textContent || "{}");
            const saved = new Map((oldData.checkpoints || []).map(cp => [cp.position, cp]));
            candidates.forEach(candidate => {
                const cp = saved.get(candidate.position);
                candidate.confirmed = Boolean(cp?.measurement_source?.includes("coach confirmed") || cp?.measurement_source?.includes("coach-confirmed"));
            });
            renderCandidates();
            const meanVisibility = tracked.reduce((sum, item) => sum + item.visibility, 0) / tracked.length;
            setStatus(`Found pose movement across ${tracked.length} frames (visibility ${Math.round(meanVisibility * 100)}%). Review each candidate. No timestamp was saved until you confirm it.`);
        } catch (error) {
            setStatus(error.message || "P-position detection failed. Try a shorter clip with the golfer fully visible.", true);
        } finally {
            try { await waitForSeek(Math.max(0, Math.min(video.duration || 0, originalTime))); } catch (_) {}
            detectButton.disabled = false;
            if (clearButton) clearButton.disabled = false;
            updateFrameStatus();
        }
    }

    detectButton.addEventListener("click", runDetection);
    document.getElementById("p-detect-clear")?.addEventListener("click", () => {
        candidates = [];
        list.replaceChildren();
        setStatus("Candidates cleared. The saved, coach-confirmed checkpoints remain in the lesson.");
    });
    updateFrameStatus();
})();
