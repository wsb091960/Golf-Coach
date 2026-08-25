from pathlib import Path

path = Path("app/store.py")
text = path.read_text(encoding="utf-8")

text = text.replace(
    '"club": shot.club,\n        "source": shot.source,',
    '"club": shot.club,\n        "shot_shape": shot.shot_shape,\n        "source": shot.source,'
)

text = text.replace(
    'club=str(shot.get("club") or ""),\n            source=str(shot.get("source") or "Garmin R10"),',
    'club=str(shot.get("club") or ""),\n            shot_shape=str(shot.get("shot_shape") or ""),\n            source=str(shot.get("source") or "Garmin R10"),'
)

text = text.replace(
    '"club",\n            "included",',
    '"club",\n            "shot_shape",\n            "included",'
)

path.write_text(text, encoding="utf-8")
print("Updated app/store.py for shot_shape")
