(() => {
    "use strict";

    const page = document.querySelector(".swing-analysis-page");
    if (!page) return;

    const analysisId = page.dataset.analysisId;

    const analysisDataNode = document.getElementById("analysis-data");
    const shotsDataNode = document.getElementById("shots-data");

    let analysis = JSON.parse(
        analysisDataNode?.textContent || "{}"
    );

    const shots = JSON.parse(
        shotsDataNode?.textContent || "[]"
    );

    let activePosition =
        analysis.checkpoints?.[0]?.position || "P1";


    function checkpointFor(position) {
        return (
            analysis.checkpoints || []
        ).find(
            checkpoint =>
                checkpoint.position === position
        );
    }


    function numericValue(id) {
        const element =
            document.getElementById(id);

        if (!element) return null;

        const text = element.value.trim();

        if (text === "") return null;

        const value = Number(text);

        return Number.isFinite(value)
            ? value
            : null;
    }


    function setValue(id, value) {
        const element =
            document.getElementById(id);

        if (!element) return;

        element.value =
            value === null ||
            value === undefined
                ? ""
                : value;
    }


    function loadCheckpoint(position) {
        activePosition = position;

        document
            .querySelectorAll(".p-position-button")
            .forEach(button => {
                button.classList.toggle(
                    "active",
                    button.dataset.position === position
                );
            });

        const checkpoint =
            checkpointFor(position) || {};

        document.getElementById(
            "checkpoint-title"
        ).textContent = position;

        setValue(
            "checkpoint-time",
            checkpoint.time_seconds
        );

        setValue(
            "checkpoint-frame",
            checkpoint.frame_number
        );

        setValue(
            "checkpoint-pelvis",
            checkpoint.pelvis_rotation
        );

        setValue(
            "checkpoint-torso",
            checkpoint.torso_rotation
        );

        setValue(
            "checkpoint-x-factor",
            checkpoint.x_factor
        );

        setValue(
            "checkpoint-shoulder-tilt",
            checkpoint.shoulder_tilt
        );

        setValue(
            "checkpoint-hip-tilt",
            checkpoint.hip_tilt
        );

        setValue(
            "checkpoint-spine-tilt",
            checkpoint.spine_tilt
        );

        setValue(
            "checkpoint-shaft-angle",
            checkpoint.shaft_angle
        );

        setValue(
            "checkpoint-source",
            checkpoint.measurement_source || "Manual"
        );

        setValue(
            "checkpoint-tgm",
            checkpoint.tgm_observation
        );

        setValue(
            "checkpoint-tpi",
            checkpoint.tpi_observation
        );

        setValue(
            "checkpoint-biomechanics",
            checkpoint.biomechanical_observation
        );

        setValue(
            "checkpoint-coaching",
            checkpoint.coaching_observation
        );

        const video =
            document.getElementById(
                "original-swing-video"
            );

        if (
            video &&
            checkpoint.time_seconds !== null &&
            checkpoint.time_seconds !== undefined
        ) {
            video.currentTime =
                checkpoint.time_seconds;
        }
    }


    async function saveCheckpoint() {
        const payload = {
            time_seconds:
                numericValue("checkpoint-time"),

            frame_number:
                numericValue("checkpoint-frame"),

            pelvis_rotation:
                numericValue("checkpoint-pelvis"),

            torso_rotation:
                numericValue("checkpoint-torso"),

            x_factor:
                numericValue("checkpoint-x-factor"),

            shoulder_tilt:
                numericValue(
                    "checkpoint-shoulder-tilt"
                ),

            hip_tilt:
                numericValue("checkpoint-hip-tilt"),

            spine_tilt:
                numericValue(
                    "checkpoint-spine-tilt"
                ),

            shaft_angle:
                numericValue(
                    "checkpoint-shaft-angle"
                ),

            measurement_source:
                document.getElementById(
                    "checkpoint-source"
                )?.value || "Manual",

            tgm_observation:
                document.getElementById(
                    "checkpoint-tgm"
                )?.value || "",

            tpi_observation:
                document.getElementById(
                    "checkpoint-tpi"
                )?.value || "",

            biomechanical_observation:
                document.getElementById(
                    "checkpoint-biomechanics"
                )?.value || "",

            coaching_observation:
                document.getElementById(
                    "checkpoint-coaching"
                )?.value || "",
        };

        const response = await fetch(
            `/swing-analysis/${encodeURIComponent(
                analysisId
            )}/workspace/checkpoint/${encodeURIComponent(
                activePosition
            )}`,
            {
                method: "PATCH",
                headers: {
                    "Content-Type":
                        "application/json",
                },
                body: JSON.stringify(payload),
            }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.detail ||
                "Checkpoint could not be saved."
            );
        }

        const index = (
            analysis.checkpoints || []
        ).findIndex(
            item =>
                item.position ===
                activePosition
        );

        if (index >= 0) {
            analysis.checkpoints[index] = data;
        }

        const button =
            document.querySelector(
                `.p-position-button[data-position="${activePosition}"]`
            );

        if (button) {
            const timeLabel =
                button.querySelector("span");

            if (timeLabel) {
                timeLabel.textContent =
                    data.time_seconds !== null &&
                    data.time_seconds !== undefined
                        ? `${Number(
                            data.time_seconds
                        ).toFixed(3)}s`
                        : "Set";
            }
        }

        const message =
            document.getElementById(
                "checkpoint-save-message"
            );

        if (message) {
            message.textContent =
                `${activePosition} saved`;

            setTimeout(() => {
                message.textContent = "";
            }, 1800);
        }
    }


    function collectAnalysisPayload() {
        const payload = {};

        document
            .querySelectorAll(
                "[data-analysis-field]"
            )
            .forEach(element => {
                const key =
                    element.dataset.analysisField;

                if (!key) return;

                if (
                    element.type === "checkbox"
                ) {
                    payload[key] =
                        element.checked;
                } else {
                    payload[key] =
                        element.value;
                }
            });

        payload.status =
            document.getElementById(
                "analysis-status"
            )?.value || analysis.status;

        return payload;
    }


    async function saveAnalysis() {
        const response = await fetch(
            `/swing-analysis/${encodeURIComponent(
                analysisId
            )}/workspace`,
            {
                method: "PATCH",
                headers: {
                    "Content-Type":
                        "application/json",
                },
                body: JSON.stringify(
                    collectAnalysisPayload()
                ),
            }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.detail ||
                "Analysis could not be saved."
            );
        }

        analysis = data;

        const statusLabel =
            document.getElementById(
                "analysis-status-label"
            );

        if (statusLabel) {
            statusLabel.textContent =
                data.status;
        }

        const message =
            document.getElementById(
                "analysis-save-message"
            );

        if (message) {
            message.textContent =
                "Analysis saved";

            setTimeout(() => {
                message.textContent = "";
            }, 1800);
        }
    }


    function renderGarminMetrics(shot) {
        document
            .querySelectorAll(
                "[data-garmin]"
            )
            .forEach(element => {
                const key =
                    element.dataset.garmin;

                const value =
                    shot?.[key];

                if (
                    value === null ||
                    value === undefined ||
                    value === ""
                ) {
                    element.textContent = "—";
                    return;
                }

                if (key === "spin_rate") {
                    element.textContent =
                        Math.round(value);
                    return;
                }

                element.textContent =
                    Number(value).toFixed(2);
            });
    }


    async function linkGarminShot(shotId) {
        if (!shotId) {
            renderGarminMetrics(null);
            return;
        }

        const response = await fetch(
            `/swing-analysis/${encodeURIComponent(
                analysisId
            )}/workspace/shot/${encodeURIComponent(
                shotId
            )}`,
            {
                method: "POST",
            }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.detail ||
                "Garmin shot could not be linked."
            );
        }

        analysis = data;
        renderGarminMetrics(data.shot);
    }


    document
        .querySelectorAll(
            ".p-position-button"
        )
        .forEach(button => {
            button.addEventListener(
                "click",
                () => {
                    loadCheckpoint(
                        button.dataset.position
                    );
                }
            );
        });


    document
        .getElementById(
            "capture-current-time"
        )
        ?.addEventListener(
            "click",
            () => {
                const video =
                    document.getElementById(
                        "original-swing-video"
                    );

                if (!video) return;

                setValue(
                    "checkpoint-time",
                    video.currentTime.toFixed(3)
                );
            }
        );


    document
        .getElementById(
            "save-checkpoint"
        )
        ?.addEventListener(
            "click",
            async () => {
                try {
                    await saveCheckpoint();
                } catch (error) {
                    alert(error.message);
                }
            }
        );


    [
        "save-analysis",
        "save-analysis-bottom",
    ].forEach(id => {
        document
            .getElementById(id)
            ?.addEventListener(
                "click",
                async () => {
                    try {
                        await saveAnalysis();
                    } catch (error) {
                        alert(error.message);
                    }
                }
            );
    });


    document
        .getElementById(
            "garmin-shot-selector"
        )
        ?.addEventListener(
            "change",
            async event => {
                try {
                    await linkGarminShot(
                        event.target.value
                    );
                } catch (error) {
                    alert(error.message);
                }
            }
        );


    const selectedShot = analysis.shot;

    if (selectedShot) {
        renderGarminMetrics(
            selectedShot
        );
    } else {
        renderGarminMetrics(null);
    }

    loadCheckpoint(activePosition);
})();
