from src.retail_features import detect_persons_yolo, queue_wait_estimate, shelf_occupancy, dwell_heatmap, download_sample_video
def test_retail(tmp_path):
    download_sample_video(tmp_path / "vid.txt")
    assert "frame_counts" in detect_persons_yolo()
    assert queue_wait_estimate(10)["est_wait_minutes"] > 0
    assert shelf_occupancy({"sku1": 0.1})[0]["low_stock"] is True
    assert dwell_heatmap([1,2,3]).shape[0] == 8
