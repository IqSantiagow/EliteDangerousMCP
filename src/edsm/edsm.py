import math

import requests

BASE_URL = "https://www.edsm.net/api-v1"
SYSTEM_BASE_URL = "https://www.edsm.net/api-system-v1"
USER_AGENT = "Elite Dangerous MCP"
TIMEOUT = 10


class EdsmClient:
    def __init__(self, client: requests.Session | None = None):
        self.client = client or requests
        self.system_cache = {}

    def _base_request_spec(self, url: str, name: str, **params) -> dict:
        response = self.client.get(
            url,
            params={"systemName": name, **params},
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT,
        )

        response.raise_for_status()

        try:
            data = response.json()
        except ValueError as e:
            raise ValueError(f"EDSM returned an invalid response for '{name}'") from e

        if not data:
            raise ValueError(f"System '{name}' not found")

        return data

    def get_system_info(self, name: str) -> dict:
        data = self.get_system(name)
        if "information" not in data:
            raise ValueError(f"System '{name}' has no detailed information")
        return data["information"]

    def get_system(self, name: str) -> dict:
        if name in self.system_cache:
            return self.system_cache[name]
        system = self._base_request_spec(
            BASE_URL + "/system", name, showCoordinates=1, showInformation=1
        )
        self.system_cache[name] = system
        return system

    def get_system_stations(self, name: str) -> list[dict]:
        return self._base_request_spec(SYSTEM_BASE_URL + "/stations", name).get(
            "stations", []
        )

    def get_system_factions(self, name: str) -> list[dict]:
        return self._base_request_spec(SYSTEM_BASE_URL + "/factions", name).get(
            "factions", []
        )

    def _get_coords(self, name: str) -> tuple[float, float, float]:
        coords = self.get_system(name).get("coords")
        if not coords:
            raise ValueError(f"System '{name}' has no known coordinates")
        return coords["x"], coords["y"], coords["z"]

    def get_distance(self, from_system: str, to_system: str) -> float:
        return math.dist(self._get_coords(from_system), self._get_coords(to_system))
