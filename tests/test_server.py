import asyncio
import math

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

import server
from src.apis.spansh_filters import SortType
from src.models.models import StationMarketItem

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
        "get_supported_commodities",
        "find_best_selling_station",
        "find_best_buying_station",
        "compare_station_markets",
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


@pytest.mark.parametrize(
    ("tool", "expected_filters"),
    [
        ("find_best_selling_station", {"demand": 300}),
        (
            "find_best_buying_station",
            {"demand": None, "supply": 300, "sort_type": SortType.MARKET_BUY_PRICE},
        ),
    ],
)
def test_station_search_tools_select_market_direction(
    monkeypatch, tool, expected_filters
):
    calls = []

    class StubSpanshClient:
        def get_item_prices_around_reference_system(self, **kwargs):
            calls.append(kwargs)
            return kwargs

    monkeypatch.setattr(server, "spansh", StubSpanshClient())

    result = call(
        tool,
        {
            "item_name": "Gold",
            "reference_system": "Sol",
            "maximum_distance": 25.0,
            "demand": 300,
        },
    )

    expected = {
        "item_name": "Gold",
        "reference_system": "Sol",
        "maximum_distance": 25.0,
        **expected_filters,
    }
    assert result.data == expected
    assert calls == [expected]


def market_item(name, buy, sell, supply, demand):
    return StationMarketItem(
        commodity=name,
        category="Metals",
        buy_price=buy,
        sell_price=sell,
        supply=supply,
        demand=demand,
    )


def test_compare_station_markets_uses_stations_and_trade_limits(monkeypatch):
    class MarketClient:
        def get_market(self, system_name, station_name):
            return {
                ("Sol", "Source"): [
                    market_item("Gold", 100, 0, 20, 0),
                    market_item("Silver", 150, 0, 3, 0),
                    market_item("Copper", 0, 0, 10, 0),
                    market_item("Aluminium", 100, 0, 10, 0),
                    market_item("Platinum", 100, 0, 40, 0),
                ],
                ("Alpha Centauri", "Destination"): [
                    market_item("Gold", 0, 200, 0, 5),
                    market_item("Silver", 0, 180, 0, 50),
                    market_item("Copper", 0, 200, 0, 10),
                    market_item("Aluminium", 0, 90, 0, 10),
                    market_item("Platinum", 0, 120, 0, 30),
                ],
            }[(system_name, station_name)]

    monkeypatch.setattr(server, "spansh", MarketClient())
    result = call(
        "compare_station_markets",
        {
            "from_system": "Sol", "from_station": "Source",
            "to_system": "Alpha Centauri", "to_station": "Destination", "cargo": 10,
        },
    )
    assert result.data == {
        "Gold": {"from": 100, "to": 200, "difference": 100, "quantity": 5, "profit": 500},
        "Silver": {"from": 150, "to": 180, "difference": 30, "quantity": 3, "profit": 90},
        "Platinum": {"from": 100, "to": 120, "difference": 20, "quantity": 10, "profit": 200},
    }


@pytest.mark.parametrize("cargo", [0, -1])
def test_compare_station_markets_rejects_nonpositive_capacity(cargo):
    with pytest.raises(ToolError, match="cargo must be greater than zero"):
        call(
            "compare_station_markets",
            {
                "from_system": "Sol", "from_station": "Source",
                "to_system": "Sol", "to_station": "Destination", "cargo": cargo,
            },
        )


def test_compare_station_markets_reports_unknown_station(monkeypatch):
    class MarketClient:
        def get_market(self, system_name, station_name):
            raise ValueError(f"Station '{station_name}' not found in '{system_name}'")

    monkeypatch.setattr(server, "spansh", MarketClient())
    with pytest.raises(ToolError, match="Station 'Missing'"):
        call(
            "compare_station_markets",
            {
                "from_system": "Sol", "from_station": "Missing",
                "to_system": "Sol", "to_station": "Destination", "cargo": 10,
            },
        )
