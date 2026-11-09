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
<form id="form"><label>Video <input type="file" name="video" accept="video/*" required></label>
<label>Camera angle <select name="camera_angle" id="angle"><option value="dtl">Down the line</option><option value="fo">Face on</option></select></label>
<label>Ten frame indices <input style="width:95%" name="frame_indices" id="frames" value="235,255,270,288,304,310,313,318,325,340" required></label>
<button type="submit">Generate ZIP contact sheet</button></form><p id="status" role="status"></p>
<small>Initial values are only test candidates for the two previously reviewed recordings. They are not automatic detections. No footage is persisted by this endpoint; uploads are processed in temporary files. Avoid uploading sensitive student footage to this unauthenticated test preview.</small>
<script>
const samples={dtl:'235,255,270,288,304,310,313,318,325,340',fo:'250,264,270,285,295,300,304,310,315,325'};
document.querySelector('#angle').addEventListener('change',e=>document.querySelector('#frames').value=samples[e.target.value]);
document.querySelector('#form').addEventListener('submit',async e=>{e.preventDefault();const status=document.querySelector('#status');status.textContent='Uploading and decoding frames…';try{const response=await fetch('/api/biomechanics/contact-sheet',{method:'POST',body:new FormData(e.target)});if(!response.ok){status.textContent='Error: '+(await response.text()).slice(0,500);return}const blob=await response.blob(),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='WSBCO_P1-P10.zip';a.click();setTimeout(()=>URL.revokeObjectURL(url),5000);status.textContent='ZIP generated. Review the ten frames before approving any P-position.'}catch(err){status.textContent='Upload failed: '+err.message}});
</script></html>"""
