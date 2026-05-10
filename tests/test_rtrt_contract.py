from types import SimpleNamespace

import app as app_module
from src.races import RaceConfig
from src.races import load_race_configs
from src.rtrt_client import RtrtClient
from src.rtrt_service import RtrtService


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class StubClient:
    def __init__(self, responses: list[dict]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, dict]] = []

    def post(self, url: str, payload: dict | None = None) -> dict:
        self.calls.append((url, payload or {}))
        return self.responses.pop(0)


def test_rtrt_client_posts_with_auth_and_baseline_params(monkeypatch):
    monkeypatch.setenv("RTRT_APPID", "appid-123")
    monkeypatch.setenv("RTRT_TOKEN", "token-xyz")

    called = {}

    def fake_post(url, data, timeout):
        called["url"] = url
        called["data"] = data
        called["timeout"] = timeout
        return FakeResponse({"ok": True})

    monkeypatch.setattr("src.rtrt_client.requests.post", fake_post)

    client = RtrtClient()
    payload = client.post("https://example.test/endpoint", {"query": "amy"})

    assert payload == {"ok": True}
    assert called["url"] == "https://example.test/endpoint"
    assert called["timeout"] == 20
    assert called["data"]["appid"] == "appid-123"
    assert called["data"]["token"] == "token-xyz"
    assert called["data"]["timesort"] == "1"
    assert called["data"]["source"] == "webtracker"
    assert called["data"]["query"] == "amy"


def test_search_athletes_uses_profiles_endpoint_with_webtracker_payload():
    race = RaceConfig(
        slug="rockford-70.3",
        display_name="Race",
        event_key="EVENT123",
        search_category="AG",
        finish_split="FINISH",
    )
    client = StubClient(
        [
            {
                "list": [
                    {"i": "e1", "pid": "P1", "name": "Amy Adams", "bib": "101", "class": "F30-34"},
                    {"i": "e2", "pid": "P2", "name": "John Doe", "bib": "202", "class": "M35-39"},
                ]
            },
        ]
    )
    service = RtrtService(client)

    rows = service.search_athletes(race, "amy")

    assert len(rows) == 2
    assert rows[0]["entry_id"] == "e1"
    assert rows[0]["profile_id"] == "P1"
    assert rows[0]["name"] == "Amy Adams"
    assert rows[0]["division"] == "F30-34"
    assert client.calls[0][0].endswith("/profiles")
    assert client.calls[0][1]["search"] == "amy"
    assert client.calls[0][1]["module"] == "0"
    assert client.calls[0][1]["max"] == "100"
    assert client.calls[0][1]["total"] == "1"
    assert client.calls[0][1]["failonmax"] == "1"


def test_search_athletes_supports_venice_name_fields_without_name_key():
    race = RaceConfig(
        slug="venice-70.3",
        display_name="Race",
        event_key="EVENT123",
        search_category="AG",
        finish_split="FINISH",
    )
    client = StubClient(
        [
            {
                "list": [
                    {
                        "i": "e130",
                        "pid": "RFX9NGWK",
                        "fname": "Kiel",
                        "lname": "Bur",
                        "bib": "130",
                        "class": "M40-44",
                    }
                ]
            }
        ]
    )
    service = RtrtService(client)

    rows = service.search_athletes(race, "kiel")

    assert len(rows) == 1
    assert rows[0]["entry_id"] == "e130"
    assert rows[0]["profile_id"] == "RFX9NGWK"
    assert rows[0]["name"] == "Kiel Bur"
    assert rows[0]["bib"] == "130"
    assert rows[0]["division"] == "M40-44"


def test_search_athletes_includes_profile_id_when_pid_is_present():
    race = RaceConfig(
        slug="venice-70.3",
        display_name="Race",
        event_key="EVENT123",
        search_category="AG",
        finish_split="FINISH",
    )
    client = StubClient(
        [
            {
                "list": [
                    {
                        "i": "entry-130",
                        "pid": "RFX9NGWK",
                        "name": "Kiel Bur",
                        "bib": "130",
                        "division": "M40-44",
                    }
                ]
            }
        ]
    )
    service = RtrtService(client)

    rows = service.search_athletes(race, "kiel")

    assert len(rows) == 1
    assert rows[0]["entry_id"] == "entry-130"
    assert rows[0]["profile_id"] == "RFX9NGWK"


def test_venice_race_default_search_category_is_optional(monkeypatch):
    monkeypatch.delenv("RTRT_VENICE_SEARCH_CATEGORY", raising=False)

    races = load_race_configs()

    assert races["venice-70.3"].search_category is None


def test_da_nang_race_config_uses_vietnam_event_key():
    races = load_race_configs()

    assert races["da-nang-70.3"].display_name == "Ironman 70.3 Da Nang"
    assert races["da-nang-70.3"].event_key == "IRM-VIETNAM-2026"


