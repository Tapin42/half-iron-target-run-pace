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
from src.storage import AthleteStore


load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")

races = load_race_configs()
default_race_slug = next(iter(races))
rtrt_service = RtrtService(RtrtClient())
store = AthleteStore(os.getenv("ATHLETE_CONFIG_FILE", "data/athletes.json"))


@app.route("/")
def home():
    athletes = store.list()
    return render_template(
        "index.html",
        race_options=races.values(),
        athletes=athletes,
        default_race_slug=default_race_slug,
        error=None,
    )


@app.post("/config")
def save_config():
    race_slug = request.form.get("race_slug", default_race_slug)
    entry_id = (request.form.get("entry_id") or "").strip()
    name = (request.form.get("name") or "").strip()
    bib = (request.form.get("bib") or "").strip()
    division = (request.form.get("division") or "").strip()
    target_finish_time = (request.form.get("target_finish_time") or "").strip()

    if race_slug not in races:
        error = "Unknown race selection."
    elif not entry_id or not name:
        error = "Select an athlete from search results first."
    elif parse_hhmmss(target_finish_time) is None:
        error = "Target finish must be in HH:MM:SS format."
    else:
        store.add(
            race_slug=race_slug,
            entry_id=entry_id,
            bib=bib,
            name=name,
            division=division,
            target_finish_time=target_finish_time,
        )
        return redirect(url_for("home"))

    return render_template(
        "index.html",
        race_options=races.values(),
        athletes=store.list(),
        default_race_slug=race_slug,
        error=error,
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
        return jsonify({"error": f"Search failed: {exc}"}), 502

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
    try:
        splits = rtrt_service.fetch_splits(race, athlete["entry_id"])
    except Exception as exc:
        detail_error = f"Could not load splits: {exc}"

    latest_split = find_latest_split(splits)
    t2_split = find_t2_split(splits)

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

    return render_template(
        "athlete_detail.html",
        athlete=athlete,
        race=race,
        splits=splits,
        latest_split=latest_split,
        t2_split=t2_split,
        metrics=metrics,
        progress=progress,
        detail_error=detail_error,
    )


if __name__ == "__main__":
    app.run(debug=True)
