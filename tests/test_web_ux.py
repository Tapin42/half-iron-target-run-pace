import app as app_module
from src.storage import AthleteStore


def _set_temp_store(monkeypatch, tmp_path):
    monkeypatch.setattr(app_module, "store", AthleteStore(str(tmp_path / "athletes.json")))


def test_home_prioritizes_athlete_list_and_links_to_config_page(monkeypatch, tmp_path):
    _set_temp_store(monkeypatch, tmp_path)
    test_client = app_module.app.test_client()

    response = test_client.get("/")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Athlete List" in body
    assert "Configured Athletes" not in body
    assert "Configure Athlete" in body
    assert 'href="/config"' in body
    assert "Half-Iron Target Run Pace</h1>" not in body


def test_config_page_renders_athlete_configuration_form(monkeypatch, tmp_path):
    _set_temp_store(monkeypatch, tmp_path)
    test_client = app_module.app.test_client()

    response = test_client.get("/config")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Configure Athlete Target" in body
    assert 'id="search_term"' in body
    assert 'id="search-results"' in body
    assert 'id="entry_id"' in body
    assert 'id="profile_id"' in body
    assert "Save Athlete Target" in body


def test_config_page_search_input_handles_enter_without_submitting_form(monkeypatch, tmp_path):
    _set_temp_store(monkeypatch, tmp_path)
    test_client = app_module.app.test_client()

    response = test_client.get("/config")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert 'const searchTermInput = document.getElementById("search_term");' in body
    assert 'searchTermInput.addEventListener("keydown", (event) => {' in body
    assert 'if (event.key !== "Enter") {' in body
    assert "event.preventDefault();" in body
    assert "searchBtn.click();" in body


def test_config_page_includes_venice_race_option(monkeypatch, tmp_path):
    _set_temp_store(monkeypatch, tmp_path)
    test_client = app_module.app.test_client()

    response = test_client.get("/config")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Ironman 70.3 Venice" in body


def test_save_config_persists_profile_id_from_selected_athlete(monkeypatch, tmp_path):
    _set_temp_store(monkeypatch, tmp_path)
    test_client = app_module.app.test_client()

    response = test_client.post(
        "/config",
        data={
            "race_slug": "venice-70.3",
            "entry_id": "entry-130",
            "profile_id": "RFX9NGWK",
            "name": "Kiel Bur",
            "bib": "130",
            "division": "M40-44",
            "target_finish_time": "04:00:00",
        },
    )

    assert response.status_code == 302
    row = app_module.store.list()[0]
    assert row["profile_id"] == "RFX9NGWK"


def test_home_shows_last_known_split_snapshot_for_saved_athlete(monkeypatch, tmp_path):
    _set_temp_store(monkeypatch, tmp_path)
    app_module.store.add(
        race_slug="rockford-70.3",
        entry_id="entry-1",
        bib="147",
        name="Taylor Runner",
        division="F35-39",
        target_finish_time="05:30:00",
    )
    monkeypatch.setattr(
        app_module.rtrt_service,
        "fetch_splits",
        lambda _race, _entry_id: [
            {"name": "SWIM", "time": "00:38:00", "seconds": 2280},
            {"name": "RUN 5 MI", "time": "04:20:00", "seconds": 15600, "distance_miles": 5.0},
        ],
    )
    test_client = app_module.app.test_client()

    response = test_client.get("/")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Latest split RUN 5 MI at 04:20:00" in body


def test_home_rows_render_inline_action_controls(monkeypatch, tmp_path):
    _set_temp_store(monkeypatch, tmp_path)
    row = app_module.store.add(
        race_slug="venice-70.3",
        entry_id="entry-130",
        profile_id="RFX9NGWK",
        bib="130",
        name="Kiel Bur",
        division="M40-44",
        target_finish_time="04:00:00",
    )
    test_client = app_module.app.test_client()

    response = test_client.get("/")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert f'/?mode=edit&amp;athlete_id={row["id"]}' in body
    assert f'/?mode=delete&amp;athlete_id={row["id"]}' in body
    assert "Edit target" in body
    assert "Delete" in body


def test_home_inline_delete_mode_renders_confirmation_controls(monkeypatch, tmp_path):
    _set_temp_store(monkeypatch, tmp_path)
    row = app_module.store.add(
        race_slug="venice-70.3",
        entry_id="entry-130",
        profile_id="RFX9NGWK",
        bib="130",
        name="Kiel Bur",
        division="M40-44",
        target_finish_time="04:00:00",
    )
    test_client = app_module.app.test_client()

    response = test_client.get(f"/?mode=delete&athlete_id={row['id']}")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert f'action="/athlete/{row["id"]}/delete"' in body
    assert 'name="confirm"' in body
    assert 'value="yes"' in body
    assert "Confirm delete" in body
    assert "Cancel" in body


