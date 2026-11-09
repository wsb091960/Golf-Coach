(() => {
    "use strict";

    const canvas = document.getElementById("standalone-flight-canvas");
    const form = document.getElementById("flight-input-form");
    if (!canvas || !form) return;

    const ctx = canvas.getContext("2d");
    const fields = form.elements;
    const sim = { camera: "behind", progress: 1, speed: 1, playing: false, frame: null, last: 0 };
    let shot = readInputs();
    let lastEstimateKey = estimateKey(shot);
    const carryField = fields.namedItem("carry_distance");
    const totalField = fields.namedItem("total_distance");
    let rolloutAllowance = Math.max(0, shot.total_distance - shot.carry_distance);
    let carryNeedsSync = false;

    function syncTotalFromCarry() {
        if (!carryNeedsSync) return;
        const carry = optionalNumber("carry_distance");
        if (carry === null) return;
        totalField.value = String(Math.round(carry + rolloutAllowance));
        carryNeedsSync = false;
    }

    carryField.addEventListener("input", () => { carryNeedsSync = true; });
    carryField.addEventListener("change", syncTotalFromCarry);
    totalField.addEventListener("change", () => {
        const carry = optionalNumber("carry_distance");
        const total = optionalNumber("total_distance");
        if (carry === null || total === null) return;
        if (total < carry) totalField.value = String(Math.round(carry));
        rolloutAllowance = Math.max(0, Number(totalField.value) - carry);
        carryNeedsSync = false;
    });

    function optionalNumber(name) {
        const field = fields.namedItem(name);
        if (!field || field.value.trim() === "") return null;
        const value = Number(field.value);
        return Number.isFinite(value) ? value : null;
    }

    function number(name, fallback = 0) {
        return optionalNumber(name) ?? fallback;
    }

    function readInputs() {
        const clubFace = number("club_face", 0);
        const clubPath = number("club_path", 0);
        const carry = number("carry_distance", 250);
        return {
            ball_speed: number("ball_speed", 150),
            smash_factor: number("smash_factor", 1.50),
            spin_rate: number("spin_rate", 2600),
            launch_angle: number("launch_angle", 14),
            launch_direction: number("launch_direction", 0),
            club_face: clubFace,
            club_path: clubPath,
            face_to_path: clubFace - clubPath,
            spin_axis: optionalNumber("spin_axis"),
            spin_axis_estimate: 0,
            carry_distance: carry,
            total_distance: Math.max(number("total_distance", 270), carry),
            apex_height: number("apex_height", 90),
        };
    }

    function refreshEstimatedClubSpeed() {
        const ballSpeed = optionalNumber("ball_speed");
        const smashFactor = optionalNumber("smash_factor");
        const output = fields.namedItem("club_speed_estimate");
        if (!output) return;
        output.value = ballSpeed !== null && smashFactor !== null && smashFactor > 0
            ? (ballSpeed / smashFactor).toFixed(1)
            : "";
    }

    function estimateKey(input) {
        return [input.ball_speed, input.launch_angle, input.spin_rate].join("|");
    }

    function estimateOutcomes(input) {
        const idealLaunch = 13;
        const idealSpin = 2600;
        const launchFactor = Math.max(.82, Math.min(1.04, 1 - Math.abs(input.launch_angle - idealLaunch) * .008));
        const spinFactor = Math.max(.86, Math.min(1.02, 1 - Math.abs(input.spin_rate - idealSpin) / idealSpin * .10));
        const carry = input.ball_speed * 1.65 * launchFactor * spinFactor;
        const roll = .10
            * Math.max(.35, Math.min(1.45, 1 - (input.launch_angle - idealLaunch) * .035))
            * Math.max(.35, Math.min(1.35, 1 - (input.spin_rate - idealSpin) / idealSpin * .45));
        input.carry_distance = carry;
        input.total_distance = carry * (1 + roll);
        input.apex_height = Math.max(12, carry * Math.tan(Math.max(3, input.launch_angle) * Math.PI / 180) * .84);
    }

    function refreshFaceToPath() {
        const face = optionalNumber("club_face") ?? 0;
        const path = optionalNumber("club_path") ?? 0;
        const derived = face - path;
        const field = fields.namedItem("face_to_path");
        if (field) field.value = derived.toFixed(1);
        shot.club_face = face;
        shot.club_path = path;
        shot.face_to_path = derived;
        // Estimated axis uses a typical driver spin loft (14.7°); gear effect and strike location are not known.
        shot.spin_axis_estimate = Math.atan(Math.tan(derived * Math.PI / 180) / Math.sin(14.7 * Math.PI / 180)) * 180 / Math.PI;
        fields.namedItem("spin_axis_estimate").value = shot.spin_axis_estimate.toFixed(1);
    }

    fields.namedItem("club_face").addEventListener("input", refreshFaceToPath);
    fields.namedItem("club_path").addEventListener("input", refreshFaceToPath);
    fields.namedItem("ball_speed").addEventListener("input", refreshEstimatedClubSpeed);
    fields.namedItem("smash_factor").addEventListener("input", refreshEstimatedClubSpeed);
    ["ball_speed", "launch_angle", "spin_rate"].forEach(name => {
        fields.namedItem(name).addEventListener("change", () => updateFlight(true));
    });
    refreshFaceToPath();
    refreshEstimatedClubSpeed();

    function finishYards() {
        const start = Math.tan(shot.launch_direction * Math.PI / 180) * shot.carry_distance;
        const curveAngle = shot.spin_axis ?? shot.spin_axis_estimate;
        const curve = curveAngle * shot.carry_distance / 125;
        return start + curve;
    }

    function roundedRect(x, y, width, height, radius) {
        ctx.beginPath();
        ctx.roundRect(x, y, width, height, radius);
        ctx.fill();
    }

    function drawTrees(w, horizon) {
        ctx.fillStyle = "#153c29";
        for (let x = -28; x < w + 28; x += 42) {
            const offset = (Math.floor(x / 42) % 3) * 5;
            ctx.beginPath();
            ctx.arc(x, horizon + 5 + offset, 28 + offset, Math.PI, 0);
            ctx.fill();
        }
    }

    function drawBehind(w, h) {
        const horizon = h * 0.27;
        const ground = h - 46;
        const sky = ctx.createLinearGradient(0, 0, 0, horizon + 30);
        sky.addColorStop(0, "#b6d5c5");
        sky.addColorStop(1, "#e9efe5");
        ctx.fillStyle = sky;
        ctx.fillRect(0, 0, w, h);
        drawTrees(w, horizon);
        const grass = ctx.createLinearGradient(0, horizon, 0, h);
        grass.addColorStop(0, "#87a95c");
        grass.addColorStop(0.58, "#527d42");
        grass.addColorStop(1, "#214a32");
        ctx.fillStyle = grass;
        ctx.fillRect(0, horizon + 8, w, h - horizon);
        for (let y = horizon + 16, band = 0; y < h; y += 54, band += 1) {
            ctx.fillStyle = band % 2 ? "rgba(236,246,214,.08)" : "rgba(16,63,31,.08)";
            ctx.fillRect(0, y, w, 27);
        }
        ctx.strokeStyle = "rgba(255,255,255,.54)";
        ctx.fillStyle = "rgba(255,255,255,.93)";
        ctx.lineWidth = 2;
        ctx.textAlign = "center";
        ctx.font = "700 12px system-ui, sans-serif";
        const max = Math.max(300, Math.ceil(shot.total_distance / 50) * 50);
        const center = w / 2;
        for (let d = 50; d <= max; d += 50) {
            const y = ground - (d / max) * (ground - horizon - 28);
            ctx.beginPath();
            ctx.ellipse(center, y, Math.max(28, w * .055), 9, 0, 0, Math.PI * 2);
            ctx.stroke();
            ctx.fillText(String(d), center, y + 4);
        }
        return { horizon, ground, max };
    }

    function drawSide(w, h) {
        const ground = h - 58;
        const sky = ctx.createLinearGradient(0, 0, 0, ground);
        sky.addColorStop(0, "#b6d5c5");
        sky.addColorStop(1, "#e9efe5");
        ctx.fillStyle = sky;
        ctx.fillRect(0, 0, w, h);
        ctx.fillStyle = "#183e2c";
        for (let x = -20; x < w + 20; x += 45) {
            ctx.beginPath();
            ctx.arc(x, ground - 5, 28, Math.PI, 0);
            ctx.fill();
        }
        const grass = ctx.createLinearGradient(0, ground - 10, 0, h);
        grass.addColorStop(0, "#70964b");
        grass.addColorStop(1, "#274a31");
        ctx.fillStyle = grass;
        ctx.fillRect(0, ground - 5, w, h - ground + 5);
        ctx.strokeStyle = "rgba(255,255,255,.55)";
        ctx.fillStyle = "#edf6e9";
        ctx.textAlign = "center";
        ctx.font = "700 12px system-ui, sans-serif";
        const max = Math.max(300, Math.ceil(shot.total_distance / 50) * 50);
        for (let d = 50; d <= max; d += 50) {
            const x = 55 + (d / max) * (w - 95);
            ctx.beginPath();
            ctx.moveTo(x, ground - 13);
            ctx.lineTo(x, ground + 8);
            ctx.stroke();
            ctx.fillText(String(d), x, ground + 29);
        }
        return { ground, max };
    }

    function drawOverhead(w, h) {
        const rough = ctx.createLinearGradient(0, 0, 0, h);
        rough.addColorStop(0, "#315b35");
        rough.addColorStop(1, "#173923");
        ctx.fillStyle = rough;
        ctx.fillRect(0, 0, w, h);
        ctx.beginPath();
        ctx.moveTo(w * .39, h);
        ctx.lineTo(w * .25, 0);
        ctx.lineTo(w * .75, 0);
        ctx.lineTo(w * .61, h);
        ctx.closePath();
        ctx.fillStyle = "#70984b";
        ctx.fill();
        ctx.save();
        ctx.clip();
        for (let y = 0, band = 0; y < h; y += 48, band += 1) {
            ctx.fillStyle = band % 2 ? "rgba(255,255,220,.07)" : "rgba(20,65,30,.08)";
            ctx.fillRect(0, y, w, 48);
        }
        ctx.restore();
        ctx.strokeStyle = "rgba(255,255,255,.5)";
        ctx.setLineDash([8, 8]);
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(w / 2, h - 48);
        ctx.lineTo(w / 2, 44);
        ctx.stroke();
        ctx.setLineDash([]);
        return { max: Math.max(300, Math.ceil(shot.total_distance / 50) * 50) };
    }

    function pathPoint(t, bounds, w, h) {
        const carry = shot.carry_distance;
        const distance = carry * t;
        const startOffset = Math.tan(shot.launch_direction * Math.PI / 180) * distance;
        const curveAngle = shot.spin_axis ?? shot.spin_axis_estimate;
        const curveOffset = curveAngle * carry / 125 * t * t;
        const lateral = startOffset + curveOffset;
        if (sim.camera === "side") {
            const x = 54 + distance / bounds.max * (w - 94);
            const apexPixels = Math.max(34, Math.min(h * .42, shot.apex_height * 1.45));
            return { x, y: bounds.ground - Math.sin(Math.PI * t) * apexPixels };
        }
        if (sim.camera === "overhead") {
            const scale = (w * .30) / Math.max(35, Math.abs(finishYards()) * 1.35);
            return { x: w / 2 + lateral * scale, y: h - 48 - distance / bounds.max * (h - 92) };
        }
        const maxHeight = Math.max(50, Math.min(h * .46, shot.apex_height * 1.35));
        const yTravel = distance / bounds.max * (bounds.ground - bounds.horizon - 20);
        return { x: w / 2 + lateral * 3.3, y: bounds.ground - yTravel - Math.sin(Math.PI * t) * maxHeight };
    }

    function draw() {
        const w = canvas.width;
        const h = canvas.height;
        ctx.clearRect(0, 0, w, h);
        const bounds = sim.camera === "side"
            ? drawSide(w, h)
            : sim.camera === "overhead"
                ? drawOverhead(w, h)
                : drawBehind(w, h);

        const progress = Math.max(0, Math.min(1, sim.progress));
        const segments = Math.max(2, Math.ceil(progress * 100));
        ctx.save();
        ctx.lineCap = "round";
        ctx.lineJoin = "round";
        ctx.strokeStyle = "rgba(255,255,255,.3)";
        ctx.lineWidth = 9;
        ctx.beginPath();
        for (let i = 0; i <= segments; i += 1) {
            const t = progress * i / segments;
            const point = pathPoint(t, bounds, w, h);
            if (i === 0) ctx.moveTo(point.x, point.y);
            else ctx.lineTo(point.x, point.y);
        }
        ctx.stroke();
        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 4;
        ctx.beginPath();
        for (let i = 0; i <= segments; i += 1) {
            const t = progress * i / segments;
            const point = pathPoint(t, bounds, w, h);
            if (i === 0) ctx.moveTo(point.x, point.y);
            else ctx.lineTo(point.x, point.y);
        }
        ctx.stroke();
        const ball = pathPoint(progress, bounds, w, h);
        ctx.fillStyle = "#f1c64e";
        ctx.beginPath();
        ctx.arc(ball.x, ball.y, 7, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = "#fff8dd";
        ctx.lineWidth = 2;
        ctx.stroke();

        if (progress >= 1) {
            const carryEnd = pathPoint(1, bounds, w, h);
            if (sim.camera === "side") {
                const rollEnd = { x: 54 + shot.total_distance / bounds.max * (w - 94), y: bounds.ground };
                ctx.setLineDash([5, 5]);
                ctx.strokeStyle = "rgba(255,255,255,.78)";
                ctx.lineWidth = 2;
                ctx.beginPath();
                ctx.moveTo(carryEnd.x, bounds.ground);
                ctx.lineTo(rollEnd.x, bounds.ground);
                ctx.stroke();
                ctx.setLineDash([]);
                ctx.fillStyle = "#f1c64e";
                ctx.beginPath();
                ctx.arc(rollEnd.x, rollEnd.y, 6, 0, Math.PI * 2);
                ctx.fill();
            }
            ctx.fillStyle = "rgba(10,45,31,.88)";
            roundedRect(20, 20, 260, 62, 8);
            ctx.fillStyle = "#ffffff";
            ctx.textAlign = "left";
            ctx.font = "800 15px system-ui,sans-serif";
            ctx.fillText("FLIGHT COMPLETE", 36, 46);
            ctx.fillStyle = "#f1c64e";
            ctx.font = "700 11px system-ui,sans-serif";
            ctx.fillText("ESTIMATED FLIGHT MODEL", 36, 66);
            if (sim.camera === "overhead") {
                ctx.fillStyle = "#f1c64e";
                ctx.beginPath();
                ctx.arc(carryEnd.x, carryEnd.y, 7, 0, Math.PI * 2);
                ctx.fill();
            }
        }
        ctx.restore();
        updateReadout();
    }

    function updateReadout() {
        const finish = finishYards();
        const values = {
            speed: `${shot.ball_speed.toFixed(1)} mph`,
            carry: `${shot.carry_distance.toFixed(0)} yd`,
            total: `${shot.total_distance.toFixed(0)} yd`,
            apex: `${shot.apex_height.toFixed(0)} ft`,
            facePath: `${shot.face_to_path.toFixed(1)}°`,
            finish: `${Math.abs(finish).toFixed(1)} yd ${Math.abs(finish) < .05 ? "" : finish < 0 ? "L" : "R"}`.trim(),
        };
        Object.entries(values).forEach(([key, value]) => {
            const node = document.querySelector(`[data-readout="${key}"]`);
            if (node) node.textContent = value;
        });
    }

    function updateFlight(recalculateOutcomes = false) {
        refreshEstimatedClubSpeed();
        const nextShot = readInputs();
        refreshFaceToPath();
        nextShot.spin_axis_estimate = shot.spin_axis_estimate;
        if (recalculateOutcomes) {
            estimateOutcomes(nextShot);
            fields.namedItem("carry_distance").value = String(Math.round(nextShot.carry_distance));
            fields.namedItem("total_distance").value = String(Math.round(nextShot.total_distance));
            fields.namedItem("apex_height").value = String(Math.round(nextShot.apex_height));
            rolloutAllowance = Math.max(0, nextShot.total_distance - nextShot.carry_distance);
            carryNeedsSync = false;
            lastEstimateKey = estimateKey(nextShot);
        }
        shot = nextShot;
        if (shot.total_distance < shot.carry_distance) {
            shot.total_distance = shot.carry_distance;
            fields.namedItem("total_distance").value = String(Math.round(shot.total_distance));
        }
        stop();
        sim.progress = 1;
        draw();
    }

    function stop() {
        sim.playing = false;
        if (sim.frame) cancelAnimationFrame(sim.frame);
        sim.frame = null;
        const button = document.getElementById("flight-pause");
        if (button) {
            button.textContent = "Resume";
            button.setAttribute("aria-pressed", "true");
        }
        draw();
    }

    function animate(time) {
        if (!sim.playing) return;
        if (!sim.last) sim.last = time;
        const elapsed = time - sim.last;
        sim.last = time;
        sim.progress = Math.min(1, sim.progress + elapsed / 2100 * sim.speed);
        draw();
        if (sim.progress >= 1) {
            stop();
            const pause = document.getElementById("flight-pause");
            if (pause) pause.textContent = "Replay";
            return;
        }
        sim.frame = requestAnimationFrame(animate);
    }

    function play(restart) {
        if (restart) sim.progress = 0;
        if (sim.progress >= 1) sim.progress = 0;
        sim.playing = true;
        sim.last = 0;
        const button = document.getElementById("flight-pause");
        if (button) {
            button.textContent = "Pause";
            button.setAttribute("aria-pressed", "false");
        }
        cancelAnimationFrame(sim.frame);
        sim.frame = requestAnimationFrame(animate);
    }

    document.querySelectorAll("[data-camera]").forEach(button => {
        button.addEventListener("click", () => {
            sim.camera = button.dataset.camera;
            document.querySelectorAll("[data-camera]").forEach(item => {
                const active = item === button;
                item.classList.toggle("is-active", active);
                item.setAttribute("aria-pressed", active ? "true" : "false");
            });
            draw();
        });
    });
    document.getElementById("flight-replay").addEventListener("click", () => play(true));
    document.getElementById("flight-pause").addEventListener("click", () => sim.playing ? stop() : play(false));
    document.getElementById("flight-speed").addEventListener("change", event => {
        sim.speed = Number(event.target.value) || 1;
    });

    function angleLabel(value) {
        return `${value >= 0 ? "+" : ""}${value.toFixed(1)}°`;
    }

    function shotPattern(startDirection, spinAxis) {
        const start = startDirection < -0.5 ? "left" : startDirection > 0.5 ? "right" : "near target";
        const curve = spinAxis < -1 ? "left" : spinAxis > 1 ? "right" : "mostly straight";
        if (start === "left" && curve === "right") return "Pull-fade";
        if (start === "left" && curve === "left") return "Pull / pull-hook";
        if (start === "right" && curve === "left") return "Push-draw";
        if (start === "right" && curve === "right") return "Push-fade";
        if (start === "near target" && curve === "right") return "Fade";
        if (start === "near target" && curve === "left") return "Draw";
        return "Mostly straight";
    }

    function analyzeLawsAndPrinciples() {
        const latest = readInputs();
        updateFlight(estimateKey(latest) !== lastEstimateKey);
        const input = readInputs();
        input.spin_axis_estimate = shot.spin_axis_estimate;
        const axis = input.spin_axis ?? input.spin_axis_estimate;
        const pattern = shotPattern(input.launch_direction, axis);
        const f2p = input.face_to_path;

        const focus = new Set([1, 12, 14]);
        if (Math.abs(input.launch_direction) > 1.5 || Math.abs(input.club_face) > 1.5) focus.add(1);
        if (Math.abs(input.club_path) > 2.5) {
            focus.add(2);
            focus.add(8);
            focus.add(10);
        }
        if (Math.abs(f2p) > 1.5) {
            focus.add(6);
            focus.add(11);
            focus.add(13);
        }
        focus.add(7);

        const faceNote = f2p > 1.5
            ? "Face is open relative to path; expect curvature to the right with centered contact."
            : f2p < -1.5
                ? "Face is closed relative to path; expect curvature to the left with centered contact."
                : "Face and path are close; use start direction and strike pattern to refine the shot.";
        const pathNote = input.club_path < -2.5
            ? "Path is left of target; assess setup alignment, swing plane, transition, and rotation."
            : input.club_path > 2.5
                ? "Path is right of target; assess setup alignment, swing plane, transition, and rotation."
                : "Path is relatively close to target line; keep it repeatable while controlling face.";
        const startNote = input.launch_direction < -1.5
            ? "Ball starts left; check face direction and verify the target line before changing motion."
            : input.launch_direction > 1.5
                ? "Ball starts right; check face direction and verify the target line before changing motion."
                : "Ball starts near target; use face-to-path to shape the curve.";
        const laws = [
            ["1. Centeredness of Contact", "Not entered. Check face strike with spray or impact tape; off-center contact can alter speed and curve."],
            ["2. Clubface Angle at Impact", `Face ${angleLabel(input.club_face)} to target. ${startNote}`],
            ["3. Clubpath at Impact", `Path ${angleLabel(input.club_path)} to target. F2P is ${angleLabel(f2p)} (face minus path). ${pathNote}`],
            ["4. Clubhead Speed at Impact", `Estimated at ${fields.namedItem("club_speed_estimate").value} mph using a ${input.smash_factor.toFixed(2)} assumed smash factor; verify with measured club speed and strike quality.`],
            ["5. Angle of Approach at Impact", "Not entered. Measure attack angle; do not infer it from the shot curve."],
            ["6. Dynamic Loft at Impact", `Launch is ${input.launch_angle.toFixed(1)}° and spin is ${input.spin_rate.toFixed(0)} rpm. Dynamic loft is not entered, so verify it before making a loft or attack-angle change.`],
        ];
        const principles = [
            ["1. Setup", "Check grip, aim, body alignment, posture, and ball position so the target line and start direction are understood."],
            ["2. Swing Plane", "Primary when path is substantially left or right; work toward the path needed for the intended curve."],
            ["3. Arc Width", "Use as a support for centered contact and consistent delivery; not the first curve correction."],
            ["4. Arc Length", "Influences speed and distance potential more than the face-to-path relationship."],
            ["5. Lever System", "Supports speed and impact delivery; assess if speed or low point is also a goal."],
            ["6. Release", "Coach how the face is delivered relative to the path; avoid forcing a hand roll without evidence."],
            ["7. Dynamic Balance", "Support a stable, repeatable center and low point through impact."],
            ["8. Swing Center", "Body rotation, arm swing, and transition/slotting can influence path direction and repeatability."],
            ["9. Clubhead Lag", "Relates to delivery and speed; it is not by itself the cause of a particular curve."],
            ["10. Connection", "Use to coordinate body and arms if the observed motion disrupts path or face delivery."],
            ["11. Left Wrist Position at Impact", "For a right-handed golfer, assess lead-wrist condition as one part of face control."],
            ["12. Tempo", "Keep the delivery repeatable while adjusting face or path."],
            ["13. Timing", "Coordinate face and path at impact; the gap between them determines the intended curve."],
            ["14. Rhythm", "Support a repeatable sequence; reassess the measured start line and curve after each change."],
        ];
        const statusFor = number => focus.has(number) ? "Primary focus" : "Supporting check";
        const lawHTML = laws.map(([title, detail]) =>
            `<div class="sim-analysis-item"><strong>${title}</strong><p>${detail}</p></div>`).join("");
        const principleHTML = principles.map(([title, detail], index) => {
            const number = index + 1;
            return `<div class="sim-analysis-item ${focus.has(number) ? "is-primary" : ""}"><strong>${title}</strong><small>${statusFor(number)}</small><p>${detail}</p></div>`;
        }).join("");
        const results = document.getElementById("laws-principles-results");
        results.innerHTML = `
            <div class="sim-analysis-note">
                <h3>${pattern} · right-handed interpretation</h3>
                <p>Start: ${angleLabel(input.launch_direction)} · Face-to-path: ${angleLabel(f2p)} · ${input.spin_axis === null ? "Estimated" : "Entered"} spin axis: ${angleLabel(axis)}. This pattern starts ${input.launch_direction < -0.5 ? "left" : input.launch_direction > 0.5 ? "right" : "near target"} and is expected to curve ${axis < -1 ? "left" : axis > 1 ? "right" : "very little"}.</p>
                <p><strong>Coaching priority:</strong> ${faceNote} ${pathNote}</p>
            </div>
            <div><h3>The six laws</h3><div class="sim-analysis-grid">${lawHTML}</div></div>
            <div><h3>The fourteen principles</h3><div class="sim-analysis-grid">${principleHTML}</div></div>
            <p class="simulator-disclaimer">This is an estimated ball-flight interpretation, not a diagnosis of swing faults. Contact location, attack angle, and dynamic loft are not supplied here. Confirm a change with video and measured shots.</p>`;
        document.getElementById("laws-analysis-title").scrollIntoView({ behavior: "smooth", block: "start" });
    }

    document.getElementById("analyze-laws-principles").addEventListener("click", analyzeLawsAndPrinciples);
    document.getElementById("clear-flight-metrics").addEventListener("click", () => {
        form.reset();
        carryNeedsSync = false;
        rolloutAllowance = 20;
        lastEstimateKey = estimateKey(readInputs());
        refreshFaceToPath();
        updateFlight(false);
        document.getElementById("laws-principles-results").innerHTML =
            "<p>Metrics reset to the demo starting values. Enter a shot and select <strong>Analyze Laws &amp; Principles</strong> to see the coaching interpretation.</p>";
    });

    form.addEventListener("submit", event => {
        event.preventDefault();
        syncTotalFromCarry();
        const current = readInputs();
        updateFlight(estimateKey(current) !== lastEstimateKey);
    });
    window.addEventListener("resize", draw);
    draw();
})();
