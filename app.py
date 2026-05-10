import os
from flask import Flask, jsonify, redirect, render_template, request, url_for
from dotenv import load_dotenv

from src.calculations import (
    compute_required_run_metrics,
    compute_run_progress_status,
    format_seconds,
    parse_hhmmss,
)
from src.races import load_race_configs
from src.rtrt_client import RtrtClient
from src.rtrt_service import (
    RtrtService,
    find_best_run_split,
    find_latest_split,
    find_t2_split,
)


load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")

races = load_race_configs()
default_race_slug = next(iter(races))
rtrt_service = RtrtService(RtrtClient())
SIMULATION_CHECKPOINTS = (
    ("Before Start", 0),
    ("During Bike", 15000),
    ("After T2", 16000),
    ("Mid Run", 18000),
    ("One Finished", 19500),
)


def _is_rtrt_config_error(exc: Exception) -> bool:
    return "RTRT credentials are not configured" in str(exc)


def _has_unparsable_run_split(splits: list[dict], t2_seconds: int | None) -> bool:
    for split in splits:
        name = str(split.get("name", "")).upper()
        seconds = split.get("seconds")
        if t2_seconds is not None and isinstance(seconds, int) and seconds < t2_seconds:
            continue
        if "RUN" in name and split.get("distance_miles") is None:
            return True
    return False


def _parse_sim_elapsed(raw_value: str | None) -> int | None:
    if raw_value is None:
        return None
    value = raw_value.strip()
    if not value:
        return None
    if value.isdigit():
        return int(value)
    return parse_hhmmss(value)


def _sim_elapsed_from_request() -> int | None:
    sim_mode = request.args.get("sim_mode")
    if sim_mode and sim_mode != "elapsed":
        return None
    return _parse_sim_elapsed(request.args.get("sim_elapsed"))


def _debug_query_from_request() -> str | None:
    if "debug" not in request.args:
        return None
    return request.args.get("debug")


def _show_simulation_ui(sim_elapsed: int | None) -> bool:
    return sim_elapsed is not None or "debug" in request.args or "sim_elapsed" in request.args


def _filter_splits_for_sim_elapsed(splits: list[dict], sim_elapsed: int | None) -> list[dict]:
    if sim_elapsed is None:
        return splits
    return [
        split
        for split in splits
        if isinstance(split.get("seconds"), int) and split["seconds"] <= sim_elapsed
    ]


def _simulation_checkpoints() -> list[dict]:
    return [
        {"label": label, "seconds": seconds, "display": format_seconds(seconds)}
        for label, seconds in SIMULATION_CHECKPOINTS
    ]


def _is_race_finish_split(split: dict, race_finish_split: str) -> bool:
    split_name = str(split.get("name", "")).strip().upper()
    finish_name = (race_finish_split or "FINISH").strip().upper()
    if not split_name or not finish_name:
        return False
    return split_name == finish_name or split_name.startswith(f"{finish_name} ")


def _render_config_page(*, error: str | None, race_slug: str):
    return render_template(
        "config.html",
        race_options=races.values(),
        default_race_slug=race_slug,
        error=error,
    )


@app.route("/")
def home():
    sim_elapsed = _sim_elapsed_from_request()
    debug_query = _debug_query_from_request()
    show_simulation_ui = _show_simulation_ui(sim_elapsed)
    notice = (request.args.get("notice") or "").strip()
    home_notice = "Unknown athlete." if notice == "unknown-athlete" else None
    return render_template(
        "index.html",
        home_notice=home_notice,
        sim_elapsed=sim_elapsed,
        show_simulation_ui=show_simulation_ui,
        debug_query=debug_query,
        sim_checkpoints=_simulation_checkpoints(),
    )


@app.get("/config")
def config_page():
    return _render_config_page(error=None, race_slug=default_race_slug)


@app.post("/config")
def save_config():
    race_slug = request.form.get("race_slug", default_race_slug)
    return (
        _render_config_page(
            error="JavaScript is required to save athlete configuration in this version.",
            race_slug=race_slug,
        ),
        400,
    )


