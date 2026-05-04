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

    def add(
        self,
        race_slug: str,
        entry_id: str,
        bib: str,
        name: str,
        division: str,
        target_finish_time: str,
    ) -> dict:
        all_rows = self._read()
        row = {
            "id": str(uuid.uuid4()),
            "race_slug": race_slug,
            "entry_id": entry_id,
            "bib": bib,
            "name": name,
            "division": division,
            "target_finish_time": target_finish_time,
        }
        all_rows.append(row)
        self._write(all_rows)
        return row
