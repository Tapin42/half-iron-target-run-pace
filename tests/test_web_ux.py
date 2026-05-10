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
    assert "item.dataset.detailUrl" in body
    assert 'src="/static/athletes.js"' in body


def test_stylesheet_preserves_vertical_scroll_for_long_home_lists():
    test_client = app_module.app.test_client()

    response = test_client.get("/static/styles.css")

    assert response.status_code == 200
    css = response.get_data(as_text=True)
    assert "overflow-y: auto;" in css
    assert "touch-action: pan-y;" in css
    assert "padding-bottom: calc(4rem + env(safe-area-inset-bottom));" in css
    assert "padding-bottom: calc(1rem + env(safe-area-inset-bottom));" in css
    assert ".search-results-list button.is-selected" in css


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
    assert "Selected athlete" not in body
    assert "e.g. 5, 5:30, or 05:30:00" in body
    assert "First result is selected automatically." in body
    assert "setSelected(results[0], firstButton);" in body


def test_athletes_js_supports_flexible_target_finish_time_inputs():
    test_client = app_module.app.test_client()

    response = test_client.get("/static/athletes.js")

    assert response.status_code == 200
    script = response.get_data(as_text=True)
    assert "function normalizeTargetFinishTime(value)" in script
    assert "throw new Error(\"invalid_target\");" in script
    assert "const numberOnly = text.match(/^\\d+$/);" in script
    assert "const normalized = normalizeTargetFinishTime(athlete.target_finish_time);" in script


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
    assert 'class="athlete-actions athlete-actions-bar detail-icon-action-bar"' in body
    assert 'aria-label="Back to athlete list"' in body
    assert 'aria-label="Refresh split data"' in body
    assert 'aria-label="Share athlete"' in body
    assert 'aria-label="Copy athlete URL"' in body
    assert 'class="panel athlete-cheer-card athlete-dashboard-panel"' in body
    assert 'class="athlete-chip-row athlete-detail-chip-row"' in body


def test_athlete_detail_uses_run_start_when_t2_missing(monkeypatch):
    monkeypatch.setattr(
        app_module.rtrt_service,
        "fetch_splits",
        lambda _race, _entry_id: [
            {"name": "BIKE 80 KM", "time": "02:30:00", "seconds": 9000, "distance_miles": None},
            {"name": "RUN START", "time": "02:35:28", "seconds": 9328, "distance_miles": None},
        ],
    )
    test_client = app_module.app.test_client()

    response = test_client.get(
        "/athlete/detail"
        "?athlete_id=local-athlete-id-1"
        "&race_slug=da-nang-70.3"
        "&entry_id=e1"
        "&name=Rodrigo%20Acevedo"
        "&bib=3585"
        "&division=M35-39"
        "&target_finish_time=04:00:00"
    )

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Rodrigo Acevedo" in body
    assert "is on the run!" in body
    assert "Run Goal:" in body
    assert "Pace:" in body
    assert "Run split data could not be fully parsed." not in body


def test_athlete_detail_treats_run_finish_as_finish_split(monkeypatch):
    monkeypatch.setattr(
        app_module.rtrt_service,
        "fetch_splits",
        lambda _race, _entry_id: [
            {"name": "RUN START", "time": "02:35:28", "seconds": 9328, "distance_miles": None},
            {"name": "RUN/FINISH", "time": "04:02:21", "seconds": 14541, "distance_miles": None},
        ],
    )
    test_client = app_module.app.test_client()

    response = test_client.get(
        "/athlete/detail"
        "?athlete_id=local-athlete-id-1"
        "&race_slug=da-nang-70.3"
        "&entry_id=e1"
        "&name=Rodrigo%20Acevedo"
        "&bib=3585"
        "&division=M35-39"
        "&target_finish_time=04:00:00"
    )

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Latest update: <strong>RUN/FINISH at 04:02:21</strong>" in body
    assert "didn't quite make it." in body
    assert "Finish:" in body
    assert "Missed target by <strong>00:02:21</strong>" in body
    assert "Run Goal:" not in body
    assert "Run split data could not be fully parsed." not in body


