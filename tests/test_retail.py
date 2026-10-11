import pytest

from src.retail import SERVICE_RATE_PER_MIN, analyze_synthetic_frame, run_demo_session


def test_frame():
    analysis = analyze_synthetic_frame(0)
    assert analysis.people_count >= 0
    assert analysis.queue_length >= 0
    assert analysis.est_wait_sec == pytest.approx(analysis.queue_length / SERVICE_RATE_PER_MIN * 60)


def test_session():
    session = run_demo_session(5)
    assert len(session) == 5
    assert all(frame["est_wait_sec"] == pytest.approx(frame["queue_length"] / SERVICE_RATE_PER_MIN * 60) for frame in session)


@pytest.mark.parametrize("frames", [0, -1, 1.5, True])
def test_demo_session_rejects_invalid_frame_counts(frames):
    with pytest.raises(ValueError, match="positive integer"):
        run_demo_session(frames=frames)


@pytest.mark.parametrize("threshold", [0, -1, 2.5, True])
def test_demo_session_rejects_invalid_queue_thresholds(threshold):
    with pytest.raises(ValueError, match="positive integer"):
        run_demo_session(queue_threshold=threshold)
