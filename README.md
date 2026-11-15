# Elite Dangerous MCP

A small [MCP](https://modelcontextprotocol.io) server that gives any AI agent
access to Elite Dangerous star system data from [EDSM](https://www.edsm.net)
and station market data from [Spansh](https://spansh.co.uk), so players can ask
their agent about the galaxy while they play.

It is also a stepping stone: the plan is to bring this server into
[EDCeleste](https://github.com/IqSantiagow/EDCeleste), a personal LLM-powered
copilot for Elite Dangerous.

## Tools

| Tool | Description |
|------|-------------|
| `get_distance_between_systems` | Distance in light years between two systems |
| `get_system_info` | Allegiance, government, economy, population and more |
| `get_system_stations` | Stations in a system |
| `get_system_factions` | Factions in a system |
| `get_supported_commodities` | Commodity names accepted by station searches |
| `find_best_selling_station` | Nearby stations buying a commodity, sorted by sell price |
| `find_best_buying_station` | Nearby stations selling a commodity, sorted by buy price |
| `compare_station_markets` | Profitable trades between two stations for a given cargo capacity |

Systems are looked up by exact name (e.g. `Sol`, `Colonia`). Unknown systems
and systems without known coordinates return an error message. Station searches
use exact commodity and system names, default to a 50 light-year radius and a
500-unit demand or supply threshold, and return up to five stations.
Station searches exclude fleet carriers and require a large landing pad and
market data updated within the last seven days. Market comparisons retrieve
both markets from Spansh using exact system and station names and limit
quantities by cargo capacity, source supply, and destination demand.

## Setup

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run server.py
```

The server speaks MCP over stdio. To use it in an MCP client, add it to the
client's configuration, for example:

```json
{
  "mcpServers": {
    "elite-dangerous": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/Elite Dangerous MCP", "server.py"]
    }
  }
}
```

## Tests

```bash
uv run --group dev pytest
```

Tests run offline against fake responses. To also run the tests against the
live EDSM API, set `EDSM_LIVE=1`.

## Layout

- `server.py` - MCP tool definitions
- `src/edsm/edsm.py` - `EdsmClient`, a thin EDSM API client (accepts an injected
  `requests.Session` for testing)
- `src/apis/spansh.py` - `SpanshClient` for nearby station market searches
- `src/apis/spansh_filters.py` - Spansh market search filters
- `src/models/models.py` - Pydantic models for Spansh station data
- `tests/` - offline and live tests

## Data

System data comes from [EDSM](https://www.edsm.net) and station market data
comes from [Spansh](https://spansh.co.uk). Results are only as complete and
current as the upstream crowd-sourced data.
