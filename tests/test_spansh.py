import runpy
from pathlib import Path
from unittest.mock import Mock

import pytest

from src.apis.spansh import SpanshClient
from src.apis.spansh_filters import SortType


def test_spansh_can_be_loaded_as_a_script():
    script = Path(__file__).resolve().parents[1] / "src" / "apis" / "spansh.py"
    assert "SpanshClient" in runpy.run_path(str(script))


def test_spansh_filters_match_station_search_format():
    http_client = Mock()
    http_client.post.return_value.json.return_value = {"results": []}

    SpanshClient(client=http_client).get_item_prices_around_reference_system(
        "Tritium", "Sol"
    )

    assert http_client.post.call_args.kwargs["json"] == {
        "filters": {
            "market": [{"name": "Tritium", "demand": {"comparison": ">=", "value": 500}}],
            "distance": {"min": "0", "max": "50"},
            "type": {"value": ["Drake-Class Carrier"], "logic": "NOT"},
            "market_updated_at": {"comparison": "<=>", "value": ["now-7d", "now"]},
            "has_large_pad": {"value": True},
        },
        "sort": [{"market_sell_price": [{"name": "Tritium", "direction": "desc"}]}],
        "size": 5,
        "page": 0,
        "reference_system": "Sol",
    }


def test_get_item_prices_sends_nested_filters():
    http_client = Mock()
    http_client.post.return_value.json.return_value = {"results": []}

    result = SpanshClient(client=http_client).get_item_prices_around_reference_system(
        "Gold", "Sol", maximum_distance=12.5, demand=600, supply=700
    )

    assert result == {"stations": []}
    assert http_client.post.call_args.kwargs["json"] == {
        "filters": {
            "market": [{
                "name": "Gold",
                "demand": {"comparison": ">=", "value": 600},
                "supply": {"comparison": ">=", "value": 700},
            }],
            "distance": {"min": "0", "max": "12.5"},
            "type": {"value": ["Drake-Class Carrier"], "logic": "NOT"},
            "market_updated_at": {"comparison": "<=>", "value": ["now-7d", "now"]},
            "has_large_pad": {"value": True},
        },
        "sort": [{"market_sell_price": [{"name": "Gold", "direction": "desc"}]}],
        "size": 5,
        "page": 0,
        "reference_system": "Sol",
    }


def test_buying_search_filters_supply_and_sorts_by_buy_price():
    http_client = Mock()
    http_client.post.return_value.json.return_value = {"results": []}

    SpanshClient(client=http_client).get_item_prices_around_reference_system(
        "Gold", "Sol", demand=None, supply=500, sort_type=SortType.MARKET_BUY_PRICE
    )

    payload = http_client.post.call_args.kwargs["json"]
    assert payload["filters"]["market"] == [{
        "name": "Gold",
        "supply": {"comparison": ">=", "value": 500},
        "buy_price": {"comparison": ">=", "value": 1},
    }]
    assert payload["sort"] == [
        {"market_buy_price": [{"name": "Gold", "direction": "asc"}]}
    ]


def test_search_accepts_extra_station_fields():
    http_client = Mock()
    http_client.post.return_value.json.return_value = {"results": [{
        "id": "1", "name": "Example", "system_name": "Sol", "distance": 5,
        "body_gravity": 1.0,
        "market": [{
            "commodity": "Gold", "category": "Metals", "buy_price": 123,
            "sell_price": 456, "supply": 700, "demand": 0,
        }],
    }]}

    result = SpanshClient(client=http_client).get_item_prices_around_reference_system(
        "Gold", "Sol", demand=None, supply=500, sort_type=SortType.MARKET_BUY_PRICE
    )

    assert result["stations"] == [{
        "name": "Example", "system": "Sol", "distance": 5,
        "desired_item": {
            "name": "Gold", "buy_price": 123, "sell_price": 456,
            "supply": 700, "demand": 0,
        },
    }]


