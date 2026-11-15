from typing import Any

import pytest
from pydantic import ValidationError

from src.models.models import (
    Station,
    StationEconomy,
    StationMarketItem,
    StationModule,
    StationNamedItem,
    StationShip,
)


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


def test_station_validates_and_serializes_nested_models():
    station = Station.model_validate({
        "id": "123",
        "name": "Daedalus",
        "system_name": "Sol",
        "distance": 0.0,
        "economies": [{"name": "Refinery", "share": 100.0}],
        "services": [{"name": "Dock"}],
        "modules": [{
            "category": "standard",
            "class": 1,
            "ed_symbol": "Adder_Armour_Grade1",
            "name": "Lightweight Alloy",
            "rating": "I",
        }],
        "ships": [{"name": "Adder", "price": 87810, "symbol": "Adder"}],
    })

    assert station.economies is not None
    assert station.services is not None
    assert station.modules is not None
    assert station.ships is not None
    assert isinstance(station.economies[0], StationEconomy)
    assert isinstance(station.services[0], StationNamedItem)
    assert isinstance(station.modules[0], StationModule)
    assert station.modules[0].class_ == 1
    assert station.model_dump(by_alias=True)["modules"][0]["class"] == 1
    assert isinstance(station.ships[0], StationShip)


def test_station_rejects_invalid_nested_market_item():
    with pytest.raises(ValidationError, match="buy_price"):
        Station.model_validate({
            "id": "123",
            "name": "Daedalus",
            "system_name": "Sol",
            "distance": 0,
            "market": [{
                "buy_price": "invalid",
                "category": "Metals",
                "commodity": "Gold",
                "demand": 1,
                "sell_price": 2,
                "supply": 3,
            }],
        })


def test_station_ignores_unexpected_fields():
    station = Station.model_validate({
        "id": "123",
        "name": "Daedalus",
        "system_name": "Sol",
        "distance": 0,
        "body_gravity": 1.0,
    })
    assert station.name == "Daedalus"
    assert "body_gravity" not in station.model_dump()
