from pathlib import Path
from jinja2 import Environment

root = Path(__file__).resolve().parents[1]
html = (root/"app/templates/session_detail.html").read_text()
router = (root/"app/routers/videos.py").read_text()

Environment().parse(html)

assert 'id="original-swing-upload-form"' in html
assert 'id="original-swing-video-file"' in html
assert 'id="original-swing-upload-progress"' in html
assert "/videos/chunked/init" in html
assert "/part/${index}" in html
assert "/finalize" in html
assert 'event.preventDefault()' in html
assert 'video_type: "original_swing"' in html
assert 'Uploading Swing Video — ${percent}%' in html
assert "analysisModal" not in html

assert '"/{session_id}/videos/chunked/init"' in router
assert '"/{session_id}/videos/chunked/{upload_id}/part/{index}"' in router
assert '"/{session_id}/videos/chunked/{upload_id}/finalize"' in router
assert "CHUNK_BYTES = 512 * 1024" in router
assert "Video exceeds 750 MB" in router

print("phase 5.2.7E chunked swing video upload tests passed")
