(() => {
    "use strict";

    const page = document.querySelector(".swing-analysis-page");
    if (!page) return;

    const analysisId = page.dataset.analysisId;
    const video = document.getElementById("original-swing-video");
    const p1Input = document.getElementById("assist-p1-time");
    const p10Input = document.getElementById("assist-p10-time");
    const fpsInput = document.getElementById("assist-fps");
    const overwriteInput = document.getElementById("assist-overwrite");
    const status = document.getElementById("assist-status");

    function msg(text, error=false) {
        if (!status) return;
        status.textContent = text;
        status.dataset.error = error ? "1" : "0";
    }

    function setTime(input, value) {
        if (input) input.value = Number(value || 0).toFixed(3);
    }

    document.getElementById("assist-mark-p1")?.addEventListener("click", () => {
        setTime(p1Input, video?.currentTime || 0);
        msg("P1 marked from current video time.");
    });

    document.getElementById("assist-mark-p10")?.addEventListener("click", () => {
        setTime(p10Input, video?.currentTime || 0);
        msg("P10 marked from current video time.");
    });

    document.getElementById("assist-use-video-range")?.addEventListener("click", () => {
        if (!video) return;
        setTime(p1Input, 0);
        setTime(p10Input, video.duration || 0);
        msg("Using full video range. Verify estimates carefully.");
    });

    document.getElementById("assist-seed-checkpoints")?.addEventListener("click", async () => {
        try {
            const p1 = Number(p1Input?.value);
            const p10 = Number(p10Input?.value);
            const fps = Number(fpsInput?.value);

            if (!Number.isFinite(p1) || !Number.isFinite(p10) || p10 <= p1) {
                throw new Error("Mark valid P1 and P10 times first.");
            }

            const response = await fetch(
                `/swing-analysis/${encodeURIComponent(analysisId)}/assist/checkpoints`,
                {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({
                        p1_time: p1,
                        p10_time: p10,
                        fps,
                        overwrite: Boolean(overwriteInput?.checked),
                    }),
                }
            );

            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || "Auto Assist failed.");

            msg("P1-P10 estimated. Verify and fine-tune each checkpoint.");
            setTimeout(() => window.location.reload(), 650);
        } catch (error) {
            msg(error.message, true);
        }
    });

    document.getElementById("assist-derive-x-factor")?.addEventListener("click", async () => {
        try {
            const response = await fetch(
                `/swing-analysis/${encodeURIComponent(analysisId)}/assist/derive-x-factor`,
                {method: "POST"}
            );
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || "X-Factor calculation failed.");
            msg(`X-Factor recalculated at ${data.updated.length} checkpoint(s).`);
            setTimeout(() => window.location.reload(), 650);
        } catch (error) {
            msg(error.message, true);
        }
    });
})();
