from unittest.mock import Mock

import pytest

from src.apis.spansh import SpanshClient


def station(market):
    return {
        "id": "1",
        "name": "Jameson Memorial",
        "system_name": "Shinrarta Dezhra",
        "distance": 0.0,
        "market": market,
    }


@pytest.mark.parametrize(
    ("looking_for_buy", "expected_market_key", "expected_sort_key", "expected_item"),
    [
        (
            False,
            "demand",
            "market_sell_price",
            {"name": "Gold", "sell_price": 2345, "demand": 600},
        ),
        (
            True,
            "supply",
            "market_buy_price",
            {"name": "Gold", "buy_price": 1234, "supply": 700},
        ),
    ],
)
def test_get_item_prices_normalizes_market_data(
    looking_for_buy,
    expected_market_key,
    expected_sort_key,
    expected_item,
):
    http_client = Mock()
    response = Mock()
    response.json.return_value = {
        "results": [
            station(
                [
                    {
                        "buy_price": 1234,
                        "category": "Metals",
                        "commodity": "Gold",
                        "demand": 600,
                        "sell_price": 2345,
                        "supply": 700,
                    },
                    {
                        "buy_price": 10,
                        "category": "Metals",
                        "commodity": "Silver",
                        "demand": 20,
                        "sell_price": 30,
                        "supply": 40,
                    },
                ]
            ),
            station(None),
            station(
                [
                    {
                        "buy_price": 10,
                        "category": "Metals",
                        "commodity": "Silver",
                        "demand": 20,
                        "sell_price": 30,
                        "supply": 40,
                    }
                ]
            ),
        ]
    }
    http_client.post.return_value = response

    result = SpanshClient(client=http_client).get_item_prices(
        item_name="Gold",
        reference_system="Sol",
        looking_for_buy=looking_for_buy,
    )

    assert result == {
        "stations": [
            {
                "name": "Jameson Memorial",
                "system": "Shinrarta Dezhra",
                "distance": 0.0,
                "desired_item": expected_item,
            }
        ]
    }
    response.raise_for_status.assert_called_once_with()
    payload = http_client.post.call_args.kwargs["json"]
    assert expected_market_key in payload["filters"]["market"]
    assert expected_sort_key in payload["sort"][0]


@pytest.mark.parametrize(
    "parameter",
    [
        "item_name",
        "reference_system",
        "maximum_distance",
        "demand",
        "looking_for_buy",
    ],
)
def test_get_item_prices_rejects_none_parameters(parameter):
    arguments = {
        "item_name": "Gold",
        "reference_system": "Sol",
        "maximum_distance": 50.0,
        "demand": 500,
        "looking_for_buy": False,
    }
    arguments[parameter] = None
    http_client = Mock()

    with pytest.raises(TypeError, match=f"{parameter} must not be None"):
        SpanshClient(client=http_client).get_item_prices(**arguments)

    http_client.post.assert_not_called()