def test_home_allows_only_one_active_row_mode(monkeypatch, tmp_path):
    _set_temp_store(monkeypatch, tmp_path)
    first = app_module.store.add(
        race_slug="venice-70.3",
        entry_id="entry-130",
        profile_id="RFX9NGWK",
        bib="130",
        name="Kiel Bur",
        division="M40-44",
        target_finish_time="04:00:00",
    )
    second = app_module.store.add(
        race_slug="venice-70.3",
        entry_id="entry-310",
        profile_id="ABCD1234",
        bib="310",
        name="Casey Pace",
        division="F35-39",
        target_finish_time="05:00:00",
    )
    test_client = app_module.app.test_client()

    response = test_client.get(f"/?mode=edit&athlete_id={first['id']}")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert f'action="/athlete/{first["id"]}/target"' in body
    assert f'action="/athlete/{second["id"]}/target"' not in body
    assert body.count('name="target_finish_time"') == 1


def test_home_cancel_action_returns_row_to_view_mode(monkeypatch, tmp_path):
    _set_temp_store(monkeypatch, tmp_path)
    row = app_module.store.add(
        race_slug="venice-70.3",
        entry_id="entry-130",
        profile_id="RFX9NGWK",
        bib="130",
        name="Kiel Bur",
        division="M40-44",
        target_finish_time="04:00:00",
    )
    test_client = app_module.app.test_client()

    mode_response = test_client.get(f"/?mode=edit&athlete_id={row['id']}")
    view_response = test_client.get("/")

    assert mode_response.status_code == 200
    mode_body = mode_response.get_data(as_text=True)
    assert f'action="/athlete/{row["id"]}/target"' in mode_body
    assert 'href="/"' in mode_body
    assert "Cancel" in mode_body

    assert view_response.status_code == 200
    view_body = view_response.get_data(as_text=True)
    assert f'action="/athlete/{row["id"]}/target"' not in view_body


def test_config_duplicate_shows_warning_and_back_to_athlete_list_link(monkeypatch, tmp_path):
    _set_temp_store(monkeypatch, tmp_path)
    existing = app_module.store.add(
        race_slug="venice-70.3",
        entry_id="entry-130",
        profile_id="RFX9NGWK",
        bib="130",
        name="Kiel Bur",
        division="M40-44",
        target_finish_time="04:00:00",
    )
    existing_snapshot = dict(existing)
    test_client = app_module.app.test_client()

    response = test_client.post(
        "/config",
        data={
            "race_slug": "venice-70.3",
            "entry_id": "entry-130",
            "profile_id": "RFX9NGWK",
            "name": "Kiel Bur",
            "bib": "130",
            "division": "M40-44",
            "target_finish_time": "04:15:00",
        },
    )

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "This athlete is already configured." in body
    assert f'href="/?mode=edit&amp;athlete_id={existing["id"]}"' in body
    assert app_module.store.list() == [existing_snapshot]


def test_config_missing_identity_shows_warning_without_mutation(monkeypatch, tmp_path):
    _set_temp_store(monkeypatch, tmp_path)
    test_client = app_module.app.test_client()

    response = test_client.post(
        "/config",
        data={
            "race_slug": "venice-70.3",
            "entry_id": "",
            "profile_id": "",
            "name": "Kiel Bur",
            "bib": "",
            "division": "M40-44",
            "target_finish_time": "04:15:00",
        },
    )

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Provide at least one athlete identity (entry ID or bib)." in body
    assert len(app_module.store.list()) == 0


def test_config_conflicting_identity_shows_warning_without_mutation(monkeypatch, tmp_path):
    _set_temp_store(monkeypatch, tmp_path)
    app_module.store.add(
        race_slug="venice-70.3",
        entry_id="entry-130",
        profile_id="RFX9NGWK",
        bib="130",
        name="Kiel Bur",
        division="M40-44",
        target_finish_time="04:00:00",
    )
    app_module.store.add(
        race_slug="venice-70.3",
        entry_id="entry-310",
        profile_id="ABCD1234",
        bib="310",
        name="Casey Pace",
        division="F35-39",
        target_finish_time="05:00:00",
    )
    test_client = app_module.app.test_client()

    response = test_client.post(
        "/config",
        data={
            "race_slug": "venice-70.3",
            "entry_id": "entry-130",
            "profile_id": "RFX9NGWK",
            "name": "Conflicting Runner",
            "bib": "310",
            "division": "M40-44",
            "target_finish_time": "04:15:00",
        },
    )

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Entry ID and bib point to different athletes." in body
    assert len(app_module.store.list()) == 2


