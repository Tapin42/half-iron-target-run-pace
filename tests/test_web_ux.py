import app as app_module


def test_home_renders_client_storage_mount_and_unknown_notice():
    test_client = app_module.app.test_client()

    response = test_client.get("/?notice=unknown-athlete")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Athlete List" in body
    assert "Unknown athlete." in body
    assert 'id="athlete-list"' in body
    assert 'id="clear-all-athletes"' in body
    assert "window.AthleteStoreClient.clearAthletes" in body
    assert 'src="/static/athletes.js"' in body


def test_config_page_renders_local_storage_wiring_and_race_options():
    test_client = app_module.app.test_client()

    response = test_client.get("/config")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Configure Athlete Target" in body
    assert "Ironman 70.3 Venice" in body
    assert "Ironman 70.3 Da Nang" in body
    assert 'id="config-form"' in body
    assert "window.AthleteStoreClient.addAthlete" in body


def test_athlete_resolver_page_exposes_redirect_hook_and_guard_notice():
    test_client = app_module.app.test_client()

    response = test_client.get("/athlete/local-athlete-id-1")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert 'data-athlete-id="local-athlete-id-1"' in body
    assert "notice=unknown-athlete" in body
    assert 'src="/static/athletes.js"' in body


def test_latest_split_api_returns_latest_split_for_valid_identity(monkeypatch):
    monkeypatch.setattr(
        app_module.rtrt_service,
        "fetch_splits",
        lambda _race, _entry_id: [
            {"name": "SWIM", "time": "00:40:00", "seconds": 2400},
            {"name": "RUN 5 MI", "time": "04:20:00", "seconds": 15600, "distance_miles": 5.0},
        ],
    )
    test_client = app_module.app.test_client()

    response = test_client.get("/api/latest-split?race_slug=rockford-70.3&entry_id=e1")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["latest_split"]["name"] == "RUN 5 MI"
    assert payload["latest_split"]["time"] == "04:20:00"


def test_latest_split_api_rejects_unknown_race():
    test_client = app_module.app.test_client()

    response = test_client.get("/api/latest-split?race_slug=unknown-race&entry_id=e1")

    assert response.status_code == 400
    assert response.get_json() == {"error": "Unknown race"}


def test_athlete_detail_query_page_renders_for_known_identity(monkeypatch):
    monkeypatch.setattr(
        app_module.rtrt_service,
        "fetch_splits",
        lambda _race, _entry_id: [
            {"name": "T2", "time": "03:40:00", "seconds": 13200},
            {"name": "RUN 3 MI", "time": "04:10:00", "seconds": 15000, "distance_miles": 3.0},
        ],
    )
    test_client = app_module.app.test_client()

    response = test_client.get(
        "/athlete/detail"
        "?athlete_id=local-athlete-id-1"
        "&race_slug=rockford-70.3"
        "&entry_id=e1"
        "&name=Taylor%20Runner"
        "&bib=147"
        "&division=F35-39"
        "&target_finish_time=05:30:00"
    )

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Taylor Runner" in body
    assert "is on the run!" in body
    assert "Run Goal:" in body
    assert "Refresh split data" in body
