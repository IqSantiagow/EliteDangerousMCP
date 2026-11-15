import pytest

from src.apis.spansh_filters import (
    Direction,
    DistanceFilter,
    MarketFilter,
    ModuleFilter,
    ShipFilter,
    SimpleFilter,
    SortFilter,
    SortType,
    SpanshFilter,
    StationFilter,
)


def dump(spansh_filter: SpanshFilter) -> dict:
    return spansh_filter.model_dump(mode="json", by_alias=True, exclude_none=True)


def test_where_to_buy_a_ship_request_matches_spansh_format():
    request = SpanshFilter(
        reference_system="Sol",
        filters=StationFilter(
            ships=[ShipFilter(name=SimpleFilter(value=["Anaconda"]))],
            distance=DistanceFilter(min=0, max=50),
            type=SimpleFilter(value=["Drake-Class Carrier"], logic="NOT"),
            has_large_pad=SimpleFilter(value=True),
        ),
        sort=[SortFilter(type=SortType.DISTANCE, direction=Direction.ASC)],
    )

    assert dump(request) == {
        "size": 5,
        "page": 0,
        "reference_system": "Sol",
        "filters": {
            "ships": [{"name": {"value": ["Anaconda"]}}],
            "distance": {"min": "0", "max": "50"},
            "type": {"value": ["Drake-Class Carrier"], "logic": "NOT"},
            "has_large_pad": {"value": True},
        },
        "sort": [{"distance": {"direction": "asc"}}],
    }


def test_station_filter_rejects_market_and_ships_together():
    with pytest.raises(ValueError, match="exactly one of market, ships or modules"):
        StationFilter(
            market=[MarketFilter(item="Gold")],
            ships=[ShipFilter(name=SimpleFilter(value=["Anaconda"]))],
        )


def test_station_filter_requires_market_or_ships():
    with pytest.raises(ValueError, match="exactly one of market, ships or modules"):
        StationFilter(distance=DistanceFilter(min=0, max=50))


def test_station_filter_rejects_modules_together_with_ships():
    with pytest.raises(ValueError, match="exactly one of market, ships or modules"):
        StationFilter(
            ships=[ShipFilter(name=SimpleFilter(value=["Anaconda"]))],
            modules=[ModuleFilter(name=SimpleFilter(value=["Frame Shift Drive"]))],
        )


def test_module_filter_serializes_class_and_rating_like_spansh():
    request = SpanshFilter(
        reference_system="Sol",
        filters=StationFilter(
            modules=[
                ModuleFilter(
                    name=SimpleFilter(value=["Frame Shift Drive"]),
                    class_=SimpleFilter(value=["5"]),
                    rating=SimpleFilter(value=["A"]),
                )
            ]
        ),
        sort=[SortFilter(type=SortType.DISTANCE, direction=Direction.ASC)],
    )

    assert dump(request)["filters"] == {
        "modules": [
            {
                "name": {"value": ["Frame Shift Drive"]},
                "class": {"value": ["5"]},
                "rating": {"value": ["A"]},
            }
        ]
    }
