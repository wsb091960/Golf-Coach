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
<h1>WSBCO Server-Decoded Swing Sheet</h1><p>Test-only preview. Upload one video and ten <b>decoded frame indices</b> in P1–P10 order. Frames are extracted on the server, not by browser seeking.</p>
<form id="form"><label>Video <input type="file" name="video" accept="video/mp4,video/quicktime,video/x-m4v,video/*" id="videoFile"></label>
<label>Camera angle <select name="camera_angle" id="angle"><option value="dtl">Down the line</option><option value="fo">Face on</option></select></label>
<label>Ten frame indices <input style="width:95%" name="frame_indices" id="frames" value="235,255,270,288,304,310,313,318,325,340" required></label>
<button type="button" id="generate">Generate ten-frame sheet</button></form><p id="status" role="status" aria-live="polite" style="min-height:2em;color:#ffe49c;font-weight:700"></p>
<small>Initial values are only test candidates for the two previously reviewed recordings. They are not automatic detections. No footage is persisted by this endpoint; uploads are processed in temporary files. Avoid uploading sensitive student footage to this unauthenticated test preview.</small>
<script>
const samples={dtl:'235,255,270,288,304,310,313,318,325,340',fo:'250,264,270,285,295,300,304,310,315,325'};
document.querySelector('#angle').addEventListener('change',e=>document.querySelector('#frames').value=samples[e.target.value]);
const status=document.querySelector('#status'),button=document.querySelector('#generate'),file=document.querySelector('#videoFile');
file.addEventListener('change',()=>{status.textContent=file.files.length?'Selected: '+file.files[0].name:'Choose a video first.'});
button.addEventListener('click',async()=>{
  status.textContent='Button pressed. Checking video…';
  if(!file.files.length){status.textContent='Please choose a video above, then press the yellow button again.';file.focus();return}
  const indices=document.querySelector('#frames').value.trim();
  if(!/^\\d+(\\s*,\\s*\\d+){9}$/.test(indices)){status.textContent='Enter exactly ten frame numbers, separated by commas.';return}
  button.disabled=true;button.textContent='Processing…';
  status.textContent='Uploading '+file.files[0].name+' and decoding frames. Please wait…';
  try{
    const response=await fetch('/api/biomechanics/contact-sheet',{method:'POST',body:new FormData(document.querySelector('#form'))});
    if(!response.ok){status.textContent='Server error ('+response.status+'): '+(await response.text()).slice(0,450);return}
    const blob=await response.blob(),url=URL.createObjectURL(blob),a=document.createElement('a');
    a.href=url;a.download='WSBCO_P1-P10.zip';document.body.appendChild(a);a.click();a.remove();
    setTimeout(()=>URL.revokeObjectURL(url),30000);
    status.textContent='Completed: ten-frame ZIP download started. Check Downloads on your device.';
  }catch(err){status.textContent='Connection or upload error: '+err.message}
  finally{button.disabled=false;button.textContent='Generate ten-frame sheet'}
});
</script></html>"""