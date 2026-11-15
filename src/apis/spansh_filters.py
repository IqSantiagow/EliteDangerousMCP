from enum import StrEnum
from typing import Self

from pydantic import (
    BaseModel,
    Field,
    field_serializer,
    field_validator,
    model_serializer,
    model_validator,
)


class SortType(StrEnum):
    MARKET_SELL_PRICE = "market_sell_price"
    MARKET_BUY_PRICE = "market_buy_price"
    DISTANCE = "distance"


class ComparisonType(StrEnum):
    LESS_THAN = "<"
    LESS_THAN_EQUAL = "<="
    EQUAL = "="
    GREATER_THAN_EQUAL = ">="
    GREATER_THAN = ">"
    APPROX = "<=>"


class Direction(StrEnum):
    ASC = "asc"
    DESC = "desc"


class SortFilter(BaseModel):
    type: SortType
    name: str | None = None  # commodity name; not used when sorting by distance
    direction: Direction

    @model_validator(mode="after")
    def validate_name(self) -> Self:
        if self.type != SortType.DISTANCE and self.name is None:
            raise ValueError("name is required when sorting by market price")
        return self

    @model_serializer
    def serialize(self) -> dict:
        if self.type == SortType.DISTANCE:
            return {"distance": {"direction": self.direction}}
        return {
            self.type.value: [{"name": self.name, "direction": self.direction}],
        }


class ComparisonFilter(BaseModel):
    comparison: ComparisonType
    value: int | float | list[int | float | str]

    @model_validator(mode="after")
    def validate_value(self) -> Self:
        value = self.value
        if isinstance(value, list):
            if self.comparison != ComparisonType.APPROX:
                raise ValueError(
                    "value must be a number or check approximation type filtering"
                )
            if len(value) != 2:
                raise ValueError(
                    "value must have 2 elements for approximation type filtering"
                )
            if any(v < 0 for v in value if isinstance(v, (int, float))):
                raise ValueError(
                    "value must have non-negative elements for approximation type filtering"
                )

        if isinstance(value, int | float):
            if self.comparison == ComparisonType.APPROX:
                raise ValueError(
                    "value must be a list for approximation type filtering"
                )
            if value < 0:
                raise ValueError(
                    "value must be non-negative for non-approximation type filtering"
                )

        return self


class MarketFilter(BaseModel):
    item: str = Field(serialization_alias="name")
    supply: ComparisonFilter | None = None
    demand: ComparisonFilter | None = None
    buy_price: ComparisonFilter | None = None

    @field_validator("supply", "demand", "buy_price")
    @classmethod
    def validate_quantity(
        cls,
        value: ComparisonFilter | None,
    ) -> ComparisonFilter | None:
        if value is None:
            return None
        if isinstance(value.value, (int, float)):
            return value.model_copy(update={"value": max(value.value, 1)})
        return value


class DistanceFilter(BaseModel):
    min: float = 0.0
    max: float = 50.0

    @field_serializer("min", "max")
    def serialize_distance(self, value: float) -> str:
        return str(int(value)) if value.is_integer() else str(value)


class SimpleFilter(BaseModel):
    value: bool | int | float | str | list
    logic: str | None = None


class ShipFilter(BaseModel):
    name: SimpleFilter


class StationFilter(BaseModel):
    market: list[MarketFilter] | None = None
    ships: list[ShipFilter] | None = None
    distance: DistanceFilter | None = None
    type: SimpleFilter | None = None
    market_updated_at: ComparisonFilter | None = None
    shipyard_updated_at: ComparisonFilter | None = None
    has_large_pad: SimpleFilter | None = None

    @model_validator(mode="after")
    def validate_exactly_one_search_target(self) -> Self:
        if (self.market is None) == (self.ships is None):
            raise ValueError("exactly one of market or ships must be set")
        return self


class SpanshFilter(BaseModel):
    size: int = 5
    page: int = 0
    reference_system: str | None = None
    filters: StationFilter
    sort: list[SortFilter]
