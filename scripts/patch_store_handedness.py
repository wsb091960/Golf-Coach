from pathlib import Path

path = Path("app/store.py")
text = path.read_text(encoding="utf-8")

text = text.replace(
    '"skill_level": student.skill_level,\n        "handicap_index": student.handicap_index,',
    '"skill_level": student.skill_level,\n        "handedness": student.handedness,\n        "handicap_index": student.handicap_index,',
)

text = text.replace(
    'skill_level=str(student.get("skill_level") or "").strip(),\n            handicap_index=student.get("handicap_index"),',
    'skill_level=str(student.get("skill_level") or "").strip(),\n            handedness=str(student.get("handedness") or "Unknown").strip(),\n            handicap_index=student.get("handicap_index"),',
)

text = text.replace(
    '"skill_level",\n            "handicap_index",',
    '"skill_level",\n            "handedness",\n            "handicap_index",',
)

path.write_text(text, encoding="utf-8")
print("Updated app/store.py for handedness")
