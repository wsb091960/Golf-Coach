"""Isolated, stateless preview of the server-decoded contact sheet API.

No production database, authentication, or student/session routes are loaded.
This preview is for test footage only, not sensitive student videos.
"""
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from app.routers.swing_contact_sheet import router

app = FastAPI(title="WSBCO Swing Sheet Preview")
app.include_router(router)

@app.get("/health")
def health():
    return {"status": "ok", "service": "swing-sheet-preview"}

@app.get("/", response_class=HTMLResponse)
def index():
    return """<!doctype html><html lang="en"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>WSBCO Server Swing Sheet Test</title><style>body{font:17px system-ui;background:#132528;color:white;max-width:680px;margin:25px auto;padding:16px}input,select,button{font:inherit;padding:9px;max-width:100%}label{display:block;margin:18px 0}button{background:#e3c46c;border:0;border-radius:7px}small{color:#d3d9d6}</style>
<h1>WSBCO Server-Decoded Swing Sheet</h1><p>Test-only preview. Upload one video. Automatic selection is temporarily disabled while we validate it against real swings. Manual extraction remains available. Adjust any individual P-position frame number below and regenerate the sheet to review the correction. Frames are extracted on the server, not by browser seeking.</p>
<div id="importFeedback" role="status" aria-live="polite" style="background:#254247;color:#ffe49c;padding:12px;border:1px solid #e3c46c;border-radius:8px;margin:12px 0">Select a previously downloaded JSON record to restore its P1–P10 frame numbers.</div><p id="importFeedback" role="status" aria-live="polite" style="background:#254247;color:#ffe49c;padding:12px;border:1px solid #e3c46c">Select a JSON review record to restore P1–P10.</p><label>Import previous approval (JSON file from Downloads) <input type="file" id="reviewImport" accept="*/*"><small>On Android choose Files or My Files, then Downloads. Select WSBCO_approved_fo_P1-P10.json or the DTL version. This is not the Video field.</small></label><form id="form"><label>Video <input type="file" name="video" accept="video/mp4,video/quicktime,video/x-m4v,video/*" id="videoFile"></label>
<label>Camera angle <select name="camera_angle" id="angle"><option value="dtl">Down the line</option><option value="fo">Face on</option></select></label>
<label><input type="checkbox" id="automatic" disabled> Automatic selection (paused: failed real-video validation)</label>\n<label>Ten manual frame indices (verified extraction method) <input style="width:95%" name="frame_indices" id="frames" value="235,255,270,288,304,310,313,318,325,340" required></label>
<div id="checkpointEditor" style="margin:16px 0"></div><p id="videoReminder" role="status" style="padding:10px;background:#254247;border:1px solid #e3c46c;color:#ffe49c">Select the original video above to generate a contact sheet. JSON restores frame numbers only.</p><button type="button" id="generate">View ten frames on screen</button> <button type="button" id="download">Download ZIP</button></form><div id="sheetArea" style="margin-top:16px"></div><div style="margin-top:14px"><details><summary>Link review record to a Golf Coach student/session (optional)</summary><p><small>Enter existing IDs from Golf Coach. These are recorded in the downloaded JSON only; no database connection or lookup is performed.</small></p><label>Student ID <input id="studentId" placeholder="Existing student ID"></label><label>Session ID <input id="sessionId" placeholder="Existing session ID"></label></details><label><input type="checkbox" id="coachConfirm" disabled> I reviewed the displayed ten checkpoints and approve these exact frames.</label><button type="button" id="approve" disabled>Approve and download review record</button></div><section id="analysisPanel" style="margin:20px 0;padding:14px;border:1px solid #e3c46c;border-radius:8px"><h2>Coach-guided TGM / TPI review</h2><p><small>This is an observation-based coaching worksheet, not automatic video measurement or an AI diagnosis. Review and approve the P-positions above before generating.</small></p><label>Observed ball flight <select id="ballFlight"><option value="">Not recorded</option><option value="straight_pull">Straight pull</option><option value="push">Straight push</option><option value="slice">Slice / fade</option><option value="hook">Hook / draw</option><option value="straight">Straight</option></select></label><label>Primary observed issue <select id="swingIssue"><option value="">Choose observation</option><option value="alignment">P1: Aim / alignment</option><option value="ball_position">P1: Ball position</option><option value="balance">P7–P10: Balance / finish</option><option value="transition">P4–P6: Transition / sequencing</option><option value="face_path">P6–P8: Clubface / path control</option></select></label><label>Coach observations <textarea id="coachNotes" rows="3" style="width:96%" placeholder="What do you actually see at P1–P10?"></textarea></label><label>TPI screen status <select id="tpiStatus"><option value="not_screened">Not screened</option><option value="screened">Screen completed; details in coach notes</option></select></label><button type="button" id="analyze">Generate coaching worksheet</button><div id="analysisResult" aria-live="polite" style="margin-top:12px"></div></section><p id="status" role="status" aria-live="polite" style="min-height:2em;color:#ffe49c;font-weight:700"></p>
<small>Automatic mode selects frames from the motion interval, not actual P1–P10 landmarks. Manual values are only test candidates for the two previously reviewed recordings. They are not automatic detections. Coach approval creates a downloadable JSON review record, not a database entry. You can import that record to restore frame selections, but must re-review before approving again. Optional student/session IDs are included for future integration but not verified or saved to the database. No footage is persisted by this endpoint; uploads are processed in temporary files. Avoid uploading sensitive student footage to this unauthenticated test preview.</small>
<script>
const samples={dtl:'235,255,270,288,304,310,313,318,325,340',fo:'250,264,270,285,295,300,304,310,315,325'};
document.querySelector('#angle').addEventListener('change',e=>{document.querySelector('#frames').value=samples[e.target.value];buildEditor()});
const positionNames=['P1 Address','P2 Shaft parallel back','P3 Lead arm parallel back','P4 Top','P5 Lead arm parallel down','P6 Shaft parallel down','P7 Impact','P8 Shaft parallel through','P9 Trail arm parallel through','P10 Finish'];
const editor=document.querySelector('#checkpointEditor'),framesField=document.querySelector('#frames');
editor.style.cssText='display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px';
function buildEditor(){
  editor.replaceChildren();
  const values=framesField.value.split(',').map(v=>Number(v.trim()));
  positionNames.forEach((name,i)=>{
    const cell=document.createElement('label');cell.style.cssText='display:block;margin:0;background:#20383a;border-radius:7px;padding:9px';
    const heading=document.createElement('span');heading.textContent=name;heading.style.cssText='display:block;font-size:13px;color:#f3d183;margin-bottom:5px';
    const input=document.createElement('input');input.type='number';input.min='0';input.step='1';input.value=String(values[i]??0);input.dataset.position=String(i);input.style.cssText='width:100%;box-sizing:border-box;background:white;color:#111';
    input.addEventListener('change',()=>{const inputs=[...editor.querySelectorAll('input')];framesField.value=inputs.map(el=>el.value).join(',')});
    cell.append(heading,input);editor.appendChild(cell);
  });
}
buildEditor();
framesField.addEventListener('change',buildEditor);
document.querySelector('#angle').addEventListener('change',()=>{setTimeout(buildEditor,0)});
let reviewedSnapshot=null;\nconst confirmBox=document.querySelector('#coachConfirm'),approveButton=document.querySelector('#approve');\nfunction invalidateApproval(){reviewedSnapshot=null;confirmBox.checked=false;confirmBox.disabled=true;approveButton.disabled=true}\nfunction syncApproval(){approveButton.disabled=!reviewedSnapshot||!confirmBox.checked||!file.files.length||reviewedSnapshot.indices!==framesField.value.trim()||reviewedSnapshot.angle!==document.querySelector('#angle').value||reviewedSnapshot.name!==file.files[0].name}\nconfirmBox.addEventListener('change',syncApproval);\nframesField.addEventListener('input',invalidateApproval);\neditor.addEventListener('input',invalidateApproval);\ndocument.querySelector('#angle').addEventListener('change',invalidateApproval);\napproveButton.addEventListener('click',()=>{syncApproval();if(approveButton.disabled)return;const frames=reviewedSnapshot.indices.split(',').map(Number);const record={schema:'wsbco.coach_review.v1',source:'manual_coach_review',coach_approved:true,approved_at:new Date().toISOString(),video_filename:reviewedSnapshot.name,student_id:document.querySelector('#studentId').value.trim()||null,session_id:document.querySelector('#sessionId').value.trim()||null,camera_angle:reviewedSnapshot.angle,frame_indices:frames,checkpoints:frames.map((n,i)=>({position:'P'+(i+1),label:positionNames[i],frame_index:n,status:'coach_approved'})),note:'Client-generated review record. Not saved to server or student database; timestamps require video metadata for validation.'};const url=URL.createObjectURL(new Blob([JSON.stringify(record,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='WSBCO_approved_'+record.camera_angle+'_P1-P10.json';document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),30000);status.textContent='Coach approval record downloaded. Save the JSON with your swing video; nothing was stored on the server.'});\ndocument.querySelector('#reviewImport').addEventListener('change',async e=>{
  const source=e.target.files[0];if(!source)return;\n  const feedback=document.querySelector('#importFeedback');feedback.textContent='Reading '+source.name+'…';
  try{
    if(!source.name.toLowerCase().endsWith('.json'))throw Error('Choose a .json review record from Downloads, not a video or ZIP file');\n    if(source.size>100000)throw Error('Review record is unexpectedly large');
    const record=JSON.parse(await source.text());
    const frames=record.frame_indices;
    if(record.schema!=='wsbco.coach_review.v1'||record.coach_approved!==true||!['fo','dtl'].includes(record.camera_angle)||!Array.isArray(frames)||frames.length!==10||frames.some((n,i)=>!Number.isSafeInteger(n)||n<0||(i>0&&n<=frames[i-1])))throw Error('Invalid or unsupported review record');
    invalidateApproval();
    document.querySelector('#angle').value=record.camera_angle;
    framesField.value=frames.join(',');buildEditor();document.querySelector('#studentId').value=typeof record.student_id==='string'?record.student_id:'';document.querySelector('#sessionId').value=typeof record.session_id==='string'?record.session_id:'';
    document.querySelector('#sheetArea').replaceChildren();
    const selected=file.files[0];
    const message='Imported '+record.camera_angle.toUpperCase()+' review: all ten frame numbers restored. '+(selected&&selected.name!==record.video_filename?'Warning: video filename differs. ':'')+'Select the original video and tap View ten frames on screen. Re-approval is required.';\n    feedback.textContent=message;status.textContent=message;document.querySelector('#videoReminder').textContent='JSON loaded. Next select the matching original '+record.camera_angle.toUpperCase()+' video in the Video field above, then tap View ten frames on screen.';
  }catch(err){feedback.textContent='Import failed: '+err.message;status.textContent=feedback.textContent}
  e.target.value='';
});
const status=document.querySelector('#status'),button=document.querySelector('#generate'),file=document.querySelector('#videoFile'),download=document.querySelector('#download');
let zipMode=false;
download.addEventListener('click',()=>{zipMode=true;button.click()});
file.addEventListener('change',()=>{invalidateApproval();const selected=!!file.files.length;document.querySelector('#videoReminder').textContent=selected?'Video ready: '+file.files[0].name+'. Tap the yellow button to generate the sheet.':'Select the original video above. JSON restores frame numbers only.';status.textContent=selected?'Selected: '+file.files[0].name:'Choose a video first.'});
button.addEventListener('click',async()=>{\n  invalidateApproval();
  status.textContent='Button pressed. Checking video…';
  if(!file.files.length){status.textContent='JSON loaded, but no video selected. Choose your original swing video in the Video field, then tap this button again.';document.querySelector('#videoReminder').textContent=status.textContent;file.scrollIntoView({behavior:'smooth',block:'center'});file.focus();return}
  const automatic=document.querySelector('#automatic').checked;\n  const indices=document.querySelector('#frames').value.trim();
  if(!automatic && !/^\\d+(\\s*,\\s*\\d+){9}$/.test(indices)){status.textContent='Enter exactly ten frame numbers, separated by commas.';return}\n  const parsed=indices.split(',').map(v=>Number(v.trim()));\n  if(!automatic && parsed.some((v,i)=>i>0 && v<=parsed[i-1])){status.textContent='Frame numbers must increase from P1 through P10. Correct the highlighted checkpoint values.';return}
  button.disabled=true;download.disabled=true;button.textContent='Processing…';
  status.textContent='Uploading '+file.files[0].name+' and decoding frames. Please wait…';
  const currentZipMode=zipMode;zipMode=false;
  const request=new XMLHttpRequest();
  request.open('POST','/api/biomechanics/contact-sheet');
  request.responseType='blob';request.timeout=90000;
  let uploaded=false;
  request.upload.onprogress=e=>{status.textContent=e.lengthComputable?'Uploading: '+Math.round(e.loaded/e.total*100)+'%':'Uploading video…'};
  request.upload.onload=()=>{uploaded=true;status.textContent='Upload complete. Server is decoding frames…'};
  const reset=()=>{button.disabled=false;download.disabled=false;button.textContent='View ten frames on screen'};
  request.onload=()=>{reset();if(request.status!==200){status.textContent='Server error '+request.status+'. Try a shorter MP4.';return}
    const url=URL.createObjectURL(request.response);
    if(!currentZipMode){const area=document.querySelector('#sheetArea');area.replaceChildren();const img=document.createElement('img');img.src=url;img.alt='Ten-frame swing contact sheet, candidates requiring coach review';img.style.cssText='width:100%;height:auto;border:2px solid #e3c46c';area.appendChild(img);reviewedSnapshot={indices:indices,angle:document.querySelector('#angle').value,name:file.files[0].name};confirmBox.disabled=false;status.textContent='Sheet displayed below. Review each frame; P-position labels are not automatically verified.';return}
    const a=document.createElement('a');
    a.href=url;a.download='WSBCO_P1-P10.zip';document.body.appendChild(a);a.click();a.remove();
    status.textContent='Finished. If no download appeared, tap this link: ';
    const link=document.createElement('a');link.href=url;link.download='WSBCO_P1-P10.zip';link.textContent='Download ZIP';link.style.color='#ffe49c';status.appendChild(link);
    setTimeout(()=>URL.revokeObjectURL(url),120000);
  };
  request.onerror=()=>{reset();status.textContent='Network error while '+(uploaded?'processing':'uploading')};
  request.ontimeout=()=>{reset();status.textContent='Timed out after 90 seconds. Try a shorter MP4.'};
  request.onabort=()=>{reset();status.textContent='Request cancelled'};
  const data=new FormData(document.querySelector('#form'));data.set('output_format',currentZipMode?'zip':'png');\n  if(automatic)data.set('frame_indices','auto');\n  request.send(data);

});
const coachingGuidance={
 alignment:{test:'Check P1 target line, feet, hips and shoulders with alignment sticks; compare start direction to target.',priority:'Verify aim first before changing the swing.',drill:'Alignment station: target stick and parallel feet-line stick; repeat five balls.',verification:'Track start direction and dispersion with Garmin R10 before and after.'},
 ball_position:{test:'Verify P1 ball position relative to lead heel and club; inspect low point and strike.',priority:'Correct ball position before modifying release or path.',drill:'Place a ball-position reference stick and rehearse five consistent setups.',verification:'Compare launch direction, launch angle and contact quality with R10.'},
 balance:{test:'Review P7–P10 weight support and finish stability; screen ankle, hip and single-leg balance.',priority:'Find whether setup, pressure shift or physical capacity limits a stable finish.',drill:'Hold a balanced finish for three seconds on five half-swings.',verification:'Count stable finishes and compare ball contact; do not infer force plates from video.'},
 transition:{test:'Inspect P4–P6 sequence and timing; check hip/thoracic mobility and ability to separate pelvis and torso.',priority:'Identify a repeatable transition cue rather than force an untested body position.',drill:'Slow-motion pump rehearsal from P4 through P6, then three-quarter shots.',verification:'Compare filmed P4–P6 checkpoints and R10 path consistency.'},
 face_path:{test:'Compare initial ball direction and curvature with R10 face, path and face-to-path; confirm strike location.',priority:'Establish face and path evidence before changing mechanics.',drill:'Start-line gate drill with an intermediate target and half-swings.',verification:'Record face, club path and face-to-path before and after.'}
};
document.querySelector('#analyze').addEventListener('click',()=>{
 const out=document.querySelector('#analysisResult');out.replaceChildren();
 if(!reviewedSnapshot||!confirmBox.checked){out.textContent='First display the ten frames and check the coach approval box. This worksheet requires a current reviewed sheet.';return}
 const issue=document.querySelector('#swingIssue').value,flight=document.querySelector('#ballFlight').value,notes=document.querySelector('#coachNotes').value.trim(),tpi=document.querySelector('#tpiStatus').value;
 if(!issue){out.textContent='Choose a primary observed issue before generating guidance.';return}
 const g=coachingGuidance[issue],sections=[['Evidence','Coach-reviewed '+reviewedSnapshot.angle.toUpperCase()+' P1–P10 candidate frames; ball flight: '+(flight||'not recorded')+'. '+(notes||'No coach notes entered.')],['TGM / ball-flight diagnostic test',g.test],['First coaching priority',g.priority],['Drill',g.drill],['Before / after verification',g.verification],['TPI body–swing connection',tpi==='screened'?'Screen marked complete; use documented results before prescribing mobility or stability changes.':'Not screened: do not assume a mobility or stability restriction.'],['Evidence limitation','No tracked club/pose landmarks or measured 3D biomechanics. These are testable hypotheses, not an automated diagnosis.']];
 sections.forEach(([heading,content])=>{const h=document.createElement('h3');h.textContent=heading;h.style.cssText='font-size:16px;color:#f3d183;margin:12px 0 4px';const p=document.createElement('p');p.textContent=content;p.style.margin='0 0 8px';out.append(h,p)});
});
</script></html>"""