class SpanshMarketFilters:
    def __init__(
        self,
        reference_system: str,
        item: str,
        maximum_distance: float = 50.0,
        demand: int = 500,
        include_fleet_carriers: bool = False,
        large_pad: bool = False,
        buying: bool = False,
    ):
        self.reference_system = reference_system
        self.item = item
        self.maximum_distance = maximum_distance
        self.demand = demand
        self.include_fleet_carriers = include_fleet_carriers
        self.large_pad = large_pad
        self.buying = buying

    def to_dict(self) -> dict:
        return {
            "filters": {
                "market": {
                    "name": self.item,
                    "demand" if not self.buying else "supply": {
                        "comparison": ">=",
                        "value": self.demand,
                    },
                    **(
                        {
                            "buy_price": {
                                "comparison": ">=",
                                "value": 1,
                            }
                        }
                        if self.buying
                        else {}
                    ),
                },
                "distance": {"min": 0, "max": self.maximum_distance},
                "demand": self.demand,
                **(
                    {"type": {"value": ["Drake-Class Carrier"], "logic": "NOT"}}
                    if not self.include_fleet_carriers
                    else {}
                ),
                "has_large_pad": {"value": self.large_pad},
                "market_updated_at": {"comparison": "<=>", "value": ["now-7d", "now"]},
            },
            "sort": [
                {
                    f"market_{'buy' if self.buying else 'sell'}_price": [
                        {
                            "name": self.item,
                            "direction": "asc" if self.buying else "desc",
                        }
                    ]
                }
            ],
            "reference_system": self.reference_system,
            "size": 5,
            "page": 0,
        }
