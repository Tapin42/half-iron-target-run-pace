from __future__ import annotations

import re

from racedata.core.models import Race
from racedata.core.timing import parse_hhmmss, parse_run_distance, strip_fractional_time
from racedata.providers.rtrt.service import RtrtProvider
from src.races import RaceConfig
from src.rtrt_client import RtrtClient


class RtrtService:
    def __init__(self, client: RtrtClient) -> None:
        self.client = client
        self._provider = RtrtProvider(client)

    def search_athletes(self, race: RaceConfig, query: str) -> list[dict]:
        rows = self._provider.search_athletes(self._to_race(race), query)
        return [
            {
                "entry_id": row.entry_id,
                "profile_id": row.profile_id,
                "name": row.name,
                "bib": row.bib,
                "division": row.division,
            }
            for row in rows
        ]

    def fetch_splits(
        self, race: RaceConfig, entry_id: str, profile_id: str | None = None
    ) -> list[dict]:
        if profile_id:
            splits = self._provider.fetch_splits(
                self._to_race(race),
                profile_id,
                entry_id=entry_id,
                collapse_intermediates=False,
            )
            if splits:
                return self._to_legacy_splits(splits)

        url = f"https://api.rtrt.me/events/{race.event_key}/entries/{entry_id}/splits"
        payload = self.client.post(url, {"max": "200"})
        rows = self._provider._extract_split_rows(payload)
        return self._normalize_legacy_rows(rows)

    def fetch_finish_split_aliases(self, race: RaceConfig) -> set[str]:
        return self._provider.fetch_finish_split_aliases(self._to_race(race))

    def _to_race(self, race: RaceConfig) -> Race:
        app_id = ""
        creds = getattr(self.client, "credentials", None)
        if creds is not None:
            app_id = creds.app_id
        return Race(
            event_key=race.event_key,
            display_name=race.display_name,
            app_id=app_id,
        )

    def _normalize_legacy_rows(self, rows: list[dict]) -> list[dict]:
        normalized = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            split_name = str(
                row.get("split") or row.get("label") or row.get("point") or row.get("name") or ""
            ).strip()
            split_time = strip_fractional_time(str(row.get("time") or row.get("netTime") or ""))
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

    def _to_legacy_splits(self, splits) -> list[dict]:
        return [
            {
                "name": split.label,
                "time": split.clock_time,
                "seconds": split.clock_seconds,
                "distance_miles": parse_run_distance(split.label),
            }
            for split in splits
        ]


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


def is_run_start_split(split_name: str) -> bool:
    normalized = re.sub(r"[^A-Z0-9]+", " ", (split_name or "").upper()).strip()
    return normalized in {"RUN START", "START RUN"}


def find_run_start_split(splits: list[dict]) -> dict | None:
    return next((split for split in splits if is_run_start_split(split.get("name", ""))), None)


# Re-export for tests and calculations.
__all__ = [
    "RtrtService",
    "find_best_run_split",
    "find_latest_split",
    "find_run_start_split",
    "find_t2_split",
    "is_run_start_split",
    "parse_run_distance",
]