def test_home_filters_latest_split_by_simulated_elapsed_time(monkeypatch, tmp_path):
    _set_temp_store(monkeypatch, tmp_path)
    row = app_module.store.add(
        race_slug="rockford-70.3",
        entry_id="entry-1",
        bib="147",
        name="Taylor Runner",
        division="F35-39",
        target_finish_time="05:30:00",
    )
    monkeypatch.setattr(
        app_module.rtrt_service,
        "fetch_splits",
        lambda _race, _entry_id: [
            {"name": "SWIM", "time": "00:40:00", "seconds": 2400},
            {"name": "T2", "time": "03:40:00", "seconds": 13200},
            {"name": "RUN 5 MI", "time": "04:20:00", "seconds": 15600, "distance_miles": 5.0},
        ],
    )
    test_client = app_module.app.test_client()

    response = test_client.get("/?sim_elapsed=10000")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Latest split SWIM at 00:40:00" in body
    assert f'href="/athlete/{row["id"]}?sim_elapsed=10000"' in body


def test_athlete_detail_shows_required_hm_completion_time_and_signed_delta(monkeypatch, tmp_path):
    _set_temp_store(monkeypatch, tmp_path)
    row = app_module.store.add(
        race_slug="rockford-70.3",
        entry_id="entry-1",
        bib="147",
        name="Taylor Runner",
        division="F35-39",
        target_finish_time="05:30:00",
    )
    monkeypatch.setattr(
        app_module.rtrt_service,
        "fetch_splits",
        lambda _race, _entry_id: [
            {"name": "T2", "time": "03:40:00", "seconds": 13200},
            {"name": "RUN 3 MI", "time": "04:10:00", "seconds": 15000, "distance_miles": 3.0},
        ],
    )
    test_client = app_module.app.test_client()

    response = test_client.get(f"/athlete/{row['id']}")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "is on the run!" in body
    assert "Run Goal:" in body
    assert "Pace:" in body
    assert "Based on a T2 time of" in body
    assert "And a goal finish of" in body
    assert "/mi /mi" not in body


def test_athlete_detail_respects_simulated_elapsed_before_t2(monkeypatch, tmp_path):
    _set_temp_store(monkeypatch, tmp_path)
    row = app_module.store.add(
        race_slug="rockford-70.3",
        entry_id="entry-1",
        bib="147",
        name="Taylor Runner",
        division="F35-39",
        target_finish_time="05:30:00",
    )
    monkeypatch.setattr(
        app_module.rtrt_service,
        "fetch_splits",
        lambda _race, _entry_id: [
            {"name": "SWIM", "time": "00:40:00", "seconds": 2400},
            {"name": "T2", "time": "03:40:00", "seconds": 13200},
            {"name": "RUN 3 MI", "time": "04:10:00", "seconds": 15000, "distance_miles": 3.0},
        ],
    )
    test_client = app_module.app.test_client()

    response = test_client.get(f"/athlete/{row['id']}?sim_elapsed=10000")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "is not yet running." in body
    assert "Simulated elapsed: 02:46:40" in body


