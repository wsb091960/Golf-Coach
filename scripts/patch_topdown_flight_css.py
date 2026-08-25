from pathlib import Path

path = Path("app/templates/session_detail.html")
text = path.read_text(encoding="utf-8")

href = '<link rel="stylesheet" href="/static/css/topdown_flight.css">'

if href in text:
    print("topdown_flight.css already linked.")
    raise SystemExit(0)

marker = '<link rel="stylesheet" href="/static/css/session_performance.css">'

if marker not in text:
    raise SystemExit("Could not find session_performance.css link.")

text = text.replace(marker, marker + "\n" + href, 1)
path.write_text(text, encoding="utf-8")

print("Linked topdown_flight.css.")
