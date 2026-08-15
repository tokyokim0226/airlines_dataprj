from __future__ import annotations

from datetime import datetime


def validate_airport_code(value: str, field_name: str) -> str:
    # Keep airport codes in one predictable format, like "LAX" or "JFK".
    if len(value) != 3 or not value.isalpha() or not value.isupper():
        raise ValueError(f"{field_name} must be a 3-letter uppercase airport code")
    return value


def validate_aware_datetime(value: datetime, field_name: str) -> datetime:
    # Timezone-aware datetimes prevent confusing local-time comparisons later.
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value


def validate_currency(value: str) -> str:
    # Currency codes follow the common 3-letter format, like "USD" or "KRW".
    if len(value) != 3 or not value.isalpha() or not value.isupper():
        raise ValueError("currency must be a 3-letter uppercase currency code")
    return value


def validate_airport_group(values: tuple[str, ...], field_name: str) -> None:
    if not values:
        raise ValueError(f"{field_name} must include at least one airport")
    for airport_code in values:
        validate_airport_code(airport_code, field_name)


def validate_travel_class(value: str) -> str:
    if value not in {"economy", "business"}:
        raise ValueError("travel_class must be economy or business")
    return value