def test_athlete_detail_simulated_elapsed_after_one_finish_keeps_on_course_athlete_open(
    monkeypatch, tmp_path
):
    _set_temp_store(monkeypatch, tmp_path)
    fast_row = app_module.store.add(
        race_slug="rockford-70.3",
        entry_id="entry-fast",
        bib="101",
        name="Fast Runner",
        division="M35-39",
        target_finish_time="05:00:00",
    )
    app_module.store.add(
        race_slug="rockford-70.3",
        entry_id="entry-steady",
        bib="202",
        name="Steady Runner",
        division="M35-39",
        target_finish_time="05:30:00",
    )

    def fake_fetch(_race, entry_id):
        if entry_id == "entry-fast":
            return [
                {"name": "T2", "time": "03:00:00", "seconds": 10800},
                {"name": "RUN 13.1 MI", "time": "04:30:00", "seconds": 16200, "distance_miles": 13.1},
                {"name": "FINISH", "time": "04:30:10", "seconds": 16210},
            ]
        return [
            {"name": "T2", "time": "03:40:00", "seconds": 13200},
            {"name": "RUN 8 MI", "time": "04:55:00", "seconds": 17700, "distance_miles": 8.0},
            {"name": "RUN 10 MI", "time": "05:15:00", "seconds": 18900, "distance_miles": 10.0},
            {"name": "FINISH", "time": "05:50:00", "seconds": 21000},
        ]

    monkeypatch.setattr(app_module.rtrt_service, "fetch_splits", fake_fetch)
    test_client = app_module.app.test_client()

    home_response = test_client.get("/?sim_elapsed=16500")
    fast_detail_response = test_client.get(f"/athlete/{fast_row['id']}?sim_elapsed=16500")

    assert home_response.status_code == 200
    home_body = home_response.get_data(as_text=True)
    assert "Latest split FINISH at 04:30:10" in home_body
    assert "Latest split T2 at 03:40:00" in home_body

    assert fast_detail_response.status_code == 200
    fast_body = fast_detail_response.get_data(as_text=True)
    assert "Latest update:" in fast_body
    assert "FINISH at 04:30:10" in fast_body
    assert "did it!" in fast_body


def test_athlete_detail_finished_over_target_shows_miss_message(monkeypatch, tmp_path):
    _set_temp_store(monkeypatch, tmp_path)
    row = app_module.store.add(
        race_slug="rockford-70.3",
        entry_id="entry-3",
        bib="303",
        name="Late Runner",
        division="M40-44",
        target_finish_time="05:00:00",
    )
    monkeypatch.setattr(
        app_module.rtrt_service,
        "fetch_splits",
        lambda _race, _entry_id: [
            {"name": "T2", "time": "03:15:00", "seconds": 11700},
            {"name": "RUN 13.1 MI", "time": "05:10:00", "seconds": 18600, "distance_miles": 13.1},
            {"name": "FINISH", "time": "05:10:05", "seconds": 18605},
        ],
    )
    test_client = app_module.app.test_client()

    response = test_client.get(f"/athlete/{row['id']}")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "didn't quite make it." in body
    assert "Missed target by" in body


def test_athlete_detail_has_manual_refresh_action(monkeypatch, tmp_path):
    _set_temp_store(monkeypatch, tmp_path)
    row = app_module.store.add(
        race_slug="rockford-70.3",
        entry_id="entry-1",
        bib="147",
        name="Taylor Runner",
        division="F35-39",
        target_finish_time="05:30:00",
    )
    monkeypatch.setattr(app_module.rtrt_service, "fetch_splits", lambda _race, _entry_id: [])
    test_client = app_module.app.test_client()

    response = test_client.get(f"/athlete/{row['id']}")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Refresh split data" in body