def test_search_athletes_limits_profiles_results_to_25_rows():
    race = RaceConfig(
        slug="venice-70.3",
        display_name="Race",
        event_key="EVENT123",
        search_category="top-age-group-men-division-ironman-tri_sprint:_ALL",
        finish_split="FINISH",
    )
    filler_rows = [{"i": f"entry-{index}", "pid": f"P-{index}", "name": f"Runner {index}"} for index in range(30)]
    client = StubClient(
        [
            {"list": filler_rows},
        ]
    )
    service = RtrtService(client)

    rows = service.search_athletes(race, "runner")

    assert len(rows) == 25
    assert rows[0]["entry_id"] == "entry-0"
    assert rows[24]["entry_id"] == "entry-24"


def test_fetch_splits_supports_embedded_split_list_shape():
    race = RaceConfig(slug="rockford-70.3", display_name="Race", event_key="EVENT123")
    client = StubClient(
        [
            {
                "list": [
                    {
                        "entry": "e1",
                        "name": "Amy Adams",
                        "splits": [
                            {"name": "T2", "time": "03:40:00"},
                            {"name": "RUN 3 MI", "time": "04:05:00"},
                        ],
                    }
                ]
            }
        ]
    )
    service = RtrtService(client)

    splits = service.fetch_splits(race, "e1")

    assert [split["name"] for split in splits] == ["T2", "RUN 3 MI"]
    assert splits[0]["seconds"] == 13200
    assert splits[1]["distance_miles"] == 3.0


def test_fetch_splits_prefers_profile_endpoint_when_profile_id_is_available():
    race = RaceConfig(slug="venice-70.3", display_name="Race", event_key="EVENT123")
    client = StubClient(
        [
            {
                "list": [
                    {"name": "T2", "time": "03:10:00.000"},
                    {"name": "RUN 3 MI", "time": "03:35:00.000"},
                ]
            }
        ]
    )
    service = RtrtService(client)

    splits = service.fetch_splits(race, "entry-unused", profile_id="RFX9NGWK")

    assert [split["name"] for split in splits] == ["T2", "RUN 3 MI"]
    assert client.calls[0][0].endswith("/profiles/RFX9NGWK/splits")


def test_fetch_splits_prefers_split_label_over_athlete_name():
    race = RaceConfig(slug="venice-70.3", display_name="Race", event_key="EVENT123")
    client = StubClient(
        [
            {
                "list": [
                    {
                        "name": "Kiel Bur",
                        "label": "BIKE 50 KM",
                        "time": "02:00:00.000",
                    }
                ]
            }
        ]
    )
    service = RtrtService(client)

    splits = service.fetch_splits(race, "entry-130")

    assert len(splits) == 1
    assert splits[0]["name"] == "BIKE 50 KM"
    assert splits[0]["time"] == "02:00:00"


def test_fetch_splits_falls_back_to_entry_endpoint_when_profile_split_rows_missing():
    race = RaceConfig(slug="venice-70.3", display_name="Race", event_key="EVENT123")
    client = StubClient(
        [
            {"error": {"type": "no_results"}},  # /profiles/{profile}/splits misses
            {"list": [{"name": "T2", "time": "03:40:00"}, {"name": "RUN 3 MI", "time": "04:05:00"}]},
        ]
    )
    service = RtrtService(client)

    splits = service.fetch_splits(race, "entry-1", profile_id="RFX9NGWK")

    assert [split["name"] for split in splits] == ["T2", "RUN 3 MI"]
    assert client.calls[0][0].endswith("/profiles/RFX9NGWK/splits")
    assert client.calls[1][0].endswith("/entries/entry-1/splits")


def test_api_search_returns_explicit_config_error(monkeypatch):
    test_client = app_module.app.test_client()

    def raise_config(_race, _query):
        raise RuntimeError("RTRT credentials are not configured")

    monkeypatch.setattr(app_module.rtrt_service, "search_athletes", raise_config)
    response = test_client.get("/api/search?race_slug=rockford-70.3&q=amy")

    assert response.status_code == 503
    assert response.get_json() == {"error": "RTRT credentials are missing. Configure RTRT_APPID and RTRT_TOKEN."}


def test_api_search_masks_upstream_error_and_returns_safe_message(monkeypatch):
    test_client = app_module.app.test_client()

    def raise_upstream(_race, _query):
        raise RuntimeError("upstream exploded with token details")

    monkeypatch.setattr(app_module.rtrt_service, "search_athletes", raise_upstream)
    response = test_client.get("/api/search?race_slug=rockford-70.3&q=amy")

    assert response.status_code == 502
    assert response.get_json() == {"error": "RTRT search is temporarily unavailable. Please try again."}


def test_athlete_detail_masks_split_errors_for_ui(monkeypatch):
    def raise_upstream(_race, _entry_id):
        raise RuntimeError("split endpoint leaked debug details")

    monkeypatch.setattr(app_module.rtrt_service, "fetch_splits", raise_upstream)
    test_client = app_module.app.test_client()
    response = test_client.get(
        "/athlete/detail"
        "?athlete_id=local-athlete-id-1"
        "&race_slug=rockford-70.3"
        "&entry_id=e1"
        "&name=Amy%20Adams"
        "&bib=101"
        "&division=F30-34"
        "&target_finish_time=05:30:00"
    )

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Could not load split data right now. Please refresh and try again." in body
    assert "split endpoint leaked debug details" not in body
