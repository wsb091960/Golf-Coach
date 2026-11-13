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
    let frameTimes = null;
    let frameMapPromise = null;

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

    function sampleRate() {
        const value = Number(fpsSelect?.value || 24);
        return Number.isFinite(value) && value > 0 ? value : 24;
    }

    function nearestFrameIndex(time) {
        if (!frameTimes?.length) return -1;
        let low = 0, high = frameTimes.length - 1;
        while (low < high) {
            const middle = Math.floor((low + high) / 2);
            if (frameTimes[middle] < time) low = middle + 1;
            else high = middle;
        }
        if (low > 0 && Math.abs(frameTimes[low - 1] - time) <= Math.abs(frameTimes[low] - time)) return low - 1;
        return low;
    }

    function updateFrameStatus() {
        if (!frameStatus || !Number.isFinite(video.currentTime)) return;
        const frame = nearestFrameIndex(video.currentTime);
        frameStatus.textContent = frame >= 0
            ? `Frame index ${frame} / ${frameTimes.length - 1} · ${video.currentTime.toFixed(3)}s`
            : `Time ${video.currentTime.toFixed(3)}s · frame map loads on first step`;
    }

    async function loadMp4Box() {
        if (window.MP4Box?.createFile) return window.MP4Box;
        await new Promise((resolve, reject) => {
            const existing = document.querySelector('script[data-mp4box="1"]');
            if (existing) {
                existing.addEventListener("load", resolve, { once: true });
                existing.addEventListener("error", () => reject(new Error("Could not load the MP4 frame reader.")), { once: true });
                return;
            }
            const script = document.createElement("script");
            script.src = "https://cdn.jsdelivr.net/npm/mp4box@0.5.4/dist/mp4box.all.min.js";
            script.dataset.mp4box = "1";
            script.onload = resolve;
            script.onerror = () => reject(new Error("Could not load the MP4 frame reader. Check the connection and retry."));
            document.head.append(script);
        });
        if (!window.MP4Box?.createFile) throw new Error("The MP4 frame reader did not initialize.");
        return window.MP4Box;
    }

    async function loadFrameTimestamps() {
        if (frameTimes?.length) return frameTimes;
        if (frameMapPromise) return frameMapPromise;
        frameMapPromise = (async () => {
            setStatus("Reading exact frame timestamps from the video file…");
            const MP4Box = await loadMp4Box();
            const response = await fetch(video.currentSrc, { credentials: "same-origin" });
            if (!response.ok) throw new Error(`Video frame map request failed (${response.status}).`);
            const data = await response.arrayBuffer();
            data.fileStart = 0;
            const parsed = await new Promise((resolve, reject) => {
                const mp4 = MP4Box.createFile();
                const timestamps = [];
                let expected = 0;
                let settled = false;
                const timeout = setTimeout(() => {
                    if (!settled) { settled = true; reject(new Error("Timed out reading video frame timestamps.")); }
                }, 30000);
                const fail = error => {
                    if (settled) return;
                    settled = true;
                    clearTimeout(timeout);
                    reject(new Error(String(error || "Could not read the MP4 frame table.")));
                };
                mp4.onError = fail;
                mp4.onReady = info => {
                    const track = (info.tracks || []).find(item => item.type === "video");
                    expected = Number(track?.nb_samples || 0);
                    if (!track || expected < 2) { fail("This MP4 does not expose a usable video frame table."); return; }
                    mp4.onSamples = (_trackId, _user, samples) => {
                        for (const sample of samples) {
                            const scale = Number(sample.timescale);
                            if (scale > 0) timestamps.push(Number(sample.cts) / scale);
                        }
                        if (!settled && timestamps.length >= expected) {
                            settled = true;
                            clearTimeout(timeout);
                            resolve(timestamps.sort((a, b) => a - b));
                        }
                    };
                    mp4.setExtractionOptions(track.id, null, { nbSamples: 512 });
                    mp4.start();
                };
                try {
                    mp4.appendBuffer(data);
                    mp4.flush();
                } catch (error) { fail(error.message); }
            });
            const base = parsed[0] || 0;
            frameTimes = parsed.map(time => Math.max(0, time - base));
            if (frameTimes.length < 2) throw new Error("The video frame table is empty.");
            updateFrameStatus();
            return frameTimes;
        })();
        try {
            return await frameMapPromise;
        } catch (error) {
            frameMapPromise = null;
            throw error;
        }
    }

    async function nudgeFrame(direction) {
        video.pause();
        try {
            const times = await loadFrameTimestamps();
            const current = nearestFrameIndex(video.currentTime);
            const next = Math.max(0, Math.min(times.length - 1, current + direction));
            video.currentTime = times[next];
            updateFrameStatus();
        } catch (error) {
            setStatus(error.message, true);
        }
    }

    document.getElementById("p-frame-back")?.addEventListener("click", () => nudgeFrame(-1));
    document.getElementById("p-frame-forward")?.addEventListener("click", () => nudgeFrame(1));
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
            const model = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task";
            const cdns = [
                {
                    bundle: "https://unpkg.com/@mediapipe/tasks-vision@0.10.22/vision_bundle.mjs",
                    wasm: "https://unpkg.com/@mediapipe/tasks-vision@0.10.22/wasm",
                },
                {
                    bundle: "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.22/vision_bundle.mjs",
                    wasm: "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.22/wasm",
                },
            ];
            let lastError;
            for (const cdn of cdns) {
                try {
                    const { FilesetResolver, PoseLandmarker } = await import(cdn.bundle);
                    const wasm = await FilesetResolver.forVisionTasks(cdn.wasm);
                    const options = {
                        runningMode: "VIDEO",
                        numPoses: 1,
                        minPoseDetectionConfidence: 0.35,
                        minPosePresenceConfidence: 0.35,
                        minTrackingConfidence: 0.35,
                    };
                    try {
                        return await PoseLandmarker.createFromOptions(wasm, {
                            ...options,
                            baseOptions: { modelAssetPath: model, delegate: "GPU" },
                        });
                    } catch (_) {
                        return await PoseLandmarker.createFromOptions(wasm, {
                            ...options,
                            baseOptions: { modelAssetPath: model, delegate: "CPU" },
                        });
                    }
                } catch (error) {
                    lastError = error;
                }
            }
            throw new Error("Body tracking could not load from either available source. Check the connection and try again.", { cause: lastError });
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
            frame: points[index].frame,
            quality,
            reason: reasons[index],
            sampleRate,
            confidenceLabel: index === 6 ? "Impact proxy · verify contact frame" : "Timing candidate · coach review required",
        }));
    }

    function formatCandidate(candidate) {
        return `Frame index ${candidate.frame} · ${candidate.time.toFixed(3)} sec`;
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
            const times = await loadFrameTimestamps();
            const sampleRateValue = sampleRate();
            const targetCount = Math.max(8, Math.ceil((end - start) * sampleRateValue) + 1);
            if (targetCount > 720) throw new Error("Trim the video to one swing (30 seconds or less) before analysis.");
            const sampleIndices = [];
            const unique = new Set();
            for (let i = 0; i < targetCount; i++) {
                const target = targetCount === 1 ? start : start + (end - start) * i / (targetCount - 1);
                const frameIndex = nearestFrameIndex(target);
                if (frameIndex >= 0 && times[frameIndex] >= start && times[frameIndex] <= end && !unique.has(frameIndex)) {
                    unique.add(frameIndex);
                    sampleIndices.push(frameIndex);
                }
            }
            if (sampleIndices.length < 8) throw new Error("The selected clip is too short. Include at least a third of a second.");
            setStatus("Loading the on-device pose model…");
            const detector = await loadVision();
            const samples = [];
            for (let index = 0; index < sampleIndices.length; index++) {
                const frame = sampleIndices[index];
                const time = times[frame];
                await waitForSeek(time);
                const result = detector.detectForVideo(video, Math.max(1, Math.round(time * 1000)));
                const metrics = frameMetrics(result);
                if (metrics) samples.push({ time, frame, ...metrics });
                if (index % 8 === 0 || index === sampleIndices.length - 1) {
                    setStatus(`Analyzing pose frames: ${index + 1} / ${sampleIndices.length}. Keep this page open.`);
                    await new Promise(resolve => requestAnimationFrame(() => resolve()));
                }
            }
            const tracked = addSpeeds(samples);
            candidates = makeCandidates(tracked, sampleRateValue);
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
