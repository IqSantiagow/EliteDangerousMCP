# Elite Dangerous MCP

A small [MCP](https://modelcontextprotocol.io) server that gives any AI agent
access to Elite Dangerous star system data from [EDSM](https://www.edsm.net),
so players can ask their agent about the galaxy while they play.

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

Systems are looked up by exact name (e.g. `Sol`, `Colonia`). Unknown systems
and systems without known coordinates return an error message.

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
- `tests/` - offline and live tests

## Data

All data comes from [EDSM](https://www.edsm.net) and is only as complete as
EDSM's crowd-sourced database.
