import asyncio
import math

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

import server

SYSTEMS = {
    "Sol": {
        "coords": (0.0, 0.0, 0.0),
        "information": {"allegiance": "Federation"},
        "stations": [{"name": "Abraham Lincoln"}],
        "factions": [{"name": "Mother Gaia"}],
    },
    "Alpha Centauri": {"coords": (3.0, 4.0, 0.0)},
    "Bare": {},
}


class StubClient:
    """Replaces server.edsm instead of EdsmClient - no HTTP at all."""

    def _system(self, name):
        if name not in SYSTEMS:
            raise ValueError(f"System '{name}' not found")
        return SYSTEMS[name]

    def get_distance(self, from_system, to_system):
        return math.dist(self._system(from_system)["coords"], self._system(to_system)["coords"])

    def get_system_info(self, name):
        return self._system(name)["information"]

    def get_system_stations(self, name):
        return self._system(name).get("stations", [])

    def get_system_factions(self, name):
        return self._system(name).get("factions", [])


def call(tool, args):
    async def _run():
        async with Client(server.mcp) as client:
            return await client.call_tool(tool, args)

    return asyncio.run(_run())


@pytest.fixture(autouse=True)
def stub_client(monkeypatch):
    monkeypatch.setattr(server, "edsm", StubClient())


def test_registered_tools():
    async def _names():
        async with Client(server.mcp) as client:
            return {t.name for t in await client.list_tools()}

    assert asyncio.run(_names()) == {
        "get_distance_between_systems",
        "get_system_info",
        "get_system_stations",
        "get_system_factions",
        "get_item_prices",
    }


def test_distance_tool():
    result = call("get_distance_between_systems", {"from_system": "Sol", "to_system": "Alpha Centauri"})
    assert result.data == pytest.approx(5.0)


def test_system_info_tool():
    assert call("get_system_info", {"system": "Sol"}).data == {"allegiance": "Federation"}


def test_stations_and_factions_tools():
    assert call("get_system_stations", {"system": "Sol"}).data == [{"name": "Abraham Lincoln"}]
    assert call("get_system_factions", {"system": "Sol"}).data == [{"name": "Mother Gaia"}]


@pytest.mark.parametrize("tool", ["get_system_stations", "get_system_factions"])
def test_empty_result_is_explicit_empty_list(tool):
    result = call(tool, {"system": "Bare"})
    assert result.structured_content == {"result": []}
    assert result.data == []


@pytest.mark.parametrize(
    "tool,args",
    [
        ("get_distance_between_systems", {"from_system": "Sol", "to_system": "Nowhere"}),
        ("get_system_info", {"system": "Nowhere"}),
        ("get_system_stations", {"system": "Nowhere"}),
        ("get_system_factions", {"system": "Nowhere"}),
    ],
)
def test_unknown_system_surfaces_error_message(tool, args):
    with pytest.raises(ToolError, match="Nowhere"):
        call(tool, args)


def test_missing_required_argument_rejected():
    with pytest.raises(ToolError):
        call("get_system_info", {})
