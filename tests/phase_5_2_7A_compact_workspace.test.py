from pathlib import Path
root=Path(__file__).resolve().parents[1]
h=(root/'app/templates/swing_analysis_onform.html').read_text()
c=(root/'app/static/css/swing_analysis_workspace.css').read_text()
assert 'compact-evidence-strip' in h
assert 'onform-screenshot-file-3' in h
assert 'compact-sequence-review' in h
assert 'push-draw-coaching-read' in h
assert 'height: 150px !important' in c
print('phase 5.2.7A compact workspace tests passed')
