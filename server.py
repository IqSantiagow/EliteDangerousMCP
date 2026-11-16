from typing import Literal

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
def get_supported_station_names() -> dict[str, list[str]]:
    """Get the ship, module and service names accepted by `find_station`."""
    from src.models.models import MODULES, SERVICES, SHIPS

    return {"ships": list(SHIPS), "modules": list(MODULES), "services": list(SERVICES)}


@mcp.tool
def find_station(
    search_for: Literal["ships", "modules", "services"],
    reference_system: str,
    names: list[str],
    maximum_distance: float = 50.0,
    module_class: int | None = None,
    rating: str | None = None,
) -> dict:
    """Find the nearest stations that have everything in `names`.

    `search_for` selects what `names` are: "ships" (a shipyard sells them),
    "modules" (outfitting sells them) or "services" (e.g. ["Repair", "Refuel"]
    for an emergency stop). A station is returned only if it has ALL the names.
    Names must match `get_supported_station_names` exactly; unknown names fail
    with an error. `module_class` (e.g. 5) and `rating` (e.g. "A") apply to every
    module in `names` and are allowed only for "modules"; leave them out for any
    class or rating.

    Provide the exact reference system name; `maximum_distance` is the search
    radius in light-years. Results are sorted by distance and include prices
    (ships, modules) or `distance_to_arrival` (services), plus when the shipyard
    or outfitting data was last updated. The search returns up to five stations
    with large pads; fleet carriers are excluded. Ship and module data must be
    updated within the last seven days; service data has no timestamp.
    """
    if not names:
        raise ValueError("names: provide at least one name")
    if search_for != "modules" and (module_class is not None or rating is not None):
        raise ValueError("module_class and rating are allowed only for modules")

    if search_for == "ships":
        return spansh.get_ship_prices_around_reference_system(
            ship_names=names,
            reference_system=reference_system,
            maximum_distance=maximum_distance,
        )
    if search_for == "modules":
        return spansh.get_module_prices_around_reference_system(
            module_names=names,
            reference_system=reference_system,
            maximum_distance=maximum_distance,
            module_class=module_class,
            rating=rating,
        )
    return spansh.get_service_stations_around_reference_system(
        services=names,
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
