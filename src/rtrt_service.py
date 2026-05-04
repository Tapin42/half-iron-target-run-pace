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

        profiles_url = f"https://api.rtrt.me/events/{race.event_key}/profiles"
        payload = self.client.post(
            profiles_url,
            {
                "max": "100",
                "total": "1",
                "failonmax": "1",
                "search": query,
                "module": "0",
                "source": "webtracker",
            },
        )
        return self._extract_entries(payload, limit=25)

    def fetch_splits(
        self, race: RaceConfig, entry_id: str, profile_id: str | None = None
    ) -> list[dict]:
        if profile_id:
            profile_url = f"https://api.rtrt.me/events/{race.event_key}/profiles/{profile_id}/splits"
            payload = self.client.post(profile_url, {"max": "200"})
            profile_splits = self._normalize_splits(self._extract_split_rows(payload))
            if profile_splits:
                return profile_splits

        split_url = f"https://api.rtrt.me/events/{race.event_key}/entries/{entry_id}/splits"
        payload = self.client.post(split_url, {"max": "200"})
        return self._normalize_splits(self._extract_split_rows(payload))

    def _normalize_splits(self, split_rows: list[dict]) -> list[dict]:
        normalized = []
        for row in split_rows:
            if not isinstance(row, dict):
                continue
            split_name = str(
                row.get("split") or row.get("label") or row.get("point") or row.get("name") or ""
            ).strip()
            split_time = str(row.get("time") or row.get("netTime") or "").split(".")[0]
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

    def _extract_split_rows(self, payload: dict) -> list[dict]:
        rows: list[dict] = []

        direct_splits = payload.get("splits")
        if isinstance(direct_splits, list):
            rows.extend(item for item in direct_splits if isinstance(item, dict))

        list_payload = payload.get("list")
        if isinstance(list_payload, list):
            for item in list_payload:
                if not isinstance(item, dict):
                    continue

                # Some RTRT payloads return split rows directly in "list".
                if item.get("time") and (
                    item.get("name") or item.get("split") or item.get("label") or item.get("point")
                ):
                    rows.append(item)

                # Fallback shape: entry records with nested split arrays.
                embedded = item.get("splits")
                if isinstance(embedded, list):
                    rows.extend(split for split in embedded if isinstance(split, dict))

        return rows

    def _extract_entries(self, payload: dict, *, limit: int | None = None) -> list[dict]:
        list_payload = payload.get("list", [])
        if not isinstance(list_payload, list):
            return []

        normalized = []
        for item in list_payload:
            if not isinstance(item, dict):
                continue
            entry_id = str(
                item.get("entry")
                or item.get("entry_id")
                or item.get("id")
                or item.get("i")
                or item.get("u")
                or item.get("pid")
                or ""
            ).strip()
            first_name = str(item.get("first") or item.get("firstname") or "").strip()
            if not first_name:
                first_name = str(item.get("fname") or "").strip()
            last_name = str(item.get("last") or item.get("lastname") or "").strip()
            if not last_name:
                last_name = str(item.get("lname") or "").strip()
            full_name = " ".join(part for part in (first_name, last_name) if part)
            name = str(item.get("name") or full_name).strip()
            bib = str(item.get("bib") or item.get("racebib") or "").strip()
            division = str(
                item.get("division")
                or item.get("agegroup")
                or item.get("category")
                or item.get("class")
                or ""
            ).strip()
            if not entry_id or not name:
                continue
            normalized.append(
                {
                    "entry_id": entry_id,
                    "profile_id": str(
                        item.get("pid")
                        or item.get("profile")
                        or item.get("profile_id")
                        or ""
                    ).strip(),
                    "name": name,
                    "bib": bib,
                    "division": division,
                }
            )
            if limit is not None and len(normalized) >= limit:
                return normalized
        return normalized


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