def test_athlete_detail_uses_points_finish_aliases_for_finish_detection(monkeypatch):
    app_module.finish_alias_cache.clear()
    monkeypatch.setattr(
        app_module.rtrt_service,
        "fetch_splits",
        lambda _race, _entry_id: [
            {"name": "RUN START", "time": "02:35:28", "seconds": 9328, "distance_miles": None},
            {"name": "GOAL LINE", "time": "04:02:21", "seconds": 14541, "distance_miles": None},
        ],
    )
    monkeypatch.setattr(
        app_module.rtrt_service,
        "fetch_finish_split_aliases",
        lambda _race: {"GOAL LINE"},
    )
    test_client = app_module.app.test_client()

    response = test_client.get(
        "/athlete/detail"
        "?athlete_id=local-athlete-id-1"
        "&race_slug=da-nang-70.3"
        "&entry_id=e1"
        "&name=Rodrigo%20Acevedo"
        "&bib=3585"
        "&division=M35-39"
        "&target_finish_time=04:00:00"
    )

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "didn't quite make it." in body
    assert "Finish:" in body
    assert "Run Goal:" not in body
    assert "Run split data could not be fully parsed." not in body


def test_finish_alias_cache_refreshes_after_six_hours(monkeypatch):
    app_module.finish_alias_cache.clear()
    race = app_module.races["da-nang-70.3"]
    ttl = app_module.FINISH_ALIAS_CACHE_TTL_SECONDS
    calls = {"count": 0}

    def fake_fetch_finish_aliases(_race):
        calls["count"] += 1
        if calls["count"] == 1:
            return {"RUN/FINISH"}
        return {"GOAL LINE"}

    timestamps = iter([1000.0, 1000.0 + ttl - 1, 1000.0 + ttl + 1])
    monkeypatch.setattr(app_module.time, "time", lambda: next(timestamps))
    monkeypatch.setattr(
        app_module.rtrt_service,
        "fetch_finish_split_aliases",
        fake_fetch_finish_aliases,
    )

    aliases_first = app_module._finish_aliases_for_race(race)
    aliases_second = app_module._finish_aliases_for_race(race)
    aliases_third = app_module._finish_aliases_for_race(race)

    assert calls["count"] == 2
    assert aliases_first == aliases_second
    assert "RUN FINISH" in aliases_first
    assert "GOAL LINE" in aliases_third
    assert aliases_third != aliases_first


def test_athlete_detail_page_includes_share_button_and_share_url(monkeypatch):
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
    assert 'id="share-athlete-button"' in body
    assert 'id="copy-athlete-url-button"' in body
    assert "share-athlete-url" in body
    assert "/share/" in body
    assert "navigator.share" in body


def test_share_page_renders_confirm_import_for_valid_signed_payload(monkeypatch):
    monkeypatch.setattr(app_module.rtrt_service, "fetch_splits", lambda *_args, **_kwargs: [])
    token = app_module._create_share_token(
        {
            "race_slug": "rockford-70.3",
            "entry_id": "e1",
            "profile_id": "",
            "name": "Taylor Runner",
            "bib": "147",
            "division": "F35-39",
            "target_finish_time": "05:30:00",
        }
    )
    test_client = app_module.app.test_client()

    response = test_client.get(f"/share/{token}")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Add shared athlete to your tracker?" in body
    assert "Taylor Runner" in body
    assert "window.AthleteStoreClient.addAthlete" in body
    assert 'src="/static/athletes.js"' in body


def test_share_page_redirects_home_for_invalid_or_unverifiable_payload(monkeypatch):
    monkeypatch.setattr(
        app_module.rtrt_service,
        "fetch_splits",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("not found")),
    )
    token = app_module._create_share_token(
        {
            "race_slug": "rockford-70.3",
            "entry_id": "e404",
            "profile_id": "",
            "name": "Unknown Runner",
            "bib": "404",
            "division": "F35-39",
            "target_finish_time": "05:30:00",
        }
    )
    test_client = app_module.app.test_client()

    bad_signature_response = test_client.get("/share/not-a-valid-token")
    unverifiable_response = test_client.get(f"/share/{token}")

    assert bad_signature_response.status_code == 302
    assert bad_signature_response.headers["Location"].endswith("/?notice=unknown-athlete")
    assert unverifiable_response.status_code == 302
    assert unverifiable_response.headers["Location"].endswith("/?notice=unknown-athlete")
