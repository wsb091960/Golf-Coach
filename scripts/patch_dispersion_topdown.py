from pathlib import Path

path = Path("app/static/js/session_performance.js")
text = path.read_text(encoding="utf-8")

start = text.find("function drawDispersion(selectedShot) {")
end = text.find("\n    function drawFacePath(", start)

if start == -1 or end == -1:
    raise SystemExit("Could not locate drawDispersion() in session_performance.js.")

replacement = '''function drawDispersion(selectedShot) {
        const ctx = clearCanvas(dispersionCanvas);
        if (!ctx) return;

        const w = dispersionCanvas.width;
        const h = dispersionCanvas.height;

        const padLeft = 54;
        const padRight = 24;
        const padTop = 30;
        const padBottom = 44;

        if (!includedShots.length) {
            ctx.fillStyle = "#73817b";
            ctx.font = "16px system-ui";
            ctx.fillText("No included shots", 28, 48);
            return;
        }

        const points = includedShots.map((shot) => {
            const carry = finite(shot.carry_distance) || 0;
            return {
                shot,
                carry,
                lateral: finalOffline(shot, carry),
            };
        });

        const carries = points.map(p => p.carry);
        const laterals = points.map(p => p.lateral);

        const minCarryRaw = Math.min(...carries);
        const maxCarryRaw = Math.max(...carries);

        const carryPadding = Math.max(
            5,
            (maxCarryRaw - minCarryRaw) * 0.35
        );

        const minCarry = Math.max(0, minCarryRaw - carryPadding);
        const maxCarry = maxCarryRaw + carryPadding;

        const maxAbsLateral = Math.max(
            10,
            ...laterals.map(v => Math.abs(v))
        );

        const lateralLimit = Math.ceil(maxAbsLateral * 1.30);

        const plotWidth = w - padLeft - padRight;
        const plotHeight = h - padTop - padBottom;

        const xFor = lateral =>
            padLeft +
            ((lateral + lateralLimit) / (lateralLimit * 2)) *
            plotWidth;

        const yFor = carry => {
            const range = Math.max(1, maxCarry - minCarry);
            return (
                padTop +
                (1 - (carry - minCarry) / range) *
                plotHeight
            );
        };

        ctx.save();
        ctx.strokeStyle = "#dfe7e3";
        ctx.fillStyle = "#718079";
        ctx.lineWidth = 1;
        ctx.font = "10px system-ui";

        for (let i = 0; i <= 8; i += 1) {
            const lateral =
                -lateralLimit +
                (lateralLimit * 2) * (i / 8);

            const x = xFor(lateral);

            ctx.beginPath();
            ctx.moveTo(x, padTop);
            ctx.lineTo(x, h - padBottom);
            ctx.stroke();

            if (i === 0 || i === 4 || i === 8) {
                ctx.fillText(
                    Math.abs(Math.round(lateral)) + " yd",
                    x - 15,
                    h - 13
                );
            }
        }

        for (let i = 0; i <= 4; i += 1) {
            const carry =
                minCarry +
                (maxCarry - minCarry) * (i / 4);

            const y = yFor(carry);

            ctx.beginPath();
            ctx.moveTo(padLeft, y);
            ctx.lineTo(w - padRight, y);
            ctx.stroke();

            ctx.fillText(
                carry.toFixed(0) + " yd",
                7,
                y + 3
            );
        }

        ctx.restore();

        const centerX = xFor(0);

        ctx.save();
        ctx.strokeStyle = "#6d8179";
        ctx.lineWidth = 2;
        ctx.setLineDash([7, 6]);
        ctx.beginPath();
        ctx.moveTo(centerX, padTop);
        ctx.lineTo(centerX, h - padBottom);
        ctx.stroke();
        ctx.restore();

        ctx.fillStyle = "#718079";
        ctx.font = "10px system-ui";
        ctx.fillText("LEFT", padLeft, 17);
        ctx.fillText("TARGET", centerX - 18, 17);
        ctx.fillText("RIGHT", w - padRight - 36, 17);

        points.forEach(({ shot, carry, lateral }) => {
            const x = xFor(lateral);
            const y = yFor(carry);
            const selected =
                selectedShot &&
                shot.id === selectedShot.id;

            if (selected) {
                ctx.strokeStyle = "#153f34";
                ctx.lineWidth = 3;
                ctx.beginPath();
                ctx.arc(x, y, 10, 0, Math.PI * 2);
                ctx.stroke();
            }

            ctx.fillStyle = selected ? "#153f34" : "#5d9282";
            ctx.beginPath();
            ctx.arc(x, y, selected ? 6 : 5, 0, Math.PI * 2);
            ctx.fill();

            ctx.fillStyle = "#31463f";
            ctx.font = "9px system-ui";
            ctx.fillText(
                String(shot.shot_number || ""),
                x + 7,
                y - 7
            );
        });

        const meanLateral =
            laterals.reduce((sum, v) => sum + v, 0) /
            laterals.length;

        const meanCarry =
            carries.reduce((sum, v) => sum + v, 0) /
            carries.length;

        const meanX = xFor(meanLateral);
        const meanY = yFor(meanCarry);

        ctx.strokeStyle = "#183d34";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(meanX - 8, meanY);
        ctx.lineTo(meanX + 8, meanY);
        ctx.moveTo(meanX, meanY - 8);
        ctx.lineTo(meanX, meanY + 8);
        ctx.stroke();

        ctx.fillStyle = "#31463f";
        ctx.font = "10px system-ui";
        ctx.fillText(
            `Avg ${meanCarry.toFixed(1)} yd / ${meanLateral.toFixed(1)} yd offline`,
            padLeft,
            h - 28
        );
    }
'''

text = text[:start] + replacement + text[end:]
path.write_text(text, encoding="utf-8")
print("Updated dispersion plot.")
