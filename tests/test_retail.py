from src.retail import analyze_synthetic_frame, run_demo_session
def test_frame():
    a = analyze_synthetic_frame(0)
    assert a.people_count >= 0
    assert a.queue_length >= 0
def test_session():
    s = run_demo_session(5)
    assert len(s) == 5
