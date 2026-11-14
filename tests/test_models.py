from typing import Any

from src.models.models import Station, StationMarketItem


def test_station_maps_market_dicts_to_station_market_items():
    market_item = {
        "buy_price": 100,
        "category": "Metals",
        "commodity": "Gold",
        "demand": 600,
        "sell_price": 90,
        "supply": 200,
        "is_rare": False,
    }
    station_response: dict[str, Any] = {
        "id": "123",
        "name": "Abraham Lincoln",
        "system_name": "Sol",
        "distance": 0.0,
        "market": [market_item],
    }

    station = Station(**station_response)

    assert station.market == [StationMarketItem(**market_item)]


def test_station_preserves_existing_market_item_instances():
    market_item = StationMarketItem(
        buy_price=100,
        category="Metals",
        commodity="Gold",
        demand=600,
        sell_price=90,
        supply=200,
    )

    station = Station(
        id="123",
        name="Abraham Lincoln",
        system_name="Sol",
        distance=0.0,
        market=[market_item],
    )

    assert station.market is not None
    assert station.market[0] is market_item
