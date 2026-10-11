import numpy as np
import pytest

from src.retail_features import (
    detect_persons_yolo,
    dwell_heatmap,
    download_sample_video,
    queue_wait_estimate,
    shelf_occupancy,
    shopper_count_series,
)


def test_retail(tmp_path):
    download_sample_video(tmp_path / "vid.txt")
    unavailable = detect_persons_yolo()
    assert unavailable["backend"] == "unavailable"
    assert unavailable["frame_counts"] == []
    assert unavailable["total_detections"] is None
    assert queue_wait_estimate(10)["est_wait_minutes"] == 6.67
    assert shelf_occupancy({"sku1": 0.1})[0]["low_stock"] is True
    assert dwell_heatmap([1, 2, 3]).shape == (8, 8)


@pytest.mark.parametrize("queue", [-1, 1.5, True, 10001])
def test_queue_estimator_rejects_invalid_queue_lengths(queue):
    with pytest.raises(ValueError, match="queue_length"):
        queue_wait_estimate(queue)


@pytest.mark.parametrize("rate", [0, -1, float("nan"), float("inf"), True])
def test_queue_estimator_rejects_invalid_service_rates(rate):
    with pytest.raises(ValueError, match="positive finite"):
        queue_wait_estimate(3, service_rate_per_min=rate)


@pytest.mark.parametrize("grid", [0, -1, 1.5, True, 257])
def test_heatmap_rejects_invalid_grid(grid):
    with pytest.raises(ValueError, match="positive integer"):
        dwell_heatmap([1, 2], grid=grid)


def test_heatmap_rejects_negative_or_nonfinite_counts():
    with pytest.raises(ValueError, match="finite non-negative"):
        dwell_heatmap([1, -1])
    with pytest.raises(ValueError, match="finite non-negative"):
        dwell_heatmap([1, np.nan])


@pytest.mark.parametrize("threshold", [-0.1, 1.1, float("nan"), True])
def test_shelf_occupancy_rejects_invalid_thresholds(threshold):
    with pytest.raises(ValueError, match="between 0 and 1"):
        shelf_occupancy({"sku": 0.5}, threshold=threshold)


@pytest.mark.parametrize("level", [-0.1, 1.1, float("inf"), True])
def test_shelf_occupancy_rejects_invalid_levels(level):
    with pytest.raises(ValueError, match="between 0 and 1"):
        shelf_occupancy({"sku": level})


def test_shopper_count_series_rejects_negative_or_fractional_values():
    with pytest.raises(ValueError, match="whole numbers"):
        shopper_count_series([1, -1])
    with pytest.raises(ValueError, match="whole numbers"):
        shopper_count_series([1, 1.5])



def test_detector_never_substitutes_sample_counts_when_no_input_is_provided():
    result = detect_persons_yolo()

    assert result["backend"] == "unavailable"
    assert result["frame_counts"] == []
    assert result["total_detections"] is None
    assert "No measurements were generated" in result["error"]


def test_detector_rejects_missing_media_without_fake_counts(tmp_path):
    result = detect_persons_yolo(tmp_path / "missing.mp4")

    assert result["backend"] == "unavailable"
    assert result["frame_counts"] == []
    assert result["total_detections"] is None