def test_update_target_route_valid_updates_target_and_redirects_home(monkeypatch, tmp_path):
    _set_temp_store(monkeypatch, tmp_path)
    row = app_module.store.add(
        race_slug="venice-70.3",
        entry_id="entry-130",
        profile_id="RFX9NGWK",
        bib="130",
        name="Kiel Bur",
        division="M40-44",
        target_finish_time="04:00:00",
    )
    test_client = app_module.app.test_client()

    response = test_client.post(
        f"/athlete/{row['id']}/target",
        data={"target_finish_time": "04:15:00"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Updated target finish time to 04:15:00 for Kiel Bur." in body
    assert app_module.store.get(row["id"])["target_finish_time"] == "04:15:00"


def test_update_target_route_invalid_format_does_not_mutate(monkeypatch, tmp_path):
    _set_temp_store(monkeypatch, tmp_path)
    row = app_module.store.add(
        race_slug="venice-70.3",
        entry_id="entry-130",
        profile_id="RFX9NGWK",
        bib="130",
        name="Kiel Bur",
        division="M40-44",
        target_finish_time="04:00:00",
    )
    test_client = app_module.app.test_client()

    response = test_client.post(f"/athlete/{row['id']}/target", data={"target_finish_time": "4h15m"})

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")
    assert app_module.store.get(row["id"])["target_finish_time"] == "04:00:00"
    with test_client.session_transaction() as session:
        flashes = session.get("_flashes", [])
    assert ("error", "Target finish must be in HH:MM:SS format.") in flashes


def test_update_target_route_unknown_id_does_not_mutate(monkeypatch, tmp_path):
    _set_temp_store(monkeypatch, tmp_path)
    app_module.store.add(
        race_slug="venice-70.3",
        entry_id="entry-130",
        profile_id="RFX9NGWK",
        bib="130",
        name="Kiel Bur",
        division="M40-44",
        target_finish_time="04:00:00",
    )
    test_client = app_module.app.test_client()

    response = test_client.post("/athlete/missing-id/target", data={"target_finish_time": "04:15:00"})

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")
    assert len(app_module.store.list()) == 1
    assert app_module.store.list()[0]["target_finish_time"] == "04:00:00"
    with test_client.session_transaction() as session:
        flashes = session.get("_flashes", [])
    assert ("warning", "Athlete not found; target was not updated.") in flashes


def test_delete_route_requires_confirmation_and_does_not_mutate(monkeypatch, tmp_path):
    _set_temp_store(monkeypatch, tmp_path)
    row = app_module.store.add(
        race_slug="venice-70.3",
        entry_id="entry-130",
        profile_id="RFX9NGWK",
        bib="130",
        name="Kiel Bur",
        division="M40-44",
        target_finish_time="04:00:00",
    )
    test_client = app_module.app.test_client()

    response = test_client.post(f"/athlete/{row['id']}/delete", data={})

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")
    assert app_module.store.get(row["id"]) is not None
    with test_client.session_transaction() as session:
        flashes = session.get("_flashes", [])
    assert ("warning", "Delete not confirmed; athlete was not removed.") in flashes


def test_delete_route_invalid_confirmation_value_does_not_mutate(monkeypatch, tmp_path):
    _set_temp_store(monkeypatch, tmp_path)
    row = app_module.store.add(
        race_slug="venice-70.3",
        entry_id="entry-130",
        profile_id="RFX9NGWK",
        bib="130",
        name="Kiel Bur",
        division="M40-44",
        target_finish_time="04:00:00",
    )
    test_client = app_module.app.test_client()
    original = dict(app_module.store.get(row["id"]))

    response = test_client.post(f"/athlete/{row['id']}/delete", data={"confirm": "no"})

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")
    assert app_module.store.get(row["id"]) == original
    with test_client.session_transaction() as session:
        flashes = session.get("_flashes", [])
    assert ("warning", "Delete not confirmed; athlete was not removed.") in flashes


def test_delete_route_confirmed_deletes_athlete(monkeypatch, tmp_path):
    _set_temp_store(monkeypatch, tmp_path)
    row = app_module.store.add(
        race_slug="venice-70.3",
        entry_id="entry-130",
        profile_id="RFX9NGWK",
        bib="130",
        name="Kiel Bur",
        division="M40-44",
        target_finish_time="04:00:00",
    )
    test_client = app_module.app.test_client()

    response = test_client.post(f"/athlete/{row['id']}/delete", data={"confirm": "yes"})

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")
    assert app_module.store.get(row["id"]) is None
    with test_client.session_transaction() as session:
        flashes = session.get("_flashes", [])
    assert ("success", "Removed athlete Kiel Bur.") in flashes


def test_delete_route_unknown_id_does_not_mutate(monkeypatch, tmp_path):
    _set_temp_store(monkeypatch, tmp_path)
    app_module.store.add(
        race_slug="venice-70.3",
        entry_id="entry-130",
        profile_id="RFX9NGWK",
        bib="130",
        name="Kiel Bur",
        division="M40-44",
        target_finish_time="04:00:00",
    )
    test_client = app_module.app.test_client()

    response = test_client.post("/athlete/missing-id/delete", data={"confirm": "yes"})

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")
    assert len(app_module.store.list()) == 1
    with test_client.session_transaction() as session:
        flashes = session.get("_flashes", [])
    assert ("warning", "Athlete not found; nothing was deleted.") in flashes


def test_athlete_detail_shows_data_warning_when_run_split_distance_unparsable(monkeypatch, tmp_path):
    _set_temp_store(monkeypatch, tmp_path)
    row = app_module.store.add(
        race_slug="rockford-70.3",
        entry_id="entry-2",
        bib="204",
        name="Casey Runner",
        division="M40-44",
        target_finish_time="05:45:00",
    )
    monkeypatch.setattr(
        app_module.rtrt_service,
        "fetch_splits",
        lambda _race, _entry_id: [
            {"name": "T2", "time": "03:40:00", "seconds": 13200},
            {"name": "RUN CHECKPOINT", "time": "04:05:00", "seconds": 14700, "distance_miles": None},
        ],
    )
    test_client = app_module.app.test_client()

    response = test_client.get(f"/athlete/{row['id']}")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Run split data could not be fully parsed." in body
