import httpx

from src.apis.spansh_filters import (
    ComparisonFilter,
    ComparisonType,
    Direction,
    DistanceFilter,
    MarketFilter,
    ShipFilter,
    SimpleFilter,
    SortFilter,
    SortType,
    SpanshFilter,
    StationFilter,
)
from src.models.models import COMMODITIES, Station, StationMarketItem

STATION_SEARCH_URL = "https://spansh.co.uk/api/stations/search"


class SpanshClient:
    def __init__(self, client: httpx.Client | None = None):
        self.client = client or httpx.Client()

    def get_item_prices_around_reference_system(
        self,
        item_name: str,
        reference_system: str,
        maximum_distance: float = 50.0,
        demand: int | None = 500,
        supply: int | None = None,
        sort_type: SortType = SortType.MARKET_SELL_PRICE,
    ) -> dict:
        for name, value in (
            ("item_name", item_name),
            ("reference_system", reference_system),
            ("maximum_distance", maximum_distance),
            ("sort_type", sort_type),
        ):
            if value is None:
                raise TypeError(f"{name} must not be None")

        if item_name not in COMMODITIES:
            raise ValueError(f"Unknown commodity: {item_name}")

        filters = MarketFilter(
            item=item_name,
            demand=(
                ComparisonFilter(
                    comparison=ComparisonType.GREATER_THAN_EQUAL, value=demand
                )
                if demand is not None
                else None
            ),
            supply=(
                ComparisonFilter(
                    comparison=ComparisonType.GREATER_THAN_EQUAL, value=supply
                )
                if supply is not None
                else None
            ),
            buy_price=(
                ComparisonFilter(comparison=ComparisonType.GREATER_THAN_EQUAL, value=1)
                if sort_type == SortType.MARKET_BUY_PRICE
                else None
            ),
        )

        spansh_filters = SpanshFilter(
            reference_system=reference_system,
            filters=StationFilter(
                market=[filters],
                distance=DistanceFilter(min=0, max=maximum_distance),
                type=SimpleFilter(value=["Drake-Class Carrier"], logic="NOT"),
                market_updated_at=ComparisonFilter(
                    comparison=ComparisonType.APPROX, value=["now-7d", "now"]
                ),
                has_large_pad=SimpleFilter(value=True),
            ),
            sort=[
                SortFilter(
                    type=sort_type,
                    name=item_name,
                    direction=(
                        Direction.ASC
                        if sort_type == SortType.MARKET_BUY_PRICE
                        else Direction.DESC
                    ),
                )
            ],
        ).model_dump(mode="json", by_alias=True, exclude_none=True)

        response = self.client.post(STATION_SEARCH_URL, json=spansh_filters)
        response.raise_for_status()

        stations = [
            Station(
                id=station["id"],
                name=station["name"],
                system_name=station["system_name"],
                distance=station["distance"],
                market=station.get("market"),
            )
            for station in response.json()["results"]
        ]

        return {
            "stations": [
                {
                    "name": station.name,
                    "system": station.system_name,
                    "distance": station.distance,
                    "desired_item": self._filter_out_item_from_stations_and_normalize(
                        station.market, item_name
                    ),
                }
                for station in stations
                if station.market is not None
                and item_name in [item.commodity for item in station.market]
            ]
        }

    def get_ship_prices_around_reference_system(
        self,
        ship_name: str,
        reference_system: str,
        maximum_distance: float = 50.0,
    ) -> dict:
        spansh_filters = SpanshFilter(
            reference_system=reference_system,
            filters=StationFilter(
                ships=[ShipFilter(name=SimpleFilter(value=[ship_name]))],
                distance=DistanceFilter(min=0, max=maximum_distance),
                type=SimpleFilter(value=["Drake-Class Carrier"], logic="NOT"),
                shipyard_updated_at=ComparisonFilter(
                    comparison=ComparisonType.APPROX, value=["now-7d", "now"]
                ),
                has_large_pad=SimpleFilter(value=True),
            ),
            sort=[SortFilter(type=SortType.DISTANCE, direction=Direction.ASC)],
        ).model_dump(mode="json", by_alias=True, exclude_none=True)

        response = self.client.post(STATION_SEARCH_URL, json=spansh_filters)
        response.raise_for_status()

        stations = []
        for result in response.json()["results"]:
            station = Station(**result)
            ship = next(
                (ship for ship in station.ships or [] if ship.name == ship_name), None
            )
            if ship is not None:
                stations.append(
                    {
                        "name": station.name,
                        "system": station.system_name,
                        "distance": station.distance,
                        "shipyard_updated_at": station.shipyard_updated_at,
                        "ship": {"name": ship.name, "price": ship.price},
                    }
                )
        return {"stations": stations}

    def get_market(
        self, system_name: str, station_name: str
    ) -> list[StationMarketItem]:
        if not system_name or not station_name:
            raise ValueError("system_name and station_name must not be empty")

        response = self.client.post(
            STATION_SEARCH_URL,
            json={
                "filters": {
                    "name": {"value": station_name},
                    "system_name": {"value": system_name},
                },
                "sort": [],
                "size": 5,
                "page": 0,
            },
        )
        response.raise_for_status()
        data = response.json()
        results = data["results"]
        if not results:
            raise ValueError(f"Station '{station_name}' not found in '{system_name}'")

        station = next(
            (
                station
                for station in results
                if station["name"] == station_name
                and station["system_name"] == system_name
            ),
            None,
        )

        if station is None:
            raise ValueError(f"Station '{station_name}' not found in '{system_name}'")

        market = station.get("market")
        if market is None:
            raise ValueError(
                f"No market data for station '{station_name}' in '{system_name}'"
            )
        return [StationMarketItem(**item) for item in market]

    def _filter_out_item_from_stations_and_normalize(
        self, market: list[StationMarketItem], item_name: str
    ) -> dict:
        item = next(item for item in market if item.commodity == item_name)

        if item is None:
            raise ValueError(
                f"Item {item_name} not found in market. This is internal MCP error, it should have been filtered out earlier."
            )
        return {
            "name": item.commodity,
            "buy_price": item.buy_price,
            "sell_price": item.sell_price,
            "demand": item.demand,
            "supply": item.supply,
        }


if __name__ == "__main__":
    client = SpanshClient()
    result = client.get_item_prices_around_reference_system("Gold", "Alpha Centauri")
    print(result)
