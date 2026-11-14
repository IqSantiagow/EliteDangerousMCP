import httpx

from src.models.models import COMMODITIES, Station, StationMarketItem

STATION_SEARCH_URL = "https://spansh.co.uk/api/stations/search"
from spansh_filters import SpanshMarketFilters


class SpanshClient:
    def __init__(self, client: httpx.Client | None = None):
        self.client = client or httpx.Client()

    def get_item_prices(
        self,
        item_name: str,
        reference_system: str,
        maximum_distance: float = 50.0,
        demand: int = 500,
        looking_for_buy: bool = False,
    ) -> dict:
        for name, value in (
            ("item_name", item_name),
            ("reference_system", reference_system),
            ("maximum_distance", maximum_distance),
            ("demand", demand),
            ("looking_for_buy", looking_for_buy),
        ):
            if value is None:
                raise TypeError(f"{name} must not be None")

        if item_name not in COMMODITIES:
            raise ValueError(f"Unknown commodity: {item_name}")

        filters = SpanshMarketFilters(
            reference_system=reference_system,
            item=item_name,
            maximum_distance=maximum_distance,
            demand=demand,
            buying=looking_for_buy,
        ).to_dict()

        response = self.client.post(STATION_SEARCH_URL, json=filters)
        response.raise_for_status()

        stations = [Station(**station) for station in response.json()["results"]]

        return {
            "stations": [
                {
                    "name": station.name,
                    "system": station.system_name,
                    "distance": station.distance,
                    "desired_item": self._filter_out_item_from_stations(
                        station.market, item_name
                    ),
                }
                for station in stations
                if station.market is not None
                and item_name in [item.commodity for item in station.market]
            ]
        }

    def _filter_out_item_from_stations(
        self, market: list[StationMarketItem], item_name: str
    ) -> StationMarketItem:
        return next(item for item in market if item.commodity == item_name)


if __name__ == "__main__":
    client = SpanshClient()
    result = client.get_item_prices("Gold", "Sol")
    print(result)
