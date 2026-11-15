from fastmcp import FastMCP

from src.apis.edsm import EdsmClient
from src.apis.spansh import SpanshClient
from src.apis.spansh_filters import SortType

mcp = FastMCP("Elite Dangerous MCP")
edsm = EdsmClient()
spansh = SpanshClient()


@mcp.tool
def get_distance_between_systems(from_system: str, to_system: str) -> float:
    """Distance in light years between two Elite Dangerous star systems,
    by exact system name, e.g. from_system="Sol", to_system="Colonia".
    Fails with an error message if a system is unknown to EDSM
    or has no known coordinates."""
    return edsm.get_distance(from_system, to_system)


@mcp.tool
def get_system_info(system: str) -> dict:
    """Get detailed information about an Elite Dangerous star system by exact system name.
    Fails with an error message if the system is unknown to EDSM."""
    return edsm.get_system_info(system)


@mcp.tool
def get_system_stations(system: str) -> list[dict]:
    """Get a list of stations in an Elite Dangerous star system by exact system name.
    Fails with an error message if the system is unknown to EDSM."""
    return edsm.get_system_stations(system)


@mcp.tool
def get_system_factions(system: str) -> list[dict]:
    """Get a list of factions in an Elite Dangerous star system by exact system name.
    Fails with an error message if the system is unknown to EDSM."""
    return edsm.get_system_factions(system)


@mcp.tool
def get_supported_commodities() -> list[str]:
    """Get a list of all supported commodities for Spansh market searches."""
    from src.models.models import COMMODITIES

    return list(COMMODITIES)


@mcp.tool
def find_best_selling_station(
    item_name: str,
    reference_system: str,
    maximum_distance: float = 50.0,
    demand: int = 500,
) -> dict:
    """Find a nearby station to sell a commodity to.

    Provide the exact commodity and reference system names. `maximum_distance` is
    the search radius in light-years; `demand` is the minimum station demand.
    Results are sorted by sell price descending. The search returns up to five
    stations with large pads and market data updated in the last seven days;
    fleet carriers are excluded.
    """
    return spansh.get_item_prices_around_reference_system(
        item_name=item_name,
        reference_system=reference_system,
        maximum_distance=maximum_distance,
        demand=demand,
    )


@mcp.tool
def find_best_buying_station(
    item_name: str,
    reference_system: str,
    maximum_distance: float = 50.0,
    demand: int = 500,
) -> dict:
    """Find a nearby station selling a commodity to the pilot.

    Provide the exact commodity and reference system names. `maximum_distance` is
    the search radius in light-years; `demand` is the minimum station supply.
    Results are sorted by buy price ascending. The search returns up to five
    stations with large pads and market data updated in the last seven days;
    fleet carriers are excluded.
    """
    return spansh.get_item_prices_around_reference_system(
        item_name=item_name,
        reference_system=reference_system,
        maximum_distance=maximum_distance,
        demand=None,
        supply=demand,
        sort_type=SortType.MARKET_BUY_PRICE,
    )


@mcp.tool
def find_station_selling_ship(
    ship_name: str,
    reference_system: str,
    maximum_distance: float = 50.0,
) -> dict:
    """Find the nearest stations whose shipyard sells a ship.

    Provide the exact ship name (e.g. "Anaconda") and reference system.
    `maximum_distance` is the search radius in light-years. Results are sorted
    by distance and include the ship price and when the shipyard data was last
    updated. The search returns up to five stations with large pads and
    shipyard data updated in the last seven days; fleet carriers are excluded.
    An unknown ship name returns no stations.
    """
    return spansh.get_ship_prices_around_reference_system(
        ship_name=ship_name,
        reference_system=reference_system,
        maximum_distance=maximum_distance,
    )


@mcp.tool
def compare_station_markets(
    from_system: str, from_station: str, to_system: str, to_station: str, cargo: int
) -> dict:
    """Compare profitable trades between two specified stations.

    Provide exact system and station names and the cargo capacity in tonnes.
    Each result includes prices, profit per tonne, the quantity limited by
    capacity, supply and demand, and the total profit before other costs.
    """
    if cargo <= 0:
        raise ValueError("cargo must be greater than zero")

    source = spansh.get_market(from_system, from_station)
    destination = {
        item.commodity: item for item in spansh.get_market(to_system, to_station)
    }

    price_comparison = {}
    for item in source:
        target = destination.get(item.commodity)
        if (
            target is not None
            and item.buy_price > 0
            and target.sell_price > item.buy_price
        ):
            quantity = min(cargo, item.supply, target.demand)
            if quantity > 0:
                difference = target.sell_price - item.buy_price
                price_comparison[item.commodity] = {
                    "from": item.buy_price,
                    "to": target.sell_price,
                    "difference": difference,
                    "quantity": quantity,
                    "profit": difference * quantity,
                }

    return price_comparison


if __name__ == "__main__":
    mcp.run()