def test_get_market_searches_by_system_and_station():
    http_client = Mock()
    http_client.post.return_value.json.return_value = {"count": 2, "results": [
        {"name": "Daedalus", "system_name": "Other", "market": []},
        {"name": "Daedalus", "system_name": "Sol", "market": [{
            "commodity": "Gold", "category": "Metals", "buy_price": 123,
            "sell_price": 456, "supply": 10, "demand": 20,
        }]},
    ]}

    market = SpanshClient(client=http_client).get_market("Sol", "Daedalus")

    assert market[0].commodity == "Gold"
    assert market[0].supply == 10
    http_client.post.assert_called_once_with(
        "https://spansh.co.uk/api/stations/search",
        json={
            "filters": {
                "name": {"value": "Daedalus"},
                "system_name": {"value": "Sol"},
            },
            "sort": [],
            "size": 5,
            "page": 0,
        },
    )
    http_client.post.return_value.raise_for_status.assert_called_once_with()


def test_get_market_reports_missing_market_data():
    http_client = Mock()
    http_client.post.return_value.json.return_value = {"count": 1, "results": [{
        "name": "Daedalus", "system_name": "Sol", "market": None,
    }]}
    with pytest.raises(ValueError, match="No market data"):
        SpanshClient(client=http_client).get_market("Sol", "Daedalus")


def test_get_market_uses_only_first_page():
    http_client = Mock()
    http_client.post.return_value.json.return_value = {
        "count": 5,
        "results": [
            {"name": "Daedalus", "system_name": "Other"} for _ in range(5)
        ],
    }

    with pytest.raises(ValueError, match="Station 'Daedalus' not found"):
        SpanshClient(client=http_client).get_market("Sol", "Daedalus")
    assert http_client.post.call_count == 1


def test_get_market_rejects_partial_name_matches():
    http_client = Mock()
    http_client.post.return_value.json.return_value = {"count": 1, "results": [
        {"name": "Daedalus", "system_name": "Sol", "market": []}
    ]}
    with pytest.raises(ValueError, match="Station 'Dae' not found"):
        SpanshClient(client=http_client).get_market("Sol", "Dae")


def test_get_market_reports_no_search_results():
    http_client = Mock()
    http_client.post.return_value.json.return_value = {"count": 0, "results": []}
    with pytest.raises(ValueError, match="Station 'Daedalus' not found"):
        SpanshClient(client=http_client).get_market("Sol", "Daedalus")


def station(market):
    return {
        "id": "1",
        "name": "Jameson Memorial",
        "system_name": "Shinrarta Dezhra",
        "distance": 0.0,
        "market": market,
    }


@pytest.mark.parametrize(
    ("sort_type", "demand", "supply", "expected_market_key"),
    [
        (
            SortType.MARKET_SELL_PRICE,
            500,
            None,
            "demand",
        ),
        (
            SortType.MARKET_BUY_PRICE,
            None,
            500,
            "supply",
        ),
    ],
)
def test_get_item_prices_normalizes_market_data(
    sort_type,
    demand,
    supply,
    expected_market_key,
):
    http_client = Mock()
    response = Mock()
    response.json.return_value = {
        "results": [
            station(
                [
                    {
                        "buy_price": 1234,
                        "category": "Metals",
                        "commodity": "Gold",
                        "demand": 600,
                        "sell_price": 2345,
                        "supply": 700,
                    },
                    {
                        "buy_price": 10,
                        "category": "Metals",
                        "commodity": "Silver",
                        "demand": 20,
                        "sell_price": 30,
                        "supply": 40,
                    },
                ]
            ),
            station(None),
            station(
                [
                    {
                        "buy_price": 10,
                        "category": "Metals",
                        "commodity": "Silver",
                        "demand": 20,
                        "sell_price": 30,
                        "supply": 40,
                    }
                ]
            ),
        ]
    }
    http_client.post.return_value = response

    result = SpanshClient(client=http_client).get_item_prices_around_reference_system(
        item_name="Gold",
        reference_system="Sol",
        demand=demand,
        supply=supply,
        sort_type=sort_type,
    )

    assert result == {
        "stations": [
            {
                "name": "Jameson Memorial",
                "system": "Shinrarta Dezhra",
                "distance": 0.0,
                "desired_item": {
                    "name": "Gold",
                    "buy_price": 1234,
                    "sell_price": 2345,
                    "demand": 600,
                    "supply": 700,
                },
            }
        ]
    }
    response.raise_for_status.assert_called_once_with()
    payload = http_client.post.call_args.kwargs["json"]
    assert expected_market_key in payload["filters"]["market"][0]
    assert sort_type.value in payload["sort"][0]


