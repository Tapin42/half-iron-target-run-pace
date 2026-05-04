import pytest

from src.storage import AthleteStore


def _build_store(tmp_path) -> AthleteStore:
    return AthleteStore(str(tmp_path / "athletes.json"))


def _add(
    store: AthleteStore,
    *,
    race_slug: str = "rockford-70.3",
    entry_id: str = "entry-1",
    bib: str = "101",
    name: str = "Taylor Runner",
    division: str = "F35-39",
    target_finish_time: str = "05:30:00",
) -> dict:
    return store.add(
        race_slug=race_slug,
        entry_id=entry_id,
        bib=bib,
        name=name,
        division=division,
        target_finish_time=target_finish_time,
    )


def test_add_rejects_duplicate_by_race_and_entry_id(tmp_path):
    store = _build_store(tmp_path)
    _add(store, entry_id="entry-7", bib="777")

    with pytest.raises(ValueError, match="duplicate identity"):
        _add(store, entry_id="entry-7", bib="888")


def test_find_by_identity_falls_back_to_bib_when_entry_missing(tmp_path):
    store = _build_store(tmp_path)
    row = _add(store, entry_id="", bib="130")

    result = store.find_by_identity("rockford-70.3", bib="130")

    assert result["status"] == "match"
    assert result["athlete"]["id"] == row["id"]


def test_find_by_identity_prioritizes_entry_id_when_both_present(tmp_path):
    store = _build_store(tmp_path)
    matched = _add(store, entry_id="entry-9", bib="909")
    _add(store, entry_id="entry-10", bib="910")

    result = store.find_by_identity("rockford-70.3", entry_id="entry-9", bib="999")

    assert result["status"] == "match"
    assert result["athlete"]["id"] == matched["id"]


def test_add_rejects_missing_identity(tmp_path):
    store = _build_store(tmp_path)
    rows_before = store.list()

    with pytest.raises(ValueError, match="missing identity"):
        _add(store, entry_id="", bib="")

    rows_after = store.list()
    assert rows_after == rows_before


def test_add_rejects_conflicting_identity_matches(tmp_path):
    store = _build_store(tmp_path)
    _add(store, entry_id="entry-a", bib="100")
    _add(store, entry_id="entry-b", bib="200")
    rows_before = store.list()

    with pytest.raises(ValueError, match="conflicting identity"):
        _add(store, entry_id="entry-a", bib="200")

    rows_after = store.list()
    assert rows_after == rows_before


def test_duplicate_attempt_does_not_mutate_existing_row(tmp_path):
    store = _build_store(tmp_path)
    original = _add(store, entry_id="entry-55", bib="155", target_finish_time="05:40:00")

    with pytest.raises(ValueError, match="duplicate identity"):
        _add(store, entry_id="entry-55", bib="155", target_finish_time="04:00:00")

    persisted = store.get(original["id"])
    assert persisted["target_finish_time"] == "05:40:00"
    assert len(store.list()) == 1


def test_add_rejects_duplicate_by_race_and_bib_when_entry_missing(tmp_path):
    store = _build_store(tmp_path)
    _add(store, entry_id="", bib="404")

    with pytest.raises(ValueError, match="duplicate identity"):
        _add(store, entry_id="", bib="404")


def test_identity_comparison_trims_whitespace_on_input_and_stored_values(tmp_path):
    store = _build_store(tmp_path)
    stored = _add(store, entry_id="entry-space", bib="900")

    all_rows = store.list()
    all_rows[0]["entry_id"] = "  entry-space  "
    all_rows[0]["bib"] = "  900  "
    store._write(all_rows)

    entry_result = store.find_by_identity("rockford-70.3", entry_id="entry-space")
    bib_result = store.find_by_identity("rockford-70.3", entry_id="", bib="900")

    assert entry_result["status"] == "match"
    assert entry_result["athlete"]["id"] == stored["id"]
    assert bib_result["status"] == "match"
    assert bib_result["athlete"]["id"] == stored["id"]


def test_update_target_time_updates_existing_row(tmp_path):
    store = _build_store(tmp_path)
    row = _add(store, entry_id="entry-81", bib="181", target_finish_time="05:30:00")

    updated = store.update_target_time(row["id"], "05:10:00")

    assert updated is not None
    assert updated["target_finish_time"] == "05:10:00"
    assert store.get(row["id"])["target_finish_time"] == "05:10:00"


def test_update_target_time_returns_none_for_unknown_id(tmp_path):
    store = _build_store(tmp_path)

    result = store.update_target_time("missing-id", "05:00:00")

    assert result is None


def test_delete_removes_existing_row(tmp_path):
    store = _build_store(tmp_path)
    row = _add(store, entry_id="entry-44", bib="144")

    deleted = store.delete(row["id"])

    assert deleted is not None
    assert deleted["id"] == row["id"]
    assert store.get(row["id"]) is None
    assert len(store.list()) == 0


def test_delete_returns_none_for_unknown_id(tmp_path):
    store = _build_store(tmp_path)

    result = store.delete("unknown-id")

    assert result is None
