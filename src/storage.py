import json
from pathlib import Path
import uuid


class AthleteStore:
    def __init__(self, file_path: str) -> None:
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self._write([])

    def _read(self) -> list[dict]:
        with self.file_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, list) else []

    def _write(self, payload: list[dict]) -> None:
        with self.file_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)

    def list(self) -> list[dict]:
        return self._read()

    def get(self, athlete_id: str) -> dict | None:
        return next((item for item in self._read() if item["id"] == athlete_id), None)

    def find_by_identity(
        self, race_slug: str, entry_id: str | None = None, bib: str | None = None
    ) -> dict:
        normalized_entry_id = (entry_id or "").strip()
        normalized_bib = (bib or "").strip()
        rows = [row for row in self._read() if row.get("race_slug") == race_slug]

        entry_match = None
        if normalized_entry_id:
            entry_match = next(
                (
                    row
                    for row in rows
                    if (row.get("entry_id") or "").strip() == normalized_entry_id
                ),
                None,
            )

        bib_match = None
        if normalized_bib:
            bib_match = next(
                (row for row in rows if (row.get("bib") or "").strip() == normalized_bib),
                None,
            )

        if normalized_entry_id:
            if entry_match and normalized_bib and bib_match and bib_match["id"] != entry_match["id"]:
                return {"status": "conflict"}
            if entry_match:
                return {"status": "match", "athlete": entry_match}
            return {"status": "none"}

        if normalized_bib:
            if bib_match:
                return {"status": "match", "athlete": bib_match}
            return {"status": "none"}

        return {"status": "none"}

    def update_target_time(self, athlete_id: str, target_finish_time: str) -> dict | None:
        all_rows = self._read()
        for row in all_rows:
            if row["id"] == athlete_id:
                row["target_finish_time"] = target_finish_time
                self._write(all_rows)
                return row
        return None

    def delete(self, athlete_id: str) -> dict | None:
        all_rows = self._read()
        for index, row in enumerate(all_rows):
            if row["id"] == athlete_id:
                deleted = all_rows.pop(index)
                self._write(all_rows)
                return deleted
        return None

    def add(
        self,
        race_slug: str,
        entry_id: str,
        bib: str,
        name: str,
        division: str,
        target_finish_time: str,
        profile_id: str = "",
    ) -> dict:
        normalized_entry_id = (entry_id or "").strip()
        normalized_bib = (bib or "").strip()
        if not normalized_entry_id and not normalized_bib:
            raise ValueError("missing identity")

        identity_check = self.find_by_identity(
            race_slug=race_slug,
            entry_id=normalized_entry_id,
            bib=normalized_bib,
        )
        if identity_check["status"] == "match":
            raise ValueError("duplicate identity")
        if identity_check["status"] == "conflict":
            raise ValueError("conflicting identity")

        all_rows = self._read()
        row = {
            "id": str(uuid.uuid4()),
            "race_slug": race_slug,
            "entry_id": normalized_entry_id,
            "profile_id": profile_id,
            "bib": normalized_bib,
            "name": name,
            "division": division,
            "target_finish_time": target_finish_time,
        }
        all_rows.append(row)
        self._write(all_rows)
        return row
