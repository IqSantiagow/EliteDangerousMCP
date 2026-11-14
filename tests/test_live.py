"""Tests against the live EDSM API. Run only with EDSM_LIVE=1 (skipped by default)."""

import os

import pytest

from src.apis.edsm import EdsmClient

pytestmark = pytest.mark.skipif(
    os.environ.get("EDSM_LIVE") != "1", reason="set EDSM_LIVE=1"
)


@pytest.fixture
def client():
    return EdsmClient()


def test_live_distance_sol_colonia(client):
    assert client.get_distance("Sol", "Colonia") == pytest.approx(22000.47, abs=1)


def test_live_unknown_system(client):
    with pytest.raises(ValueError, match="not found"):
        client.get_system("Nowhere xyz 123")


def test_live_sol_has_stations(client):
    assert client.get_system_stations("Sol")


def test_live_sol_has_factions(client):
    assert client.get_system_factions("Sol")
