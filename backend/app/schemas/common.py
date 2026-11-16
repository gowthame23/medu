from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Annotated, Optional
from pydantic import BaseModel, BeforeValidator, PlainSerializer, ConfigDict


def validate_money(v: Any) -> Decimal:
    """
    Validates monetary values:
    - Never accepts float
    - Accepts str, int, Decimal
    - Rejects more than 2 decimal places
    """
    if isinstance(v, float):
        raise ValueError("Floats are strictly forbidden for financial calculations. Use string or Decimal.")
    if isinstance(v, (str, int, Decimal)):
        try:
            d = Decimal(str(v))
        except Exception:
            raise ValueError(f"Invalid monetary decimal format: {v}")
        # Check decimal places
        sign, digits, exponent = d.as_tuple()
        if exponent < -2:
            raise ValueError(f"Monetary values cannot have more than 2 decimal places: {v}")
        return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    raise ValueError(f"Unsupported money type: {type(v)}")


def serialize_money(v: Decimal) -> str:
    """Serializes Decimal as fixed 2-decimal string e.g. '1499.00'."""
    return f"{v:.2f}"


Money = Annotated[
    Decimal,
    BeforeValidator(validate_money),
    PlainSerializer(serialize_money, return_type=str, when_used="json-unless-none")
]


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
    )
