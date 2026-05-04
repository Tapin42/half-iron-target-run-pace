import re
from src.calculations import parse_hhmmss
from src.races import RaceConfig
from src.rtrt_client import RtrtClient


class RtrtService:
    def __init__(self, client: RtrtClient) -> None:
        self.client = client

    def search_athletes(self, race: RaceConfig, query: str) -> list[dict]:
        query = (query or "").strip()
        if len(query) < 2:
            return []

        search_url = f"https://api.rtrt.me/events/{race.event_key}/search"
        payload = self.client.post(search_url, {"query": query})
        rows = self._extract_entries(payload)
        if rows:
            return rows

        # Fallback for events where /search is unavailable.
        if not race.search_category:
            return []
        split_url = (
            f"https://api.rtrt.me/events/{race.event_key}/categories/"
            f"{race.search_category}/splits/{race.finish_split}"
        )
        fallback_payload = self.client.post(split_url, {"max": "500"})
        candidates = self._extract_entries(fallback_payload)
        query_lower = query.lower()
        return [
            row
            for row in candidates
            if query_lower in row["name"].lower() or query_lower in row["bib"].lower()
        ][:25]

    def fetch_splits(self, race: RaceConfig, entry_id: str) -> list[dict]:
        split_url = f"https://api.rtrt.me/events/{race.event_key}/entries/{entry_id}/splits"
        payload = self.client.post(split_url, {"max": "200"})
        split_rows = payload.get("list", [])
        if not isinstance(split_rows, list):
            return []

        normalized = []
        for row in split_rows:
            if not isinstance(row, dict):
                continue
            split_name = str(row.get("name") or row.get("split") or "").strip()
            split_time = str(row.get("time") or "").split(".")[0]
            seconds = parse_hhmmss(split_time)
            if not split_name or seconds is None:
                continue
            normalized.append(
                {
                    "name": split_name,
                    "time": split_time,
                    "seconds": seconds,
                    "distance_miles": parse_run_distance(split_name),
                }
            )
        return normalized

    def _extract_entries(self, payload: dict) -> list[dict]:
        list_payload = payload.get("list", [])
        if not isinstance(list_payload, list):
            return []

        normalized = []
        for item in list_payload:
            if not isinstance(item, dict):
                continue
            entry_id = str(item.get("entry") or item.get("entry_id") or item.get("id") or "").strip()
            name = str(item.get("name") or "").strip()
            bib = str(item.get("bib") or "").strip()
            division = str(item.get("division") or "").strip()
            if not entry_id or not name:
                continue
            normalized.append(
                {
                    "entry_id": entry_id,
                    "name": name,
                    "bib": bib,
                    "division": division,
                }
            )
        return normalized[:25]


def parse_run_distance(split_name: str) -> float | None:
    text = split_name.upper()
    mile_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:MI|MILE)", text)
    if mile_match:
        return float(mile_match.group(1))

    km_match = re.search(r"(\d+(?:\.\d+)?)\s*K", text)
    if km_match:
        return float(km_match.group(1)) * 0.621371

    return None


def find_t2_split(splits: list[dict]) -> dict | None:
    return next((split for split in splits if split["name"].upper() == "T2"), None)


def find_latest_split(splits: list[dict]) -> dict | None:
    if not splits:
        return None
    return max(splits, key=lambda split: split["seconds"])


def find_best_run_split(splits: list[dict], t2_seconds: int) -> dict | None:
    run_splits = [
        split
        for split in splits
        if split.get("distance_miles") and split["seconds"] >= t2_seconds
    ]
    if not run_splits:
        return None
    return max(run_splits, key=lambda split: split["distance_miles"])
