import math
import re


HM_MILES = 13.1


def parse_hhmmss(value: str) -> int | None:
    match = re.fullmatch(r"(\d{1,2}):([0-5]\d):([0-5]\d)", (value or "").strip())
    if not match:
        return None
    hours, minutes, seconds = map(int, match.groups())
    return (hours * 3600) + (minutes * 60) + seconds


def format_seconds(total_seconds: int | float | None) -> str:
    if total_seconds is None or total_seconds < 0:
        return ""
    total = int(round(total_seconds))
    hours = total // 3600
    minutes = (total % 3600) // 60
    seconds = total % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def format_pace(seconds_per_mile: float | None) -> str:
    if seconds_per_mile is None or seconds_per_mile <= 0:
        return ""
    rounded = int(round(seconds_per_mile))
    minutes = rounded // 60
    seconds = rounded % 60
    return f"{minutes}:{seconds:02d} /mi"


def compute_required_run_metrics(target_finish_time: str, t2_time: str) -> dict | None:
    target_total_seconds = parse_hhmmss(target_finish_time)
    t2_seconds = parse_hhmmss(t2_time)
    if target_total_seconds is None or t2_seconds is None:
        return None

    target_run_seconds = target_total_seconds - t2_seconds
    if target_run_seconds <= 0:
        return None

    pace_seconds_per_mile = target_run_seconds / HM_MILES
    return {
        "target_total_seconds": target_total_seconds,
        "t2_seconds": t2_seconds,
        "target_run_seconds": target_run_seconds,
        "target_run_time": format_seconds(target_run_seconds),
        "pace_seconds_per_mile": pace_seconds_per_mile,
        "required_pace": format_pace(pace_seconds_per_mile),
    }


def compute_run_progress_status(
    target_run_seconds: int,
    run_elapsed_seconds: int,
    run_distance_miles: float,
) -> dict | None:
    if target_run_seconds <= 0 or run_elapsed_seconds < 0 or run_distance_miles <= 0:
        return None

    goal_pace_seconds = target_run_seconds / HM_MILES
    expected_seconds = goal_pace_seconds * run_distance_miles
    delta_seconds = math.floor(run_elapsed_seconds - expected_seconds)
    if delta_seconds < 0:
        state = "ahead"
    elif delta_seconds > 0:
        state = "behind"
    else:
        state = "on"

    return {
        "state": state,
        "delta_seconds": delta_seconds,
        "expected_seconds": int(round(expected_seconds)),
        "goal_pace_seconds": goal_pace_seconds,
    }
