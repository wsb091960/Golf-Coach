(() => {
  const video = document.getElementById("gcie-review-video");
  const canvas = document.getElementById("gcie-pose-canvas");
  const toggle = document.getElementById("gcie-pose-toggle");
  const status = document.getElementById("gcie-pose-status");
  const badge = document.getElementById("gcie-pose-label");
  if (!video || !canvas || !toggle || !status) return;

  const context = canvas.getContext("2d");
  let landmarker = null;
  let enabled = false;
  let loading = false;
  let lastDrawAt = 0;
  let lastTimestamp = 0;
  let callbackId = null;
  const links = [
    [11, 12, "#f1c34c"], [23, 24, "#f1c34c"],
    [11, 23, "#5dd2a0"], [12, 24, "#5dd2a0"],
    [11, 13, "#e8efe9"], [13, 15, "#e8efe9"], [12, 14, "#e8efe9"], [14, 16, "#e8efe9"],
    [23, 25, "#e8efe9"], [25, 27, "#e8efe9"], [24, 26, "#e8efe9"], [26, 28, "#e8efe9"],
  ];

  function setStatus(message, isError = false) {
    status.textContent = message;
    status.classList.toggle("is-error", isError);
  }

  async function loadModel() {
    const modelAssetPath = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task";
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
        const files = await FilesetResolver.forVisionTasks(cdn.wasm);
        const options = {
          runningMode: "VIDEO", numPoses: 1,
          minPoseDetectionConfidence: 0.35,
          minPosePresenceConfidence: 0.35,
          minTrackingConfidence: 0.35,
        };
        try {
          return await PoseLandmarker.createFromOptions(files, {
            ...options, baseOptions: { modelAssetPath, delegate: "GPU" },
          });
        } catch (_) {
          return await PoseLandmarker.createFromOptions(files, {
            ...options, baseOptions: { modelAssetPath, delegate: "CPU" },
          });
        }
      } catch (error) {
        lastError = error;
      }
    }
    throw new Error("Body tracking could not load from either available source. Check the connection and try again.", { cause: lastError });
  }

  function canvasSize() {
    const rect = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    const width = Math.max(1, Math.round(rect.width * dpr));
    const height = Math.max(1, Math.round(rect.height * dpr));
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
    }
    return { width, height, dpr };
  }

  function drawPose(landmarks) {
    const { width, height } = canvasSize();
    context.clearRect(0, 0, width, height);
    if (!landmarks?.length || !video.videoWidth || !video.videoHeight) {
      if (badge) badge.hidden = true;
      setStatus("No clear body landmarks in this frame. Pause on a frame with the golfer fully visible.");
      return;
    }

    const scale = Math.min(width / video.videoWidth, height / video.videoHeight);
    const drawnWidth = video.videoWidth * scale;
    const drawnHeight = video.videoHeight * scale;
    const offsetX = (width - drawnWidth) / 2;
    const offsetY = (height - drawnHeight) / 2;
    const point = index => {
      const p = landmarks[index];
      if (!p || Number(p.visibility ?? 1) < 0.3) return null;
      return { x: offsetX + p.x * drawnWidth, y: offsetY + p.y * drawnHeight, visibility: Number(p.visibility ?? 0) };
    };
    const visible = landmarks.filter(p => Number(p.visibility ?? 0) >= 0.3);

    context.lineCap = "round";
    context.lineJoin = "round";
    for (const [from, to, color] of links) {
      const a = point(from), b = point(to);
      if (!a || !b) continue;
      context.beginPath();
      context.moveTo(a.x, a.y);
      context.lineTo(b.x, b.y);
      context.strokeStyle = color;
      context.lineWidth = Math.max(2, width / 300);
      context.shadowColor = "#061c15";
      context.shadowBlur = 4;
      context.stroke();
    }
    context.shadowBlur = 0;
    [0, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28].forEach(index => {
      const p = point(index);
      if (!p) return;
      context.beginPath();
      context.arc(p.x, p.y, Math.max(3, width / 185), 0, Math.PI * 2);
      context.fillStyle = index === 11 || index === 12 || index === 23 || index === 24 ? "#f1c34c" : "#63d7a7";
      context.fill();
      context.strokeStyle = "#fff";
      context.lineWidth = Math.max(1.5, width / 550);
      context.stroke();
    });

    const confidence = Math.round(visible.reduce((sum, p) => sum + Number(p.visibility || 0), 0) / Math.max(1, visible.length) * 100);
    const nearest = [...document.querySelectorAll(".gcie-checkpoint[data-checkpoint-time]")]
      .map(button => ({ button, time: Number(button.dataset.checkpointTime) }))
      .filter(item => Number.isFinite(item.time))
      .sort((a, b) => Math.abs(a.time - video.currentTime) - Math.abs(b.time - video.currentTime))[0];
    const checkpoint = nearest && Math.abs(nearest.time - video.currentTime) < 0.09 ? ` · ${nearest.button.querySelector("b")?.textContent || ""}` : "";
    if (badge) {
      badge.textContent = `BODY LANDMARKS · ${confidence}%${checkpoint}`;
      badge.hidden = false;
    }
    setStatus(`Pose visible · ${confidence}% landmark confidence · 2D overlay estimate. Confirm against the frame before using as a measurement.`);
  }

  function drawCurrentFrame(force = false) {
    if (!enabled || !landmarker || video.readyState < 2 || video.seeking) return;
    const now = performance.now();
    if (!force && now - lastDrawAt < 80) return;
    lastDrawAt = now;
    try {
      lastTimestamp = Math.max(Math.round(now), lastTimestamp + 1);
      const result = landmarker.detectForVideo(video, lastTimestamp);
      drawPose(result?.landmarks?.[0] || null);
    } catch (error) {
      setStatus(error.message || "Pose overlay could not analyze this frame.", true);
    }
  }

  function scheduleNext() {
    if (!enabled || video.paused || video.ended) return;
    if (typeof video.requestVideoFrameCallback === "function") {
      callbackId = video.requestVideoFrameCallback(() => {
        drawCurrentFrame();
        scheduleNext();
      });
    } else {
      callbackId = requestAnimationFrame(() => {
        drawCurrentFrame();
        scheduleNext();
      });
    }
  }

  function stopLoop() {
    if (callbackId === null) return;
    if (typeof video.cancelVideoFrameCallback === "function") video.cancelVideoFrameCallback(callbackId);
    else cancelAnimationFrame(callbackId);
    callbackId = null;
  }

  toggle.addEventListener("click", async () => {
    if (enabled) {
      enabled = false;
      stopLoop();
      context.clearRect(0, 0, canvas.width, canvas.height);
      if (badge) badge.hidden = true;
      toggle.textContent = "Show body overlay";
      toggle.setAttribute("aria-pressed", "false");
      toggle.classList.remove("is-active");
      setStatus("Overlay is off.");
      return;
    }
    if (!Number.isFinite(video.duration) || video.readyState < 2) {
      setStatus("Wait for the video to load, then turn on the overlay.", true);
      return;
    }
    toggle.disabled = true;
    setStatus("Loading the on-device pose tracker…");
    try {
      if (!landmarker && !loading) {
        loading = true;
        landmarker = await loadModel();
        loading = false;
      }
      enabled = true;
      toggle.textContent = "Hide body overlay";
      toggle.setAttribute("aria-pressed", "true");
      toggle.classList.add("is-active");
      drawCurrentFrame(true);
      scheduleNext();
    } catch (error) {
      loading = false;
      setStatus(error.message || "The pose model could not be loaded. Try again when connected.", true);
    } finally {
      toggle.disabled = false;
    }
  });

  video.addEventListener("play", scheduleNext);
  video.addEventListener("pause", () => { stopLoop(); drawCurrentFrame(true); });
  video.addEventListener("seeked", () => drawCurrentFrame(true));
  video.addEventListener("loadedmetadata", () => canvasSize());
  window.addEventListener("resize", () => drawCurrentFrame(true));
})();