@app.get("/api/search")
def search_athletes():
    race_slug = request.args.get("race_slug", default_race_slug)
    query = request.args.get("q", "")
    race = races.get(race_slug)
    if not race:
        return jsonify({"error": "Unknown race"}), 400

    try:
        athletes = rtrt_service.search_athletes(race, query)
    except Exception as exc:
        if _is_rtrt_config_error(exc):
            return (
                jsonify(
                    {
                        "error": "RTRT credentials are missing. Configure RTRT_APPID and RTRT_TOKEN."
                    }
                ),
                503,
            )
        app.logger.exception("RTRT search failed")
        return jsonify({"error": "RTRT search is temporarily unavailable. Please try again."}), 502

    return jsonify({"results": athletes})


@app.get("/api/latest-split")
def latest_split():
    race_slug = request.args.get("race_slug", default_race_slug)
    entry_id = (request.args.get("entry_id") or "").strip()
    profile_id = (request.args.get("profile_id") or "").strip()
    race = races.get(race_slug)
    if not race:
        return jsonify({"error": "Unknown race"}), 400
    if not entry_id:
        return jsonify({"error": "Missing entry_id"}), 400

    sim_elapsed = _sim_elapsed_from_request()
    try:
        if profile_id:
            splits = rtrt_service.fetch_splits(race, entry_id, profile_id=profile_id)
        else:
            splits = rtrt_service.fetch_splits(race, entry_id)
        splits = _filter_splits_for_sim_elapsed(splits, sim_elapsed)
        return jsonify({"latest_split": find_latest_split(splits)})
    except Exception:
        app.logger.exception("RTRT split fetch failed for home snapshot")
        return jsonify({"latest_split": None}), 200


@app.get("/athlete/<athlete_id>")
def athlete_resolver(athlete_id: str):
    sim_elapsed = _sim_elapsed_from_request()
    debug_query = _debug_query_from_request()
    return render_template(
        "athlete_resolver.html",
        athlete_id=athlete_id,
        sim_elapsed=sim_elapsed,
        debug_query=debug_query,
    )


