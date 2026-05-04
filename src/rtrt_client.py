import os
import requests


RTRT_BASE_PARAMS = {
    "timesort": "1",
    "nohide": "1",
    "checksum": "",
    "max": "200",
    "catloc": "1",
    "cattotal": "1",
    "units": "standard",
    "source": "webtracker",
}


class RtrtClient:
    def __init__(self) -> None:
        self.app_id = os.getenv("RTRT_APPID", "")
        self.token = os.getenv("RTRT_TOKEN", "")

    def ready(self) -> bool:
        return bool(self.app_id and self.token)

    def post(self, url: str, payload: dict | None = None) -> dict:
        if not self.ready():
            raise RuntimeError("RTRT credentials are not configured")

        data = RTRT_BASE_PARAMS.copy()
        data["appid"] = self.app_id
        data["token"] = self.token
        if payload:
            data.update(payload)

        response = requests.post(url, data=data, timeout=20)
        response.raise_for_status()
        result = response.json()
        if not isinstance(result, dict):
            raise RuntimeError("RTRT payload is not an object")
        return result
