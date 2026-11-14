from unittest.mock import Mock

import pytest

from src.apis.spansh import SpanshClient


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
