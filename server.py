from fastmcp import FastMCP

from src.edsm.edsm import EdsmClient

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


if __name__ == "__main__":
    mcp.run()
