from fastmcp import FastMCP

from src.apis.edsm import EdsmClient

mcp = FastMCP("Elite Dangerous MCP")
edsm = EdsmClient()


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
def get_item_prices(
    item_name: str,
    reference_system: str,
    maximum_distance: float = 50.0,
    demand: int = 500,
    looking_for_buy: bool = False,
) -> dict:
    """Search Spansh station markets for a commodity near a star system.

    Provide the exact commodity and reference system names. `maximum_distance` is
    the search radius in light-years, and `demand` is the minimum quantity
    threshold (both default to 50 light-years and 500 units, respectively).
    With `looking_for_buy=False` (default), find stations that will buy the
    commodity: demand must meet the threshold, and results are sorted by sell
    price descending. With `looking_for_buy=True`, find stations selling the
    commodity: supply must meet the threshold, and results are sorted by buy
    price ascending.
    The response is Spansh JSON, limited to five stations with market data updated
    in the last seven days; fleet carriers are excluded.
    """
    from src.apis.spansh import SpanshClient

    client = SpanshClient()
    return client.get_item_prices(
        item_name=item_name,
        reference_system=reference_system,
        maximum_distance=maximum_distance,
        demand=demand,
        looking_for_buy=looking_for_buy,
    )


if __name__ == "__main__":
    mcp.run()
