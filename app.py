import os
from flask import Flask, flash, jsonify, redirect, render_template, request, url_for
from dotenv import load_dotenv
from markupsafe import Markup, escape

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
from src.storage import AthleteStore


load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")

races = load_race_configs()
default_race_slug = next(iter(races))
rtrt_service = RtrtService(RtrtClient())
store = AthleteStore(os.getenv("ATHLETE_CONFIG_FILE", "data/athletes.json"))
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


def _athletes_with_latest_split_snapshot(
    rows: list[dict], *, sim_elapsed: int | None
) -> list[dict]:
    enriched: list[dict] = []
    for athlete in rows:
        athlete_row = dict(athlete)
        athlete_row["latest_split"] = None
        race = races.get(athlete_row.get("race_slug"))
        if not race:
            enriched.append(athlete_row)
            continue
        try:
            entry_id = athlete_row.get("entry_id", "")
            profile_id = athlete_row.get("profile_id")
            if profile_id:
                splits = rtrt_service.fetch_splits(race, entry_id, profile_id=profile_id)
            else:
                splits = rtrt_service.fetch_splits(race, entry_id)
            splits = _filter_splits_for_sim_elapsed(splits, sim_elapsed)
            athlete_row["latest_split"] = find_latest_split(splits)
        except Exception:
            app.logger.exception(
                "RTRT split fetch failed while loading home snapshot for athlete %s",
                athlete_row.get("entry_id", ""),
            )
        enriched.append(athlete_row)
    return enriched


def _render_config_page(*, error: str | None, race_slug: str):
    return render_template(
        "config.html",
        race_options=races.values(),
        default_race_slug=race_slug,
        error=error,
        error_html=None,
    )


@app.route("/")
def home():
    sim_elapsed = _sim_elapsed_from_request()
    mode = (request.args.get("mode") or "").strip().lower()
    active_mode = mode if mode in {"edit", "delete"} else None
    active_athlete_id = (request.args.get("athlete_id") or "").strip() if active_mode else None
    athletes = _athletes_with_latest_split_snapshot(store.list(), sim_elapsed=sim_elapsed)
    return render_template(
        "index.html",
        athletes=athletes,
        sim_elapsed=sim_elapsed,
        sim_checkpoints=_simulation_checkpoints(),
        active_mode=active_mode,
        active_athlete_id=active_athlete_id,
    )


@app.get("/config")
def config_page():
    return _render_config_page(error=None, race_slug=default_race_slug)


@app.post("/config")
def save_config():
    race_slug = request.form.get("race_slug", default_race_slug)
    entry_id = (request.form.get("entry_id") or "").strip()
    profile_id = (request.form.get("profile_id") or "").strip()
    name = (request.form.get("name") or "").strip()
    bib = (request.form.get("bib") or "").strip()
    division = (request.form.get("division") or "").strip()
    target_finish_time = (request.form.get("target_finish_time") or "").strip()

    identity_check = store.find_by_identity(race_slug=race_slug, entry_id=entry_id, bib=bib)

    error_html = None

    if race_slug not in races:
        error = "Unknown race selection."
    elif not name:
        error = "Select an athlete from search results first."
    elif not entry_id and not bib:
        error = "Provide at least one athlete identity (entry ID or bib)."
    elif identity_check["status"] == "match":
        athlete_id = identity_check["athlete"]["id"]
        edit_url = url_for("home", mode="edit", athlete_id=athlete_id)
        error = "This athlete is already configured."
        error_html = Markup(
            f'This athlete is already configured. <a href="{escape(edit_url)}">Go to athlete list to edit this row.</a>'
        )
    elif identity_check["status"] == "conflict":
        error = "Entry ID and bib point to different athletes."
    elif parse_hhmmss(target_finish_time) is None:
        error = "Target finish must be in HH:MM:SS format."
    else:
        try:
            store.add(
                race_slug=race_slug,
                entry_id=entry_id,
                profile_id=profile_id,
                bib=bib,
                name=name,
                division=division,
                target_finish_time=target_finish_time,
            )
            return redirect(url_for("home"))
        except ValueError as exc:
            if str(exc) == "duplicate identity":
                identity_match = store.find_by_identity(race_slug=race_slug, entry_id=entry_id, bib=bib)
                if identity_match["status"] == "match":
                    athlete_id = identity_match["athlete"]["id"]
                    edit_url = url_for("home", mode="edit", athlete_id=athlete_id)
                    error = "This athlete is already configured."
                    error_html = Markup(
                        f'This athlete is already configured. <a href="{escape(edit_url)}">Go to athlete list to edit this row.</a>'
                    )
                else:
                    error = "This athlete is already configured."
            elif str(exc) == "conflicting identity":
                error = "Entry ID and bib point to different athletes."
            elif str(exc) == "missing identity":
                error = "Provide at least one athlete identity (entry ID or bib)."
            else:
                error = "Could not save athlete configuration."

    return render_template(
        "config.html",
        race_options=races.values(),
        default_race_slug=race_slug,
        error=error,
        error_html=error_html,
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


@app.get("/athlete/<athlete_id>")
def athlete_detail(athlete_id: str):
    athlete = store.get(athlete_id)
    if not athlete:
        return redirect(url_for("home"))

    race = races.get(athlete["race_slug"])
    if not race:
        return redirect(url_for("home"))

    detail_error = None
    splits: list[dict] = []
    sim_elapsed = _sim_elapsed_from_request()
    try:
        if athlete.get("profile_id"):
            splits = rtrt_service.fetch_splits(
                race, athlete["entry_id"], profile_id=athlete["profile_id"]
            )
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
    run_split_parse_warning = _has_unparsable_run_split(
        splits,
        t2_split["seconds"] if t2_split else None,
    )

    metrics = None
    progress = None
    if t2_split:
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
        sim_checkpoints=_simulation_checkpoints(),
    )


@app.post("/athlete/<athlete_id>/target")
def update_athlete_target(athlete_id: str):
    athlete = store.get(athlete_id)
    if not athlete:
        flash("Athlete not found; target was not updated.", "warning")
        return redirect(url_for("home"))

    target_finish_time = (request.form.get("target_finish_time") or "").strip()
    if parse_hhmmss(target_finish_time) is None:
        flash("Target finish must be in HH:MM:SS format.", "error")
        return redirect(url_for("home"))

    store.update_target_time(athlete_id, target_finish_time)
    flash(f"Updated target finish time to {target_finish_time} for {athlete['name']}.", "success")
    return redirect(url_for("home"))


@app.post("/athlete/<athlete_id>/delete")
def delete_athlete(athlete_id: str):
    confirm = (request.form.get("confirm") or "").strip().lower()
    if confirm != "yes":
        flash("Delete not confirmed; athlete was not removed.", "warning")
        return redirect(url_for("home"))

    deleted = store.delete(athlete_id)
    if not deleted:
        flash("Athlete not found; nothing was deleted.", "warning")
        return redirect(url_for("home"))

    flash(f"Removed athlete {deleted['name']}.", "success")
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)
