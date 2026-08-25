(() => {
    const dataNode = document.getElementById("session-shot-data");
    if (!dataNode) return;

    const primaryClub = dataNode.dataset.primaryClub || "Club"; 

    let shots = [];
    try {
        shots = JSON.parse(dataNode.textContent || "[]");
    } catch (error) {
        console.error("Could not parse session shot data.", error);
        return;
    }

    const includedShots = shots.filter(shot => shot.included !== false);

    const flightCanvas = document.getElementById("flight-canvas");
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
        drawRangeBackdrop(canvas, ctx, canvas.id === 'topdown-flight-canvas' ? 'topdown' : 'range');
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

        if (variant === "topdown") {
            const fairway = ctx.createLinearGradient(0, 0, w, 0);
            fairway.addColorStop(0, "rgba(43,66,39,.30)");
            fairway.addColorStop(.18, "rgba(126,157,78,.72)");
            fairway.addColorStop(.5, "rgba(145,174,88,.88)");
            fairway.addColorStop(.82, "rgba(126,157,78,.72)");
            fairway.addColorStop(1, "rgba(43,66,39,.30)");
            ctx.fillStyle = fairway;
            ctx.fillRect(w * .12, 0, w * .76, h);
        }

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

        const carry = finite(shot.carry_distance) || 100;
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
        const carry=valueNumber(selectedShot.carry_distance)||1,total=valueNumber(selectedShot.total_distance)||carry;
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

    function drawTopDownFlight(shot) {
        const ctx=clearCanvas(topDownCanvas);if(!ctx)return;
        const w=topDownCanvas.width,h=topDownCanvas.height,centerX=w/2,top=34,bottom=h-42,sidePad=30;
        drawGrid(ctx,w,h,8,10);
        ctx.save();ctx.strokeStyle="rgba(255,255,255,.70)";ctx.lineWidth=2;ctx.setLineDash([8,7]);ctx.beginPath();ctx.moveTo(centerX,bottom);ctx.lineTo(centerX,top);ctx.stroke();ctx.restore();
        ctx.fillStyle="#edf6e9";ctx.font=graphFont(topDownCanvas,12,700);ctx.fillText("TARGET LINE",centerX+10,top+12);ctx.fillText("LEFT",12,h-14);ctx.fillText("RIGHT",w-52,h-14);
        if(!shot)return;
        const carry=finite(shot.carry_distance)||1,total=finite(shot.total_distance)||carry,landing=finalOffline(shot,carry);
        const yardsPerPixel=Math.max(total,carry)/(bottom-top),scale=1/yardsPerPixel;
        const widest=Math.max(Math.abs(landing),Math.abs(startDirectionAtCarry(shot,carry)));
        const fitScale=widest>0?(w/2-sidePad)/widest:scale;
        const equalScale=Math.min(scale,fitScale);
        ctx.fillStyle="#ffd45b";ctx.beginPath();ctx.arc(centerX,bottom,7,0,Math.PI*2);ctx.fill();
        ctx.save();ctx.strokeStyle="#f8fff4";ctx.lineWidth=5;ctx.lineCap="round";ctx.beginPath();
        for(let i=0;i<=100;i++){const t=i/100,x=centerX+lateralAt(shot,t,carry)*equalScale,y=bottom-carry*t*equalScale;i?ctx.lineTo(x,y):ctx.moveTo(x,y);}ctx.stroke();ctx.restore();
        const carryX=centerX+landing*equalScale,carryY=bottom-carry*equalScale;
        ctx.fillStyle="#ffd45b";ctx.strokeStyle="#ffffff";ctx.lineWidth=3;ctx.beginPath();ctx.arc(carryX,carryY,9,0,Math.PI*2);ctx.fill();ctx.stroke();
        if(total>carry){const totalY=bottom-total*equalScale;ctx.save();ctx.strokeStyle="#789088";ctx.lineWidth=3;ctx.setLineDash([7,6]);ctx.beginPath();ctx.moveTo(carryX,carryY);ctx.lineTo(carryX,totalY);ctx.stroke();ctx.restore();}
        ctx.fillStyle="#ffffff";ctx.font=graphFont(topDownCanvas,14,700);ctx.fillText(`Carry ${fmt(carry,1)} yd`,Math.min(w-145,Math.max(12,carryX+12)),Math.max(18,carryY-8));ctx.fillText(`Offline ${fmt(landing,1)} yd`,14,28);
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
        const w=dispersionCanvas.width,h=dispersionCanvas.height,L=128,R=24,T=35,rowH=46,trackW=w-L-R;
        const info=document.getElementById("selected-shape-map-info");
        if(!selectedShot){ctx.fillStyle="#edf6e9";ctx.font=graphFont(dispersionCanvas,15,650);ctx.fillText("Select a shot below",24,52);if(info)info.textContent="Select a shot to compare it with the same-club session average.";return;}
        const num=v=>{if(v===null||v===undefined||v==="")return null;const n=Number(v);return Number.isFinite(n)?n:null;};
        const clubName=String(selectedShot.club||"").trim().toLowerCase();
        const peers=includedShots.filter(s=>String(s.club||"").trim().toLowerCase()===clubName);
        const average=key=>{const values=peers.map(s=>num(s[key])).filter(v=>v!==null);return values.length?values.reduce((a,b)=>a+b,0)/values.length:null;};
        const metrics=[
            ["carry_distance","Carry","yd",1,false],["ball_speed","Ball Speed","mph",1,false],
            ["club_speed","Club Speed","mph",1,false],["smash_factor","Smash","",2,false],
            ["launch_angle","Launch","°",1,false],["spin_rate","Spin","rpm",0,false],
            ["attack_angle","Attack","°",1,true],["offline_distance","Offline","yd",1,true]
        ];
        ctx.font=graphFont(dispersionCanvas,12,700);ctx.fillStyle="#edf6e9";ctx.textAlign="right";ctx.fillText("SELECTED",w-116,16);ctx.fillStyle="#b27a18";ctx.fillText("CLUB AVG",w-24,16);
        metrics.forEach(([key,label,unit,digits,signed],i)=>{
            const raw=num(selectedShot[key]),avg=average(key),value=raw===null?0:Math.abs(raw),mean=avg===null?0:Math.abs(avg),max=Math.max(value,mean,1)*1.18,y=T+i*rowH;
            ctx.textAlign="left";ctx.fillStyle="#ffffff";ctx.font=graphFont(dispersionCanvas,13,750);ctx.fillText(label,8,y+14);
            ctx.fillStyle="rgba(255,255,255,.16)";ctx.fillRect(L,y+3,trackW,12);ctx.fillStyle="#f8fff4";ctx.fillRect(L,y+3,trackW*(value/max),12);
            const avgX=L+trackW*(mean/max);ctx.strokeStyle="#c48a22";ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(avgX,y-2);ctx.lineTo(avgX,y+20);ctx.stroke();
            const display=(n,isOffline=false)=>{if(n===null)return "—";if(isOffline){const side=Math.abs(n)<.05?"":n<0?" L":" R";return `${Math.abs(n).toFixed(digits)}${unit}${side}`;}return `${n.toFixed(digits)}${unit}`;};
            ctx.font=graphFont(dispersionCanvas,12,650);ctx.textAlign="right";ctx.fillStyle="#f8fff4";ctx.fillText(display(raw,key==="offline_distance"),w-116,y+36);ctx.fillStyle="#9a6814";ctx.fillText(display(avg,key==="offline_distance"),w-24,y+36);
        });
        if(info)info.innerHTML=`<span><b>${selectedShot.club||"Club"}</b></span><span>Selected shot compared with <b>${peers.length} included ${peers.length===1?"shot":"shots"}</b></span><span><b>Green</b> selected</span><span class="club-average-key"><b>Gold</b> club average</span>`;
    }

    function drawFacePath(shot) {
        const ctx = clearCanvas(facePathCanvas);
        if (!ctx) return;

        const w = facePathCanvas.width;
        const h = facePathCanvas.height;
        drawGrid(ctx, w, h, 8, 8);

        const cx = w / 2;
        const cy = h / 2;

        ctx.strokeStyle = "rgba(255,255,255,.72)";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(cx, 30);
        ctx.lineTo(cx, h - 30);
        ctx.stroke();

        if (!shot) return;

        const path = finite(shot.club_path) || 0;
        const face = finite(shot.club_face) || 0;

        function arrow(angleDeg, length, label, strokeStyle, offsetX, dashPattern = []) {
            const angle = (angleDeg - 90) * Math.PI / 180;
            const endX = cx + Math.cos(angle) * length;
            const endY = cy + Math.sin(angle) * length;

            ctx.strokeStyle = strokeStyle;
            ctx.fillStyle = strokeStyle;
            ctx.lineWidth = 6;
            ctx.setLineDash(dashPattern);

            ctx.beginPath();
            ctx.moveTo(cx, cy + 120);
            ctx.lineTo(endX, endY);
            ctx.stroke();

            ctx.font = graphFont(facePathCanvas, 14, 700);
            ctx.fillText(
                `${label} ${angleDeg.toFixed(1)}°`,
                40 + offsetX,
                34
            );
        }

        arrow(path, 180, "Path", "#c48a22", 0, [3, 8]);
        arrow(face, 155, "Face", "#f8fff4", 155, []);

        ctx.fillStyle = "#243a33";
        ctx.font = graphFont(facePathCanvas, 14, 700);
        ctx.fillText(
            `Face-to-Path ${fmt(shot.face_to_path, 1)}°`,
            40,
            h - 25
        );
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

        node.textContent =
            `${value.toFixed(digits)}${metricUnits[key] || ""}`;
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
            drawFlight(null);
            drawTopDownFlight(null);
            drawDispersion(null);
            drawFacePath(null);
            return;
        }

        selectedTitle.textContent =
            `Shot ${shot.shot_number || index + 1} · ${shot.club || "primaryClub"}`;

        selectedShape.textContent =
            shot.shot_shape || "Unknown";

        updateMetrics(shot);
        drawFlight(shot);
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

    drawFlight(null);
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