@app.get("/athlete/detail")
def athlete_detail_page():
    athlete = {
        "id": (request.args.get("athlete_id") or "").strip(),
        "race_slug": (request.args.get("race_slug") or "").strip(),
        "entry_id": (request.args.get("entry_id") or "").strip(),
        "profile_id": (request.args.get("profile_id") or "").strip(),
        "name": (request.args.get("name") or "").strip(),
        "bib": (request.args.get("bib") or "").strip(),
        "division": (request.args.get("division") or "").strip(),
        "target_finish_time": (request.args.get("target_finish_time") or "").strip(),
    }
    if not athlete["race_slug"] or not athlete["entry_id"] or not athlete["name"]:
        return redirect(url_for("home", notice="unknown-athlete"))

    race = races.get(athlete["race_slug"])
    if not race:
        return redirect(url_for("home", notice="unknown-athlete"))

    detail_error = None
    splits: list[dict] = []
    sim_elapsed = _sim_elapsed_from_request()
    debug_query = _debug_query_from_request()
    show_simulation_ui = _show_simulation_ui(sim_elapsed)
    try:
        if athlete["profile_id"]:
            splits = rtrt_service.fetch_splits(race, athlete["entry_id"], profile_id=athlete["profile_id"])
        else:
            splits = rtrt_service.fetch_splits(race, athlete["entry_id"])
        splits = _filter_splits_for_sim_elapsed(splits, sim_elapsed)
    except Exception as exc:
        if _is_rtrt_config_error(exc):
            detail_error = "RTRT credentials are missing. Configure RTRT_APPID and RTRT_TOKEN."
        else:
            app.logger.exception("RTRT split fetch failed for athlete %s", athlete["entry_id"])
            detail_error = "Could not load split data right now. Please refresh and try again."

    latest_split = find_latest_split(splits)
    t2_split = find_t2_split(splits)
    finish_candidates = [
        split for split in splits if _is_race_finish_split(split, race.finish_split)
    ]
    finish_split = max(finish_candidates, key=lambda split: split["seconds"]) if finish_candidates else None
    run_split_parse_warning = _has_unparsable_run_split(
        splits,
        t2_split["seconds"] if t2_split else None,
    )

    athlete_state = "pre_run"
    if finish_split:
        athlete_state = "finished"
    elif t2_split:
        athlete_state = "on_run"

    finish_summary = None
    target_total_seconds = parse_hhmmss(athlete["target_finish_time"])
    if finish_split and target_total_seconds is not None:
        delta_seconds = finish_split["seconds"] - target_total_seconds
        finish_summary = {
            "result": "hit" if delta_seconds <= 0 else "missed",
            "delta_display": format_seconds(abs(delta_seconds)),
            "finish_time": finish_split["time"],
            "target_time": athlete["target_finish_time"],
        }

    metrics = None
    progress = None
    if t2_split and athlete_state == "on_run":
        metrics = compute_required_run_metrics(athlete["target_finish_time"], t2_split["time"])
        if metrics:
            best_run = find_best_run_split(splits, t2_split["seconds"])
            if best_run:
                run_elapsed = best_run["seconds"] - t2_split["seconds"]
                progress = compute_run_progress_status(
                    target_run_seconds=metrics["target_run_seconds"],
                    run_elapsed_seconds=run_elapsed,
                    run_distance_miles=best_run["distance_miles"],
                )
                if progress:
                    progress["distance_miles"] = best_run["distance_miles"]
                    progress["actual_run_elapsed"] = format_seconds(run_elapsed)
                    progress["delta_display"] = format_seconds(abs(progress["delta_seconds"]))
                    if progress["delta_seconds"] < 0:
                        progress["delta_signed"] = f"-{progress['delta_display']}"
                    else:
                        progress["delta_signed"] = f"+{progress['delta_display']}"

    detail_params = {
        "athlete_id": athlete["id"],
        "race_slug": athlete["race_slug"],
        "entry_id": athlete["entry_id"],
        "profile_id": athlete["profile_id"],
        "name": athlete["name"],
        "bib": athlete["bib"],
        "division": athlete["division"],
        "target_finish_time": athlete["target_finish_time"],
    }
    if debug_query is not None:
        detail_params["debug"] = debug_query

    refresh_params = dict(detail_params)
    if sim_elapsed is not None:
        refresh_params["sim_elapsed"] = sim_elapsed

    checkpoint_links = []
    for checkpoint in _simulation_checkpoints():
        checkpoint_query = dict(detail_params)
        checkpoint_query["sim_elapsed"] = checkpoint["seconds"]
        checkpoint_links.append(
            {"label": checkpoint["label"], "url": url_for("athlete_detail_page", **checkpoint_query)}
        )

    live_url = None
    if sim_elapsed is not None:
        live_url = url_for("athlete_detail_page", **detail_params)

    return render_template(
        "athlete_detail.html",
        athlete=athlete,
        race=race,
        splits=splits,
        latest_split=latest_split,
        t2_split=t2_split,
        metrics=metrics,
        progress=progress,
        run_split_parse_warning=run_split_parse_warning,
        detail_error=detail_error,
        sim_elapsed=sim_elapsed,
        show_simulation_ui=show_simulation_ui,
        debug_query=debug_query,
        sim_checkpoints=_simulation_checkpoints(),
        checkpoint_links=checkpoint_links,
        live_url=live_url,
        athlete_state=athlete_state,
        finish_summary=finish_summary,
        back_url=url_for("home", sim_elapsed=sim_elapsed, debug=debug_query),
        refresh_url=url_for("athlete_detail_page", **refresh_params),
    )


if __name__ == "__main__":
    app.run(debug=True)
