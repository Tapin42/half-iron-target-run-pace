from src.calculations import (
    compute_required_run_metrics,
    compute_run_progress_status,
    format_seconds,
    parse_hhmmss,
)


def test_parse_hhmmss_valid():
    assert parse_hhmmss("4:35:10") == 16510


def test_parse_hhmmss_invalid():
    assert parse_hhmmss("4:75:10") is None
    assert parse_hhmmss("abc") is None


def test_format_seconds():
    assert format_seconds(3661) == "01:01:01"


def test_required_run_metrics_from_t2():
    metrics = compute_required_run_metrics("05:30:00", "03:40:00")
    assert metrics is not None
    assert metrics["target_run_seconds"] == 6600
    assert metrics["target_run_time"] == "01:50:00"
    assert metrics["required_pace"] == "8:24 /mi"


def test_required_run_metrics_not_possible():
    assert compute_required_run_metrics("04:30:00", "04:35:00") is None


def test_run_progress_ahead():
    status = compute_run_progress_status(
        target_run_seconds=6600,
        run_elapsed_seconds=1200,
        run_distance_miles=3.0,
    )
    assert status["state"] == "ahead"
    assert status["delta_seconds"] == -312


def test_run_progress_behind():
    status = compute_run_progress_status(
        target_run_seconds=6600,
        run_elapsed_seconds=1800,
        run_distance_miles=3.0,
    )
    assert status["state"] == "behind"
    assert status["delta_seconds"] == 288
