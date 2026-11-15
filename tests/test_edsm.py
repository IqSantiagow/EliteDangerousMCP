import math
from json import JSONDecodeError

import httpx
import pytest

from src.apis.edsm import EdsmClient

SOL = {
    "name": "Sol",
    "coords": {"x": 0.0, "y": 0.0, "z": 0.0},
    "information": {"allegiance": "Federation", "population": 22780919531},
}
COLONIA = {"name": "Colonia", "coords": {"x": -9530.5, "y": -910.28, "z": 19808.125}}
SOL_STATIONS = [{"name": "Abraham Lincoln"}]
SOL_FACTIONS = [{"name": "Mother Gaia"}]


class FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("GET", "https://example.com")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError(
                f"{self.status_code} error", request=request, response=response
            )

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class FakeSession:
    """Injected into EdsmClient instead of httpx.Client.

    Responses are set by key: the system name for /system, `stations:<name>`
    and `factions:<name>` for the other endpoints.
    """

    def __init__(self):
        self.calls = []
        self.responses = {}

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append(
            {"url": url, "params": params, "headers": headers, "timeout": timeout}
        )
        assert params is not None
        endpoint = url.rsplit("/", 1)[1]
        name = params["systemName"]
        return self.responses[name if endpoint == "system" else f"{endpoint}:{name}"]


@pytest.fixture
def session():
    return FakeSession()


@pytest.fixture
def client(session):
    return EdsmClient(client=session)


def test_default_client_uses_httpx():
    client = EdsmClient().client
    try:
        assert isinstance(client, httpx.Client)
    finally:
        client.close()


def test_get_system_sends_expected_request(client, session):
    session.responses["Sol"] = FakeResponse(SOL)

    assert client.get_system("Sol") == SOL

    (call,) = session.calls
    assert call["url"] == "https://www.edsm.net/api-v1/system"
    assert call["params"] == {
        "systemName": "Sol",
        "showCoordinates": 1,
        "showInformation": 1,
    }
    assert call["headers"] == {"User-Agent": "Elite Dangerous MCP"}
    assert call["timeout"] == 10


@pytest.mark.parametrize("empty", [[], {}, None])
def test_get_system_unknown_system_raises(client, session, empty):
    session.responses["Nowhere"] = FakeResponse(empty)

    with pytest.raises(ValueError, match="'Nowhere' not found"):
        client.get_system("Nowhere")


def test_get_system_http_error_propagates(client, session):
    session.responses["Sol"] = FakeResponse({}, status=500)

    with pytest.raises(httpx.HTTPStatusError):
        client.get_system("Sol")


def test_get_system_invalid_json_raises_value_error(client, session):
    session.responses["Sol"] = FakeResponse(JSONDecodeError("boom", "", 0))

    with pytest.raises(ValueError, match="invalid response for 'Sol'"):
        client.get_system("Sol")


def test_get_system_info_returns_information(client, session):
    session.responses["Sol"] = FakeResponse(SOL)

    assert client.get_system_info("Sol") == SOL["information"]


def test_get_system_info_missing_information_raises(client, session):
    session.responses["Colonia"] = FakeResponse(COLONIA)

    with pytest.raises(ValueError, match="no detailed information"):
        client.get_system_info("Colonia")


def test_get_distance_euclidean(client, session):
    session.responses["Sol"] = FakeResponse(SOL)
    session.responses["Colonia"] = FakeResponse(COLONIA)

    expected = math.sqrt(9530.5**2 + 910.28**2 + 19808.125**2)
    assert client.get_distance("Sol", "Colonia") == pytest.approx(expected)
    assert client.get_distance("Sol", "Colonia") == pytest.approx(
        client.get_distance("Colonia", "Sol")
    )


def test_get_distance_same_system_is_zero(client, session):
    session.responses["Sol"] = FakeResponse(SOL)

    assert client.get_distance("Sol", "Sol") == 0


def test_get_distance_unknown_system_raises(client, session):
    session.responses["Sol"] = FakeResponse(SOL)
    session.responses["Nowhere"] = FakeResponse([])

    with pytest.raises(ValueError, match="'Nowhere' not found"):
        client.get_distance("Sol", "Nowhere")


def test_get_distance_system_without_coords_raises_clear_error(client, session):
    session.responses["Sol"] = FakeResponse(SOL)
    session.responses["Hidden"] = FakeResponse({"name": "Hidden"})

    with pytest.raises(ValueError, match="'Hidden' has no known coordinates"):
        client.get_distance("Sol", "Hidden")


def test_get_system_stations_uses_stations_endpoint(client, session):
    session.responses["stations:Sol"] = FakeResponse(
        {"name": "Sol", "stations": SOL_STATIONS}
    )

    assert client.get_system_stations("Sol") == SOL_STATIONS

    (call,) = session.calls
    assert call["url"] == "https://www.edsm.net/api-system-v1/stations"
    assert call["params"] == {"systemName": "Sol"}
    assert call["headers"] == {"User-Agent": "Elite Dangerous MCP"}
    assert call["timeout"] == 10


def test_get_system_factions_uses_factions_endpoint(client, session):
    session.responses["factions:Sol"] = FakeResponse(
        {"name": "Sol", "controllingFaction": {}, "factions": SOL_FACTIONS}
    )

    assert client.get_system_factions("Sol") == SOL_FACTIONS

    (call,) = session.calls
    assert call["url"] == "https://www.edsm.net/api-system-v1/factions"


def test_stations_and_factions_default_to_empty_list(client, session):
    session.responses["stations:Bare"] = FakeResponse({"name": "Bare"})
    session.responses["factions:Bare"] = FakeResponse({"name": "Bare"})

    assert client.get_system_stations("Bare") == []
    assert client.get_system_factions("Bare") == []


@pytest.mark.parametrize("method", ["get_system_stations", "get_system_factions"])
def test_stations_and_factions_unknown_system_raises(client, session, method):
    session.responses["stations:Nowhere"] = FakeResponse([])
    session.responses["factions:Nowhere"] = FakeResponse([])

    with pytest.raises(ValueError, match="'Nowhere' not found"):
        getattr(client, method)("Nowhere")


def test_get_system_is_cached(client, session):
    session.responses["Sol"] = FakeResponse(SOL)

    client.get_system("Sol")
    client.get_system("Sol")

    assert len(session.calls) == 1
