import pytest

from src.apis.spansh_filters import SpanshMarketFilters


@pytest.mark.parametrize(
    "buying,expected_market,expected_sort_key,expected_direction",
    [
        (
            False,
            {"name": "Gold", "demand": {"comparison": ">=", "value": 500}},
            "market_sell_price",
            "desc",
        ),
        (
            True,
            {
                "name": "Gold",
                "supply": {"comparison": ">=", "value": 500},
                "buy_price": {"comparison": ">=", "value": 1},
            },
            "market_buy_price",
            "asc",
        ),
    ],
)
def test_market_filters_match_buy_or_sell_direction(
    buying, expected_market, expected_sort_key, expected_direction
):
    filters = SpanshMarketFilters(
        reference_system="Sol",
        item="Gold",
        buying=buying,
    ).to_dict()

    assert filters["filters"]["market"] == expected_market
    assert filters["sort"] == [
        {
            expected_sort_key: [
                {"name": "Gold", "direction": expected_direction}
            ]
        }
    ]
