(() => {
    const dataNode = document.getElementById("session-shot-data");
    if (!dataNode) return;

    const primaryClub = dataNode.dataset.primaryClub || "Club"; 
    const isLeftHanded = String(dataNode.dataset.handedness || "").toLowerCase().includes("left");

    let shots = [];
    try {
        shots = JSON.parse(dataNode.textContent || "[]");
    } catch (error) {
        console.error("Could not parse session shot data.", error);
        return;
    }

    const includedShots = shots.filter(shot => shot.included !== false);

    const flightCanvas = document.getElementById("flight-canvas");
    const simulatorCanvas = document.getElementById("shot-simulator-canvas");
    const topDownCanvas = document.getElementById("topdown-flight-canvas");
    const dispersionCanvas = document.getElementById("dispersion-canvas");
    const facePathCanvas = document.getElementById("face-path-canvas");

    const selectedTitle = document.getElementById("selected-shot-title");
    const selectedShape = document.getElementById("selected-shape");

    const metricUnits = {
        carry_distance: " yd",
        total_distance: " yd",
        ball_speed: " mph",
        club_speed: " mph",
        smash_factor: "",
        launch_angle: "°",
        launch_direction: "°",
        attack_angle: "°",
        spin_rate: " rpm",
        club_path: "°",
        club_face: "°",
        face_to_path: "°",
        offline_distance: " yd",
    };

    function finite(value) {
    if (
        value === null ||
        value === undefined ||
        value === ""
    ) {
        return null;
    }

    const n = Number(value);

    return Number.isFinite(n) ? n : null;
}

    function fmt(value, digits = 1) {
        const n = finite(value);
        return n === null ? "—" : n.toFixed(digits);
    }

    function clearCanvas(canvas) {
        if (!canvas) return null;
        const ctx = canvas.getContext("2d");
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        const variant = canvas.id === 'topdown-flight-canvas'
            ? 'topdown'
            : canvas.id === 'dispersion-canvas'
                ? 'dispersion'
                : 'range';
        drawRangeBackdrop(canvas, ctx, variant);
        return ctx;
    }

    function graphFont(canvas, size, weight = 600) {
        // Canvas drawing coordinates use the intrinsic buffer, which may be
        // wider than the responsive CSS display. Compensate so text retains
        // the requested readable CSS-pixel size instead of being squeezed.
        const displayedWidth = canvas.clientWidth || canvas.width;
        const scale = Math.max(1, canvas.width / displayedWidth);
        return `${weight} ${Math.round(size * scale)}px system-ui, sans-serif`;
    }

    function drawRangeBackdrop(canvas, ctx, variant = "range") {
        const w = canvas.width;
        const h = canvas.height;

        if (variant === "dispersion") {
            const rough = ctx.createLinearGradient(0, 0, 0, h);
            rough.addColorStop(0, "#315c36");
            rough.addColorStop(1, "#173823");
            ctx.fillStyle = rough;
            ctx.fillRect(0, 0, w, h);

            ctx.save();
            ctx.fillStyle = "rgba(8,39,23,.72)";
            for (let y = 25; y < h; y += 42) {
                ctx.beginPath(); ctx.arc(24 + (y % 17), y, 22, 0, Math.PI * 2); ctx.fill();
                ctx.beginPath(); ctx.arc(w - 24 - (y % 13), y + 8, 24, 0, Math.PI * 2); ctx.fill();
            }
            ctx.restore();

            const rangePath = new Path2D();
            rangePath.moveTo(w * .39, h);
            rangePath.lineTo(w * .22, 0);
            rangePath.lineTo(w * .78, 0);
            rangePath.lineTo(w * .61, h);
            rangePath.closePath();
            const field = ctx.createLinearGradient(0, 0, w, 0);
            field.addColorStop(0, "#638846");
            field.addColorStop(.5, "#8eae57");
            field.addColorStop(1, "#638846");
            ctx.fillStyle = field;
            ctx.fill(rangePath);
            ctx.save();
            ctx.clip(rangePath);
            for (let y = 0, band = 0; y < h; y += 44, band += 1) {
                ctx.fillStyle = band % 2 ? "rgba(255,255,220,.06)" : "rgba(24,70,34,.07)";
                ctx.fillRect(0, y, w, 44);
            }
            ctx.restore();
            ctx.strokeStyle = "rgba(218,233,169,.34)"; ctx.lineWidth = 3; ctx.stroke(rangePath);

            ctx.fillStyle = "rgba(125,163,78,.95)";
            ctx.fillRect(w * .38, h - 43, w * .24, 36);
            ctx.strokeStyle = "rgba(230,240,188,.5)"; ctx.lineWidth = 2;
            ctx.strokeRect(w * .38, h - 43, w * .24, 36);
            ctx.fillStyle = "#f7f1d7";
            for (const x of [w * .44, w * .50, w * .56]) { ctx.beginPath(); ctx.arc(x, h - 25, 4, 0, Math.PI * 2); ctx.fill(); }

            ctx.strokeStyle = "rgba(255,255,255,.16)"; ctx.lineWidth = 1;
            ctx.strokeRect(.5, .5, w - 1, h - 1);
            return;
        }

        if (variant === "topdown") {
            const rough = ctx.createLinearGradient(0, 0, 0, h);
            rough.addColorStop(0, "#315b35");
            rough.addColorStop(.55, "#244a2e");
            rough.addColorStop(1, "#173923");
            ctx.fillStyle = rough;
            ctx.fillRect(0, 0, w, h);

            // Tree lines frame the hole without competing with the data.
            ctx.save();
            ctx.fillStyle = "rgba(9,42,25,.72)";
            for (let y = 28; y < h; y += 38) {
                const radius = 20 + ((y / 38) % 3) * 3;
                ctx.beginPath(); ctx.arc(24 + (y % 22), y, radius, 0, Math.PI * 2); ctx.fill();
                ctx.beginPath(); ctx.arc(w - 24 - (y % 19), y + 7, radius + 2, 0, Math.PI * 2); ctx.fill();
            }
            ctx.restore();

            const fairwayPath = new Path2D();
            fairwayPath.moveTo(w * .43, h);
            fairwayPath.bezierCurveTo(w * .31, h * .78, w * .26, h * .45, w * .36, 58);
            fairwayPath.quadraticCurveTo(w * .50, 24, w * .64, 58);
            fairwayPath.bezierCurveTo(w * .76, h * .43, w * .70, h * .78, w * .57, h);
            fairwayPath.closePath();
            const fairway = ctx.createLinearGradient(0, 0, w, 0);
            fairway.addColorStop(0, "#648b45");
            fairway.addColorStop(.5, "#8bad55");
            fairway.addColorStop(1, "#5f8642");
            ctx.fillStyle = fairway;
            ctx.fill(fairwayPath);

            ctx.save();
            ctx.clip(fairwayPath);
            for (let y = 0, band = 0; y < h; y += 48, band += 1) {
                ctx.fillStyle = band % 2 ? "rgba(255,255,210,.055)" : "rgba(21,70,34,.065)";
                ctx.fillRect(0, y, w, 48);
            }
            ctx.restore();
            ctx.strokeStyle = "rgba(207,226,150,.34)";
            ctx.lineWidth = 3;
            ctx.stroke(fairwayPath);

            // Target green, bunkers and flag.
            ctx.fillStyle = "#9fbd63";
            ctx.beginPath(); ctx.ellipse(w * .5, 58, w * .145, 45, 0, 0, Math.PI * 2); ctx.fill();
            ctx.strokeStyle = "rgba(224,239,176,.5)"; ctx.lineWidth = 2; ctx.stroke();
            ctx.fillStyle = "#d9c995";
            ctx.beginPath(); ctx.ellipse(w * .34, 70, 43, 18, -.28, 0, Math.PI * 2); ctx.fill();
            ctx.beginPath(); ctx.ellipse(w * .66, 82, 48, 19, .32, 0, Math.PI * 2); ctx.fill();
            ctx.strokeStyle = "#f7f1d7"; ctx.lineWidth = 3;
            ctx.beginPath(); ctx.moveTo(w * .5, 67); ctx.lineTo(w * .5, 29); ctx.stroke();
            ctx.fillStyle = "#d7a62a";
            ctx.beginPath(); ctx.moveTo(w * .5, 29); ctx.lineTo(w * .5 + 27, 38); ctx.lineTo(w * .5, 46); ctx.closePath(); ctx.fill();

            // Tee box at the origin.
            ctx.fillStyle = "rgba(132,169,83,.94)";
            ctx.fillRect(w * .43, h - 44, w * .14, 38);
            ctx.strokeStyle = "rgba(222,235,176,.45)"; ctx.lineWidth = 2;
            ctx.strokeRect(w * .43, h - 44, w * .14, 38);
            ctx.fillStyle = "#f7f1d7";
            ctx.beginPath(); ctx.arc(w * .47, h - 25, 4, 0, Math.PI * 2); ctx.fill();
            ctx.beginPath(); ctx.arc(w * .53, h - 25, 4, 0, Math.PI * 2); ctx.fill();

            ctx.strokeStyle = "rgba(255,255,255,.16)";
            ctx.lineWidth = 1;
            ctx.strokeRect(.5, .5, w - 1, h - 1);
            return;
        }

        const gradient = ctx.createLinearGradient(0, 0, 0, h);
        gradient.addColorStop(0, "#617d42");
        gradient.addColorStop(0.55, "#405f35");
        gradient.addColorStop(1, "#253d2b");
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, w, h);

        ctx.save();
        ctx.globalAlpha = 0.16;
        const stripeWidth = Math.max(34, w / 14);
        for (let x = -stripeWidth; x < w + stripeWidth; x += stripeWidth) {
            ctx.fillStyle = (Math.round(x / stripeWidth) % 2) ? "#a8bf75" : "#304c2d";
            ctx.fillRect(x, 0, stripeWidth, h);
        }
        ctx.restore();

        ctx.strokeStyle = "rgba(255,255,255,.13)";
        ctx.lineWidth = 1;
        ctx.strokeRect(.5, .5, w - 1, h - 1);
    }

    function drawGrid(ctx, width, height, xSteps = 10, ySteps = 5) {
        ctx.save();
        ctx.strokeStyle = "rgba(255,255,255,.14)";
        ctx.lineWidth = 1;

        for (let i = 0; i <= xSteps; i += 1) {
            const x = (i / xSteps) * width;
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x, height);
            ctx.stroke();
        }

        for (let i = 0; i <= ySteps; i += 1) {
            const y = (i / ySteps) * height;
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(width, y);
            ctx.stroke();
        }

        ctx.restore();
    }

    function estimatedApexFeet(shot) {
        const measured = finite(shot.apex_height);
        if (measured !== null && measured > 0) return measured;

        const carry = finite(shot.carry_distance);
        if (!(carry > 0)) return null;
        const launch = finite(shot.launch_angle);

        if (launch !== null) {
            return Math.max(
                36,
                carry *
                Math.tan(Math.max(3, launch) * Math.PI / 180) *
                0.84
            );
        }

        return Math.max(36, carry * 0.66);
    }

    function drawFlight(selectedShot) {
        const ctx = clearCanvas(flightCanvas);
        if (!ctx) return;
        flightCanvas._selectedShot = selectedShot || null;
        const button = document.getElementById("pga-tour-overlay-toggle");
        const cohortButton = document.getElementById("senior-overlay-toggle");
        if (button && !button.dataset.ready) {
            button.dataset.ready = "1";
            button.addEventListener("click", () => {
                const showing = flightCanvas.dataset.pgaOverlay === "true";
                flightCanvas.dataset.pgaOverlay = showing ? "false" : "true";
                button.setAttribute("aria-pressed", showing ? "false" : "true");
                button.textContent = showing ? "Show PGA Tour" : "Hide PGA Tour";
                drawFlight(flightCanvas._selectedShot);
            });
        }
        if (cohortButton && !cohortButton.dataset.ready) {
            cohortButton.dataset.ready = "1";
            cohortButton.addEventListener("click", () => {
                const showing = flightCanvas.dataset.seniorOverlay === "true";
                flightCanvas.dataset.seniorOverlay = showing ? "false" : "true";
                cohortButton.setAttribute("aria-pressed", showing ? "false" : "true");
                cohortButton.textContent = showing ? "Show 65yo · 10 HCP" : "Hide 65yo · 10 HCP";
                drawFlight(flightCanvas._selectedShot);
            });
        }
        const valueNumber = value => {
            if (value === null || value === undefined || value === "") return null;
            const parsed = Number(value);
            return Number.isFinite(parsed) ? parsed : null;
        };
        const tourData = {
            driver:{carry:282,apex:35},"3 wood":{carry:249,apex:34},"5 wood":{carry:236,apex:33},
            "3 iron":{carry:217,apex:34},"4 iron":{carry:209,apex:34},"5 iron":{carry:198,apex:33},
            "6 iron":{carry:186,apex:33},"7 iron":{carry:176,apex:32},"8 iron":{carry:164,apex:31},
            "9 iron":{carry:152,apex:31},"pitching wedge":{carry:141,apex:32}
        };
        const cohortData = {
            driver:{carry:202,apex:25},"3 wood":{carry:185,apex:26},"5 wood":{carry:174,apex:26},
            "3 iron":{carry:158,apex:26},"4 iron":{carry:150,apex:26},"5 iron":{carry:143,apex:26},
            "6 iron":{carry:135,apex:25},"7 iron":{carry:127,apex:25},"8 iron":{carry:119,apex:24},
            "9 iron":{carry:110,apex:24},"pitching wedge":{carry:100,apex:23}
        };
        const clubKey = value => {
            let key=String(value||"").toLowerCase().replace(/[-_]/g," ").replace(/\s+/g," ").trim();
            key=key.replace(/^([3-9])i$/, "$1 iron").replace(/^([357])w$/, "$1 wood");
            if(key==="pw"||key==="p wedge")key="pitching wedge";
            if(key.includes("driver"))key="driver";
            const match=key.match(/([3-9])\s*(iron|wood)/);if(match)key=`${match[1]} ${match[2]}`;
            return key;
        };
        const benchmark = selectedShot ? tourData[clubKey(selectedShot.club)] || null : null;
        const cohortBenchmark = selectedShot ? cohortData[clubKey(selectedShot.club)] || null : null;
        if (button) {
            button.disabled = Boolean(selectedShot && !benchmark);
            button.title = benchmark ? "TrackMan 2023 PGA Tour average" : "No PGA Tour benchmark for this club";
        }
        if (cohortButton) {
            cohortButton.disabled = Boolean(selectedShot && !cohortBenchmark);
            cohortButton.title = cohortBenchmark ? "65yo · 10 HCP modeled cohort" : "No cohort benchmark for this club";
        }
        const w=flightCanvas.width,h=flightCanvas.height;
        if(!selectedShot){ctx.fillStyle="#edf6e9";ctx.font=graphFont(flightCanvas,16,650);ctx.fillText("Select a shot below",35,55);return;}
        const carry=valueNumber(selectedShot.carry_distance);
        if (!(carry > 0)) {
            ctx.fillStyle="#edf6e9";
            ctx.font=graphFont(flightCanvas,18,750);
            ctx.fillText("Carry unavailable",35,58);
            ctx.font=graphFont(flightCanvas,13,600);
            ctx.fillText("Enter ball speed or club speed to calculate an estimate.",35,86);
            return;
        }
        const total=valueNumber(selectedShot.total_distance)||carry;
        let apexFt=valueNumber(selectedShot.apex_height);
        if(!(apexFt>0)){const launch=valueNumber(selectedShot.launch_angle);const apexYards=launch!==null?Math.max(4,carry*Math.tan(Math.max(3,launch)*Math.PI/180)*.28):Math.max(4,carry*.22);apexFt=apexYards*3;}
        const showTour=flightCanvas.dataset.pgaOverlay==="true"&&benchmark;
        const showCohort=flightCanvas.dataset.seniorOverlay==="true"&&cohortBenchmark;
        const apexYd=apexFt/3,tourCarry=showTour?benchmark.carry:0,tourApexYd=showTour?benchmark.apex:0,cohortCarry=showCohort?cohortBenchmark.carry:0,cohortApexYd=showCohort?cohortBenchmark.apex:0;
        const L=58,R=26,G=h-48,T=28,maxX=Math.max(carry,total,tourCarry,cohortCarry)*1.08,maxY=Math.max(10,apexYd*1.25,tourApexYd*1.25,cohortApexYd*1.25),scale=Math.min((w-L-R)/maxX,(G-T)/maxY),plotRight=L+maxX*scale,plotTop=G-maxY*scale;
        ctx.fillStyle="rgba(116,151,76,.62)";ctx.fillRect(L,plotTop,plotRight-L,G-plotTop);ctx.strokeStyle="rgba(255,255,255,.15)";ctx.fillStyle="#edf6e9";ctx.lineWidth=1;ctx.font=graphFont(flightCanvas,12,600);
        const xStep=maxX>220?50:maxX>100?25:10;for(let d=0;d<=maxX;d+=xStep){const x=L+d*scale;ctx.beginPath();ctx.moveTo(x,plotTop);ctx.lineTo(x,G);ctx.stroke();const tick=`${d} yd`;ctx.fillText(tick,Math.max(L,Math.min(w-R-ctx.measureText(tick).width,x-12)),G+20);}
        const yStep=maxY>35?10:5;for(let y=0;y<=maxY;y+=yStep){const py=G-y*scale;ctx.beginPath();ctx.moveTo(L,py);ctx.lineTo(plotRight,py);ctx.stroke();if(y)ctx.fillText(`${y} yd`,8,py+3);}
        ctx.strokeStyle="rgba(245,242,207,.72)";ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(L,G);ctx.lineTo(plotRight,G);ctx.stroke();
        ctx.strokeStyle="#f8fff4";ctx.lineWidth=4;ctx.setLineDash([]);ctx.beginPath();for(let i=0;i<=90;i++){const q=i/90,x=L+carry*q*scale,y=G-(4*apexYd*q*(1-q))*scale;i?ctx.lineTo(x,y):ctx.moveTo(x,y);}ctx.stroke();
        if(total>carry){ctx.save();ctx.setLineDash([8,7]);ctx.strokeStyle="#789088";ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(L+carry*scale,G);ctx.lineTo(L+total*scale,G);ctx.stroke();ctx.restore();}
        if(showTour){ctx.save();ctx.strokeStyle="#c48a22";ctx.lineWidth=4;ctx.setLineDash([12,8]);ctx.beginPath();for(let i=0;i<=100;i++){const q=i/100,x=L+tourCarry*q*scale,y=G-(4*tourApexYd*q*(1-q))*scale;i?ctx.lineTo(x,y):ctx.moveTo(x,y);}ctx.stroke();ctx.restore();ctx.fillStyle="#9a6814";ctx.font=graphFont(flightCanvas,13,650);ctx.fillText(`PGA Tour ${tourCarry} yd · ${Math.round(tourApexYd*3)} ft`,Math.min(plotRight-175,L+tourCarry*.56*scale),Math.max(plotTop+16,G-tourApexYd*scale-10));}
        if(showCohort){ctx.save();ctx.strokeStyle="#4d74a8";ctx.lineWidth=4;ctx.setLineDash([4,7]);ctx.beginPath();for(let i=0;i<=100;i++){const q=i/100,x=L+cohortCarry*q*scale,y=G-(4*cohortApexYd*q*(1-q))*scale;i?ctx.lineTo(x,y):ctx.moveTo(x,y);}ctx.stroke();ctx.restore();ctx.fillStyle="#365d92";ctx.font=graphFont(flightCanvas,13,650);ctx.fillText(`65yo · 10 HCP ${cohortCarry} yd · ${Math.round(cohortApexYd*3)} ft`,Math.min(plotRight-205,L+cohortCarry*.54*scale),Math.max(plotTop+32,G-cohortApexYd*scale+16));}
        ctx.fillStyle="#ffffff";ctx.font=graphFont(flightCanvas,14,700);
        const carryLabel=`Carry ${carry.toFixed(1)} yd`,apexLabel=`Apex ${apexFt.toFixed(0)} ft`;
        const clampLabel=(label,x)=>Math.max(L+4,Math.min(w-R-ctx.measureText(label).width-4,x));
        ctx.fillText(carryLabel,clampLabel(carryLabel,L+carry*scale-50),G-14);
        ctx.fillText(apexLabel,clampLabel(apexLabel,L+carry*.5*scale+10),Math.max(plotTop+18,G-apexYd*scale-10));
    }

    function startDirectionAtCarry(shot, carry) {
        const launchDirection = finite(shot.launch_direction);
        if (launchDirection !== null) return Math.tan(launchDirection * Math.PI / 180) * carry;
        const face = finite(shot.club_face);
        if (face !== null) return Math.tan(face * Math.PI / 180) * carry;
        return 0;
    }

    function curveInfluence(shot, carry) {
        const axis = finite(shot.spin_axis);
        if (axis !== null) return Math.max(-25, Math.min(25, axis)) * Math.max(0.25, carry / 180);
        const ftp = finite(shot.face_to_path);
        if (ftp !== null) return Math.max(-12, Math.min(12, ftp)) * Math.max(0.4, carry / 130);
        return 0;
    }

    function finalOffline(shot, carry) {
        const measured = finite(shot.offline_distance);
        if (measured !== null) return measured;
        return startDirectionAtCarry(shot, carry) + curveInfluence(shot, carry);
    }

    function lateralAt(shot, t, carry) {
        const startEnd = startDirectionAtCarry(shot, carry);
        const landing = finalOffline(shot, carry);

        // A quadratic bend preserves the measured initial start direction and
        // adds curvature continuously in one direction—no artificial S-bend.
        return (startEnd * t) + ((landing - startEnd) * t * t);
    }

    const simulator = {
        shot: null,
        camera: "behind",
        speed: 1,
        progress: 0,
        playing: false,
        frame: null,
        lastTime: 0,
    };

    function simulatorMode(shot) {
        if (!shot) return "—";
        const source = String(shot.source || "").toLowerCase();
        const hasMeasuredFlight = finite(shot.launch_angle) !== null && finite(shot.spin_rate) !== null;
        return source.includes("estimated") || !hasMeasuredFlight ? "Estimated" : "Measured";
    }

    function simulatorPoint(shot, progress) {
        const carry = Math.max(0, finite(shot.carry_distance) || 0);
        const total = Math.max(carry, finite(shot.total_distance) || carry);
        const apexYards = Math.max(4, (estimatedApexFeet(shot) || 36) / 3);
        const landing = finalOffline(shot, carry);
        const flightEnd = .76;
        const bounceEnd = .89;
        let forward;
        let lateral;
        let height;
        let phase;

        if (progress <= flightEnd) {
            const t = progress / flightEnd;
            forward = carry * t;
            lateral = lateralAt(shot, t, carry);
            height = 4 * apexYards * t * (1 - t);
            phase = t < .08 ? "Launch" : t < .88 ? "In flight" : "Descending";
        } else if (progress <= bounceEnd) {
            const t = (progress - flightEnd) / (bounceEnd - flightEnd);
            forward = carry + (total - carry) * .34 * t;
            lateral = landing;
            height = apexYards * .055 * Math.sin(Math.PI * Math.min(1, t * 1.7)) * (1 - t);
            phase = "Bounce";
        } else {
            const t = (progress - bounceEnd) / (1 - bounceEnd);
            forward = carry + (total - carry) * (.34 + .66 * t);
            lateral = landing;
            height = 0;
            phase = progress >= 1 ? "Finished" : "Roll";
        }
        return { carry, total, apexYards, landing, forward, lateral, height, phase };
    }

    function simulatorProjection(camera, point, bounds) {
        const { w, h, maxDistance, lateralLimit, apexYards } = bounds;
        const distanceRatio = Math.max(0, Math.min(1, point.forward / maxDistance));
        if (camera === "side") {
            const left = 52;
            const right = w - 34;
            const ground = h - 60;
            return {
                x: left + distanceRatio * (right - left),
                y: ground - (point.height / Math.max(apexYards * 1.18, 14)) * (h - 145),
                groundY: ground,
                scale: .85 + distanceRatio * .2,
            };
        }
        if (camera === "overhead") {
            const top = 46;
            const bottom = h - 48;
            return {
                x: w / 2 + (point.lateral / lateralLimit) * (w * .42),
                y: bottom - distanceRatio * (bottom - top),
                groundY: bottom - distanceRatio * (bottom - top),
                scale: .9,
            };
        }
        const horizon = 112;
        const ground = h - 54;
        const depth = Math.pow(distanceRatio, .72);
        const perspectiveWidth = w * (.44 - depth * .25);
        const liftScale = (h - 175) / Math.max(apexYards * 1.22, 14);
        return {
            x: w / 2 + (point.lateral / lateralLimit) * perspectiveWidth,
            y: ground - depth * (ground - horizon) - point.height * liftScale * (.72 + depth * .28),
            groundY: ground - depth * (ground - horizon),
            scale: 1.15 - depth * .5,
        };
    }

    function drawSimulatorBackdrop(ctx, camera, bounds) {
        const { w, h, maxDistance, lateralLimit } = bounds;
        const sky = ctx.createLinearGradient(0, 0, 0, h * .46);
        sky.addColorStop(0, "#b9d7c7");
        sky.addColorStop(1, "#e9efe2");
        ctx.fillStyle = sky;
        ctx.fillRect(0, 0, w, h);

        if (camera === "side") {
            const ground = h - 60;
            const turf = ctx.createLinearGradient(0, ground - 70, 0, h);
            turf.addColorStop(0, "#6f964a"); turf.addColorStop(1, "#274a31");
            ctx.fillStyle = turf; ctx.fillRect(0, ground - 12, w, h - ground + 12);
            ctx.fillStyle = "#173b2a";
            for (let x = 0; x < w; x += 42) { ctx.beginPath(); ctx.arc(x, ground - 9, 34, Math.PI, 0); ctx.fill(); }
            ctx.strokeStyle = "rgba(255,255,255,.42)"; ctx.fillStyle = "#315f3d"; ctx.lineWidth = 1;
            ctx.font = graphFont(simulatorCanvas, 11, 750); ctx.textAlign = "center";
            for (let d = 50; d < maxDistance; d += 50) {
                const x = 52 + (d / maxDistance) * (w - 86);
                ctx.beginPath(); ctx.moveTo(x, ground - 14); ctx.lineTo(x, ground + 10); ctx.stroke();
                ctx.fillStyle = "#edf6e9"; ctx.fillText(`${d}`, x, ground + 30);
            }
            return;
        }

        if (camera === "overhead") {
            const rough = ctx.createLinearGradient(0, 0, 0, h);
            rough.addColorStop(0, "#315b35"); rough.addColorStop(1, "#173923");
            ctx.fillStyle = rough; ctx.fillRect(0, 0, w, h);
            const fairway = new Path2D();
            fairway.moveTo(w * .39, h); fairway.lineTo(w * .25, 0); fairway.lineTo(w * .75, 0); fairway.lineTo(w * .61, h); fairway.closePath();
            ctx.fillStyle = "#70984b"; ctx.fill(fairway);
            ctx.save(); ctx.clip(fairway);
            for (let y = 0, band = 0; y < h; y += 48, band += 1) { ctx.fillStyle = band % 2 ? "rgba(255,255,220,.07)" : "rgba(20,65,30,.08)"; ctx.fillRect(0, y, w, 48); }
            ctx.restore();
            ctx.strokeStyle = "rgba(255,255,255,.62)"; ctx.setLineDash([8, 8]); ctx.lineWidth = 2;
            ctx.beginPath(); ctx.moveTo(w / 2, h - 48); ctx.lineTo(w / 2, 46); ctx.stroke(); ctx.setLineDash([]);
            ctx.fillStyle = "#f0c95c"; ctx.beginPath(); ctx.arc(w / 2, h - 48, 7, 0, Math.PI * 2); ctx.fill();
            return;
        }

        const horizon = 112;
        ctx.fillStyle = "#153c29";
        for (let x = -20; x < w + 30; x += 46) {
            const r = 30 + ((x / 46) % 3) * 4;
            ctx.beginPath(); ctx.arc(x, horizon + 7, r, Math.PI, 0); ctx.fill();
        }
        const grass = ctx.createLinearGradient(0, horizon, 0, h);
        grass.addColorStop(0, "#789d4f"); grass.addColorStop(1, "#294b31");
        ctx.fillStyle = grass; ctx.fillRect(0, horizon, w, h - horizon);
        ctx.save();
        for (let band = 0; band < 8; band += 1) {
            const y0 = horizon + Math.pow(band / 8, 1.65) * (h - 54 - horizon);
            const y1 = horizon + Math.pow((band + 1) / 8, 1.65) * (h - 54 - horizon);
            ctx.fillStyle = band % 2 ? "rgba(238,243,190,.07)" : "rgba(19,66,35,.08)";
            ctx.fillRect(0, y0, w, y1 - y0);
        }
        ctx.restore();
        ctx.strokeStyle = "rgba(255,255,255,.34)"; ctx.lineWidth = 2;
        ctx.beginPath(); ctx.moveTo(w / 2, horizon); ctx.lineTo(w / 2, h - 54); ctx.stroke();
        ctx.font = graphFont(simulatorCanvas, 11, 800); ctx.textAlign = "center";
        for (let d = 50; d < maxDistance; d += 50) {
            const depth = Math.pow(d / maxDistance, .72);
            const y = h - 54 - depth * (h - 54 - horizon);
            const half = 24 + depth * 62;
            ctx.strokeStyle = "rgba(255,255,255,.38)";
            ctx.beginPath(); ctx.ellipse(w / 2, y, half, 7 + depth * 5, 0, 0, Math.PI * 2); ctx.stroke();
            ctx.fillStyle = "rgba(14,55,34,.78)"; ctx.fillRect(w / 2 - 18, y - 9, 36, 18);
            ctx.fillStyle = "#f3f8ef"; ctx.fillText(String(d), w / 2, y + 4);
        }
        ctx.fillStyle = "#f0c95c"; ctx.beginPath(); ctx.arc(w / 2, h - 54, 8, 0, Math.PI * 2); ctx.fill();
    }

    function updateSimulatorReadout(point, mode) {
        const values = {
            distance: point ? `${point.forward.toFixed(0)} yd` : "—",
            height: point ? `${(point.height * 3).toFixed(0)} ft` : "—",
            offline: point ? `${Math.abs(point.lateral).toFixed(1)} yd${Math.abs(point.lateral) < .05 ? "" : point.lateral < 0 ? " L" : " R"}` : "—",
            mode,
        };
        Object.entries(values).forEach(([key, value]) => {
            const node = document.querySelector(`[data-sim-readout="${key}"]`);
            if (node) node.textContent = value;
        });
    }

    function renderSimulator() {
        if (!simulatorCanvas) return;
        const ctx = simulatorCanvas.getContext("2d");
        const w = simulatorCanvas.width;
        const h = simulatorCanvas.height;
        const shot = simulator.shot;
        const carry = shot ? Math.max(0, finite(shot.carry_distance) || 0) : 0;
        const total = shot ? Math.max(carry, finite(shot.total_distance) || carry) : 0;
        const apexYards = shot ? Math.max(4, (estimatedApexFeet(shot) || 36) / 3) : 12;
        const landing = shot ? finalOffline(shot, carry) : 0;
        const lateralLimit = Math.max(35, Math.ceil(Math.abs(landing) * 1.45 / 10) * 10);
        const bounds = { w, h, maxDistance: Math.max(100, Math.ceil(Math.max(carry, total) * 1.12 / 50) * 50), lateralLimit, apexYards };
        ctx.clearRect(0, 0, w, h);
        drawSimulatorBackdrop(ctx, simulator.camera, bounds);

        if (!shot || !(carry > 0)) {
            ctx.fillStyle = "rgba(10,45,31,.86)"; ctx.fillRect(24, 24, 430, 76);
            ctx.fillStyle = "#ffffff"; ctx.font = graphFont(simulatorCanvas, 18, 800); ctx.textAlign = "left";
            ctx.fillText(shot ? "Carry unavailable" : "Select a shot to start the replay", 42, 57);
            ctx.font = graphFont(simulatorCanvas, 12, 650); ctx.fillStyle = "#dcebe4";
            ctx.fillText(shot ? "Enter ball or club speed to calculate an estimate." : "Choose any row in the shot table.", 42, 82);
            updateSimulatorReadout(null, shot ? simulatorMode(shot) : "—");
            return;
        }

        const steps = Math.max(2, Math.ceil(simulator.progress * 120));
        ctx.save(); ctx.lineCap = "round"; ctx.lineJoin = "round";
        ctx.strokeStyle = "rgba(255,255,255,.22)"; ctx.lineWidth = 9;
        ctx.beginPath();
        for (let i = 0; i <= steps; i += 1) {
            const p = simulatorPoint(shot, simulator.progress * (i / steps));
            const screen = simulatorProjection(simulator.camera, p, bounds);
            if (i) ctx.lineTo(screen.x, screen.y); else ctx.moveTo(screen.x, screen.y);
        }
        ctx.stroke();
        ctx.strokeStyle = "#f8fff4"; ctx.lineWidth = 4; ctx.stroke(); ctx.restore();

        const point = simulatorPoint(shot, simulator.progress);
        const screen = simulatorProjection(simulator.camera, point, bounds);
        if (simulator.camera !== "overhead" && point.height > .1) {
            ctx.save(); ctx.strokeStyle = "rgba(8,38,25,.3)"; ctx.setLineDash([5, 7]); ctx.lineWidth = 2;
            ctx.beginPath(); ctx.moveTo(screen.x, screen.y + 9); ctx.lineTo(screen.x, screen.groundY); ctx.stroke(); ctx.restore();
            ctx.fillStyle = "rgba(8,35,24,.28)"; ctx.beginPath(); ctx.ellipse(screen.x, screen.groundY, 12 * screen.scale, 4 * screen.scale, 0, 0, Math.PI * 2); ctx.fill();
        }
        ctx.shadowColor = "rgba(0,0,0,.32)"; ctx.shadowBlur = 9;
        ctx.fillStyle = "#ffd45b"; ctx.strokeStyle = "#ffffff"; ctx.lineWidth = 3;
        ctx.beginPath(); ctx.arc(screen.x, screen.y, Math.max(6, 9 * screen.scale), 0, Math.PI * 2); ctx.fill(); ctx.stroke();
        ctx.shadowBlur = 0;

        const mode = simulatorMode(shot);
        ctx.fillStyle = "rgba(9,45,31,.88)"; ctx.fillRect(20, 20, 265, 61);
        ctx.fillStyle = "#ffffff"; ctx.font = graphFont(simulatorCanvas, 15, 850); ctx.textAlign = "left";
        ctx.fillText(point.phase.toUpperCase(), 36, 47);
        ctx.fillStyle = mode === "Measured" ? "#dcebe4" : "#ffd45b"; ctx.font = graphFont(simulatorCanvas, 11, 800);
        ctx.fillText(`${mode.toUpperCase()} FLIGHT MODEL`, 36, 68);
        updateSimulatorReadout(point, mode);
    }

    function stopSimulator() {
        simulator.playing = false;
        simulator.lastTime = 0;
        if (simulator.frame) cancelAnimationFrame(simulator.frame);
        simulator.frame = null;
        const pause = document.getElementById("simulator-pause");
        if (pause) { pause.textContent = "Resume"; pause.setAttribute("aria-pressed", "true"); }
    }

    function simulatorTick(time) {
        if (!simulator.playing) return;
        if (!simulator.lastTime) simulator.lastTime = time;
        const delta = Math.min(64, time - simulator.lastTime);
        simulator.lastTime = time;
        simulator.progress = Math.min(1, simulator.progress + (delta / 5200) * simulator.speed);
        renderSimulator();
        if (simulator.progress >= 1) { stopSimulator(); return; }
        simulator.frame = requestAnimationFrame(simulatorTick);
    }

    function playSimulator(restart = false) {
        if (!simulator.shot || !(finite(simulator.shot.carry_distance) > 0)) { renderSimulator(); return; }
        if (restart || simulator.progress >= 1) simulator.progress = 0;
        if (simulator.frame) cancelAnimationFrame(simulator.frame);
        simulator.playing = true;
        simulator.lastTime = 0;
        const pause = document.getElementById("simulator-pause");
        if (pause) { pause.textContent = "Pause"; pause.setAttribute("aria-pressed", "false"); }
        renderSimulator();
        simulator.frame = requestAnimationFrame(simulatorTick);
    }

    function selectSimulatorShot(shot) {
        simulator.shot = shot || null;
        simulator.progress = 0;
        if (!shot) { stopSimulator(); renderSimulator(); return; }
        playSimulator(true);
    }

    document.querySelectorAll("[data-sim-camera]").forEach(button => {
        button.addEventListener("click", () => {
            simulator.camera = button.dataset.simCamera || "behind";
            document.querySelectorAll("[data-sim-camera]").forEach(item => {
                const active = item === button;
                item.classList.toggle("is-active", active);
                item.setAttribute("aria-pressed", active ? "true" : "false");
            });
            renderSimulator();
        });
    });
    const replayButton = document.getElementById("simulator-replay");
    if (replayButton) replayButton.addEventListener("click", () => playSimulator(true));
    const pauseButton = document.getElementById("simulator-pause");
    if (pauseButton) pauseButton.addEventListener("click", () => simulator.playing ? stopSimulator() : playSimulator(false));
    const speedSelect = document.getElementById("simulator-speed");
    if (speedSelect) speedSelect.addEventListener("change", () => { simulator.speed = finite(speedSelect.value) || 1; });

    const chartTabs = Array.from(document.querySelectorAll("[data-chart-tab]"));
    const chartPanels = Array.from(document.querySelectorAll("[data-chart-panel]"));

    function activateChartView(name, focusTab = false) {
        chartTabs.forEach(tab => {
            const active = tab.dataset.chartTab === name;
            tab.classList.toggle("is-active", active);
            tab.setAttribute("aria-selected", active ? "true" : "false");
            tab.tabIndex = active ? 0 : -1;
            if (active && focusTab) tab.focus();
        });
        chartPanels.forEach(panel => {
            const active = panel.dataset.chartPanel === name;
            panel.hidden = !active;
            panel.classList.toggle("is-active", active);
        });
        if (name === "flight") renderSimulator();
        if (name !== "flight" && simulator.playing) stopSimulator();
    }

    chartTabs.forEach((tab, index) => {
        tab.addEventListener("click", () => activateChartView(tab.dataset.chartTab));
        tab.addEventListener("keydown", event => {
            if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
            event.preventDefault();
            let next = index;
            if (event.key === "ArrowRight") next = (index + 1) % chartTabs.length;
            if (event.key === "ArrowLeft") next = (index - 1 + chartTabs.length) % chartTabs.length;
            if (event.key === "Home") next = 0;
            if (event.key === "End") next = chartTabs.length - 1;
            activateChartView(chartTabs[next].dataset.chartTab, true);
        });
    });
    if (chartTabs.length) activateChartView("flight");

    function topDownGeometry(width, top, bottom, sidePad, carry, total, widest) {
        const forwardScale = (bottom - top) / Math.max(carry, total, 1);
        const lateralLimit = Math.max(
            40,
            Math.ceil((Math.max(widest, 1) * 1.2) / 10) * 10
        );
        const lateralScale = (width / 2 - sidePad) / lateralLimit;
        return { forwardScale, lateralScale, lateralLimit };
    }

    function drawTopDownFlight(shot) {
        const ctx=clearCanvas(topDownCanvas);if(!ctx)return;
        const w=topDownCanvas.width,h=topDownCanvas.height,centerX=w/2,top=34,bottom=h-42,sidePad=30;
        ctx.save();ctx.strokeStyle="rgba(255,255,255,.70)";ctx.lineWidth=2;ctx.setLineDash([8,7]);ctx.beginPath();ctx.moveTo(centerX,bottom);ctx.lineTo(centerX,top);ctx.stroke();ctx.restore();
        ctx.fillStyle="#edf6e9";ctx.font=graphFont(topDownCanvas,12,700);ctx.fillText("TARGET LINE",centerX+36,top-5);
        if(!shot)return;
        const carry=finite(shot.carry_distance);
        if (!(carry > 0)) {
            ctx.fillStyle="#edf6e9";
            ctx.font=graphFont(topDownCanvas,18,750);
            ctx.fillText("Carry unavailable",35,58);
            ctx.font=graphFont(topDownCanvas,13,600);
            ctx.fillText("Enter ball speed or club speed to calculate an estimate.",35,86);
            return;
        }
        const total=finite(shot.total_distance)||carry,landing=finalOffline(shot,carry);
        const widest=Math.max(Math.abs(landing),Math.abs(startDirectionAtCarry(shot,carry)));
        const geometry=topDownGeometry(w,top,bottom,sidePad,carry,total,widest);
        const forwardScale=geometry.forwardScale,lateralScale=geometry.lateralScale,lateralLimit=geometry.lateralLimit;
        ctx.save();ctx.strokeStyle="rgba(255,255,255,.18)";ctx.fillStyle="#edf6e9";ctx.lineWidth=1;ctx.font=graphFont(topDownCanvas,11,650);ctx.textAlign="center";ctx.setLineDash([5,8]);
        for(let yards=-lateralLimit;yards<=lateralLimit;yards+=20){
            if(yards===0)continue;
            const x=centerX+yards*lateralScale;
            ctx.beginPath();ctx.moveTo(x,top);ctx.lineTo(x,bottom);ctx.stroke();
            ctx.fillText(`${Math.abs(yards)} ${yards<0?"L":"R"}`,x,h-13);
        }
        ctx.restore();
        ctx.save();ctx.strokeStyle="rgba(255,255,255,.3)";ctx.fillStyle="#f3f8ef";ctx.lineWidth=2;ctx.font=graphFont(topDownCanvas,11,800);ctx.textAlign="right";
        for(let distance=50;distance<Math.max(total,carry);distance+=50){
            const y=bottom-distance*forwardScale;
            if(y<=top+8)continue;
            ctx.beginPath();ctx.moveTo(centerX-16,y);ctx.lineTo(centerX+16,y);ctx.stroke();
            ctx.fillStyle="rgba(15,54,35,.72)";ctx.fillRect(centerX-72,y-9,47,18);
            ctx.fillStyle="#f3f8ef";ctx.fillText(`${distance}`,centerX-31,y+4);
        }
        ctx.restore();
        ctx.fillStyle="#ffd45b";ctx.beginPath();ctx.arc(centerX,bottom,7,0,Math.PI*2);ctx.fill();
        ctx.save();ctx.strokeStyle="#f8fff4";ctx.lineWidth=5;ctx.lineCap="round";ctx.beginPath();
        for(let i=0;i<=100;i++){const t=i/100,x=centerX+lateralAt(shot,t,carry)*lateralScale,y=bottom-carry*t*forwardScale;i?ctx.lineTo(x,y):ctx.moveTo(x,y);}ctx.stroke();ctx.restore();
        const carryX=centerX+landing*lateralScale,carryY=bottom-carry*forwardScale;
        ctx.fillStyle="#ffd45b";ctx.strokeStyle="#ffffff";ctx.lineWidth=3;ctx.beginPath();ctx.arc(carryX,carryY,9,0,Math.PI*2);ctx.fill();ctx.stroke();
        if(total>carry){const totalY=bottom-total*forwardScale;ctx.save();ctx.strokeStyle="#789088";ctx.lineWidth=3;ctx.setLineDash([7,6]);ctx.beginPath();ctx.moveTo(carryX,carryY);ctx.lineTo(carryX,totalY);ctx.stroke();ctx.restore();}
        const offlineSide=Math.abs(landing)<.05?"":landing<0?" L":" R";
        ctx.fillStyle="#ffffff";ctx.font=graphFont(topDownCanvas,14,700);ctx.textAlign="left";ctx.fillText(`Carry ${fmt(carry,1)} yd`,Math.min(w-145,Math.max(12,carryX+12)),Math.max(18,carryY-8));ctx.fillText(`Offline ${Math.abs(landing).toFixed(1)} yd${offlineSide}`,14,28);
        const start=finite(shot.launch_direction);if(start!==null)ctx.fillText(`Start ${start.toFixed(1)}°`,w-115,28);
        ctx.fillStyle="#edf6e9";ctx.font=graphFont(topDownCanvas,12,650);ctx.fillText(shot.shot_shape||"Unknown",14,48);
    }

    function derivedOffline(shot) {
        const offline=finite(shot.offline_distance);
        if(offline!==null)return offline;
        const carry=finite(shot.carry_distance)||0;
        return finalOffline(shot,carry);
    }

    function drawDispersion(selectedShot) {
        const ctx=clearCanvas(dispersionCanvas);if(!ctx)return;
        const w=dispersionCanvas.width,h=dispersionCanvas.height,centerX=w/2,top=34,bottom=h-42,sidePad=38;
        const info=document.getElementById("dispersion-map-info");
        const mapped=includedShots.map((shot,index)=>({
            shot,index,carry:finite(shot.carry_distance),offline:derivedOffline(shot)
        })).filter(item=>item.carry!==null&&item.carry>0&&Number.isFinite(item.offline));
        if(!mapped.length){
            ctx.fillStyle="#edf6e9";ctx.font=graphFont(dispersionCanvas,17,750);ctx.textAlign="left";ctx.fillText("No included shots have carry data yet",32,58);
            ctx.font=graphFont(dispersionCanvas,13,600);ctx.fillText("Add or import shots and they will appear as numbered landing points.",32,84);
            if(info)info.textContent="Included shots from the shot table will appear here.";
            return;
        }

        const maxCarry=Math.max(...mapped.map(item=>item.carry));
        const maxDistance=Math.max(100,Math.ceil((maxCarry*1.12)/50)*50);
        const maxOffline=Math.max(...mapped.map(item=>Math.abs(item.offline)),1);
        const lateralLimit=Math.max(40,Math.ceil((maxOffline*1.25)/10)*10);
        const forwardScale=(bottom-top)/maxDistance;
        const lateralScale=(w/2-sidePad)/lateralLimit;

        ctx.save();ctx.strokeStyle="rgba(255,255,255,.72)";ctx.lineWidth=2;ctx.setLineDash([9,7]);
        ctx.beginPath();ctx.moveTo(centerX,bottom);ctx.lineTo(centerX,top);ctx.stroke();ctx.restore();
        ctx.fillStyle="#edf6e9";ctx.font=graphFont(dispersionCanvas,12,800);ctx.textAlign="left";ctx.fillText("TARGET LINE",centerX+12,top+4);

        ctx.save();ctx.font=graphFont(dispersionCanvas,11,750);ctx.textAlign="center";
        for(let yards=-lateralLimit;yards<=lateralLimit;yards+=20){
            if(yards===0)continue;
            const x=centerX+yards*lateralScale;
            ctx.strokeStyle="rgba(255,255,255,.16)";ctx.lineWidth=1;ctx.setLineDash([5,8]);
            ctx.beginPath();ctx.moveTo(x,top);ctx.lineTo(x,bottom);ctx.stroke();
            ctx.fillStyle="#edf6e9";ctx.fillText(`${Math.abs(yards)} ${yards<0?"L":"R"}`,x,h-13);
        }
        ctx.restore();

        ctx.save();ctx.font=graphFont(dispersionCanvas,11,800);ctx.textAlign="center";
        for(let distance=50;distance<=maxDistance;distance+=50){
            const y=bottom-distance*forwardScale;
            if(y<top-2)continue;
            const ringWidth=distance%100===0?72:48,ringHeight=distance%100===0?18:12;
            ctx.strokeStyle=distance%100===0?"rgba(255,255,255,.38)":"rgba(255,255,255,.22)";
            ctx.lineWidth=2;ctx.setLineDash([6,6]);ctx.beginPath();ctx.ellipse(centerX,y,ringWidth,ringHeight,0,0,Math.PI*2);ctx.stroke();
            ctx.setLineDash([]);ctx.fillStyle="rgba(16,55,35,.76)";ctx.fillRect(centerX-ringWidth-51,y-9,44,18);
            ctx.fillStyle="#f3f8ef";ctx.fillText(`${distance}`,centerX-ringWidth-29,y+4);
        }
        ctx.restore();

        const average=key=>mapped.reduce((sum,item)=>sum+item[key],0)/mapped.length;
        const avgCarry=average("carry"),avgOffline=average("offline");
        const sd=key=>Math.sqrt(mapped.reduce((sum,item)=>sum+Math.pow(item[key]-average(key),2),0)/mapped.length);
        const ellipseX=centerX+avgOffline*lateralScale,ellipseY=bottom-avgCarry*forwardScale;
        const ellipseRx=Math.max(22,sd("offline")*lateralScale*2);
        const ellipseRy=Math.max(13,sd("carry")*forwardScale*2);
        ctx.save();ctx.fillStyle="rgba(215,166,42,.18)";ctx.strokeStyle="rgba(255,212,91,.88)";ctx.lineWidth=3;ctx.setLineDash([8,6]);
        ctx.beginPath();ctx.ellipse(ellipseX,ellipseY,ellipseRx,ellipseRy,0,0,Math.PI*2);ctx.fill();ctx.stroke();ctx.restore();

        // Session average is a gold diamond.
        ctx.save();ctx.translate(ellipseX,ellipseY);ctx.rotate(Math.PI/4);ctx.fillStyle="#d7a62a";ctx.strokeStyle="#ffffff";ctx.lineWidth=2;ctx.fillRect(-7,-7,14,14);ctx.strokeRect(-7,-7,14,14);ctx.restore();

        const palette=["#f8fff4","#ffd45b","#b9e29a","#e6b58d","#d8e7c8","#f0c95c"];
        const clubColors=new Map();
        mapped.forEach(item=>{
            const club=String(item.shot.club||"Club");
            if(!clubColors.has(club))clubColors.set(club,palette[clubColors.size%palette.length]);
            const x=centerX+item.offline*lateralScale,y=bottom-item.carry*forwardScale;
            const selected=selectedShot&&String(selectedShot.id)===String(item.shot.id);
            if(selected){ctx.fillStyle="rgba(255,212,91,.3)";ctx.beginPath();ctx.arc(x,y,17,0,Math.PI*2);ctx.fill();}
            ctx.fillStyle=clubColors.get(club);ctx.strokeStyle=selected?"#ffd45b":"#ffffff";ctx.lineWidth=selected?5:2.5;
            ctx.beginPath();ctx.arc(x,y,selected?11:9,0,Math.PI*2);ctx.fill();ctx.stroke();
            ctx.fillStyle="#173f35";ctx.font=graphFont(dispersionCanvas,10,900);ctx.textAlign="center";ctx.textBaseline="middle";
            ctx.fillText(String(item.shot.shot_number||item.index+1),x,y+.5);
        });

        if(selectedShot){
            const selectedItem=mapped.find(item=>String(item.shot.id)===String(selectedShot.id));
            if(selectedItem){
                const side=Math.abs(selectedItem.offline)<.05?"":selectedItem.offline<0?" L":" R";
                ctx.fillStyle="#ffffff";ctx.font=graphFont(dispersionCanvas,13,800);ctx.textAlign="left";ctx.textBaseline="alphabetic";
                ctx.fillText(`Selected #${selectedItem.shot.shot_number||selectedItem.index+1} · ${selectedItem.carry.toFixed(1)} yd · ${Math.abs(selectedItem.offline).toFixed(1)} yd${side}`,20,27);
            }
        }
        if(info)info.textContent=`${mapped.length} included ${mapped.length===1?"shot":"shots"} from the shot table · Numbered dots = shots · Gold ring = selected · Gold diamond/ellipse = session average and pattern`;
    }

    function drawFacePath(shot) {
        if (!facePathCanvas) return;
        const ctx = facePathCanvas.getContext("2d");
        const w = facePathCanvas.width;
        const h = facePathCanvas.height;
        ctx.clearRect(0, 0, w, h);
        const background = ctx.createLinearGradient(0, 0, 0, h);
        background.addColorStop(0, "#214d3b");
        background.addColorStop(1, "#0d2b23");
        ctx.fillStyle = background;
        ctx.fillRect(0, 0, w, h);

        ctx.save();
        ctx.strokeStyle = "rgba(255,255,255,.08)";
        ctx.lineWidth = 1;
        for (let x = 50; x < w; x += 50) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke(); }
        for (let y = 50; y < h; y += 50) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }
        ctx.restore();

        const impact = { x: w * .5, y: h - 92 };
        ctx.save();
        ctx.strokeStyle = "rgba(255,255,255,.7)";
        ctx.lineWidth = 2;
        ctx.setLineDash([10, 8]);
        ctx.beginPath(); ctx.moveTo(impact.x, 34); ctx.lineTo(impact.x, h - 24); ctx.stroke();
        ctx.restore();
        ctx.fillStyle = "#dcebe4";
        ctx.font = graphFont(facePathCanvas, 12, 800);
        ctx.textAlign = "center";
        ctx.fillText("TARGET LINE", impact.x, 24);

        const summaryNodes = document.querySelectorAll("[data-delivery], [data-delivery-note]");
        if (!shot) {
            ctx.fillStyle = "#edf6e9";
            ctx.font = graphFont(facePathCanvas, 18, 750);
            ctx.textAlign = "left";
            ctx.fillText("Select a shot to view impact geometry", 35, 58);
            summaryNodes.forEach(node => { node.textContent = node.hasAttribute("data-delivery") ? "—" : "Select a shot"; });
            return;
        }

        const path = finite(shot.club_path);
        const face = finite(shot.club_face);
        const attack = finite(shot.attack_angle);
        const faceToPath = finite(shot.face_to_path) ?? (face !== null && path !== null ? face - path : null);
        const launch = finite(shot.launch_direction) ?? face;
        const vector = angle => {
            const radians = angle * Math.PI / 180;
            return { x: Math.sin(radians), y: -Math.cos(radians) };
        };
        const point = (origin, direction, distance) => ({ x: origin.x + direction.x * distance, y: origin.y + direction.y * distance });
        const directionText = value => value === null ? "Unavailable" : Math.abs(value) < .05 ? "On target" : `${Math.abs(value).toFixed(1)}° ${value < 0 ? "left" : "right"}`;
        const signed = value => value === null ? "—" : `${value > 0 ? "+" : ""}${value.toFixed(1)}°`;
        const arrowHead = (end, direction, color, size = 14) => {
            const normal = { x: -direction.y, y: direction.x };
            ctx.fillStyle = color;
            ctx.beginPath();
            ctx.moveTo(end.x, end.y);
            ctx.lineTo(end.x - direction.x * size + normal.x * size * .55, end.y - direction.y * size + normal.y * size * .55);
            ctx.lineTo(end.x - direction.x * size - normal.x * size * .55, end.y - direction.y * size - normal.y * size * .55);
            ctx.closePath();
            ctx.fill();
        };

        if (path !== null) {
            const pathVector = vector(path);
            const start = point(impact, pathVector, -72);
            const end = point(impact, pathVector, 235);
            ctx.save(); ctx.strokeStyle = "#d7a62a"; ctx.lineWidth = 7; ctx.lineCap = "round";
            ctx.beginPath(); ctx.moveTo(start.x, start.y); ctx.lineTo(end.x, end.y); ctx.stroke(); ctx.restore();
            arrowHead(end, pathVector, "#d7a62a", 17);
            ctx.fillStyle = "#f0c95c"; ctx.font = graphFont(facePathCanvas, 14, 850); ctx.textAlign = "left";
            ctx.fillText(`CLUB PATH  ${directionText(path).toUpperCase()}`, Math.max(24, Math.min(w - 245, end.x + 18)), Math.max(52, end.y + 6));
        }

        if (launch !== null) {
            const launchVector = vector(launch);
            const end = point(impact, launchVector, 210);
            ctx.save(); ctx.strokeStyle = "#f5fff9"; ctx.lineWidth = 4; ctx.lineCap = "round";
            ctx.beginPath(); ctx.moveTo(impact.x, impact.y); ctx.lineTo(end.x, end.y); ctx.stroke(); ctx.restore();
            arrowHead(end, launchVector, "#f5fff9", 15);
            ctx.fillStyle = "#ffffff"; ctx.font = graphFont(facePathCanvas, 14, 850); ctx.textAlign = "left";
            ctx.fillText(`${finite(shot.launch_direction) !== null ? "BALL START" : "EXPECTED START"}  ${directionText(launch).toUpperCase()}`, Math.max(24, Math.min(w - 265, end.x + 18)), Math.max(72, end.y + 6));
        }

        if (face !== null) {
            const normal = vector(face);
            const tangent = { x: -normal.y, y: normal.x };
            const heel = point(impact, tangent, -58);
            const toe = point(impact, tangent, 58);
            ctx.save(); ctx.strokeStyle = "#ffffff"; ctx.lineWidth = 13; ctx.lineCap = "round";
            ctx.shadowColor = "rgba(0,0,0,.35)"; ctx.shadowBlur = 8;
            ctx.beginPath(); ctx.moveTo(heel.x, heel.y); ctx.lineTo(toe.x, toe.y); ctx.stroke(); ctx.restore();
            ctx.fillStyle = "#d7a62a"; ctx.beginPath(); ctx.arc(toe.x, toe.y, 7, 0, Math.PI * 2); ctx.fill();
            ctx.fillStyle = "#ffffff"; ctx.font = graphFont(facePathCanvas, 13, 800); ctx.textAlign = "left";
            ctx.fillText(`FACE  ${directionText(face).toUpperCase()}`, Math.min(w - 190, impact.x + 78), impact.y + 5);
        }

        if (path !== null && face !== null && faceToPath !== null) {
            const start = (-Math.PI / 2) + (path * Math.PI / 180);
            const end = (-Math.PI / 2) + (face * Math.PI / 180);
            const radius = 82;
            ctx.save(); ctx.fillStyle = "rgba(215,166,42,.23)"; ctx.strokeStyle = "#f0c95c"; ctx.lineWidth = 3;
            ctx.beginPath(); ctx.moveTo(impact.x, impact.y); ctx.arc(impact.x, impact.y, radius, start, end, faceToPath < 0); ctx.closePath(); ctx.fill(); ctx.stroke(); ctx.restore();
            const middle = (start + end) / 2;
            const labelX = impact.x + Math.cos(middle) * 112;
            const labelY = impact.y + Math.sin(middle) * 112;
            ctx.fillStyle = "#f0c95c"; ctx.font = graphFont(facePathCanvas, 15, 900); ctx.textAlign = "center";
            ctx.fillText(`F/P ${signed(faceToPath)}`, labelX, labelY);
        }

        ctx.fillStyle = "#ffd45b"; ctx.strokeStyle = "#ffffff"; ctx.lineWidth = 3;
        ctx.beginPath(); ctx.arc(impact.x, impact.y, 11, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
        ctx.fillStyle = "#dcebe4"; ctx.font = graphFont(facePathCanvas, 11, 800); ctx.textAlign = "center";
        ctx.fillText("IMPACT", impact.x, impact.y + 31);

        const setSummary = (key, value, note) => {
            const valueNode = document.querySelector(`[data-delivery="${key}"]`);
            const noteNode = document.querySelector(`[data-delivery-note="${key}"]`);
            if (valueNode) valueNode.textContent = value;
            if (noteNode) noteNode.textContent = note;
        };
        const pathPattern = path === null ? "No path data" : Math.abs(path) < .5 ? "Neutral path" : ((path < 0) !== isLeftHanded ? "Out-to-in" : "In-to-out");
        const relationNote = faceToPath === null ? "No relationship available" : Math.abs(faceToPath) < .5 ? "Face matched to path" : `Face ${Math.abs(faceToPath).toFixed(1)}° ${faceToPath < 0 ? "left" : "right"} of path`;
        const curveTendency = faceToPath === null ? "Curvature unavailable" : Math.abs(faceToPath) < .5 ? "Minimal curvature tendency" : `${faceToPath < 0 ? "Left" : "Right"}-curving tendency`;
        setSummary("path", signed(path), path === null ? "No path data" : `${pathPattern} · ${directionText(path)} of target`);
        setSummary("face", signed(face), face === null ? "No face data" : `${directionText(face)} of target`);
        setSummary("relation", signed(faceToPath), relationNote);
        setSummary("attack", signed(attack), attack === null ? "No attack data" : Math.abs(attack) < .2 ? "Level delivery" : `${Math.abs(attack).toFixed(1)}° ${attack > 0 ? "up" : "down"}`);
        setSummary("outcome", shot.shot_shape || curveTendency, `${curveTendency}. Start is controlled mainly by face direction; curve is driven mainly by face-to-path.`);
    }

    function updateMetrics(shot) {
    const metricDigits = {
        carry_distance: 1,
        total_distance: 1,
        ball_speed: 1,
        club_speed: 1,
        smash_factor: 2,
        launch_angle: 1,
        attack_angle: 1,
        spin_rate: 0,
        club_path: 1,
        club_face: 1,
        face_to_path: 1,
        offline_distance: 1,
    };

    document.querySelectorAll("[data-metric]").forEach(node => {
        const key = node.dataset.metric;
        const value = finite(shot ? shot[key] : null);

        if (value === null) {
            node.textContent = "—";
            return;
        }

        const digits =
            Object.prototype.hasOwnProperty.call(metricDigits, key)
                ? metricDigits[key]
                : 1;

        if (key === "offline_distance") {
            const side = Math.abs(value) < .05 ? "" : value < 0 ? " L" : " R";
            node.textContent = `${Math.abs(value).toFixed(digits)}${metricUnits[key] || ""}${side}`;
        } else {
            node.textContent = `${value.toFixed(digits)}${metricUnits[key] || ""}`;
        }
    });
}
    function selectShot(index) {
        const shot = shots[index];

        document.querySelectorAll(".shot-row").forEach(row => {
            row.classList.toggle(
                "selected",
                Number(row.dataset.shotIndex) === index
            );
        });

        if (!shot) {
            selectedTitle.textContent = "Select a Shot";
            selectedShape.textContent = "—";
            updateMetrics(null);
            selectSimulatorShot(null);
            drawTopDownFlight(null);
            drawDispersion(null);
            drawFacePath(null);
            return;
        }

        const isEstimated = String(shot.source || "").includes("Estimated Outcomes");
        selectedTitle.textContent =
            `Shot ${shot.shot_number || index + 1} · ${shot.club || primaryClub}${isEstimated ? " · Estimated" : ""}`;

        selectedShape.textContent =
            shot.shot_shape || "Unknown";

        updateMetrics(shot);
        selectSimulatorShot(shot);
        drawTopDownFlight(shot);
        drawDispersion(shot);
        drawFacePath(shot);
    }

    document.querySelectorAll(".shot-row").forEach(row => {
        row.addEventListener("click", event => {
            if (event.target.closest("form") || event.target.closest("a") || event.target.closest("[data-edit-shot]")) {
                return;
            }

            selectShot(Number(row.dataset.shotIndex));
        });
    });

    selectSimulatorShot(null);
    drawTopDownFlight(null);
    drawDispersion(null);
    drawFacePath(null);

    if (shots.length) {
        const requestedShotId = new URLSearchParams(window.location.search).get("selected_shot");
        let initialIndex = requestedShotId
            ? shots.findIndex(shot => String(shot.id) === String(requestedShotId))
            : -1;
        if (initialIndex < 0) {
            initialIndex = shots.findIndex(shot => shot.included !== false);
        }
        selectShot(initialIndex >= 0 ? initialIndex : 0);
    }

    const modal = document.getElementById("video-modal");

    document.querySelectorAll("[data-open-video]").forEach(button => {
        button.addEventListener("click", () => {
            if (modal) modal.hidden = false;
        });
    });

    document.querySelectorAll("[data-close-video]").forEach(button => {
        button.addEventListener("click", () => {
            if (modal) modal.hidden = true;
        });
    });

    if (modal) {
        modal.addEventListener("click", event => {
            if (event.target === modal) {
                modal.hidden = true;
            }
        });
    }


    const uploadForm=document.getElementById("onform-upload-form");
    if(uploadForm&&!uploadForm.dataset.chunkReady){
        uploadForm.dataset.chunkReady="1";
        uploadForm.addEventListener("submit",async event=>{
            event.preventDefault();
            const input=uploadForm.querySelector('input[name="video_file"]'),file=input&&input.files[0];
            if(!file)return;
            const sessionId=uploadForm.dataset.sessionId,button=uploadForm.querySelector('button[type="submit"]');
            const progress=document.getElementById("onform-upload-progress"),bar=progress&&progress.querySelector("span"),status=progress&&progress.querySelector("strong");
            if(progress)progress.hidden=false;if(button)button.disabled=true;
            try{
                const init=await fetch(`/sessions/${encodeURIComponent(sessionId)}/videos/chunked/init`,{method:"POST"});
                if(!init.ok)throw new Error((await init.json()).detail||"Could not start upload");
                const setup=await init.json(),chunkSize=setup.chunk_bytes,total=Math.ceil(file.size/chunkSize);
                for(let index=0;index<total;index++){
                    if(status)status.textContent=`Uploading video · ${Math.round(index/total*100)}%`;
                    const response=await fetch(`/sessions/${encodeURIComponent(sessionId)}/videos/chunked/${setup.upload_id}/part/${index}`,{method:"POST",headers:{"Content-Type":"application/octet-stream"},body:file.slice(index*chunkSize,Math.min(file.size,(index+1)*chunkSize))});
                    if(!response.ok)throw new Error((await response.json()).detail||`Chunk ${index+1} failed`);
                    if(bar)bar.style.width=`${Math.round((index+1)/total*100)}%`;
                }
                if(status)status.textContent="Finalizing video…";
                const fields=new FormData(uploadForm),payload={filename:file.name,content_type:file.type||"video/mp4",total_chunks:total};
                ["title","camera_view","club","shot_number","notes","onform_url"].forEach(key=>payload[key]=String(fields.get(key)||""));
                const finish=await fetch(`/sessions/${encodeURIComponent(sessionId)}/videos/chunked/${setup.upload_id}/finalize`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
                const result=await finish.json();if(!finish.ok)throw new Error(result.detail||"Could not finalize video");
                window.location.assign(result.redirect_url);
            }catch(error){if(status)status.textContent=error.message||"Video upload failed";if(button)button.disabled=false;}
        });
    }



    const editShotModal=document.getElementById("edit-shot-modal");
    const editShotForm=document.getElementById("edit-shot-form");
    const editableShotFields=["club","shot_shape","carry_distance","total_distance","ball_speed","club_speed","smash_factor","launch_angle","launch_direction","spin_rate","spin_axis","apex_height","attack_angle","club_path","club_face","face_to_path","offline_distance"];
    document.querySelectorAll("[data-edit-shot]").forEach(button=>button.addEventListener("click",event=>{
        event.stopPropagation();
        const index=Number(button.dataset.shotIndex),shot=shots[index];
        if(!shot||!editShotModal||!editShotForm)return;
        editableShotFields.forEach(key=>{
            const field=editShotForm.elements.namedItem(key);
            if(!field)return;
            const value=shot[key];
            field.value=value===null||value===undefined?"":String(value);
        });
        const sessionPath=window.location.pathname.replace(/\/$/,"");
        editShotForm.action=`${sessionPath}/shots/${encodeURIComponent(shot.id)}/edit`;
        const heading=document.getElementById("edit-shot-heading");
        if(heading)heading.textContent=`Edit Shot ${shot.shot_number||index+1} · ${shot.club||"Club"}`;
        editShotModal.hidden=false;
    }));
    document.querySelectorAll("[data-close-edit-shot]").forEach(button=>button.addEventListener("click",()=>{if(editShotModal)editShotModal.hidden=true;}));
    if(editShotModal)editShotModal.addEventListener("click",event=>{if(event.target===editShotModal)editShotModal.hidden=true;});

    const manualShotModal=document.getElementById("manual-shot-modal");
    document.querySelectorAll("[data-open-manual-shot]").forEach(button=>button.addEventListener("click",()=>{if(manualShotModal)manualShotModal.hidden=false;}));
    document.querySelectorAll("[data-close-manual-shot]").forEach(button=>button.addEventListener("click",()=>{if(manualShotModal)manualShotModal.hidden=true;}));
    if(manualShotModal)manualShotModal.addEventListener("click",event=>{if(event.target===manualShotModal)manualShotModal.hidden=true;});

})();
