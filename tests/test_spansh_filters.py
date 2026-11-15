import pytest
from pydantic import ValidationError

from src.apis.spansh_filters import ComparisonFilter, MarketFilter, SortFilter, SortType, Direction


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
    filters = MarketFilter.model_validate({
        "item": "Gold",
        **({"supply": {"comparison": ">=", "value": 500},
            "buy_price": {"comparison": ">=", "value": 1}}
           if buying else {"demand": {"comparison": ">=", "value": 500}}),
    })
    sort = SortFilter(
        type=SortType(expected_sort_key),
        name="Gold",
        direction=Direction(expected_direction),
    )

    assert filters.model_dump(by_alias=True, exclude_none=True) == expected_market
    assert sort.model_dump(mode="json") == {
        expected_sort_key: [{"name": "Gold", "direction": expected_direction}]
    }


def test_market_filters_are_a_pydantic_model():
    filters = MarketFilter(item="Gold")

    assert filters.model_dump() == {
        "item": "Gold",
        "supply": None,
        "demand": None,
        "buy_price": None,
    }


@pytest.mark.parametrize("field", ["supply", "demand", "buy_price"])
@pytest.mark.parametrize(
    "value, expected", [(0, 1), (0.5, 1), (1, 1), (2.5, 2.5)]
)
def test_market_numeric_values_are_at_least_one(field, value, expected):
    quantity = ComparisonFilter.model_validate({"comparison": ">=", "value": value})
    filters = MarketFilter.model_validate({"item": "Gold", field: quantity})

    assert getattr(filters, field).value == expected
    assert quantity.value == value


@pytest.mark.parametrize("field", ["supply", "demand", "buy_price"])
def test_market_fields_preserve_approximate_ranges(field):
    filters = MarketFilter.model_validate({
        "item": "Gold", field: {"comparison": "<=>", "value": [0, 5]}
    })

    assert getattr(filters, field).value == [0, 5]


@pytest.mark.parametrize(
    "data",
    [
        {"comparison": ">=", "value": -1},
        {"comparison": ">=", "value": [1, 5]},
        {"comparison": "<=>", "value": 1},
        {"comparison": "<=>", "value": [1]},
        {"comparison": "<=>", "value": [-1, 5]},
        {"comparison": "invalid", "value": 1},
        {"value": 1},
    ],
)
def test_comparison_rejects_invalid_values(data):
    with pytest.raises(ValidationError):
        ComparisonFilter.model_validate(data)


def test_comparison_accepts_timestamp_range():
    comparison = ComparisonFilter.model_validate({
        "comparison": "<=>", "value": ["now-7d", "now"]
    })
    assert comparison.value == ["now-7d", "now"]