@pytest.mark.parametrize(
    "parameter",
    [
        "item_name",
        "reference_system",
        "maximum_distance",
        "sort_type",
    ],
)
def test_get_item_prices_rejects_none_parameters(parameter):
    arguments = {
        "item_name": "Gold",
        "reference_system": "Sol",
        "maximum_distance": 50.0,
        "demand": 500,
        "sort_type": SortType.MARKET_SELL_PRICE,
    }
    arguments[parameter] = None
    http_client = Mock()

    with pytest.raises(TypeError, match=f"{parameter} must not be None"):
        SpanshClient(client=http_client).get_item_prices_around_reference_system(**arguments)

    http_client.post.assert_not_called()


COMMON_STATION_FILTERS = {
    "distance": {"min": "0", "max": "25"},
    "type": {"value": ["Drake-Class Carrier"], "logic": "NOT"},
    "has_large_pad": {"value": True},
}


def search_payload(filters: dict) -> dict:
    return {
        "filters": filters,
        "sort": [{"distance": {"direction": "asc"}}],
        "size": 5,
        "page": 0,
        "reference_system": "Sol",
    }


def client_returning(results: list) -> tuple[Mock, SpanshClient]:
    http_client = Mock()
    http_client.post.return_value.json.return_value = {"results": results}
    return http_client, SpanshClient(client=http_client)


def test_ship_search_sends_one_entry_per_ship_and_shipyard_freshness():
    http_client, client = client_returning([])

    result = client.get_ship_prices_around_reference_system(
        ["Anaconda", "Python"], "Sol", maximum_distance=25
    )

    assert result == {"stations": []}
    assert http_client.post.call_args.kwargs["json"] == search_payload(
        {
            "ships": [
                {"name": {"value": ["Anaconda"]}},
                {"name": {"value": ["Python"]}},
            ],
            "shipyard_updated_at": {"comparison": "<=>", "value": ["now-7d", "now"]},
            **COMMON_STATION_FILTERS,
        }
    )


def test_ship_search_returns_only_stations_with_every_requested_ship():
    def station(name, ships):
        return {
            "id": name,
            "name": name,
            "system_name": "Wolf 359",
            "distance": 7.8,
            "shipyard_updated_at": "2026-11-14T10:00:00Z",
            "ships": [{"name": n, "price": p, "symbol": n} for n, p in ships],
        }

    _, client = client_returning(
        [
            station("Both", [("Anaconda", 146969450), ("Python", 56978000), ("Hauler", 52720)]),
            station("Only Anaconda", [("Anaconda", 146969450)]),
        ]
    )

    result = client.get_ship_prices_around_reference_system(["Anaconda", "Python"], "Sol")

    assert result == {
        "stations": [
            {
                "name": "Both",
                "system": "Wolf 359",
                "distance": 7.8,
                "shipyard_updated_at": "2026-11-14T10:00:00Z",
                "ships": [
                    {"name": "Anaconda", "price": 146969450},
                    {"name": "Python", "price": 56978000},
                ],
            }
        ]
    }


def test_module_search_applies_shared_class_and_rating_to_every_module():
    http_client, client = client_returning([])

    result = client.get_module_prices_around_reference_system(
        ["Frame Shift Drive", "Power Plant"],
        "Sol",
        maximum_distance=25,
        module_class=5,
        rating="A",
    )

    assert result == {"stations": []}
    entry = {"class": {"value": ["5"]}, "rating": {"value": ["A"]}}
    assert http_client.post.call_args.kwargs["json"] == search_payload(
        {
            "modules": [
                {"name": {"value": ["Frame Shift Drive"]}, **entry},
                {"name": {"value": ["Power Plant"]}, **entry},
            ],
            "outfitting_updated_at": {"comparison": "<=>", "value": ["now-7d", "now"]},
            **COMMON_STATION_FILTERS,
        }
    )


