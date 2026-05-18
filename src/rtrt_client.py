from __future__ import annotations

from racedata.providers.rtrt.client import RtrtClient, SessionCredentials


class RtrtClientAdapter(RtrtClient):
    """Half-iron adapter: requires env credentials (no session UUID)."""

    def __init__(self) -> None:
        creds = SessionCredentials.from_env()
        if not creds:
            self._missing = True
            super().__init__(SessionCredentials(app_id="", token=""))
            return
        self._missing = False
        super().__init__(creds)

    def ready(self) -> bool:
        return not getattr(self, "_missing", True) and bool(self.credentials.app_id and self.credentials.token)

    def post(self, url: str, payload: dict | None = None) -> dict:
        if not self.ready():
            raise RuntimeError("RTRT credentials are not configured")
        return super().post(url, payload)


# Backward-compatible alias used across the app/tests.
RtrtClient = RtrtClientAdapter
