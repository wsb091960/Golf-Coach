from app.gcie.lesson_generator import PATTERNS, generate

def test_all_nine_patterns_generate_complete_provisional_plans():
    assert len(PATTERNS) == 9
    for pattern in PATTERNS:
        plan = generate(pattern, "right", "Driver", "")
        assert "PROVISIONAL / UNVERIFIED" in plan
        assert "TGM FRAMEWORK" in plan
        assert "P1–P10" in plan
        assert "TPI BODY" in plan
        assert "GARMIN R10" in plan
        assert "No measured outcome yet" in plan

def test_push_draw_targets_not_presented_as_measurements():
    plan = generate("push-draw", "right", "Driver", "")
    assert "NOT measurements" in plan
    assert "face-to-path −1.5°" in plan

def test_left_handed_plan_flags_direction_reversal():
    assert "reverse the directional descriptions" in generate("push-draw", "left", "Driver", "test")
