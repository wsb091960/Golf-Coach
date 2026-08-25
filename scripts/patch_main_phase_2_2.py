from pathlib import Path
path = Path("app/main.py")
text = path.read_text(encoding="utf-8")
imp = "from app.routers.videos import router as videos_router\n"
if imp not in text:
    marker = "from app.routers.students import router as students_router\n"
    if marker not in text: raise SystemExit("students_router import not found")
    text = text.replace(marker, marker + imp, 1)
inc = "app.include_router(videos_router)\n"
if inc not in text:
    marker = "app.include_router(analysis_router)\n"
    if marker not in text: raise SystemExit("analysis_router include not found")
    text = text.replace(marker, marker + inc, 1)
path.write_text(text, encoding="utf-8")
print("Updated app/main.py for Phase 2.2")
