import pytest

from src.calculations import (
    compute_required_run_metrics,
    compute_run_progress_status,
    format_pace,
    format_seconds,
    parse_hhmmss,
)
from src.rtrt_service import find_best_run_split, parse_run_distance


def test_parse_hhmmss_valid():
    assert parse_hhmmss("4:35:10") == 16510


def test_parse_hhmmss_invalid():
    assert parse_hhmmss("4:75:10") is None
    assert parse_hhmmss("abc") is None
    assert parse_hhmmss("-1:10:00") is None


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
    assert compute_required_run_metrics("04:30:00", "04:30:00") is None


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


def test_run_progress_on_pace():
    status = compute_run_progress_status(
        target_run_seconds=6600,
        run_elapsed_seconds=1512,
        run_distance_miles=3.0,
    )
    assert status["state"] == "on"
    assert status["delta_seconds"] == 0


def test_format_pace():
    assert format_pace(504.2) == "8:24 /mi"


def test_parse_run_distance_miles_and_km():
    assert parse_run_distance("RUN 5 MI") == 5.0
    assert parse_run_distance("RUN 10K") == 6.21371


def test_parse_run_distance_supports_comma_decimal_km():
    assert parse_run_distance("Run 2,6 km") == pytest.approx(1.6155646, rel=1e-6)
    assert parse_run_distance("Run 6,1 km") == pytest.approx(3.7903629999999996, rel=1e-6)


def test_parse_run_distance_supports_meter_checkpoints():
    assert parse_run_distance("Run 400 m") == pytest.approx(0.2485484, rel=1e-6)


def test_find_best_run_split_uses_farthest_recognized_distance():
    splits = [
        {"name": "T2", "seconds": 13200, "distance_miles": None},
        {"name": "RUN 3 MI", "seconds": 15000, "distance_miles": 3.0},
        {"name": "RUN 5 MI", "seconds": 17000, "distance_miles": 5.0},
        {"name": "RUN", "seconds": 18000, "distance_miles": None},
    ]
    best = find_best_run_split(splits, t2_seconds=13200)
    assert best is not None
    assert best["name"] == "RUN 5 MI"