def test_module_search_omits_class_and_rating_when_not_given():
    http_client, client = client_returning([])

    client.get_module_prices_around_reference_system(["Frame Shift Drive"], "Sol")

    sent = http_client.post.call_args.kwargs["json"]["filters"]["modules"]
    assert sent == [{"name": {"value": ["Frame Shift Drive"]}}]


def test_module_search_returns_only_stations_with_every_module_and_matching_rows():
    def module(name, class_, rating, price):
        return {
            "name": name,
            "class": class_,
            "rating": rating,
            "category": "Core Internals",
            "ed_symbol": "x",
            "price": price,
        }

    def station(name, modules):
        return {
            "id": name,
            "name": name,
            "system_name": "Wolf 359",
            "distance": 7.8,
            "outfitting_updated_at": "2026-11-14T10:00:00Z",
            "modules": modules,
        }

    _, client = client_returning(
        [
            station(
                "Both",
                [
                    module("Frame Shift Drive", 5, "A", 1_800_000),
                    module("Frame Shift Drive", 4, "A", 600_000),
                    module("Power Plant", 5, "A", 900_000),
                ],
            ),
            station("Only drive", [module("Frame Shift Drive", 5, "A", 1_800_000)]),
        ]
    )

    result = client.get_module_prices_around_reference_system(
        ["Frame Shift Drive", "Power Plant"], "Sol", module_class=5, rating="A"
    )

    assert result == {
        "stations": [
            {
                "name": "Both",
                "system": "Wolf 359",
                "distance": 7.8,
                "outfitting_updated_at": "2026-11-14T10:00:00Z",
                "modules": [
                    {"name": "Frame Shift Drive", "class": 5, "rating": "A", "price": 1_800_000},
                    {"name": "Power Plant", "class": 5, "rating": "A", "price": 900_000},
                ],
            }
        ]
    }


def test_service_search_sends_one_entry_per_service():
    http_client, client = client_returning([])

    result = client.get_service_stations_around_reference_system(
        ["Repair", "Refuel"], "Sol", maximum_distance=25
    )

    assert result == {"stations": []}
    assert http_client.post.call_args.kwargs["json"] == search_payload(
        {
            "services": [
                {"name": {"value": ["Repair"]}},
                {"name": {"value": ["Refuel"]}},
            ],
            **COMMON_STATION_FILTERS,
        }
    )


def test_service_search_returns_stations_that_have_every_service():
    _, client = client_returning(
        [
            {
                "id": "1",
                "name": "Both",
                "system_name": "Wolf 359",
                "distance": 7.8,
                "distance_to_arrival": 450.5,
                "services": [{"name": "Repair"}, {"name": "Refuel"}, {"name": "Market"}],
            },
            {
                "id": "2",
                "name": "Only repair",
                "system_name": "Sirius",
                "distance": 8.6,
                "services": [{"name": "Repair"}],
            },
        ]
    )

    result = client.get_service_stations_around_reference_system(["Repair", "Refuel"], "Sol")

    assert result == {
        "stations": [
            {"name": "Both", "system": "Wolf 359", "distance": 7.8, "distance_to_arrival": 450.5}
        ]
    }


@pytest.mark.parametrize(
    ("method", "names", "message"),
    [
        ("get_ship_prices_around_reference_system", ["Anaconda", "Spaceboat"], "Unknown ships: Spaceboat"),
        ("get_module_prices_around_reference_system", ["Warp Core"], "Unknown modules: Warp Core"),
        ("get_service_stations_around_reference_system", ["Repair", "Teleport"], "Unknown services: Teleport"),
    ],
)
def test_station_searches_reject_unsupported_names_before_any_request(method, names, message):
    http_client, client = client_returning([])

    with pytest.raises(ValueError, match=message):
        getattr(client, method)(names, "Sol")

    http_client.post.assert_not_called()


@pytest.mark.parametrize(
    "method",
    [
        "get_ship_prices_around_reference_system",
        "get_module_prices_around_reference_system",
        "get_service_stations_around_reference_system",
    ],
)
def test_station_searches_require_at_least_one_name(method):
    http_client, client = client_returning([])

    with pytest.raises(ValueError, match="at least one name"):
        getattr(client, method)([], "Sol")

    http_client.post.assert_not_called()
