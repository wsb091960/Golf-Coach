document.addEventListener('DOMContentLoaded',()=>{
  const video=document.querySelector('#swingVideo');
  const canvas=document.querySelector('#overlayCanvas');
  const ctx=canvas.getContext('2d');
  const empty=document.querySelector('#videoEmpty');
  const emptyDetail=document.querySelector('#videoEmptyDetail');
  const instruction=document.querySelector('#landmarkInstruction');
  const frameStrip=document.querySelector('#frameStrip');

  const shotSelect=document.querySelector('#garminShotSelect');
  const shotStatus=document.querySelector('#garminShotStatus');
  const shotGrid=document.querySelector('#garminMetricGrid');
  const correlationList=document.querySelector('#correlationList');
  let sessionShots=[];
  let selectedShot=null;

  let sessionGoal='';
  let lastAnalysis=null;


  const phaseConfig={
    p1:['left_shoulder','right_shoulder','left_hip','right_hip'],
    p2:['left_shoulder','right_shoulder','left_hip','right_hip'],
    p3:['left_shoulder','right_shoulder','left_hip','right_hip'],
    p4:['left_shoulder','right_shoulder','left_hip','right_hip'],
    p5:['left_shoulder','right_shoulder','left_hip','right_hip'],
    p6:['left_shoulder','right_shoulder','left_hip','right_hip'],
    p7:['left_shoulder','right_shoulder','left_hip','right_hip'],
    p8:['left_shoulder','right_shoulder','left_hip','right_hip'],
    p9:['left_shoulder','right_shoulder','left_hip','right_hip'],
    p10:[]
  };
  const phaseLabels={p1:'P1 · Address',p2:'P2 · Shaft parallel',p3:'P3 · Lead arm parallel',p4:'P4 · Top',p5:'P5 · Lead arm parallel',p6:'P6 · Shaft parallel',p7:'P7 · Impact',p8:'P8 · Shaft parallel',p9:'P9 · Trail arm parallel',p10:'P10 · Finish'};
  const measuredPhases=new Set(['p1','p4','p7','p10']);
  const servicePhaseMap={p1:'address',p4:'top',p7:'impact',p10:'finish'};
  const pointLabels={left_shoulder:'player’s left shoulder joint (outer shoulder, not neck)',right_shoulder:'player’s right shoulder joint (outer shoulder, not neck)',left_hip:'player’s left hip',right_hip:'player’s right hip',nose:'nose',left_ankle:'player’s left ankle',right_ankle:'player’s right ankle'};

  function requiredPoints(phase){
    if(phase!=='p10')return phaseConfig[phase];
    return document.querySelector('#cameraView').value==='face-on'
      ? ['nose','left_shoulder','right_shoulder','left_ankle','right_ankle']
      : ['left_shoulder','right_shoulder','left_hip','right_hip','left_ankle','right_ankle'];
  }
  const frames={};
  let activePhase='p1';
  let marking=false;

  function message(text,error=false){instruction.textContent=text;instruction.classList.toggle('is-error',error)}
  function resizeCanvas(){canvas.width=Math.max(1,video.videoWidth||1280);canvas.height=Math.max(1,video.videoHeight||720);drawPoints()}
  function phaseButton(phase){return frameStrip.querySelector(`[data-phase="${phase}"]`)}
  function nextPoint(){const frame=frames[activePhase];if(!frame)return null;return requiredPoints(activePhase).find(name=>!frame.points[name])||null}
  function drawPoints(){
    ctx.clearRect(0,0,canvas.width,canvas.height);
    const frame=frames[activePhase];if(!frame)return;
    Object.entries(frame.points).forEach(([name,p],index)=>{
      const x=p[0]*canvas.width,y=p[1]*canvas.height;
      ctx.beginPath();ctx.arc(x,y,9,0,Math.PI*2);ctx.fillStyle='#41d394';ctx.fill();ctx.lineWidth=3;ctx.strokeStyle='#fff';ctx.stroke();
      ctx.fillStyle='#fff';ctx.font='700 15px system-ui';ctx.fillText(String(index+1),x+13,y+5);
    });
    [['left_shoulder','right_shoulder'],['left_hip','right_hip'],['nose','left_ankle'],['nose','right_ankle']].forEach(([a,b])=>{
      if(!frame.points[a]||!frame.points[b])return;
      ctx.beginPath();ctx.moveTo(frame.points[a][0]*canvas.width,frame.points[a][1]*canvas.height);ctx.lineTo(frame.points[b][0]*canvas.width,frame.points[b][1]*canvas.height);ctx.strokeStyle='#41d394';ctx.lineWidth=3;ctx.stroke();
    });
  }
  function updatePhase(){
    document.querySelectorAll('.frame-button').forEach(b=>b.classList.toggle('active',b.dataset.phase===activePhase));
    const frame=frames[activePhase];
    if(frame){video.currentTime=frame.time;video.pause();const next=nextPoint();marking=Boolean(next);message(next?`Click the ${pointLabels[next]}.`:`${phaseLabels[activePhase]} complete. Select another position or analyze.`)}
    else{marking=false;message(`Pause at ${phaseLabels[activePhase]}, then click Capture current position.`)}
    canvas.classList.toggle('is-marking',marking);drawPoints();
  }
  Object.keys(phaseConfig).forEach(phase=>{const b=document.createElement('button');b.type='button';b.className='frame-button';b.dataset.phase=phase;b.innerHTML=`<strong>${phaseLabels[phase].split(' · ')[0]}</strong><span>${phaseLabels[phase].split(' · ')[1]}</span><small>${measuredPhases.has(phase)?'Measured':'Visual'}</small>`;b.title=measuredPhases.has(phase)?'Included in numerical biomechanics':'Coach-verified visual checkpoint';b.addEventListener('click',()=>{activePhase=phase;updatePhase()});frameStrip.appendChild(b)});

  function loadVideo(src){empty.style.display='grid';empty.querySelector('strong').textContent='Loading video…';video.src=src;video.load()}
  video.addEventListener('loadedmetadata',()=>{resizeCanvas();empty.style.display='none';message(`Pause at ${phaseLabels[activePhase]}, then click Capture current position.`)});
  video.addEventListener('error',()=>{empty.style.display='grid';empty.querySelector('strong').textContent='Video could not be loaded';emptyDetail.textContent='Return to the session and confirm the video still plays.';message('The selected video stream could not be opened.',true)});
  window.addEventListener('resize',drawPoints);

  const query=new URLSearchParams(window.location.search);
  const sessionId=query.get('session_id'),videoId=query.get('video_id');
  if(sessionId&&videoId){
    loadVideo(`/sessions/${encodeURIComponent(sessionId)}/videos/${encodeURIComponent(videoId)}/stream`);
    const source=document.querySelector('#bioSourceContext');source.hidden=false;
    document.querySelector('#bioSourceStudent').textContent=query.get('student')||'Session video';
    document.querySelector('#bioBackToSession').href=`/sessions/${encodeURIComponent(sessionId)}`;
    document.querySelector('#handedness').value=(query.get('handedness')||'').toLowerCase().includes('left')?'left':'right';
    document.querySelector('#cameraView').value=(query.get('camera_view')||'').toLowerCase().includes('face')?'face-on':'down-the-line';
  }else{empty.querySelector('strong').textContent='Choose a swing video';emptyDetail.textContent='MP4 or MOV'}

  const shotFields=[['carry_distance','Carry','yd',1],['total_distance','Total','yd',1],['ball_speed','Ball speed','mph',1],['club_speed','Club speed','mph',1],['smash_factor','Smash','',2],['launch_angle','Launch','°',1],['launch_direction','Start','°',1],['attack_angle','Attack','°',1],['spin_rate','Spin','rpm',0],['spin_axis','Spin axis','°',1],['club_path','Path','°',1],['club_face','Face','°',1],['face_to_path','Face/path','°',1],['offline_distance','Offline','yd',1]];
  function renderShot(){
    selectedShot=sessionShots.find(s=>String(s.id)===shotSelect.value)||null;
    if(!selectedShot){shotStatus.textContent=sessionId?'No included Garmin shots are available for this session. Analysis will be video-only.':'Open Biomechanics from a session to attach Garmin evidence.';shotGrid.innerHTML='';return}
    shotStatus.textContent=`Shot ${selectedShot.shot_number||'—'} · ${selectedShot.club||'Unknown club'} · ${selectedShot.shot_shape||'Unknown shape'}`;
    shotGrid.innerHTML=shotFields.filter(([key])=>selectedShot[key]!==null&&selectedShot[key]!==undefined&&selectedShot[key]!=='').map(([key,label,unit,digits])=>`<article><small>${label}</small><strong>${Number(selectedShot[key]).toFixed(digits)}${unit?` ${unit}`:''}</strong></article>`).join('');
  }
  async function loadSessionShots(){
    if(!sessionId){renderShot();return}
    try{const response=await fetch(`/biomechanics/session/${encodeURIComponent(sessionId)}/shots`);if(!response.ok)throw new Error('Shot data request failed');const data=await response.json();sessionShots=data.shots||[];sessionGoal=String(data.session_notes||'').trim();const goalText=document.querySelector('#sessionGoalText');if(goalText)goalText.textContent=sessionGoal||'No objective entered in Session Notes.';shotSelect.innerHTML=sessionShots.length?sessionShots.map((s,i)=>`<option value="${s.id}">Shot ${s.shot_number||i+1} · ${s.club||'Unknown'} · ${s.shot_shape||'Unknown'}</option>`).join(''):'<option value="">No Garmin shots</option>';renderShot()}catch(error){shotSelect.innerHTML='<option value="">Unavailable</option>';shotStatus.textContent='Garmin shot data could not be loaded. Analysis will be video-only.'}
  }
  shotSelect.addEventListener('change',renderShot);
  loadSessionShots();


  document.querySelector('#videoInput').addEventListener('change',event=>{const file=event.target.files[0];if(file)loadVideo(URL.createObjectURL(file))});
  document.querySelector('#captureFrame').addEventListener('click',()=>{
    if(!video.src||video.readyState<1){message('Load a video first.',true);return}
    video.pause();frames[activePhase]={time:video.currentTime,points:{}};marking=true;canvas.classList.add('is-marking');phaseButton(activePhase).classList.remove('complete');drawPoints();message(`Click the ${pointLabels[nextPoint()]}.`);
  });
  document.querySelector('#clearFrame').addEventListener('click',()=>{delete frames[activePhase];phaseButton(activePhase).classList.remove('complete');updatePhase()});
  canvas.addEventListener('click',event=>{
    if(!marking||!frames[activePhase])return;
    const name=nextPoint();if(!name)return;
    const point=window.VideoCoordinates.clientToMediaPoint(event.clientX,event.clientY,canvas.getBoundingClientRect(),video.videoWidth,video.videoHeight);
    if(!point){message('Click inside the visible video image—not the black side bars.',true);return}
    frames[activePhase].points[name]=point;drawPoints();
    const next=nextPoint();
    if(next)message(`Click the ${pointLabels[next]}.`);else{marking=false;canvas.classList.remove('is-marking');phaseButton(activePhase).classList.add('complete');message(`${phaseLabels[activePhase]} complete. Select another position or analyze.`)}
  });

  function renderCoachingProcess(data){
    const metrics=data.metrics||[];
    const priority=[...(data.priorities||[]),...(data.watches||[])][0]||metrics[0]||null;
    const observe=document.querySelector('#observeSummary');
    const corroborate=document.querySelector('#corroborateSummary');
    const prescribe=document.querySelector('#prescribeSummary');
    const retest=document.querySelector('#retestSummary');
    if(observe)observe.textContent=priority?`${priority.label}: ${priority.value}${priority.unit} (${priority.status.replace('-',' ')}), with ${data.confidence}% overall 2D confidence.`:`Verified frames produced ${data.confidence}% confidence but no ranked movement flag.`;
    if(corroborate)corroborate.textContent=selectedShot?`Shot ${selectedShot.shot_number||'—'} with ${selectedShot.club||'unknown club'} finished as ${selectedShot.shot_shape||'an unclassified shape'}. Use its measured start, curve and strike values to test the video finding.`:'No Garmin shot is attached; corroborate with observed strike and a new measured shot group.';
    if(prescribe)prescribe.textContent=priority?`First coaching candidate: ${priority.label}. ${priority.coaching_note}`:'No priority threshold was triggered. Preserve the motion unless repeated ball flight identifies a performance need.';
    if(retest){const club=selectedShot&&selectedShot.club?selectedShot.club:'same club';const view=document.querySelector('#cameraView').selectedOptions[0].text;retest.textContent=`Record five shots with ${club}, the same target and the ${view.toLowerCase()} camera view. Compare the group—not one best result.`}
  }


  function renderXFactor(x){
    const status=document.querySelector('#xFactorStatus'),grid=document.querySelector('#xFactorMetrics');
    if(!x||!x.available){status.textContent=x&&x.reason?x.reason:'X-factor was not calculated.';status.classList.add('is-unavailable');grid.innerHTML='';return}
    status.classList.remove('is-unavailable');status.textContent=`${x.method} · ${x.confidence}% confidence${x.quality_warning?` · ${x.quality_warning}`:''}`;
    const values=[['P4 thorax turn',x.p4_thorax_turn],['P4 pelvis turn',x.p4_pelvis_turn],['P4 X-factor',x.p4_x_factor],['P5 thorax turn',x.p5_thorax_turn],['P5 pelvis turn',x.p5_pelvis_turn],['P5 separation',x.p5_separation],['X-factor stretch',x.x_factor_stretch]];
    grid.innerHTML=values.map(([label,value])=>`<article><small>${label}</small><strong>${Number(value).toFixed(1)}°</strong></article>`).join('')+`<p>${x.coaching_note}</p>`;
  }


  document.querySelector('#cameraView').addEventListener('change',()=>{
    const method=document.querySelector('#finishMethodText');if(method)method.textContent=document.querySelector('#cameraView').value==='face-on'?'Face on uses the visible head relative to the lead foot, normalized to shoulder width.':'Down the line uses shoulder-to-pelvis stacking and does not require the nose.';
    if(frames.p10){delete frames.p10;const button=phaseButton('p10');if(button)button.classList.remove('complete')}
    if(activePhase==='p10')updatePhase();
    message('Camera view changed. Recapture P10 with the view-specific landmarks.');
  });


  function value(shot,key,digits=1,unit=''){const n=shot&&Number(shot[key]);return Number.isFinite(n)?`${n.toFixed(digits)}${unit}`:'—'}
  function buildCoachingObservations(data){
    const shot=selectedShot||{};
    const goal=sessionGoal||'Improve the student’s intended ball flight with repeatable contact and dispersion.';
    const handed=document.querySelector('#handedness').value;
    const pushDraw=/push\s*draw|right[ -]to[ -]left|draw/i.test(goal);
    const pathTarget=handed==='left'?'-3° to -6°':'+3° to +6°';
    const faceTarget=handed==='left'?'-1° to -3°':'+1° to +3°';
    const ftpTarget=handed==='left'?'+1° to +3°':'−1° to −3°';
    const startTarget=handed==='left'?'1°–3° left':'1°–3° right';
    const ranked=[...(data.priorities||[]),...(data.watches||[])];
    const finding=ranked[0];
    const bioFinding=finding?`${finding.label}: ${finding.value}${finding.unit} (${finding.status.replace('-',' ')}). ${finding.coaching_note}`:'No biomechanical priority threshold was triggered; preserve motion unless repeated ball flight supports a change.';
    const flightPlan=pushDraw?`Desired delivery window: path ${pathTarget}; face ${faceTarget}; face-to-path ${ftpTarget}; start ${startTarget}; gentle curvature toward the target.`:'Use the selected Garmin shot to define the desired start line, curvature and finish before changing movement.';
    return `SESSION OBJECTIVE\n${goal}\n\nCURRENT GARMIN EVIDENCE\nShot ${shot.shot_number||'—'} · ${shot.club||'Unknown club'} · ${shot.shot_shape||'Unknown shape'}\nCarry ${value(shot,'carry_distance',1,' yd')} | Ball speed ${value(shot,'ball_speed',1,' mph')} | Club speed ${value(shot,'club_speed',1,' mph')} | Smash ${value(shot,'smash_factor',2)}\nPath ${value(shot,'club_path',1,'°')} | Face ${value(shot,'club_face',1,'°')} | Face-to-path ${value(shot,'face_to_path',1,'°')} | Start ${value(shot,'launch_direction',1,'°')} | Offline ${value(shot,'offline_distance',1,' yd')}\n\nCOACHING INTERPRETATION\n${flightPlan}\nVideo finding to investigate: ${bioFinding}\nDo not treat a single 2D checkpoint as the cause. Confirm the pattern across multiple shots and centered contact.\n\nSETUP AND STRIKE CHECK\n1. Verify Garmin and target-line alignment.\n2. Confirm the student is not aimed left of the intended start line.\n3. Establish centered contact before changing delivery.\n4. Use a start-line gate slightly to the push side of the target.\n\nMOVEMENT PRIORITY\nUse P5–P7 to evaluate hand lowering, trail-elbow position, trail-hip depth and delivery direction. Move the path progressively toward the desired window without forcing an exaggerated inside approach. Preserve posture and rotation through P7–P8.\n\nDRILLS\n• Pump-to-P6: rehearse P4 to P6 two or three times, allowing the hands to lower while retaining trail-hip depth; then hit a half-speed shot.\n• Start-line gate: score whether the ball begins through the intended push-side gate before judging curve.\n• Waist-high face control: stabilize the lead wrist and continue turning through P8 without an aggressive hand roll.\n\nPROGRESSION\nFirst create centered contact and a start on the intended side. Next move path in the required direction while preserving face direction. Accept a straight push before adding gentle draw curvature. Avoid converting the fade into a pull hook.\n\nFIVE-SHOT RETEST\nUse the same club, target and camera view. Compare median start angle, path, face, face-to-path, spin axis, smash, carry and offline dispersion—not the best shot.\n\nDECISION\nKeep the change if path moves toward the target window, start remains on the intended side, face-to-path creates controlled curvature, strike stays stable and dispersion improves. Refine or discard it if path becomes excessive, the face crosses the target, contact deteriorates or dispersion widens.`;
  }

  document.querySelector('#runAnalysis').addEventListener('click',async()=>{
    const verified=Object.fromEntries(Object.entries(frames).filter(([phase,frame])=>requiredPoints(phase).every(name=>frame.points[name])).map(([phase,frame])=>[phase,frame.points]));
    const completed=Object.fromEntries(Object.entries(verified).filter(([phase])=>measuredPhases.has(phase)).map(([phase,points])=>[servicePhaseMap[phase],points]));
    if(!Object.keys(completed).length){message('Complete at least one measured position: P1, P4, P7 or P10.',true);return}
    const button=document.querySelector('#runAnalysis');button.disabled=true;button.textContent='Analyzing…';
    try{
      const response=await fetch('/biomechanics/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({camera_view:document.querySelector('#cameraView').value,handedness:document.querySelector('#handedness').value,frames:completed,visual_frames:verified,shot:selectedShot})});
      const data=await response.json();if(!response.ok)throw new Error(data.detail||'Analysis failed');
      document.querySelector('#confidenceValue').textContent=data.confidence+'%';
      document.querySelector('#metricGrid').innerHTML=data.metrics.length?data.metrics.map(m=>`<article class="metric ${m.status}"><small>${m.label}</small><strong>${m.value}${m.unit}</strong><div class="status">${m.status.replace('-',' ')}</div><p>${m.coaching_note}</p></article>`).join(''):'<div class="empty-results">The completed frame does not contain a measured checkpoint. Add Address, Top, Impact, or Finish.</div>';

      correlationList.innerHTML=(data.correlations||[]).length?`<h4>Video + Garmin correlations</h4>${data.correlations.map(item=>`<article><strong>${item.title}</strong><p>${item.text}</p></article>`).join('')}`:'';
      const ranked=[...data.priorities,...data.watches];document.querySelector('#priorityList').innerHTML=ranked.length?ranked.map((m,i)=>`<div class="priority"><b>${i+1}. ${m.label}</b><span>${m.coaching_note}</span></div>`).join(''):'<div class="empty-results">No priority flags in the verified frames.</div>';
      lastAnalysis=data;document.querySelector('#saveCoachingPlan').disabled=!sessionId;
      renderXFactor(data.x_factor);
      renderCoachingProcess(data);
      message('Analysis complete. Review the measured checkpoints below.');
    }catch(error){message(error.message||'Analysis failed.',true)}finally{button.disabled=false;button.textContent='Analyze Biomechanics'}
  });

  document.querySelector('#saveCoachingPlan').addEventListener('click',async()=>{
    if(!sessionId||!lastAnalysis){message('Run the analysis before saving coaching observations.',true);return}
    const button=document.querySelector('#saveCoachingPlan');button.disabled=true;button.textContent='Saving plan…';
    try{const response=await fetch(`/biomechanics/session/${encodeURIComponent(sessionId)}/coaching-observations`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({coaching_observations:buildCoachingObservations(lastAnalysis)})});const data=await response.json();if(!response.ok)throw new Error(data.detail||'Plan could not be saved');button.textContent='Plan saved to Coaching Observations';const review=document.querySelector('#reviewSavedPlan');review.href=data.session_url;review.hidden=false;message('The goal-driven plan was saved in the session Coaching Observations box.')}catch(error){button.disabled=false;button.textContent='Save Plan to Coaching Observations';message(error.message,true)}
  });

  updatePhase();
});
